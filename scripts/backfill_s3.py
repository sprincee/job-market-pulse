"""Upload local raw snapshots (data/raw/**) to the raw bucket under the same keys.
Plain .json files are gzipped on the way up. Keys already in the bucket are
skipped, so it's safe to rerun.

    $env:AWS_PROFILE = "jmp"
    .venv\\Scripts\\python.exe scripts\\backfill_s3.py jmp-raw-723951823306 --dry-run
"""
import argparse, gzip, logging, pathlib
import boto3

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("backfill")

def existing_keys(s3, bucket: str) -> set[str]:
    keys = set()
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="raw/"):
        keys.update(o["Key"] for o in page.get("Contents", []))
    return keys

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("bucket")
    p.add_argument("--dry-run", action="store_true", help="list what would be uploaded")
    args = p.parse_args()

    s3 = boto3.client("s3")
    have = existing_keys(s3, args.bucket)
    uploaded = skipped = 0

    for path in sorted((DATA / "raw").rglob("*.json*")):
        key = path.relative_to(DATA).as_posix()
        if key.endswith(".json"):
            key += ".gz"
        if key in have:
            skipped += 1
            continue
        if args.dry_run:
            log.info("would upload %s", key)
        else:
            body = path.read_bytes()
            if path.suffix == ".json":
                body = gzip.compress(body, compresslevel=6)
            s3.put_object(Bucket=args.bucket, Key=key, Body=body, ContentType="application/gzip")
            log.info("uploaded %s (%d KB)", key, len(body) // 1024)
        uploaded += 1

    log.info("%s %d, skipped %d (already in bucket)", "would upload" if args.dry_run else "uploaded", uploaded, skipped)

if __name__ == "__main__":
    main()
