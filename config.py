"""Configuration. No secrets here — this repo is public.

Secrets come from the environment:
  POSTHOG_API_KEY    personal API key, scope `query:read`
  SLACK_WEBHOOK_URL  Slack incoming webhook for the target channel
"""

# PostHog project
POSTHOG_HOST = "https://us.posthog.com"
PROJECT_ID = 532714

# Only count the marketing site. Without this filter the numbers silently
# combine noriagentic.com, usenori.ai and two `ta-01k…` preview sandboxes,
# which all report into this same project.
SITE_HOST = "noriagentic.com"

# How many rows to show in the list sections of the digest
TOP_PAGES = 5
TOP_SOURCES = 6
