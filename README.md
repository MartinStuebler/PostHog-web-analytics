# PostHog web analytics → Slack

Pulls yesterday's web analytics for **noriagentic.com** out of PostHog and posts a digest to Slack, daily.

Standard library only. No dependencies, no build step.

> **Status: untested against the live API.** The queries were written from the PostHog schema but have not been run, because the author had no API key. Do the dry run in step 3 before trusting the cron.

---

## What it posts

- Visitors, pageviews and sessions for yesterday, with the change against the day before
- Top 5 pages
- Where visitors came from, by `utm_source` where tagged and referring domain otherwise
- Any UTM-tagged campaigns that landed
- A footer noting what is excluded and why

---

## Setup

### 1. Create the secrets

This repo is public. Nothing sensitive goes in the code; both values live in GitHub Actions secrets.

| Secret | Where it comes from |
|---|---|
| `POSTHOG_API_KEY` | PostHog → Settings → Personal API keys. Scope it **`query:read`** and restrict it to project `532714`. |
| `SLACK_WEBHOOK_URL` | Slack → your app → Incoming Webhooks → add one for the target channel. |

Add both under **Settings → Secrets and variables → Actions**.

The target channel is `C0BGDN7PK3K` in the `tilework-tech` workspace. The channel is baked into the webhook, not into this code.

### 2. Check the config

`config.py` holds the non-secret bits:

- `PROJECT_ID = 532714`
- `SITE_HOST = "noriagentic.com"`

**The host filter is load-bearing.** Four domains report into that PostHog project: `noriagentic.com`, `usenori.ai`, and two `ta-01k…` preview sandboxes. Without the filter the digest silently adds all four together.

### 3. Dry run before enabling the cron

```bash
export POSTHOG_API_KEY='…'
python3 digest.py --dry-run
```

That runs the queries and prints the Slack blocks without posting. If the HogQL is wrong you will see the API error here rather than in a broken 9am message.

Then a real post:

```bash
export SLACK_WEBHOOK_URL='…'
python3 digest.py
```

### 4. Turn on the schedule

The workflow runs at **13:00 UTC**, which is 9am Eastern during daylight saving. GitHub's cron has no DST handling, so it becomes 8am ET in winter. Change the cron to `0 14 * * *` then if the hour matters.

You can also trigger it by hand from the Actions tab via `workflow_dispatch`.

---

## Known limits

- **Undercounts.** No reverse proxy is configured on the PostHog install, so ad blockers drop an unknown share of events. Every number here is a floor.
- **Internal traffic is included.** PostHog has an internal-users filter defined but "enable on all new insights" is switched off, and these queries do not apply it. Your own visits are in the totals.
- **No conversion data.** No conversion goal exists in the project yet, so the digest can report arrivals but not outcomes.
- **Day boundaries** follow the PostHog project timezone, currently UTC. If the project timezone changes, these numbers shift with it and will still reconcile with the PostHog UI.

## Files

| File | Does |
|---|---|
| `config.py` | Project id, host filter, row limits |
| `posthog_client.py` | HogQL query API client and the four queries |
| `digest.py` | Formats the Slack blocks and posts them |
| `.github/workflows/daily-digest.yml` | The 13:00 UTC cron |
