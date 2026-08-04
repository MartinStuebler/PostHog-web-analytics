"""Build the daily Slack digest and post it.

Three lines, by design. Anything that does not change the reader's day was
cut: sessions duplicate visitors, pages three to five are two-visitor noise,
and a day-over-day percentage at this volume is noise wearing a suit.

Run:  POSTHOG_API_KEY=… SLACK_WEBHOOK_URL=… python3 digest.py
Dry run (prints, posts nothing):  python3 digest.py --dry-run
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

import config
import posthog_client as ph


def _pretty_day(value) -> str:
    """'2026-08-03' becomes 'Mon 3 Aug'."""
    if isinstance(value, dt.date):
        day = value
    else:
        try:
            day = dt.date.fromisoformat(str(value)[:10])
        except ValueError:
            return str(value)
    return f"{day:%a} {day.day} {day:%b}"


def _comparison(visitors: int, baseline: float | None) -> str:
    if baseline is None or baseline <= 0:
        return "No baseline yet."
    rounded = round(baseline)
    # Within 15% of the mean is not a story at this sample size.
    if abs(visitors - baseline) <= baseline * 0.15:
        return f"In line with the 7-day average of {rounded}."
    direction = "Above" if visitors > baseline else "Below"
    return f"{direction} the 7-day average of {rounded}."


def build_blocks(totals, baseline, top_page, campaigns) -> list[dict]:
    if not totals or not totals.get("visitors"):
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":red_circle: *{config.SITE_HOST}* recorded no visitors yesterday.\n"
                    "Either traffic genuinely stopped or the snippet is no longer firing."
                ),
            },
        }]

    lines = [
        f"*{config.SITE_HOST} · {_pretty_day(totals['day'])}*",
        f"{totals['visitors']} visitors, {totals['pageviews']} pageviews. "
        f"{_comparison(totals['visitors'], baseline)}",
        "",
    ]

    if top_page:
        lines.append(
            f"Most read after the homepage: `{top_page['path']}`, "
            f"{top_page['visitors']} visitors"
        )
    else:
        lines.append("Only the homepage was read.")

    lines.append("")

    if campaigns:
        for c in campaigns:
            lines.append(f":tada: *{c['campaign']}* brought {c['visitors']} visitors")
    else:
        lines.append("No tagged campaigns landed.")

    return [{"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}]


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

    totals = ph.yesterday_totals(api_key)
    baseline = ph.baseline_visitors(api_key)
    top_page = ph.top_page_excluding_home(api_key)
    campaigns = ph.tagged_campaigns(api_key)

    blocks = build_blocks(totals, baseline, top_page, campaigns)

    if dry_run:
        print(blocks[0]["text"]["text"])
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
