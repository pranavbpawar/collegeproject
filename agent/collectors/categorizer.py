"""
NEF Agent — Standalone Website Categorizer (no database required)
Agent-side companion to backend/app/services/website_categorizer.py.

Uses a built-in rule set (pattern matching) so the agent can tag domains
immediately without a network round-trip to the backend.
The backend's WebsiteCategorizer remains the authoritative source; this
is a fast, offline-capable copy of the same rules.

Categories:
  productivity  — work tools, coding, docs, cloud services
  social_media  — social networks, messaging apps
  entertainment — streaming, gaming, video
  news          — news outlets, blogs
  shopping      — e-commerce
  adult         — adult content (always flagged)
  unknown       — no rule matched
"""

import re
from typing import Tuple

# ── Built-in rule set ──────────────────────────────────────────────────────────
# Each entry: (pattern_regex, category, productivity_score 0-100)
# Evaluated top-to-bottom; first match wins.
# % wildcard from DB is replaced by .* in regex here.

_RULES: list[Tuple[str, str, int]] = [
    # ── Productivity / Work tools ──────────────────────────────────────────────
    (r".*github\.com$",           "productivity",   90),
    (r".*gitlab\.com$",           "productivity",   90),
    (r".*bitbucket\.org$",        "productivity",   85),
    (r".*stackoverflow\.com$",    "productivity",   85),
    (r".*docs\.google\.com$",     "productivity",   90),
    (r".*drive\.google\.com$",    "productivity",   85),
    (r".*sheets\.google\.com$",   "productivity",   85),
    (r".*slides\.google\.com$",   "productivity",   80),
    (r".*meet\.google\.com$",     "productivity",   90),
    (r".*calendar\.google\.com$", "productivity",   80),
    (r".*office\.com$",           "productivity",   90),
    (r".*sharepoint\.com$",       "productivity",   85),
    (r".*teams\.microsoft\.com$", "productivity",   90),
    (r".*outlook\.com$",          "productivity",   85),
    (r".*live\.com$",             "productivity",   80),
    (r".*slack\.com$",            "productivity",   85),
    (r".*zoom\.us$",              "productivity",   90),
    (r".*atlassian\.net$",        "productivity",   85),
    (r".*jira\..+$",              "productivity",   85),
    (r".*confluence\..+$",        "productivity",   80),
    (r".*notion\.so$",            "productivity",   80),
    (r".*figma\.com$",            "productivity",   80),
    (r".*linear\.app$",           "productivity",   85),
    (r".*trello\.com$",           "productivity",   80),
    (r".*asana\.com$",            "productivity",   80),
    (r".*aws\.amazon\.com$",      "productivity",   85),
    (r".*console\.aws\.amazon\.com$", "productivity", 90),
    (r".*cloud\.google\.com$",    "productivity",   85),
    (r".*portal\.azure\.com$",    "productivity",   85),
    (r".*digitalocean\.com$",     "productivity",   80),
    (r".*cloudflare\.com$",       "productivity",   80),
    (r".*heroku\.com$",           "productivity",   80),
    (r".*vercel\.com$",           "productivity",   80),
    (r".*netlify\.com$",          "productivity",   80),
    (r".*npmjs\.com$",            "productivity",   85),
    (r".*pypi\.org$",             "productivity",   85),
    (r".*readthedocs\.io$",       "productivity",   85),
    (r".*developer\..+\.com$",    "productivity",   80),
    (r".*docs\..+\.com$",         "productivity",   80),
    (r".*api\..+\.com$",          "productivity",   80),
    (r".*mail\.google\.com$",     "productivity",   80),
    (r".*gmail\.com$",            "productivity",   75),

    # ── Social media ──────────────────────────────────────────────────────────
    (r".*facebook\.com$",         "social_media",   20),
    (r".*instagram\.com$",        "social_media",   15),
    (r".*twitter\.com$",          "social_media",   25),
    (r".*x\.com$",                "social_media",   25),
    (r".*tiktok\.com$",           "social_media",   10),
    (r".*snapchat\.com$",         "social_media",   10),
    (r".*linkedin\.com$",         "social_media",   65),  # higher — professional
    (r".*pinterest\.com$",        "social_media",   20),
    (r".*reddit\.com$",           "social_media",   35),  # can be productive
    (r".*quora\.com$",            "social_media",   45),
    (r".*discord\.com$",          "social_media",   50),  # mixed

    # ── Entertainment / Streaming ─────────────────────────────────────────────
    (r".*youtube\.com$",          "entertainment",  25),
    (r".*youtu\.be$",             "entertainment",  25),
    (r".*netflix\.com$",          "entertainment",  10),
    (r".*twitch\.tv$",            "entertainment",  10),
    (r".*spotify\.com$",          "entertainment",  35),
    (r".*hulu\.com$",             "entertainment",  10),
    (r".*disneyplus\.com$",       "entertainment",  10),
    (r".*primevideo\.com$",       "entertainment",  10),
    (r".*soundcloud\.com$",       "entertainment",  25),
    (r".*gaming\..+$",            "entertainment",  10),
    (r".*steampowered\.com$",     "entertainment",  10),
    (r".*epicgames\.com$",        "entertainment",  10),

    # ── News ──────────────────────────────────────────────────────────────────
    (r".*bbc\.com$",              "news",           50),
    (r".*bbc\.co\.uk$",           "news",           50),
    (r".*cnn\.com$",              "news",           50),
    (r".*nytimes\.com$",          "news",           50),
    (r".*theguardian\.com$",      "news",           50),
    (r".*reuters\.com$",          "news",           55),
    (r".*bloomberg\.com$",        "news",           60),
    (r".*techcrunch\.com$",       "news",           60),
    (r".*wired\.com$",            "news",           55),
    (r".*hn\.algolia\.com$",      "news",           65),
    (r".*news\.ycombinator\.com$","news",           65),

    # ── Shopping ─────────────────────────────────────────────────────────────
    (r".*amazon\.com$",           "shopping",       20),
    (r".*amazon\.\w+$",           "shopping",       20),
    (r".*ebay\.com$",             "shopping",       15),
    (r".*etsy\.com$",             "shopping",       15),
    (r".*walmart\.com$",          "shopping",       15),
    (r".*aliexpress\.com$",       "shopping",       10),
    (r".*flipkart\.com$",         "shopping",       15),

    # ── Adult content (always flag) ───────────────────────────────────────────
    (r".*pornhub\.com$",          "adult",          0),
    (r".*xvideos\.com$",          "adult",          0),
    (r".*xnxx\.com$",             "adult",          0),
    (r".*onlyfans\.com$",         "adult",          0),
]

# Precompile patterns for speed
_COMPILED = [(re.compile(pattern), category, score) for pattern, category, score in _RULES]


def categorize(domain: str) -> Tuple[str, int]:
    """
    Categorize a domain into (category, productivity_score).
    productivity_score: 0 (worst) to 100 (best).
    Matches are case-insensitive.
    """
    domain = domain.lower().strip().rstrip(".")

    # Strip leading "www." for cleaner matching
    if domain.startswith("www."):
        domain = domain[4:]

    for pattern, category, score in _COMPILED:
        if pattern.match(domain):
            return category, score

    return "unknown", 50


def categorize_domains(domains: list) -> list:
    """
    Batch categorize a list of domain strings.
    Returns list of dicts: {domain, category, productivity_score}
    """
    result = []
    for d in domains:
        if not d:
            continue
        cat, score = categorize(d)
        result.append({
            "domain":              d,
            "category":            cat,
            "productivity_score":  score,
        })
    return result
