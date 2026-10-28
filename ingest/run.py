import datetime, gzip, json, sys, time, logging, pathlib
from zoneinfo import ZoneInfo
import requests, yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ingest import metrics
from ingest.sources import ashby, greenhouse, lever
from ingest.storage import make_store

SOURCES = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}
ROOT = pathlib.Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/New_York")  # Lambda's clock is UTC; partition dates are Eastern

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")
log.setLevel(logging.INFO)  # Lambda pre-installs a root handler, which makes basicConfig a no-op

def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "job-market-pulse/0.1 (personal research project)"
    return s

def main() -> dict:
    """Fetch every company, write raw files + a run manifest, return the manifest."""
    companies = yaml.safe_load((ROOT / "config/companies.yaml").read_text())
    started = datetime.datetime.now(TZ)
    today = started.date().isoformat()
    store = make_store(ROOT)
    session = make_session()
    results = []
    log.info("run %s -> %s", today, store)

    for c in companies:
        t0 = time.monotonic()
        entry = {"name": c["name"], "ats": c["ats"], "token": c["token"]}
        try:
            jobs = SOURCES[c["ats"]].fetch(c["token"], session)
            body = gzip.compress(json.dumps(jobs).encode("utf-8"), compresslevel=6)
            store.put(f"raw/source={c['ats']}/date={today}/{c['token']}.json.gz", body, "application/gzip")
            entry |= {"status": "ok", "jobs": len(jobs), "bytes_gz": len(body)}
            log.info("%-14s %4d jobs", c["name"], len(jobs))
        except Exception as e:
            entry |= {"status": "failed", "error": f"{type(e).__name__}: {e}"[:500]}
            log.error("%-14s FAILED: %s", c["name"], e)
        entry["seconds"] = round(time.monotonic() - t0, 2)
        results.append(entry)
        time.sleep(1)  # be polite to the APIs

    ok = [r for r in results if r["status"] == "ok"]
    finished = datetime.datetime.now(TZ)
    manifest = {
        "run_date": today,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "duration_s": round((finished - started).total_seconds(), 1),
        "environment": "lambda" if metrics.in_lambda() else "local",
        "jobs_total": sum(r["jobs"] for r in ok),
        "companies_total": len(results),
        "companies_ok": len(ok),
        "companies_failed": len(results) - len(ok),
        "companies": results,
    }
    # Not caught: a missing manifest should fail the run loudly.
    store.put(f"runs/date={today}/manifest.json", json.dumps(manifest, indent=2).encode("utf-8"), "application/json")
    metrics.publish(manifest["companies_ok"], manifest["companies_failed"], manifest["jobs_total"])

    log.info("done: %d jobs, %d/%d companies ok", manifest["jobs_total"], len(ok), len(results))
    return manifest

if __name__ == "__main__":
    sys.exit(1 if main()["companies_failed"] else 0)
