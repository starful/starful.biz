# Starful

Starful is a FastAPI-based web service for IT career exploration and interview preparation.  
It serves job-specific content from Markdown files, provides an AI-powered STARR interview feedback experience, and is deployed on Google Cloud Run.

## Overview

- Content-driven architecture using Markdown in `app/contents`
- Server-rendered UI with Jinja2 templates
- JSON index cache at `app/static/json/job_data.json`
- STARR analysis API backed by Gemini (`gemini-2.5-flash`)
- Production deployment via Cloud Build + Cloud Run

## Tech Stack

- Backend: Python, FastAPI, Uvicorn
- Templating/UI: Jinja2, HTML, CSS
- Content parsing: Markdown, Python JSON/frontmatter-style metadata
- AI: Google GenAI SDK
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

Required for STARR API:

- `GEMINI_API_KEY=<your_gemini_api_key>`

Optional:

- `SITE_URL=https://starful.biz` (default is `https://starful.biz`)

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
- Practice page: `http://127.0.0.1:8000/practice`

## Core Routes

- `GET /` - Home page with grouped career cards
- `GET /career/{item_id}` - Career detail page (Markdown-rendered)
- `GET /search?q=...` - Title-based search
- `GET /practice` - STARR interview practice UI
- `POST /api/analyze-starr` - AI STARR feedback endpoint
- `GET /sitemap.xml` - Dynamic sitemap
- `GET /robots.txt` - Robots policy + sitemap reference

## STARR API (Example)

Endpoint:

```text
POST /api/analyze-starr
Content-Type: application/json
```

Request body:

```json
{
  "s": "Situation text",
  "t": "Task text",
  "a": "Action text",
  "r": "Result text",
  "reflection": "Reflection text",
  "job_title": "Backend Engineer"
}
```

Response fields:

- `score` (0-100)
- `summary`
- `s_feedback`, `t_feedback`, `a_feedback`, `r_feedback`
- `reflection_feedback`
- `improved_answer`

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

### Recommended (Cloud Build)

```bash
gcloud builds submit --config cloudbuild.yaml
```

This pipeline:

1. Builds and tags Docker images
2. Pushes images to Artifact Registry
3. Deploys `starful-biz` to Cloud Run
4. Injects secrets into Cloud Run

### Automation Script

You can also run:

```bash
./deploy.sh
```

This script orchestrates content generation, image sync/optimization, data rebuild, optional Git push confirmation, and Cloud Run deployment.

## Troubleshooting

- STARR API returns `503`:
  - `GEMINI_API_KEY` is missing in runtime environment
- STARR API returns `500`:
  - Check model availability and API key validity
- `sitemap.xml` issues:
  - Verify route response at `/sitemap.xml` in production
- Empty or stale home data:
  - Rebuild `app/static/json/job_data.json` with `scripts/build_data.py`

## License

This repository currently does not define a formal license file.  
Add a `LICENSE` file if you want to specify usage terms.