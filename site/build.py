"""Render the static site from the dbt warehouse into build/site/.

    .venv\\Scripts\\python.exe site\\build.py
    .venv\\Scripts\\python.exe -m http.server 8000 -d build\\site    # preview
"""
import logging, os, pathlib, shutil
import duckdb
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WAREHOUSE = os.environ.get("JMP_DUCKDB_PATH", str(ROOT / "data/warehouse/jmp.duckdb"))
OUT = ROOT / "build/site"
TOP_N = 20
SMALL_SAMPLE = 50  # below this, a role's percentages move a lot on a few postings

ROLES = {
    "swe": "Software engineering",
    "sre_platform": "SRE & platform",
    "data_eng": "Data engineering",
    "data_analyst": "Data analysis",
    "data_science": "Data science",
    "ml_ai": "Machine learning & AI",
    "security": "Security",
    "it_identity": "IT & identity",
    "solutions_eng": "Solutions engineering",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("site")


def rows(con: duckdb.DuckDBPyConnection, sql: str, *params) -> list[dict]:
    cur = con.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def role_facts(con: duckdb.DuckDBPyConnection, role: str | None) -> dict:
    """Headline numbers for one role, or for all tech roles when role is None."""
    where = "is_active and is_tech_role" + (" and role = ?" if role else "")
    params = [role] if role else []
    return rows(con, f"""
        select
            count(distinct unique_role_key) as roles,
            count(distinct company_token) as companies,
            round(100.0 * count(distinct unique_role_key) filter (where work_mode = 'remote')
                / nullif(count(distinct unique_role_key), 0)) as remote_pct,
            count(distinct unique_role_key) filter (
                where is_new_since_tracking_began
                  and first_seen > (select max(last_seen) from fct_postings) - interval 7 day
            ) as new_7d
        from fct_postings
        where {where}
    """, *params)[0]


def skills_for(con: duckdb.DuckDBPyConnection, role: str) -> list[dict]:
    return rows(con, """
        select skill, category, pct_of_roles, roles_mentioning, roles_total,
               pct_of_companies, companies_mentioning, companies_total
        from agg_skill_demand
        where role = ?
        order by pct_of_roles desc, skill
    """, role)


def main() -> None:
    con = duckdb.connect(WAREHOUSE, read_only=True)
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]))

    as_of = con.execute("select max(last_seen) from fct_postings").fetchone()[0]
    first_day = con.execute("select min(first_seen) from fct_postings").fetchone()[0]
    days = con.execute("select count(distinct snapshot_date) from stg_postings_daily").fetchone()[0]
    context = {"as_of": as_of.strftime("%B %-d, %Y") if os.name != "nt" else as_of.strftime("%B %#d, %Y"),
               "roles": ROLES, "small_sample": SMALL_SAMPLE, "top_n": TOP_N}

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "roles").mkdir(parents=True)
    shutil.copy(HERE / "static/style.css", OUT / "style.css")

    def render(template: str, path: str, **extra) -> None:
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(template).render(**context, **extra), encoding="utf-8")

    cards = []
    for slug, label in ROLES.items():
        skills = skills_for(con, slug)
        facts = role_facts(con, slug)
        render("role.html", f"roles/{slug}/index.html", slug=slug, label=label, facts=facts, skills=skills)
        cards.append({"slug": slug, "label": label, "facts": facts, "top": [s["skill"] for s in skills[:4]]})

    render("404.html", "404.html")
    render("index.html", "index.html", facts=role_facts(con, None), skills=skills_for(con, "all_tech"), cards=cards)
    render("methodology.html", "methodology/index.html",
           companies=rows(con, "select company_name, ats from dim_company order by lower(company_name)"),
           days=days, first_day=first_day.isoformat(),
           postings=con.execute("select count(*) from fct_postings").fetchone()[0],
           skill_count=con.execute("select count(*) from skills").fetchone()[0])
    log.info("built %s (data as of %s)", OUT, as_of)


if __name__ == "__main__":
    main()
