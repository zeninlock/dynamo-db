from fastapi import FastAPI, HTTPException
from node.models import PutRequest
from node.store import KeyValueStore

app = FastAPI()

kv = KeyValueStore()


@app.get("/")
def root():
    return {"message": "DynamoLab storage node is running"}


@app.put("/store/{key}")
def put_key(key: str, request: PutRequest):
    record = kv.put(key, request.value)

    return {
        "status": "stored",
        "record": record
    }


@app.get("/store/{key}")
def get_key(key: str):
    record = kv.get(key)

    if record is None:
        raise HTTPException(status_code=404, detail="Key not found")

    return record


@app.delete("/store/{key}")
def delete_key(key: str):
    record = kv.delete(key)

    return {
        "status": "deleted",
        "record": record
    }


@app.get("/debug/keys")
def debug_keys():
    return kv.debug()


@app.get("/health")
def health():
    return {"status": "UP"}