# PostHog web analytics → Slack

Posts a three-line daily digest for **noriagentic.com** into Slack at 9am Eastern.

Python standard library only. No dependencies, no build step, no server.

Status: **working and verified against the live API.** Runs `30921492886` and `30922524517` both completed and posted.

---

## What it posts

A normal morning:

> **noriagentic.com · Mon 3 Aug**
> 47 visitors, 73 pageviews. Above the 7-day average of 31.
>
> Most read after the homepage: `/newsletter.html`, 7 visitors
>
> No tagged campaigns landed.

When a UTM-tagged campaign lands, the last line is replaced:

> 🎉 **email-outreach-2026-07** brought 6 visitors

When nothing was recorded, the whole message becomes an alarm:

> 🔴 **noriagentic.com** recorded no visitors yesterday.
> Either traffic genuinely stopped or the snippet is no longer firing.

---

## Why it is only three lines

The first version reported sessions, five top pages, six traffic sources, day-over-day percentages and a footer of caveats. It was a report when it needed to be a glance. What got cut, and why:

- **Sessions.** Tracked visitors almost exactly, 47 against 57. Two numbers, one fact.
- **Pages three to five.** Two and three visitors each. Noise presented as a ranking.
- **The source list.** After the NULL fix it filled with `internal (self-referral)` and a preview host. Not acquisition data.
- **Day-over-day percentages.** This was the worst one. At 30 to 50 visitors a day, one quiet Sunday produces "up 147%", which teaches the reader to ignore the number entirely. Replaced with a **7-day average**, and anything within 15% of it reads "in line" rather than inventing a story.
- **The footer caveat.** True, but nobody reads the same disclaimer every morning. It lives here instead, under Known limits.

The homepage is excluded from "most read" on purpose. `/` wins every single day and tells you nothing; second place is the actual signal.

---

## Setup

### Secrets

The repo is public. Nothing sensitive is in the code; both values are GitHub Actions secrets.

> ⚠️ **The secret names do not describe what they hold.** This is deliberate to avoid re-entering credentials, and the workflow maps them explicitly. Do not "fix" this by matching on the name.

| Secret name | Actually contains |
|---|---|
| `POTSHOT_TO_SLACK_GROWTH` | PostHog personal API key, scope `query:read` |
| `POSTHOG_SLACK_KEY_GROWTH` | Slack incoming webhook URL (`hooks.slack.com/services/…`) |

Set them under **Settings → Secrets and variables → Actions**. They must be *repository* secrets under the **Actions** tab; Codespaces and Dependabot secrets are separate and invisible to the workflow.

Secret **names** may only contain letters, numbers and underscores. Copying a name with surrounding backticks will be rejected.

### Where the values come from

- **PostHog key:** `us.posthog.com/project/532714/settings/user-api-keys`. Scope it to `query:read` and to project 532714 only. The value is shown once.
- **Slack webhook:** `api.slack.com/apps` (the developer site, not the Slack client) → your app → **Incoming Webhooks** → activate → Add New Webhook to Workspace → pick the channel. The channel is baked into the webhook, not into this code.

Target channel is `C0BGDN7PK3K` in the `tilework-tech` workspace.

---

## Configuration

`config.py` holds everything non-secret:

- `PROJECT_ID = 532714`
- `SITE_HOST = "noriagentic.com"`

**The host filter is load-bearing.** Four domains report into that one PostHog project:

1. `noriagentic.com` — the marketing site, the only one we count
2. `usenori.ai`
3. `ta-01kysj5jhh2wche4fe…` — preview sandbox
4. `ta-01kyw19bpfkwekys3…` — preview sandbox

Without the filter the digest silently adds all four together. If a fifth domain appears, this filter is the first thing to check.

---

## Running it

Scheduled at **13:00 UTC**, which is 9am Eastern during daylight saving.

GitHub cron has no DST awareness, so it becomes 8am ET in winter. Change the cron in `.github/workflows/daily-digest.yml` to `0 14 * * *` if the hour matters. The alternative is setting the PostHog project timezone to `America/New_York`, which would also stop "Today" reading zero in the PostHog UI until mid-afternoon.

Manually: the **Actions** tab → Daily PostHog digest → Run workflow. Or `gh workflow run daily-digest.yml`.

Locally, without posting anything:

```bash
export POSTHOG_API_KEY='…'
python3 digest.py --dry-run
```

That prints the exact message text. Add `SLACK_WEBHOOK_URL` and drop `--dry-run` to post for real.

Needs Python 3.9 or newer.

---

## Known limits

- **Every number is a floor.** No reverse proxy is configured on the PostHog install, so ad blockers drop an unknown share of events. PostHog's own estimate is 10 to 25%.
- **Internal traffic is included.** The project has an internal-users filter defined, but "enable on all new insights" is switched off and these queries do not apply it. Your own visits are in the totals.
- **No conversion data.** No conversion goal exists in the project, so the digest reports arrivals and not outcomes. The site's real conversion is the free-trial signup, and the funnel crosses to `login.norisessions.com`, which may not be instrumented in this project at all.
- **Day boundaries follow the PostHog project timezone**, currently UTC. Change that and these numbers shift with it, but they will still reconcile with the PostHog UI, which is the point.
- **UTM tagging is new.** Most traffic still lands in Direct. Some of that is genuine, some is untagged links shared in DMs and Slack, which analytics cannot attribute.

---

## A trap worth knowing

Missing event properties come back from HogQL as `NULL`, not as an empty string. An earlier version tested `properties.utm_source != ''`, which never matches on a NULL, so every visit collapsed into one row labelled `None` and untagged traffic was reported as a tagged campaign. Every property read in `posthog_client.py` is now wrapped in `coalesce()`. Keep it that way.

---

## Files

| File | Does |
|---|---|
| `config.py` | Project id, host filter |
| `posthog_client.py` | Query API client and the four HogQL queries |
| `digest.py` | Builds the message, posts it |
| `.github/workflows/daily-digest.yml` | The 13:00 UTC cron and the secret mapping |

## Documentation

Everything explaining why this exists lives in [`docs/`](docs/):

- [`DECISIONS.md`](docs/DECISIONS.md) — why the webhook, why no link builder yet, the Linear workspace, TIL-17, security, and everything still open
- [`utm-taxonomy.md`](docs/utm-taxonomy.md) — the link-tagging vocabulary and the three ways to destroy the data
- [`nori_posthog_setup_guide.md`](docs/nori_posthog_setup_guide.md) — remaining PostHog setup, click by click
- [`nori_slack_utm_workflow_spec.md`](docs/nori_slack_utm_workflow_spec.md) — build spec for the self-service link builder
- [`nori_hubspot_handoff.md`](docs/nori_hubspot_handoff.md) — HubSpot object model and import mechanics
- [`nori_crm_design_brief.md`](docs/nori_crm_design_brief.md) — CRM spreadsheet schema and outreach logic

Customer email addresses in the HubSpot docs are redacted, since this repo is public.
