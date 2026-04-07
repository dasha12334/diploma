import json
from typing import Tuple

Share = Tuple[int, int]


def serialize_share(share: Share) -> bytes:
    x, y = share
    payload = {"x": x, "y": str(y)}
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def deserialize_share(data: bytes) -> Share:
    payload = json.loads(data.decode("utf-8"))
    return int(payload["x"]), int(payload["y"])