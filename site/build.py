"""Render the static site from the dbt warehouse into build/site/.

    .venv\\Scripts\\python.exe site\\build.py
    .venv\\Scripts\\python.exe -m http.server 8000 -d build\\site    # preview
"""
import logging, os, pathlib, re, shutil
import duckdb
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
WAREHOUSE = os.environ.get("JMP_DUCKDB_PATH", str(ROOT / "data/warehouse/jmp.duckdb"))
OUT = ROOT / "build/site"
SITE_URL = "https://d1ssgqjo1cgaqc.cloudfront.net"  # absolute link previews need; change when the domain is connected
TOP_N = 20
SMALL_SAMPLE = 50  # below this, a role's percentages move a lot on a few postings
MIN_GAP = 5  # percentage points above tech overall for a skill to count as standing out
MIN_MENTIONS = 5  # ...and only if enough roles mention it to mean something
SIGNATURE_N = 4
MAX_JOBS = 25
MAX_JOBS_PER_COMPANY = 3  # so one big board doesn't fill the list
TOP_COMPANIES = 8

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
# How each role reads mid-sentence, where it isn't just the label in lowercase.
ROLES_IN_SENTENCE = {"sre_platform": "SRE and platform", "ml_ai": "machine learning and AI", "it_identity": "IT and identity"}
ENTRY_LABEL = "Internships & entry level"
ENTRY_IN_SENTENCE = "internship and entry-level"
# Skills whose names would be lost in a plain slug.
SKILL_SLUGS = {"C++": "cpp", "C#": "csharp", ".NET": "dotnet"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("site")


def rows(con: duckdb.DuckDBPyConnection, sql: str, *params) -> list[dict]:
    cur = con.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def skill_slug(skill: str) -> str:
    return SKILL_SLUGS.get(skill) or re.sub(r"[^a-z0-9]+", "-", skill.lower().replace(".js", "js").replace("a/b", "ab")).strip("-")


def short_date(day) -> str:
    return day.strftime("%b ") + str(day.day)


def facts_for(con: duckdb.DuckDBPyConnection, where: str = "true", *params) -> dict:
    """Headline numbers for the active tech postings matching a filter."""
    return rows(con, f"""
        select
            count(distinct p.unique_role_key) as roles,
            count(distinct p.company_token) as companies,
            round(100.0 * count(distinct p.unique_role_key) filter (where p.work_mode = 'remote')
                / nullif(count(distinct p.unique_role_key), 0)) as remote_pct,
            count(distinct p.unique_role_key) filter (
                where p.is_new_since_tracking_began
                  and p.first_seen > (select max(last_seen) from fct_postings) - interval 7 day
            ) as new_7d
        from fct_postings as p
        where p.is_active and p.is_tech_role and {where}
    """, *params)[0]


def skills_for(con: duckdb.DuckDBPyConnection, role: str) -> list[dict]:
    return rows(con, """
        select skill, category, pct_of_roles, roles_mentioning, roles_total,
               pct_of_companies, companies_mentioning, companies_total
        from agg_skill_demand
        where role = ?
        order by pct_of_roles desc, skill
    """, role)


def jobs_for(con: duckdb.DuckDBPyConnection, where: str = "true", *params) -> list[dict]:
    """Open postings to link to, newest first: one per unique role, capped per company."""
    jobs = rows(con, f"""
        with unique_roles as (
            select p.title, p.company_token, p.location, p.url, p.first_seen, p.is_new_since_tracking_began,
                   count(*) over (partition by p.unique_role_key) as listings
            from fct_postings as p
            where p.is_active and p.is_tech_role and p.url like 'https://%' and {where}
            qualify row_number() over (partition by p.unique_role_key order by p.first_seen desc, p.posting_key) = 1
        )
        select r.title, c.company_name, r.location, r.url, r.first_seen, r.is_new_since_tracking_began, r.listings
        from unique_roles as r
        join dim_company as c on c.company_token = r.company_token
        qualify row_number() over (partition by r.company_token order by r.first_seen desc, r.title) <= {MAX_JOBS_PER_COMPANY}
        order by r.first_seen desc, c.company_name, r.title
        limit {MAX_JOBS}
    """, *params)
    for job in jobs:
        # Locations can list dozens of places; show the first, and count the rest.
        places = [p.strip() for p in re.split(r";|\|", job["location"] or "") if p.strip()]
        extra = max(len(places), job["listings"]) - 1
        job["place"] = (places[0] if places else "") + (f" + {extra} more" if extra > 0 else "")
        job["seen"] = short_date(job["first_seen"]) if job["is_new_since_tracking_began"] else None
    return jobs


def signature_skills(skills: list[dict], market: list[dict]) -> list[dict]:
    """What sets a role apart: the skills furthest above their share of tech overall.
    Ranked by percentage points, not a ratio. A ratio favors rare skills (2% vs 0.2%
    is 10x), which is the wrong answer to "what should I learn next?". Marks each
    skill with its overall share, and the winners as `high`."""
    overall = {s["skill"]: s["pct_of_roles"] for s in market}
    for s in skills:
        s["overall"] = overall[s["skill"]]
        s["gap"] = whole_pct(s["pct_of_roles"]) - whole_pct(s["overall"])
        s["high"] = False
    candidates = [s for s in skills if s["roles_mentioning"] >= MIN_MENTIONS and s["gap"] >= MIN_GAP]
    signature = sorted(candidates, key=lambda s: s["gap"], reverse=True)[:SIGNATURE_N]
    for s in signature:
        s["high"] = True
    return signature


def whole_pct(value: float) -> int:
    return int(value + .5)


def main() -> None:
    con = duckdb.connect(WAREHOUSE, read_only=True)
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]))
    env.filters["skill_slug"] = skill_slug

    as_of = con.execute("select max(last_seen) from fct_postings").fetchone()[0]
    first_day = con.execute("select min(first_seen) from fct_postings").fetchone()[0]
    days = con.execute("select count(distinct snapshot_date) from stg_postings_daily").fetchone()[0]
    context = {"as_of": as_of.strftime("%B ") + f"{as_of.day}, {as_of.year}", "site_url": SITE_URL,
               "roles": ROLES, "entry_label": ENTRY_LABEL, "small_sample": SMALL_SAMPLE, "top_n": TOP_N,
               "signature_n": SIGNATURE_N, "min_gap": MIN_GAP, "min_mentions": MIN_MENTIONS}

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copy(HERE / "static/style.css", OUT / "style.css")
    shutil.copy(HERE / "static/og.png", OUT / "og.png")

    def render(template: str, path: str, **extra) -> None:
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(env.get_template(template).render(**context, **extra), encoding="utf-8")

    market = skills_for(con, "all_tech")
    cards = []
    for slug, label in ROLES.items():
        skills = skills_for(con, slug)
        signature = signature_skills(skills, market)
        facts = facts_for(con, "p.role = ?", slug)
        render("role.html", f"roles/{slug}/index.html", slug=slug, label=label, facts=facts, skills=skills, signature=signature,
               in_sentence=ROLES_IN_SENTENCE.get(slug, label.lower()), jobs=jobs_for(con, "p.role = ?", slug))
        cards.append({"href": f"/roles/{slug}/", "label": label, "facts": facts, "top": [s["skill"] for s in skills[:3]],
                      "signature": signature[0] if signature else None})

    entry_skills = skills_for(con, "entry_level")
    entry_signature = signature_skills(entry_skills, market)
    entry_facts = facts_for(con, "p.is_entry_level")
    entry_companies = rows(con, """
        select c.company_name, count(distinct p.unique_role_key) as roles
        from fct_postings as p join dim_company as c using (company_token)
        where p.is_active and p.is_entry_level
        group by 1 order by 2 desc, 1 limit 2
    """)
    render("role.html", "entry-level/index.html", slug="entry-level", label=ENTRY_LABEL, facts=entry_facts, skills=entry_skills,
           signature=entry_signature, in_sentence=ENTRY_IN_SENTENCE, jobs=jobs_for(con, "p.is_entry_level"),
           entry_companies=entry_companies)
    cards.append({"href": "/entry-level/", "label": ENTRY_LABEL, "facts": entry_facts, "top": [s["skill"] for s in entry_skills[:3]],
                  "signature": entry_signature[0] if entry_signature else None})

    # Skill pages.
    by_role = {}
    for r in rows(con, f"""
        select role, skill, pct_of_roles, roles_mentioning, roles_total, pct_of_companies, companies_mentioning, companies_total
        from agg_skill_demand
        where role in ({", ".join("?" for _ in ROLES)}) and roles_mentioning >= ?
        order by pct_of_roles desc
    """, *ROLES, MIN_MENTIONS):
        r["label"] = ROLES[r["role"]]
        by_role.setdefault(r["skill"], []).append(r)
    slugs = [skill_slug(s["skill"]) for s in market]
    if len(set(slugs)) != len(slugs):
        raise ValueError("two skills share a page address")
    for s in market:
        name = s["skill"]
        match = "p.posting_key in (select posting_key from fct_skill_mentions where skill = ?)"
        companies = rows(con, """
            select c.company_name, count(distinct m.unique_role_key) as roles
            from fct_skill_mentions as m
            join fct_postings as p on p.posting_key = m.posting_key and p.is_active
            join dim_company as c on c.company_token = m.company_token
            where m.skill = ?
            group by 1 order by 2 desc, 1 limit ?
        """, name, TOP_COMPANIES)
        related = [x for x in market if x["category"] == s["category"] and x["skill"] != name][:8]
        render("skill.html", f"skills/{skill_slug(name)}/index.html", skill=s, facts=facts_for(con, match, name),
               by_role=by_role.get(name, []), companies=companies, related=related, jobs=jobs_for(con, match, name))

    render("404.html", "404.html")
    render("index.html", "index.html", facts=facts_for(con), skills=market, cards=cards)
    render("methodology.html", "methodology/index.html",
           companies=rows(con, "select company_name, ats from dim_company order by lower(company_name)"),
           days=days, first_day=first_day.isoformat(),
           postings=con.execute("select count(*) from fct_postings").fetchone()[0],
           skill_count=con.execute("select count(*) from skills").fetchone()[0])
    log.info("built %s (data as of %s, %d skill pages)", OUT, as_of, len(market))


if __name__ == "__main__":
    main()
