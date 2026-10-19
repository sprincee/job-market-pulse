BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

def fetch(token: str, session) -> list[dict]:
    r = session.get(BASE.format(token=token), params={"content": "true"}, timeout=30)
    r.raise_for_status()
    return r.json()["jobs"]