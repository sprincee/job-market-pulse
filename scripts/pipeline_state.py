"""Move the daily build's state between S3 and a fresh machine.

    pull: download the warehouse and only the raw days it still needs
    push: compact the warehouse, export Parquet tables, upload both

Run `pull` before dbt and `push` only after dbt's tests pass, so a failed run
leaves the last good warehouse in place and the next run retries the same days.

    python scripts/pipeline_state.py pull
    python scripts/pipeline_state.py push
"""
import argparse, logging, os, pathlib, re
import boto3, duckdb

ROOT = pathlib.Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "data/warehouse/jmp.duckdb"
COMPACT = WAREHOUSE.with_name("jmp_compact.duckdb")
EXPORTS = ROOT / "build/marts"
STATE_KEY = "warehouse/jmp.duckdb"
MARTS = ["fct_postings", "fct_skill_mentions", "agg_skill_demand", "dim_company"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline_state")


def list_keys(s3, bucket: str, prefix: str) -> list[str]:
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(o["Key"] for o in page.get("Contents", []))
    return keys


def last_loaded_date() -> str | None:
    if not WAREHOUSE.exists():
        return None
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        newest = con.execute("select max(snapshot_date) from stg_postings_daily").fetchone()[0]
    return newest.isoformat() if newest else None


def pull(s3, raw_bucket: str, curated_bucket: str) -> None:
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    if list_keys(s3, curated_bucket, STATE_KEY):
        s3.download_file(curated_bucket, STATE_KEY, str(WAREHOUSE))
        log.info("warehouse downloaded: %.1f MB", WAREHOUSE.stat().st_size / 1e6)
    else:
        log.info("no warehouse yet: dbt will build everything from raw")

    last = last_loaded_date()
    count = 0
    for key in list_keys(s3, raw_bucket, "raw/"):
        date = re.search(r"date=(\d{4}-\d{2}-\d{2})/", key)
        # >= rather than >: DuckDB errors on an empty glob, so keep the newest
        # loaded day on hand. dbt's own date filter still skips it.
        if date and (last is None or date.group(1) >= last):
            path = ROOT / "data" / key
            path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(raw_bucket, key, str(path))
            count += 1
    log.info("downloaded %d raw files (warehouse last loaded: %s)", count, last)


def push(s3, curated_bucket: str) -> None:
    COMPACT.unlink(missing_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    # Rebuilding tables leaves empty blocks behind; copying drops them.
    with duckdb.connect() as con:
        con.execute(f"attach '{WAREHOUSE.as_posix()}' as src (read_only)")
        con.execute(f"attach '{COMPACT.as_posix()}' as dst")
        con.execute("copy from database src to dst")
        for table in MARTS:
            con.execute(f"copy src.{table} to '{(EXPORTS / table).as_posix()}.parquet' (format parquet, compression zstd)")
    s3.upload_file(str(COMPACT), curated_bucket, STATE_KEY)
    log.info("warehouse uploaded: %.1f MB", COMPACT.stat().st_size / 1e6)
    for table in MARTS:
        s3.upload_file(str(EXPORTS / f"{table}.parquet"), curated_bucket, f"marts/{table}.parquet")
    log.info("exported %d tables", len(MARTS))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["pull", "push"])
    args = p.parse_args()
    s3 = boto3.client("s3")
    if args.action == "pull":
        pull(s3, os.environ["RAW_BUCKET"], os.environ["CURATED_BUCKET"])
    else:
        push(s3, os.environ["CURATED_BUCKET"])


if __name__ == "__main__":
    main()
