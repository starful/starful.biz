"""SEO utilities: featured careers, legacy redirects, FAQ structured data."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# GSC でノ出が多い職種（内部リンク・サイトマップ優先度用）
FEATURED_CAREER_SLUGS: List[str] = [
    "data_scientist",
    "graphics_engine_developer",
    "cto",
    "developer_relations_engineer",
    "prompt_engineer",
    "interaction_designer",
    "application_security_engineer",
    "serverless_engineer",
    "ui_ux_researcher",
    "vpoe",
    "analytics_engineer",
    "ui_ux_designer",
    "ethical_hacker",
    "concept_artist",
]

# GSC 低信号・無信号で撤退した職種 → ホームへ 301（404 増を防ぐ）
REMOVED_CAREER_SLUGS: frozenset[str] = frozenset(
    {
        "3d_artist",
        "ai_product_manager",
        "analytics_manager",
        "android_engineer",
        "application_architect",
        "architect",
        "big_data_engineer",
        "blue_team_engineer",
        "brand_marketer",
        "business_systems_analyst",
        "cloud_application_developer",
        "cloud_database_engineer",
        "cloud_finops_manager",
        "cloud_native_engineer",
        "cloud_security_engineer",
        "compliance_engineer",
        "computational_biologist",
        "content_designer",
        "content_marketer",
        "content_planner",
        "content_strategist",
        "customer_support_engineer",
        "data_quality_analyst",
        "database_developer",
        "design_system_manager",
        "desktop_application_developer",
        "developer_advocate",
        "digital_marketing_manager",
        "director_of_ux",
        "e_commerce_manager",
        "ecommerce_manager",
        "electrical_engineer",
        "engineering_manager",
        "engineering_program_manager",
        "erp_developer",
        "event_marketer",
        "frontend_architect",
        "functional_analyst",
        "game_artist",
        "game_data_analyst",
        "game_designer",
        "game_developer",
        "game_planner",
        "game_systems_designer",
        "go_developer",
        "growth_manager",
        "hybrid_cloud_engineer",
        "llm_prompt_engineer",
        "marketing_data_analyst",
        "mlops_engineer",
        "mobile_developer",
        "mobile_engineer",
        "operations_planner",
        "performance_marketer",
        "platform_planner",
        "project_manager",
        "recommendation_system_engineer",
        "scrum_master",
        "search_ads_specialist",
        "security_engineer",
        "social_media_manager",
        "solutions_architect",
        "sound_designer",
        "system_integrator",
        "tech_evangelist",
        "tech_pm",
        "test_automation_engineer",
        "ux_planner",
        "ux_strategist",
        "web_developer",
        "web_master",
        "web_performance_engineer",
    }
)

# 旧URL・別名スラッグ → 現行 career ID
CAREER_SLUG_ALIASES: Dict[str, str] = {
    "ux_designer": "ui_ux_designer",
    "ux_researcher": "ui_ux_researcher",
    "devrel": "developer_relations_engineer",
    "dev_relations_engineer": "developer_relations_engineer",
    "appsec": "application_security_engineer",
    "ds": "data_scientist",
}

# レガシーブログ等：プレフィックス一致でホームへ 301
LEGACY_PATH_PREFIXES: Tuple[str, ...] = (
    "/entry",
    "/archive",
    "/category",
    "/pages",
    "/e/",
)


def legacy_redirect_target(path: str) -> Optional[str]:
    """Return '/' if path is a legacy blog URL that should 301 to home."""
    p = path.rstrip("/") or "/"
    for prefix in LEGACY_PATH_PREFIXES:
        if p == prefix or p.startswith(prefix + "/"):
            return "/"
    return None


def resolve_career_id(item_id: str) -> str:
    key = (item_id or "").strip().lower()
    return CAREER_SLUG_ALIASES.get(key, item_id)


def is_removed_career(item_id: str) -> bool:
    key = (item_id or "").strip().lower()
    return key in REMOVED_CAREER_SLUGS


def legacy_query_should_drop_to_home(path: str, query: str) -> bool:
    """True for legacy ?page= URLs that should 301 to apex home."""
    if not query:
        return False
    p = (path or "/").rstrip("/") or "/"
    if p != "/":
        return False
    # page=<digits> only (optionally with other junk params still drop to /)
    return "page=" in query


def featured_jobs_from_data(jobs: List[dict]) -> List[dict]:
    by_id = {j.get("id"): j for j in jobs if j.get("id")}
    out: List[dict] = []
    seen: set = set()
    for slug in FEATURED_CAREER_SLUGS:
        job = by_id.get(slug)
        if job and slug not in seen:
            seen.add(slug)
            out.append(job)
    return out


def extract_faq_from_markdown(body: str, limit: int = 6) -> List[Dict[str, str]]:
    """Extract Q/A pairs from Starful markdown (一問一答ドリル形式)."""
    if not body:
        return []
    pattern = re.compile(
        r"- \*\*Q\.\s*(.+?)\*\*\s*\n\s*- \*\*A\.\*\*\s*(.+?)(?=\n- \*\*Q\.|\n#{1,3} |\Z)",
        re.DOTALL,
    )
    pairs: List[Dict[str, str]] = []
    for q_raw, a_raw in pattern.findall(body):
        q = re.sub(r"\s+", " ", q_raw).strip()
        a = re.sub(r"\s+", " ", a_raw).strip()
        if q and a:
            pairs.append({"question": q[:200], "answer": a[:500]})
        if len(pairs) >= limit:
            break
    return pairs


def faq_page_json_ld(
    faq_items: List[Dict[str, str]], page_url: str
) -> Optional[Dict[str, Any]]:
    if not faq_items:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["answer"],
                },
            }
            for item in faq_items
        ],
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url},
    }


def merge_career_json_ld(
    graph: List[Dict[str, Any]], faq_ld: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    items = list(graph)
    if faq_ld:
        items.append(faq_ld)
    return {"@graph": items}


def canonical_career_url(base_url: str, career_id: str) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", f"career/{career_id}".lstrip("/"))
