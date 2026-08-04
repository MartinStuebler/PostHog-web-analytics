# Decisions and open threads

Written 2026-08-04. Records the reasoning that would otherwise have to be redone, and what is still unfinished.

---

## Why the digest posts via an incoming webhook

A webhook can only post. It cannot edit or delete. That was accepted knowingly.

Deleting or updating a previous message needs `chat.delete` or `chat.update` from the Slack Web API, which needs a bot token with `chat:write`, and only works on messages that same bot posted via `chat.postMessage`. It also needs the previous message's timestamp stored between runs, for example as a GitHub Actions variable.

A "keep the channel clean by deleting yesterday's post" change was raised and then dropped. Two arguments against it, worth remembering if it comes up again:

- One message a day is roughly thirty a month. That is not noise.
- Delete and update both destroy history. You lose the ability to scroll back to what last Tuesday looked like.

If it is ever revisited, `chat.update` beats delete: one permanent message that rewrites itself, with no gap where the channel is empty.

**Revisited and closed on 2026-08-04.** Four test messages accumulated in the channel during setup and prompted a second look at the bot-token rework. Decision: delete those four by hand and keep the webhook. Steady state is one message a day, which is not worth a token, a scope, a channel invite, a fifth secret and a state file committed back by the Action on every run.

Target channel is `#growth-and-marketing`.

---

## Why the Slack UTM builder was never built

Three delivery options were put up. Martin chose **Slack Workflow Builder**, knowingly accepting that it cannot URL-encode, cannot slugify, and breaks on any link that already contains `?`.

The build spec is in `nori_slack_utm_workflow_spec.md` and remains valid.

It was not built because the workspace could not be reached: `tilework.slack.com` showed a sign-in wall, and the assistant does not authenticate. Execution was to happen via a separate agent login that never materialised in this session.

A Claude-in-Slack skill was then written as a better alternative, since it can parse URLs and enforce the taxonomy properly. Martin had it deleted after reviewing it. Its content survives as `utm-taxonomy.md`, which is the durable part.

**Net state: no self-service link builder exists.** The taxonomy exists; the tool does not.

---

## The Linear workspace

Workspace `tilework`, one team, **Free plan**. Roughly 28 projects against 34 issues, of which 3 are Done. That ratio is the finding: it is a directory of intentions rather than a tracker.

- No **In Progress** state is in use. Work sits in Todo, then becomes Done.
- Three completed issues, all 10 to 12 June, all customer work. Nothing finished since.
- Work arrives in bursts: 15 April, 10 to 14 June, 20 July. Nothing since.
- Almost nothing is assigned. Two people appear, `CR` (Clifford Ressel) and `RI`. CR leads nearly every project.
- Linear's own onboarding issues TIL-1 to TIL-4 are still open from 15 April.
- Cycles, Initiatives and Import are still parked under "Try". None of the process machinery is switched on.

**Two project conventions**, worth following if you add one:

- 🤝 plus the customer name for engagements. Two carry real milestones, e.g. Arlo's `Engagement 1 (2026-06-10 → 2026-06-17)`.
- A plain capability name for product work: Nori CLI, AI gateway, Self-service, Agent ergonomics.

**Nine of eleven customer projects map onto HubSpot deals**: London → London Consoluting, Chorus → Chorus Health, Layer → Layerify.com, Arlo → Arlo Health, plus Tuva, Breezeway, Verci, College Walk and Impilo exactly. Apollo and Ashley Stewart have no matching deal. The two systems track the same customers with no link between them and are already drifting.

---

## TIL-17 is blocked on Clifford

`linear.app/tilework/issue/TIL-17` — "PostHog: feature flags, experiments & analytics", created by Clifford Ressel, still Backlog and unassigned.

Its scope is **feature flags, experiments and product usage analytics across sks, cli and handroll**. None of that is what was built here, which is marketing-site web analytics and attribution for noriagentic.com. Adjacent, not the same.

Claiming it was proposed and then correctly rejected as a title match rather than a scope match. Instead a comment was posted asking Clifford what he scoped it to and how Martin can support it.

Three ways to go once he replies:

- If TIL-17 does cover the marketing site, assign it and add the remaining PostHog work as sub-issues.
- If it does not, create a separate issue and link it as related.
- Either way, the flags and experiments half is untouched and should not be represented as handled.

---

## Security

A live Slack token beginning `xoxe.xoxp-` was pasted into the working chat during setup, and is therefore in that transcript. Revocation was requested immediately via **OAuth & Permissions → Revoke All OAuth Tokens**, or by deleting the app outright.

**This has not been independently verified as revoked.** Confirm it.

A second exposure followed: the Incoming Webhooks settings page was pasted into the same chat, and Slack's "sample curl request" on that page renders the real webhook URL once one exists. Lower severity than the token, since a webhook only permits posting into one channel and reads nothing, but it allows anyone holding it to post there. The fix is to delete the webhook on that page, add a new one, and replace the `POSTHOG_SLACK_KEY_GROWTH` secret.

**Both exposures need confirming as closed.** Neither has been independently verified.

The general rule this establishes: never paste a settings page into a chat. Screenshot the part you need, or describe it.

Customer email addresses appearing in the HubSpot docs were redacted to `<redacted>@domain` before those files were committed here, since this repo is public. The domains are kept because the analysis is about domain matching. Re-check this if the docs are ever regenerated from source.

---

## Still open

**PostHog** — full click-by-click steps in `nori_posthog_setup_guide.md`:

1. **usenori.ai.** Four domains report into project 532714: noriagentic.com, usenori.ai and two `ta-01k…` preview sandboxes. Only noriagentic.com is authorized. Decide whether usenori.ai is a separate product, in which case give it its own project rather than filtering forever.
2. **Internal-user filter.** The filter exists but "enable on all new insights" is off, so your own visits are in every number, including this digest.
3. **Conversion goal.** None defined. The site's real conversion is the free-trial signup, and the funnel crosses to `login.norisessions.com`, which may not be instrumented in this project. Until a goal exists, PostHog counts arrivals and cannot judge them.
4. **Reverse proxy.** Not configured, so ad blockers drop an estimated 10 to 25% of events. Every number is a floor. Lowest priority: it improves counting accuracy for an outcome that is still undefined.

**Slack** — no self-service link builder. See above.

**Linear** — awaiting Clifford's reply on TIL-17.

---

## Artefact

A one-page dashboard covering the first 24 hours after tracking went live, including the two setup gaps:
`https://claude.ai/code/artifact/12518484-84b2-49f3-93f4-6542f7f367d8`

It is a point-in-time snapshot with hardcoded numbers, not a live view. The live view is this repo's daily digest.
