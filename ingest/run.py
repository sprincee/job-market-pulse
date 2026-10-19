import json, sys, time, datetime, logging, pathlib
import requests, yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ingest.sources import greenhouse, lever

SOURCES = {"greenhouse": greenhouse, "lever": lever}
ROOT = pathlib.Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")

def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "job-market-pulse/0.1 (personal research project)"
    return s

def main() -> int:
    companies = yaml.safe_load((ROOT / "config/companies.yaml").read_text())
    today = datetime.date.today().isoformat()
    session = make_session()
    failures, total = [], 0

    for c in companies:
        source = SOURCES[c["ats"]]
        try:
            jobs = source.fetch(c["token"], session)
            out = ROOT / f"data/raw/source={c['ats']}/date={today}"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{c['token']}.json").write_text(json.dumps(jobs))
            total += len(jobs)
            log.info("%-14s %4d jobs", c["name"], len(jobs))
        except Exception as e:
            failures.append(c["name"])
            log.error("%-14s FAILED: %s", c["name"], e)
        time.sleep(1)  # be polite to the APIs

    log.info("done: %d jobs, %d/%d companies ok", total, len(companies) - len(failures), len(companies))
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())