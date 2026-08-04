"""Thin PostHog query-API client. Standard library only, no dependencies."""

import json
import urllib.error
import urllib.request

import config


class PostHogError(RuntimeError):
    pass


def run_hogql(query: str, api_key: str) -> list[dict]:
    """Run a HogQL query and return rows as a list of dicts keyed by column name.

    The query API returns {"results": [[...]], "columns": [...]}; this flattens
    that into something callers can read by name instead of index.
    """
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


def _window(days_back: int) -> str:
    """SQL fragment for a single whole day, `days_back` days before today.

    days_back=1 is yesterday. Days are bounded by the project timezone, which
    is what PostHog's own UI uses, so these numbers reconcile with the web
    analytics screens.
    """
    return (
        f"timestamp >= toStartOfDay(now()) - INTERVAL {days_back} DAY "
        f"AND timestamp < toStartOfDay(now()) - INTERVAL {days_back - 1} DAY"
    )


def _host_filter() -> str:
    host = config.SITE_HOST.replace("'", "''")
    return f"properties.$host = '{host}'"


def daily_totals(api_key: str) -> list[dict]:
    """Yesterday and the day before, so the digest can show a delta."""
    query = f"""
        SELECT
            toDate(timestamp) AS day,
            uniq(person_id) AS visitors,
            countIf(event = '$pageview') AS pageviews,
            uniq(properties.$session_id) AS sessions
        FROM events
        WHERE timestamp >= toStartOfDay(now()) - INTERVAL 2 DAY
          AND timestamp < toStartOfDay(now())
          AND {_host_filter()}
        GROUP BY day
        ORDER BY day
    """
    return run_hogql(query, api_key)


def top_pages(api_key: str) -> list[dict]:
    query = f"""
        SELECT
            properties.$pathname AS path,
            uniq(person_id) AS visitors,
            count() AS views
        FROM events
        WHERE event = '$pageview'
          AND {_window(1)}
          AND {_host_filter()}
        GROUP BY path
        ORDER BY visitors DESC
        LIMIT {config.TOP_PAGES}
    """
    return run_hogql(query, api_key)


def top_sources(api_key: str) -> list[dict]:
    """Group by utm_source where tagged, falling back to referring domain.

    Deliberately not using PostHog's derived channel type: this keeps the
    digest honest about which visits actually carried a UTM tag.
    """
    query = f"""
        SELECT
            multiIf(
                coalesce(properties.utm_source, '') != '',
                    properties.utm_source,
                coalesce(properties.$referring_domain, '') IN ('', '$direct'),
                    'direct',
                properties.$referring_domain
            ) AS source,
            uniq(person_id) AS visitors
        FROM events
        WHERE event = '$pageview'
          AND {_window(1)}
          AND {_host_filter()}
        GROUP BY source
        ORDER BY visitors DESC
        LIMIT {config.TOP_SOURCES}
    """
    return run_hogql(query, api_key)


def tagged_campaigns(api_key: str) -> list[dict]:
    """Visits that arrived on a UTM-tagged link, by campaign."""
    query = f"""
        SELECT
            properties.utm_campaign AS campaign,
            coalesce(properties.utm_source, 'unknown') AS source,
            uniq(person_id) AS visitors
        FROM events
        WHERE event = '$pageview'
          AND {_window(1)}
          AND {_host_filter()}
          AND coalesce(properties.utm_campaign, '') != ''
        GROUP BY campaign, source
        ORDER BY visitors DESC
        LIMIT 10
    """
    return run_hogql(query, api_key)
