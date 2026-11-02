"""Write random samples for a human accuracy check of role rules and skill patterns.
Mark the `correct` column y or n; rerun with --score to get the results.

    .venv\\Scripts\\python.exe scripts\\sample_review.py           # writes data/review/*.csv
    .venv\\Scripts\\python.exe scripts\\sample_review.py --score   # reports accuracy
"""
import argparse, collections, csv, pathlib, re
import duckdb

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/review"
ROLES_PER_GROUP = 9
OTHER_TITLES = 19
RANDOM_MENTIONS = 70
TRICKY_MENTIONS = 30
TRICKY = "'Go','R','Excel','Git','Helm','Swift','React','Spark','Rust','LLMs','RAG','Java'"


def write(path: pathlib.Path, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel reads UTF-8
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{path}: {len(rows)} rows")


def sample() -> None:
    OUT.mkdir(exist_ok=True)
    c = duckdb.connect(str(ROOT / "data/warehouse/jmp.duckdb"), read_only=True)
    c.execute("select setseed(0.42)")

    titles = c.execute(f"""
        select role, title from (
            select role, title, row_number() over (partition by role order by hash(title)) as n
            from (select distinct role, title from fct_postings where is_active and is_tech_role)
        ) where n <= {ROLES_PER_GROUP}
        union all
        select * from (
            select distinct 'other' as role, title from fct_postings
            where is_active and role = 'other'
              and regexp_matches(title, '(?i)engineer|developer|scientist|architect|analyst|researcher')
            order by random() limit {OTHER_TITLES}
        )
        order by role
    """).fetchall()
    write(OUT / "titles.csv", ["assigned_role", "title", "correct"], [[r, t, ""] for r, t in titles])

    query = """
        select m.skill, s.pattern, p.title, t.body_text
        from fct_skill_mentions m
        join fct_postings p on p.posting_key = m.posting_key and p.is_active
        join stg_posting_text t on t.posting_key = m.posting_key
        join skills s on s.skill = m.skill
    """
    mentions = c.execute(f"{query} order by random() limit {RANDOM_MENTIONS}").fetchall()
    mentions += c.execute(f"{query} where m.skill in ({TRICKY}) order by random() limit {TRICKY_MENTIONS}").fetchall()
    rows = []
    for skill, pattern, title, body in mentions:
        text = f"{title} {body}"
        m = re.search(pattern, text)
        rows.append([skill, title, text[max(0, m.start() - 80):m.end() + 60] if m else text[:140], ""])
    write(OUT / "skills.csv", ["skill", "title", "context", "correct"], sorted(rows))


def score() -> None:
    for name, group_col in (("titles.csv", "assigned_role"), ("skills.csv", "skill")):
        with open(OUT / name, encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if r["correct"].strip()]
        right = [r for r in rows if re.match(r"(?i)y", r["correct"].strip())]
        print(f"\n{name}: {len(right)}/{len(rows)} correct ({len(right) / max(len(rows), 1):.0%})")
        wrong = collections.Counter(r[group_col] for r in rows if r not in right)
        print("  wrong by group:", dict(wrong.most_common()))
        for r in rows:
            if r not in right:
                print("  ", r[group_col], "|", r["title"][:70])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--score", action="store_true")
    (score if p.parse_args().score else sample)()
