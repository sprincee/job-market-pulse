"""Where ingest output goes: S3 when RAW_BUCKET is set (Lambda), else local disk.
Both use the same keys, so data/ mirrors the bucket."""
import os, pathlib


class LocalStore:
    def __init__(self, root: pathlib.Path):
        self.root = root

    def put(self, key: str, body: bytes, content_type: str) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def __str__(self) -> str:
        return str(self.root)


class S3Store:
    def __init__(self, bucket: str):
        import boto3  # lazy: local-disk runs don't need boto3 installed
        self.bucket = bucket
        self.s3 = boto3.client("s3")

    def put(self, key: str, body: bytes, content_type: str) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType=content_type)

    def __str__(self) -> str:
        return f"s3://{self.bucket}"


def make_store(root: pathlib.Path) -> LocalStore | S3Store:
    bucket = os.environ.get("RAW_BUCKET")
    return S3Store(bucket) if bucket else LocalStore(root / "data")
