# PostHog setup guide, click by click

Project `532714`, US region, `us.posthog.com`. Every path below was walked in the live product on 2026-07-31. I changed nothing; all steps are unexecuted.

---

## Read this first: the dashboard undercounts a problem

The Web analytics domains screen lists four domains PostHog has seen events from in the last three days:

1. `https://noriagentic.com`
2. `https://usenori.ai`
3. `https://ta-01kysj5jhh2wche4fe…` (preview host)
4. `https://ta-01kyw19bpfkwekys3…` (preview host)

I had reported one preview environment polluting the data. It is worse than that. **There are two separate production domains and two preview hosts, all reporting into one project.** The "34 visitors, 77 pageviews" figure is noriagentic.com plus usenori.ai plus two sandboxes, added together.

Nothing below matters as much as separating these. Do step 1 and 2 before you read the rest.

Also note the screen says plainly: **"There are no authorized URLs."**

---

## Step 1 — Authorize the real domains

**Settings → Project → Web analytics**, or go direct to
`us.posthog.com/project/532714/settings/project-web-analytics`

Under **Web analytics domains**:

1. Find the row `SUGGESTION  https://noriagentic.com` and click **Apply suggestion**.
2. Decide about `https://usenori.ai` before touching it. See step 2.
3. **Do not** apply either `ta-01kysj…` or `ta-01kyw19…`. Those are the preview hosts. Applying them tells PostHog to treat sandbox traffic as real.

If you prefer to type them, **Add new authorized URL** takes a concrete URL. Wildcards are rejected; the help text states URLs must be concrete and launchable.

---

## Step 2 — Decide what this project is measuring

You have a fork here, and it is a real decision, not a setting.

**Option A, cleanest: one project per site.** noriagentic.com stays in project 532714, usenori.ai gets its own project and its own snippet key. Separate baselines, no cross-contamination, no filtering discipline required forever.

**Option B, faster: keep both, always segment.** Authorize both domains, then use the **All domains** dropdown at the top of Web analytics to look at one site at a time. Works, but every chart is wrong by default and right only when someone remembers to filter. Given the last 24 hours were read without that filter, assume it will be forgotten.

Recommendation: A, if usenori.ai is a distinct product rather than a marketing alias. The two-minute cost now is smaller than permanently untrustworthy numbers.

Either way, get the preview hosts out. They are ephemeral sandbox URLs and nothing good comes from them sitting in a production project.

---

## Step 3 — Turn the internal-user filter on by default

**Settings → Project → Customization**, or
`us.posthog.com/project/532714/settings/project-customization`

Scroll to **Filter out internal and test users**. A filter already exists there: a chip reading `User not in Internal / Test users`. It is defined but not applied.

Below it, the toggle **"Enable this filter on all new insights"** is **off**. Turn it on.

That toggle is why the Web analytics header shows *Filter test accounts* switched off, and why the 34 includes you. There is a second toggle, *Filter out internal and test users from revenue analytics*, also off; irrelevant until revenue data exists.

Then add a rule to that filter matching the preview hosts, so sandbox sessions are excluded even if someone re-authorizes them later. Click **+ Filter** beside the existing chip and match on Current URL containing `ta-01k`.

---

## Step 4 — Define one conversion goal

Right now PostHog counts visitors and cannot tell a good one from a bad one. Web analytics shows an empty **Track your conversions** card confirming none exists.

1. Go to **Web analytics**.
2. Scroll to the **Track your conversions** card.
3. Click **New action**.
4. Define the action for a newsletter signup: match on the form submit or the button click on `/newsletter.html`. If the page has no distinct success state yet, the honest first goal is a pageview of a thank-you or confirmation URL, which may mean adding one to the site.
5. Save, then return to Web analytics; the conversion tile will populate from that action forward.

Note it is not retroactive in a useful sense for click-based actions, so the sooner this exists the sooner it is worth reading.

---

## Step 5 — The broken-snippet alert

This is the highest-value alert for a site instrumented three days ago. If a deploy drops the snippet you want to know that day.

1. **Product analytics** in the left nav. There is an **Alerts** tab beside All insights / My insights / History.
2. Alerts attach to a saved insight, so first save one: open the hourly unique-visitors trend, name it something like `Daily unique visitors`, and save it. The existing `Unique visitors unique users` insight is currently a **Draft** with unsaved changes stored only in the browser, so it cannot carry an alert as-is.
3. From the saved insight, open the **…** menu and create an alert.
4. Condition: daily unique visitors **below 5**. Deliver to email.

Five is a floor chosen to be obviously abnormal rather than merely quiet. Raise it once you know the site's real baseline.

---

## Step 6 — Confirm UTM attribution actually works

Do this after the Slack link tagger is live. It is the only test that proves the tagging effort is paying off.

1. Build one tagged link, e.g.
   `https://noriagentic.com/?utm_source=linkedin&utm_medium=social&utm_campaign=agentics-2026-07`
2. Open it yourself in a browser where you are not excluded by the internal filter, or temporarily switch the filter off.
3. **Web analytics → Sources** tile. The visit should appear under the campaign rather than falling into Direct.

If it lands in Direct anyway, the parameters are malformed. Check for a double `?` first, that is the failure mode the Slack workflow cannot prevent.

---

## Not yet: reverse proxy

Installation Health flags it, and it is genuinely why 34 is a floor rather than a count: without it ad blockers drop an unknown share of events. But it is the most engineering work on this list and it only makes counting more accurate. Counting an undefined outcome more accurately is still not insight. Do steps 1 to 5 first.

---

## Order of operations

1. Authorize noriagentic.com, refuse the preview hosts (2 min)
2. Decide the usenori.ai question, split projects if A (15 min)
3. Enable the internal filter by default, add the `ta-01k` exclusion (5 min)
4. Save an insight and attach the below-5 alert (10 min)
5. Define the newsletter conversion goal (30 min, may need a site change)
6. Verify a tagged link lands in the right bucket (5 min, after Slack)

Steps 1 to 3 are pure hygiene and should happen before another week of data accumulates against a dirty baseline.
