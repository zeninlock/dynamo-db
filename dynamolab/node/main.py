import os

from fastapi import FastAPI, HTTPException

from node.models import DeleteRequest, PutRequest
from node.store import KeyValueStore


NODE_ID = os.getenv("NODE_ID", "node-unknown")

app = FastAPI()
kv = KeyValueStore()


@app.get("/")
def root():
    return {
        "message": "DynamoLab storage node is running",
        "node_id": NODE_ID,
    }


@app.get("/health")
def health():
    return {
        "status": "UP",
        "node_id": NODE_ID,
    }


@app.put("/store/{key}")
def put_key(key: str, request: PutRequest):
    record = kv.put(
        key=key,
        value=request.value,
        version=request.version,
    )

    return {
        "status": "stored",
        "node_id": NODE_ID,
        "record": record,
    }


@app.get("/store/{key}")
def get_key(key: str):
    record = kv.get(key)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Key not found",
        )

    return {
        "node_id": NODE_ID,
        "record": record,
    }


@app.delete("/store/{key}")
def delete_key(key: str, request: DeleteRequest | None = None):
    version = request.version if request is not None else None

    record = kv.delete(
        key=key,
        version=version,
    )

    return {
        "status": "deleted",
        "node_id": NODE_ID,
        "record": record,
    }


@app.get("/debug/keys")
def debug_keys():
    return {
        "node_id": NODE_ID,
        **kv.debug(),
    }