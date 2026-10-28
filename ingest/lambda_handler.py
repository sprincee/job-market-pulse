"""Lambda entry point. Partial failures are reported through the manifest and
the CompaniesFailed metric, not by failing: a failed invocation would retry
all companies (decision C). Fail only if nothing worked."""
from ingest.run import main


def handler(event: dict, context) -> dict:
    manifest = main()
    if manifest["companies_ok"] == 0:
        raise RuntimeError(f"all {manifest['companies_total']} companies failed")
    keys = ("run_date", "duration_s", "jobs_total", "companies_ok", "companies_failed")
    return {k: manifest[k] for k in keys}
