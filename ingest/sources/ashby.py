BASE = "https://api.ashbyhq.com/posting-api/job-board/{token}"

def fetch(token: str, session) -> list[dict]:
    r = session.get(BASE.format(token=token), params={"includeCompensation": "true"}, timeout=30)
    r.raise_for_status()
    return r.json()["jobs"]
