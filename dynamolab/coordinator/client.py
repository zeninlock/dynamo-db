import httpx


def put_to_node(
    node_url: str,
    key: str,
    value: str,
    version: int,
    timeout: float = 1.0,
):
    response = httpx.put(
        f"{node_url}/store/{key}",
        json={
            "value": value,
            "version": version,
        },
        timeout=timeout,
    )

    response.raise_for_status()
    return response.json()


def get_from_node(
    node_url: str,
    key: str,
    timeout: float = 1.0,
):
    response = httpx.get(
        f"{node_url}/store/{key}",
        timeout=timeout,
    )

    if response.status_code == 404:
        return {
            "found": False,
            "record": None,
        }

    response.raise_for_status()

    payload = response.json()

    return {
        "found": True,
        "record": payload["record"],
        "node_id": payload.get("node_id"),
    }


def delete_from_node(
    node_url: str,
    key: str,
    version: int,
    timeout: float = 1.0,
):
    response = httpx.request(
        method="DELETE",
        url=f"{node_url}/store/{key}",
        json={
            "version": version,
        },
        timeout=timeout,
    )

    response.raise_for_status()
    return response.json()