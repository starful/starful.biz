# Positions CSV (moved)

Position topics are managed in **okadmin** `data/topic_banks/starful.biz/positions.csv`.

## Retired (do not regenerate)

GSC cleanup (2026-07-12) withdrew low/no-signal careers. They live in:

- `app/seo_helpers.py` → `REMOVED_CAREER_SLUGS` (runtime 301 + generator blocklist)
- `scripts/data/retired_positions.csv` (audit copy of names removed from the topic bank)
- `scripts/content_guards.py` (used by `generate_md_guides.py`)

Do **not** re-add those rows to the topic bank unless you also remove them from `REMOVED_CAREER_SLUGS`.
