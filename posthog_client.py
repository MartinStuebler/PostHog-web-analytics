"""Thin PostHog query-API client. Standard library only, no dependencies.

Four small queries, each answering one line of the digest. Anything that does
not change a reader's day was deliberately left out.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import config


class PostHogError(RuntimeError):
    pass


def run_hogql(query: str, api_key: str) -> list[dict]:
    """Run a HogQL query, return rows as dicts keyed by column name."""
    url = f"{config.POSTHOG_HOST}/api/projects/{config.PROJECT_ID}/query/"
    body = json.dumps({"query": {"kind": "HogQLQuery", "query": query}}).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise PostHogError(f"PostHog returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise PostHogError(f"Could not reach PostHog: {exc.reason}") from exc

    columns = payload.get("columns") or []
    results = payload.get("results") or []
    return [dict(zip(columns, row)) for row in results]


def _host_filter() -> str:
    """Only the marketing site.

    Four domains report into this project: noriagentic.com, usenori.ai and two
    `ta-01k…` preview sandboxes. Without this the numbers silently combine them.
    """
    host = config.SITE_HOST.replace("'", "''")
    return f"properties.$host = '{host}'"


# Yesterday, bounded by the project timezone so these reconcile with the UI.
_YESTERDAY = (
    "timestamp >= toStartOfDay(now()) - INTERVAL 1 DAY "
    "AND timestamp < toStartOfDay(now())"
)


def yesterday_totals(api_key: str) -> dict | None:
    query = f"""
        SELECT
            toDate(timestamp) AS day,
            uniq(person_id) AS visitors,
            countIf(event = '$pageview') AS pageviews
        FROM events
        WHERE {_YESTERDAY}
          AND {_host_filter()}
        GROUP BY day
    """
    rows = run_hogql(query, api_key)
    return rows[0] if rows else None


def baseline_visitors(api_key: str) -> float | None:
    """Mean daily visitors over the seven days before yesterday.

    Deliberately not day-over-day. At 30 to 50 visitors a single day swings
    hard enough that a percentage against yesterday is noise wearing a suit.
    """
    query = f"""
        SELECT avg(visitors) AS baseline
        FROM (
            SELECT toDate(timestamp) AS day, uniq(person_id) AS visitors
            FROM events
            WHERE timestamp >= toStartOfDay(now()) - INTERVAL 8 DAY
              AND timestamp < toStartOfDay(now()) - INTERVAL 1 DAY
              AND {_host_filter()}
            GROUP BY day
        )
    """
    rows = run_hogql(query, api_key)
    if not rows or rows[0].get("baseline") is None:
        return None
    return float(rows[0]["baseline"])


def top_page_excluding_home(api_key: str) -> dict | None:
    """The most-read page that is not the homepage.

    `/` wins every day and says nothing. The second place is the actual signal.
    """
    query = f"""
        SELECT
            properties.$pathname AS path,
            uniq(person_id) AS visitors
        FROM events
        WHERE event = '$pageview'
          AND {_YESTERDAY}
          AND {_host_filter()}
          AND coalesce(properties.$pathname, '/') NOT IN ('/', '')
        GROUP BY path
        ORDER BY visitors DESC
        LIMIT 1
    """
    rows = run_hogql(query, api_key)
    return rows[0] if rows else None


def tagged_campaigns(api_key: str) -> list[dict]:
    """Visits that arrived on a UTM-tagged link. Usually empty, and that is
    itself the finding."""
    query = f"""
        SELECT
            properties.utm_campaign AS campaign,
            uniq(person_id) AS visitors
        FROM events
        WHERE event = '$pageview'
          AND {_YESTERDAY}
          AND {_host_filter()}
          AND coalesce(properties.utm_campaign, '') != ''
        GROUP BY campaign
        ORDER BY visitors DESC
        LIMIT 5
    """
    return run_hogql(query, api_key)
