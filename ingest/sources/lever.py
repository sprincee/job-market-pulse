BASE = "https://api.lever.co/v0/postings/{token}"

def fetch(token: str, session) -> list[dict]:
    r = session.get(BASE.format(token=token), params={"mode": "json"}, timeout=30)
    r.raise_for_status()
    return r.json()