"""Build the daily Slack digest and post it.

Run:  POSTHOG_API_KEY=… SLACK_WEBHOOK_URL=… python3 digest.py
Dry run (prints, posts nothing):  python3 digest.py --dry-run
"""

import json
import os
import sys
import urllib.error
import urllib.request

import config
import posthog_client as ph


def _delta(today: int, yesterday: int) -> str:
    """Human-readable change. Avoids a percentage when the base is tiny,
    because at this traffic level percentages read as false precision."""
    if yesterday == 0:
        return "no prior day"
    diff = today - yesterday
    if diff == 0:
        return "flat"
    pct = round(abs(diff) / yesterday * 100)
    arrow = "up" if diff > 0 else "down"
    if yesterday < 10:
        return f"{arrow} {abs(diff)} from {yesterday}"
    return f"{arrow} {pct}% from {yesterday}"


def build_blocks(totals, pages, sources, campaigns) -> list[dict]:
    if not totals:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn",
                     "text": f":warning: *{config.SITE_HOST}* — no events yesterday. "
                             "Either traffic genuinely stopped or the snippet is not firing."},
        }]

    latest = totals[-1]
    prior = totals[-2] if len(totals) > 1 else {"visitors": 0, "pageviews": 0, "sessions": 0}

    headline = (
        f"*{latest['visitors']} visitors* · {latest['pageviews']} pageviews · "
        f"{latest['sessions']} sessions"
    )
    movement = (
        f"Visitors {_delta(latest['visitors'], prior['visitors'])}. "
        f"Pageviews {_delta(latest['pageviews'], prior['pageviews'])}."
    )

    blocks = [
        {"type": "header",
         "text": {"type": "plain_text", "text": f"{config.SITE_HOST} · {latest['day']}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{headline}\n{movement}"}},
    ]

    if pages:
        lines = "\n".join(
            f"`{p['path'] or '/'}` — {p['visitors']} visitors, {p['views']} views"
            for p in pages
        )
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn", "text": f"*Top pages*\n{lines}"}})

    if sources:
        lines = "\n".join(f"{s['source']} — {s['visitors']}" for s in sources)
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn", "text": f"*Where they came from*\n{lines}"}})

    if campaigns:
        lines = "\n".join(
            f"`{c['campaign']}` via {c['source']} — {c['visitors']}" for c in campaigns
        )
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn", "text": f"*Tagged campaigns*\n{lines}"}})
    else:
        blocks.append({"type": "context", "elements": [
            {"type": "mrkdwn", "text": "_No UTM-tagged visits yesterday._"}]})

    blocks.append({"type": "context", "elements": [
        {"type": "mrkdwn",
         "text": f"Filtered to {config.SITE_HOST}. Excludes usenori.ai and preview hosts. "
                 "Ad blockers are not proxied, so treat these as a floor."}]})
    return blocks


def post_to_slack(blocks: list[dict], webhook: str) -> None:
    body = json.dumps({"blocks": blocks}).encode()
    req = urllib.request.Request(
        webhook, data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Slack returned {resp.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Slack rejected the message ({exc.code}): {detail}") from exc


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    api_key = os.environ.get("POSTHOG_API_KEY")
    if not api_key:
        print("POSTHOG_API_KEY is not set", file=sys.stderr)
        return 1

    totals = ph.daily_totals(api_key)
    pages = ph.top_pages(api_key)
    sources = ph.top_sources(api_key)
    campaigns = ph.tagged_campaigns(api_key)

    blocks = build_blocks(totals, pages, sources, campaigns)

    if dry_run:
        print(json.dumps(blocks, indent=2, default=str))
        return 0

    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("SLACK_WEBHOOK_URL is not set", file=sys.stderr)
        return 1

    post_to_slack(blocks, webhook)
    print("Posted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
