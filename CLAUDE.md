# Job Market Pulse

## What this is
A data platform that tracks what skills tech employers are actually asking for across technical roles: SWE, SRE/platform, DE, DA, data science, ML/AI, security, IT/identity, and solutions engineering (taxonomy in `config/roles.yaml`, matched on job title, first match wins). My own target lanes are SRE/platform, DE, DA, security, and IT/identity. It ingests postings daily from public ATS job-board APIs, builds trend tables, and publishes a public dashboard + pipeline status page.

It is a portfolio project meant to show DE, DA, and SRE skills in one system, and it doubles as my own job-search tool ("postings that match me" alerts). I'm an MSIS student (UMD, graduating May 2027) with a background in cloud infrastructure and identity (Intune, Entra ID, Conditional Access), AWS Cloud Practitioner + AI Practitioner certified, studying for AWS SAA and Terraform Associate.

## How to work with me (important)
- I'm using this project to learn. Explain what you change and why, briefly and plainly.
- For core logic (transformations, skill extraction, Terraform design), propose an approach and let me decide before writing large amounts of code.
- Boilerplate, config, and scaffolding: go ahead.
- Don't add dependencies or new services without telling me why.
- Keep costs near $0. Flag anything that would cost money on AWS.

## Architecture (target)
```
Greenhouse / Lever / Ashby public job-board APIs
   -> ingest (Python; later AWS Lambda on a daily EventBridge schedule)
   -> S3 raw/     raw JSON, Hive-style partitions: source=<ats>/date=YYYY-MM-DD/<token>.json
   -> transform   dbt + DuckDB -> clean Parquet tables
   -> S3 curated/ fct_postings, fct_skill_mentions, dim_company
   -> site        Evidence.dev static dashboard on S3 + CloudFront
   +  status page pipeline freshness, success rate, incidents
```
All AWS infrastructure is Terraform (remote state in S3). CI/CD via GitHub Actions using OIDC (no stored AWS keys).

## Current state
Week 1: local ingestion only. No AWS yet.
- First successful run 2026-10-19: 10/10 companies, 6,171 postings (Anduril ~2.5k and Databricks ~900 are the largest boards).
- Dev environment: Windows, PowerShell, VS Code, Python venv in `.venv`.
- Next up: daily runs to build history, then week 2 (staging models, dedupe, role classification via `config/roles.yaml`, skill extraction).
- `config/companies.yaml` — companies to track (name, ats, token, lanes)
- `config/roles.yaml` — role taxonomy for classification (used in week 2)
- dbt Labs merged with Fivetran (2026); its old Greenhouse board `dbtlabsinc` 404s. Replaced with Vercel. Future: `company_aliases` mapping for mergers/renames.
- `ingest/sources/greenhouse.py`, `ingest/sources/lever.py` — one `fetch(token, session)` per ATS
- `ingest/run.py` — loops companies, writes raw JSON to `data/raw/...`, retries with backoff, 1s delay between requests, logs per-company counts, exits 1 if any company failed (future alerting hook)
- Run from project root: `python -m ingest.run`
- `data/`, `logs/`, `.venv/`, `__pycache__/`, secrets, and Terraform state are gitignored. Data was untracked before the first push, so it was never on GitHub.
- OneDrive sync is off for this folder, so it doesn't upload anything.

## Where we left off (update at the end of each session)
Last session: 2026-10-19
- Done: first ingestion run committed; `.gitignore` filled in; raw data and `__pycache__` removed from the commit.
- Next: schedule daily ingestion with Windows Task Scheduler. The plan:
  - a `scripts/run_daily.cmd` wrapper: cd to the project root, run the venv's `python.exe -m ingest.run`, append output to `logs/ingest.log`;
  - register the task with `Register-ScheduledTask`, daily at 9am, with `-StartWhenAvailable -RunOnlyIfNetworkAvailable -WakeToRun`.
- Open question: `.venv` wasn't found in the project root. Confirm where the venv lives before writing the wrapper.

## Data sources
- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` (public, no auth)
- Lever: `https://api.lever.co/v0/postings/{token}?mode=json` (public, no auth; respect ~1s between requests)
- Ashby: public posting API (add later; verify endpoint in docs first)
- Do NOT scrape LinkedIn/Indeed (ToS). Known bias: many large DC-area employers use Workday, which has no clean public API — document this in the README rather than hacking around it.

## Roadmap (launch target ~Nov 30, 2026)
1. Company list + raw ingestion running daily (start accumulating history ASAP)
2. Clean, dedupe, classify roles (DE/DA/SRE/security), skill extraction via keyword dictionary (`config/skills.yaml`, with aliases like k8s -> Kubernetes). LLM extraction is a later v2.
3. Evidence.dev dashboard: skill demand, remote share, salary ranges (from pay-transparency postings)
4. Terraform: S3 buckets, Lambda + EventBridge, CloudWatch alarms + SNS; data quality tests; freshness SLO; public status page
5. "Matches for me" alert feed, README, architecture diagram
6. Launch + LinkedIn post with findings

## Conventions
- Python 3, `requests` + `pyyaml`; keep deps in `requirements.txt` (`pip freeze > requirements.txt`)
- Small modules, type hints, logging (not print)
- Never commit secrets, `.env`, `.terraform/`, or `*.tfstate*`
- Write postmortems in `docs/postmortems/` when the pipeline breaks