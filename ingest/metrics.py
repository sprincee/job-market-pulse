"""CloudWatch metrics the alarms watch. Only sent from Lambda, so a laptop run
can't mask a Lambda that never ran. No dimensions: each combination is a
separately billed metric."""
import logging, os

log = logging.getLogger("ingest")
NAMESPACE = "JobMarketPulse"


def in_lambda() -> bool:
    return "AWS_LAMBDA_FUNCTION_NAME" in os.environ  # set by the Lambda runtime


def publish(companies_ok: int, companies_failed: int, postings_total: int) -> None:
    if not in_lambda():
        log.info("metrics skipped (not running in Lambda)")
        return
    try:
        import boto3
        boto3.client("cloudwatch").put_metric_data(Namespace=NAMESPACE, MetricData=[
            {"MetricName": "RunSucceeded", "Value": 1 if companies_ok else 0, "Unit": "Count"},
            {"MetricName": "CompaniesFailed", "Value": companies_failed, "Unit": "Count"},
            {"MetricName": "PostingsTotal", "Value": postings_total, "Unit": "Count"},
        ])
    except Exception:
        # Data is already saved; failing here would retry all companies.
        # If this keeps failing, the freshness alarm fires.
        log.exception("failed to publish metrics")
