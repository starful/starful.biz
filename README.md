# Starful

| | |
|--|--|
| **Live** | [https://starful.biz](https://starful.biz) |
| **GitHub** | [starful/starful.biz](https://github.com/starful/starful.biz) |
| **Hub ID** | `starful.biz` |
| **GA4** | Property `481809450` · GSC `sc-domain:starful.biz` |
| **GCS** | `starful-biz-assets` (root prefix) · Places: `office`, `company` |

Starful is a FastAPI-based web service for IT career exploration and interview preparation.  
It serves job-specific content from Markdown files, MBTI-based career hubs, and is deployed on Google Cloud Run.

## Overview

- Content-driven architecture using Markdown in `app/contents`
- Server-rendered UI with Jinja2 templates
- JSON index cache at `app/static/json/job_data.json`
- MBTI type hubs (`/mbti`) mapped to career guides
- Production deployment via Cloud Build + Cloud Run

## Tech Stack

- Backend: Python, FastAPI, Uvicorn
- Templating/UI: Jinja2, HTML, CSS
- Content parsing: Markdown, Python JSON/frontmatter-style metadata
- Optional backend integration: Firebase Admin SDK
- Deployment: Docker, Google Cloud Build, Cloud Run, Secret Manager

## Repository Structure

```text
app/
  __init__.py            # FastAPI app entrypoint and routes
  contents/              # Job/career content in Markdown
  templates/             # Jinja2 templates
  static/
    css/                 # Stylesheets
    img/                 # Production images
    json/job_data.json   # Generated content index
scripts/
  build_data.py          # Builds job_data.json from Markdown
  generate_md_guides.py  # AI content generation
  generate_images.py     # Image generation
  resize_images.py       # Image optimization
cloudbuild.yaml          # Cloud Build pipeline
deploy.sh                # End-to-end automation script
```

## Prerequisites

- Python 3.10+ (recommended)
- `pip`
- Google Cloud SDK (`gcloud`) for deployment
- (Optional) `gsutil` for asset sync pipelines

## Environment Variables

Create a local `.env` file in the project root.

Optional:

- `SITE_URL=https://starful.biz` (default is `https://starful.biz`)
- `GEMINI_API_KEY=...` (used by local content generation scripts)

For production, secrets are configured in `cloudbuild.yaml` and injected into Cloud Run using Secret Manager.

## Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the development server:

```bash
uvicorn app:app --reload
```

3. Open:

- Home: `http://127.0.0.1:8000/`
- MBTI: `http://127.0.0.1:8000/mbti`

## Core Routes

- `GET /` - Home page with grouped career cards
- `GET /career/{item_id}` - Career detail page (Markdown-rendered)
- `GET /search?q=...` - Title-based search
- `GET /mbti` - MBTI type index
- `GET /mbti/{TYPE}` - Type hub with recommended careers
- `GET /sitemap.xml` - Dynamic sitemap
- `GET /robots.txt` - Robots policy + sitemap reference

## Content Workflow

1. Add or edit Markdown files in `app/contents`
2. Rebuild the JSON index:

```bash
python3 scripts/build_data.py
```

3. Restart the app (or redeploy) to ensure fresh data is served

## SEO/Indexing Notes

- `sitemap.xml` is generated dynamically at runtime
- `robots.txt` includes an explicit sitemap directive
- Canonical URLs are normalized to `https://starful.biz`

After major URL/content updates, resubmit sitemap in Google Search Console and request indexing for key URLs.

## Deployment

Career thumbnail PNGs are stored on **GCS** (`gs://starful-biz-assets`), not in the Docker image.  
okadmin uploads to GCS take effect immediately without redeploying Cloud Run.

### Docker images

- `Dockerfile.base` — Python + `pip install` (rebuild when `requirements.txt` changes)
- `Dockerfile` — app code only, `FROM starful-web-base`

Cloud Build pulls cached layers from Artifact Registry (`--cache-from`) so code-only deploys skip reinstalling dependencies.

### Recommended (Cloud Build — code only, fast)

```bash
gcloud builds submit --config cloudbuild.yaml
# or
./deploy.sh --deploy-only
```

### Full pipeline (content + GCS image stubs + deploy)

```bash
./deploy.sh --full --with-deploy
```

### Automation Script

You can also run:

```bash
./deploy.sh --deploy-only    # fast: Cloud Run only
./deploy.sh --images-only    # upload missing slug PNGs to GCS
./deploy.sh --full --with-deploy
```

This script orchestrates content generation, GCS image uploads, data rebuild, optional Git push, and Cloud Run deployment.

## OK Admin (Work Hub)

- **Pipeline:** `generate_md_guides` → `generate_images` → resize → normalize names → build (+ GCS normalize post-step)
- **Git / Deploy:** **Git** tab Ship prep → Review & merge · **Deploy** tab from `main`
- [okadmin/README.md](../okadmin/README.md)

## Troubleshooting

- `sitemap.xml` issues:
  - Verify route response at `/sitemap.xml` in production
- Empty or stale home data:
  - Rebuild `app/static/json/job_data.json` with `scripts/build_data.py`

## License

This repository currently does not define a formal license file.  
Add a `LICENSE` file if you want to specify usage terms.