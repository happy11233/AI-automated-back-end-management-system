import json


def dumps_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
