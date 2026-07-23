import hashlib
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from coordinator.client import (
    delete_from_node,
    get_from_node,
    put_to_node,
)
from coordinator.config import NODES, REPLICATION_FACTOR, WRITE_QUORUM, READ_QUORUM


def validate_cluster_config() -> None:
    node_count = len(NODES)

    if node_count == 0:
        raise RuntimeError("The cluster must contain at least one node")

    if REPLICATION_FACTOR < 1:
        raise RuntimeError("Replication factor must be at least 1")

    if REPLICATION_FACTOR > node_count:
        raise RuntimeError(
            "Replication factor cannot exceed the number of physical nodes"
        )

    if WRITE_QUORUM < 1 or WRITE_QUORUM > REPLICATION_FACTOR:
        raise RuntimeError(
            "Write quorum must be between 1 and the replication factor"
        )

    if READ_QUORUM < 1 or READ_QUORUM > REPLICATION_FACTOR:
        raise RuntimeError(
            "Read quorum must be between 1 and the replication factor"
        )


app = FastAPI()


class PutRequest(BaseModel):
    value: str


def current_time_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def stable_hash(text: str) -> int:
    digest = hashlib.md5(text.encode()).hexdigest()
    return int(digest, 16)


def get_replica_nodes(key: str):
    if REPLICATION_FACTOR > len(NODES):
        raise RuntimeError(
            "Replication factor cannot exceed the number of nodes"
        )

    primary_index = stable_hash(key) % len(NODES)
    replicas = []

    for offset in range(REPLICATION_FACTOR):
        node_index = (primary_index + offset) % len(NODES)
        replicas.append(NODES[node_index])

    return replicas

validate_cluster_config()



@app.get("/")
def root():
    return {
        "message": "DynamoLab coordinator is running",
        "replication_factor": REPLICATION_FACTOR,
    }


@app.get("/cluster")
def cluster():
    return {
        "nodes": NODES,
        "node_count": len(NODES),
        "replication_factor": REPLICATION_FACTOR,
        "write_quorum": WRITE_QUORUM,
        "read_quorum": READ_QUORUM,
        "strong_overlap_condition": (
            READ_QUORUM + WRITE_QUORUM > REPLICATION_FACTOR
        ),
    }


@app.get("/placement/{key}")
def placement(key: str):
    replicas = get_replica_nodes(key)

    return {
        "key": key,
        "replicas": replicas,
        "replica_count": len(replicas),
    }


@app.put("/kv/{key}")
def put_key(key: str, request: PutRequest):
    replicas = get_replica_nodes(key)
    version = current_time_ms()

    acknowledgements = []
    failures = []

    for node in replicas:
        try:
            result = put_to_node(
                node_url=node["url"],
                key=key,
                value=request.value,
                version=version,
            )

            acknowledgements.append({
                "node": node["id"],
                "response": result,
            })

        except Exception as error:
            failures.append({
                "node": node["id"],
                "error": str(error),
            })

    acknowledgement_count = len(acknowledgements)

    if acknowledgement_count < WRITE_QUORUM:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Write quorum was not reached",
                "key": key,
                "version": version,
                "required_write_quorum": WRITE_QUORUM,
                "received_acknowledgements": acknowledgement_count,
                "replicas": replicas,
                "acknowledgements": acknowledgements,
                "failures": failures,
            },
        )

    return {
        "status": "write_success",
        "key": key,
        "value": request.value,
        "version": version,
        "replication_factor": REPLICATION_FACTOR,
        "required_write_quorum": WRITE_QUORUM,
        "received_acknowledgements": acknowledgement_count,
        "acknowledgements": acknowledgements,
        "failures": failures,
    }

@app.get("/kv/{key}")
def get_key(key: str):
    replicas = get_replica_nodes(key)

    replica_responses = []
    failures = []

    for node in replicas:
        try:
            result = get_from_node(
                node_url=node["url"],
                key=key,
            )

            replica_responses.append({
                "node": node["id"],
                "result": result,
            })

        except Exception as error:
            failures.append({
                "node": node["id"],
                "error": str(error),
            })

    response_count = len(replica_responses)

    if response_count < READ_QUORUM:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Read quorum was not reached",
                "key": key,
                "required_read_quorum": READ_QUORUM,
                "received_responses": response_count,
                "replicas": replicas,
                "responses": replica_responses,
                "failures": failures,
            },
        )

    found_records = [
        {
            "node": item["node"],
            "record": item["result"]["record"],
        }
        for item in replica_responses
        if item["result"]["found"]
    ]

    if len(found_records) == 0:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Key not found",
                "key": key,
                "required_read_quorum": READ_QUORUM,
                "received_responses": response_count,
            },
        )

    latest = max(
        found_records,
        key=lambda item: item["record"]["version"],
    )

    return {
        "status": "read_success",
        "key": key,
        "replication_factor": REPLICATION_FACTOR,
        "required_read_quorum": READ_QUORUM,
        "received_responses": response_count,
        "selected_node": latest["node"],
        "record": latest["record"],
        "replica_responses": replica_responses,
        "failures": failures,
    }


@app.delete("/kv/{key}")
def delete_key(key: str):
    replicas = get_replica_nodes(key)
    version = current_time_ms()

    acknowledgements = []
    failures = []

    for node in replicas:
        try:
            result = delete_from_node(
                node_url=node["url"],
                key=key,
                version=version,
            )

            acknowledgements.append({
                "node": node["id"],
                "response": result,
            })

        except Exception as error:
            failures.append({
                "node": node["id"],
                "error": str(error),
            })

    acknowledgement_count = len(acknowledgements)

    if acknowledgement_count < WRITE_QUORUM:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Delete quorum was not reached",
                "key": key,
                "version": version,
                "required_write_quorum": WRITE_QUORUM,
                "received_acknowledgements": acknowledgement_count,
                "acknowledgements": acknowledgements,
                "failures": failures,
            },
        )

    return {
        "status": "delete_success",
        "key": key,
        "version": version,
        "required_write_quorum": WRITE_QUORUM,
        "received_acknowledgements": acknowledgement_count,
        "acknowledgements": acknowledgements,
        "failures": failures,
    }