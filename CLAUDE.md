# Job Market Pulse

## What this is
A data platform that tracks what skills tech employers are actually asking for across technical roles: SWE, SRE/platform, DE, DA, data science, ML/AI, security, IT/identity, and solutions engineering (taxonomy in `config/roles.yaml`, matched on job title, first match wins). My own target lanes are SRE/platform, DE, DA, security, and IT/identity. It ingests postings daily from public ATS job-board APIs, builds trend tables, and publishes a public dashboard + pipeline status page.

**Mission:** help students and anyone in tech figure out which skills they should actually build, based on what employers are really asking for. The dashboard is for a broad audience, not just me. Design decisions should serve "what should I learn next?"

It is a portfolio project meant to show DE, DA, and SRE skills in one system, and it doubles as my own job-search tool ("postings that match me" alerts). I'm an MSIS student (UMD, graduating May 2027) with a background in cloud infrastructure and identity (Intune, Entra ID, Conditional Access), AWS Cloud Practitioner + AI Practitioner certified, studying for AWS SAA and Terraform Associate.

## How to work with me (important)
- I'm using this project to learn. Explain what you change and why, briefly and plainly.
- For core logic (transformations, skill extraction, Terraform design), propose an approach and let me decide before writing large amounts of code.
- Boilerplate, config, and scaffolding: go ahead.
- Talk before building: explain the next step and wait for my OK before multi-step work or anything with effects outside the repo (scheduled tasks, installs, AWS resources). "Ready to work" is not a go-ahead to execute the whole plan.
- I make my own commits. Give me a commit message instead of committing.
- Don't add dependencies or new services without telling me why.
- Keep costs near $0. Flag anything that would cost money on AWS.

## Architecture (target)
```
Greenhouse / Lever / Ashby public job-board APIs
   -> ingest (Python; AWS Lambda on a daily EventBridge schedule)
   -> S3 raw/     raw JSON (gzipped), Hive-style partitions: source=<ats>/date=YYYY-MM-DD/<token>.json.gz
   -> transform   dbt + DuckDB -> clean Parquet tables
   -> S3 curated/ fct_postings, fct_skill_mentions, dim_company
   -> site        Evidence.dev static dashboard on S3 + CloudFront (rebuilt automatically after each daily run)
   +  status page pipeline freshness, success rate, incidents
```
All AWS infrastructure is Terraform (remote state in S3). CI/CD via GitHub Actions using OIDC (no stored AWS keys).
Decided 2026-10-25: go straight to AWS ("path B"), not a laptop-hosted interim. Site on S3 + CloudFront (not Vercel).

## AWS ingestion design (decided 2026-10-25, not built yet)
```
EventBridge Scheduler (daily, America/New_York)
   -> Lambda "ingest" (Python 3.13, one function, ~60s/run)
        -> S3 raw bucket:  raw/source=<ats>/date=YYYY-MM-DD/<token>.json.gz
        -> S3 raw bucket:  runs/date=YYYY-MM-DD/manifest.json   (run summary; feeds the status page later)
        -> CloudWatch Logs + metrics -> alarms -> SNS -> email
Terraform state: its own S3 bucket (versioned, native S3 locking via use_lockfile)
```
- Region: `us-east-1`. Single environment (prod); local runs are dev.
- A: one Lambda loops all companies (fan-out only if it nears the 15-min limit).
- B: `companies.yaml` is bundled in the deployment package (change = commit + deploy).
- C: partial failure does NOT fail the Lambda (that would trigger async retries of all companies). Record failures in the manifest + a `companies_failed` metric and alarm on it. Fail only if everything failed.
- D: separate buckets: `tfstate`, `raw`, `curated`, `site`. Lambda role can write only to `raw`. Block public access, SSE-S3 encryption, versioning on raw.
- E: EventBridge Scheduler (timezone-aware), not EventBridge rules (UTC only).
- F: zip package, deps built with `pip install --platform manylinux2014_x86_64 --only-binary=:all:` (building on Windows, running on Linux).
- G: my access via IAM Identity Center + `aws sso login`; no IAM user access keys. GitHub Actions deploys via OIDC later.
- Code changes: `run.py` writes gzipped files to S3 when `RAW_BUCKET` is set, else local disk; small Lambda handler calling `main()`; run manifest; `boto3` added to local venv only (Lambda runtime includes it). One-time backfill of local snapshots to S3.
- Terraform layout: `infra/bootstrap/` (creates tfstate bucket, local state, run once), `infra/{main,s3,iam,lambda,schedule,alarms}.tf`.
- Alarms (free tier): Lambda errors; companies_failed >= 1; freshness (no successful run in 26h, missing data = breaching).
- Cost guardrails: never put the Lambda in a VPC (NAT gateway ~$32/mo); CloudWatch log retention 30 days; SSE-S3 not KMS CMKs ($1/key/mo); AWS Budgets alerts at $1 and $5 before creating anything else.
- After Lambda has run cleanly for a few days alongside the laptop, disable the Windows task (`Disable-ScheduledTask JobMarketPulse-Ingest`).

## Current state
Local ingestion works; AWS not started.
- 2026-10-25 run: 37/37 companies, 12,885 postings, ~60s. Raw is ~171 MB/day, ~17 MB gzipped (~10x).
- Largest shares: Anduril 19%, Databricks 7%, OpenAI 6%, Stripe 6%. Report skills both as "% of postings" and "% of companies" so big boards don't dominate.
- Pay info present in ~62% of Greenhouse, ~79% of Lever, ~73% of Ashby postings. Ashby has structured `jobs[].compensation`; Greenhouse/Lever need extraction from text.
- History gap: no runs 2026-10-20 to 2026-10-24 (before the scheduler existed).
- Daily schedule (interim until Lambda): Windows Task Scheduler task `JobMarketPulse-Ingest`, daily 2pm, runs `scripts/run_daily.cmd` (venv Python, appends to `logs/ingest.log`). Allowed on battery; StartWhenAvailable catches missed runs. Check with `Get-ScheduledTaskInfo JobMarketPulse-Ingest` (LastTaskResult 0 = ok, 1 = a company failed).
- Dev environment: Windows, PowerShell, VS Code, Python 3.13 venv in `.venv` (created 2026-10-25).
- `config/companies.yaml` — 37 companies (name, ats, token, lanes): original 10 + well-known tech, AI, data/infra, security, DC area. 31 Greenhouse, 4 Ashby, 2 Lever.
- `config/roles.yaml` — role taxonomy for classification (used in week 2)
- dbt Labs merged with Fivetran (2026); its old Greenhouse board `dbtlabsinc` 404s. Fivetran is tracked. Future: `company_aliases` mapping for mergers/renames.
- `ingest/sources/{greenhouse,lever,ashby}.py` — one `fetch(token, session)` per ATS
- `ingest/run.py` — loops companies, writes raw JSON to `data/raw/...`, retries with backoff, 1s delay between requests, logs per-company counts, exits 1 if any company failed (future alerting hook)
- Run from project root: `python -m ingest.run`
- `data/`, `logs/`, `.venv/`, `__pycache__/`, secrets, and Terraform state are gitignored. Data was untracked before the first push, so it was never on GitHub.
- OneDrive sync is off for this folder, so it doesn't upload anything.

## Where we left off (update at the end of each session)
Last session: 2026-10-25
- Done: venv + clean `requirements.txt`; daily Task Scheduler job; Ashby source; expanded to 37 companies (all verified against live APIs).
- Decided: the AWS ingestion design above (all recommendations A–G accepted).
- AWS account: exists, root MFA on. Free-tier type unknown (older 12-month free tier vs newer credit-based plan); check in the Billing console.
- Tools: Terraform CLI and AWS CLI v2 are NOT installed (checked 2026-10-25).
- Next session, in order (explain each step and wait for OK):
  1. Install Terraform and AWS CLI v2 (e.g. `winget`).
  2. Check the account's free-tier type; create AWS Budgets alerts ($1, $5).
  3. Set up IAM Identity Center + a user/permission set for me; `aws configure sso`; stop using root.
  4. Terraform bootstrap (tfstate bucket), then S3 + IAM + Lambda + Scheduler + alarms.
  5. `run.py` S3 writer + manifest + Lambda handler; backfill local snapshots.
- Then: week 2 transforms on the snapshots already collected; dashboard; status page and "matches for me" can follow launch.

## Data sources
- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` (public, no auth)
- Lever: `https://api.lever.co/v0/postings/{token}?mode=json` (public, no auth; respect ~1s between requests; slowest source, ~8s per board)
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true` (public, no auth; verified 2026-10-25). Docs' example shows compensation at top level, but it's actually per job.
- Watch for same-name token collisions when adding companies (e.g. Lever `arcadia` and Ashby `primer` are different companies than expected).
- Do NOT scrape LinkedIn/Indeed (ToS). Known bias: many large DC-area employers use Workday, which has no clean public API — document this in the README rather than hacking around it. Not found on any of the three (2026-10-25): Netflix, HubSpot, Etsy, Confluent, HashiCorp, SentinelOne, Tenable, Cvent, Grammarly, Postman.

## Roadmap (launch target ~mid-Nov 2026)
1. ~~Company list + raw ingestion running daily~~ (done locally; moving to AWS)
2. Terraform: S3 buckets, Lambda + EventBridge for ingestion, CloudWatch alarms + SNS. Do this first so history accumulates in AWS.
3. Clean, dedupe, classify roles, skill extraction via keyword dictionary (`config/skills.yaml`, with aliases like k8s -> Kubernetes). LLM extraction is a later v2.
4. Evidence.dev dashboard on S3 + CloudFront: skill demand, remote share, salary ranges
5. Launch + LinkedIn post with findings
6. After launch: data quality tests, freshness SLO, public status page, "matches for me" alert feed, README, architecture diagram

## Conventions
- Python 3, `requests` + `pyyaml`; keep deps in `requirements.txt`. Regenerate from the venv with `.venv\Scripts\python.exe -m pip freeze`, written as UTF-8 (PowerShell 5.1's `>` writes UTF-16, which breaks pip; use `| Out-File -Encoding ascii requirements.txt`)
- Small modules, type hints, logging (not print)
- Never commit secrets, `.env`, `.terraform/`, or `*.tfstate*`
- Write postmortems in `docs/postmortems/` when the pipeline breaks
