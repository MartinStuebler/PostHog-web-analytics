# Build spec: UTM link builder in Slack Workflow Builder

For the agent with Slack workspace access. Nothing in this spec has been built yet. I could not reach the workspace (`app.slack.com/client` redirects to a workspace sign-in and I do not authenticate), so every step below is unexecuted. Treat it as a build order, not a report.

Written 2026-07-30 for the Nori workspace.

---

## 0. Why this exists

noriagentic.com sends 53% of its traffic to the Direct bucket. Direct is not a channel, it is the residual bin for anything analytics cannot attribute. A known Luma visit is already landing there because someone hand-rolled `?referrer=luma#agentics`, which is not a parameter any analytics tool reads.

PostHog reads standard `utm_*` parameters natively. The fix is that people tag links. They will only tag links consistently if tagging is easier than not tagging, and if the vocabulary is chosen for them.

**The point of this build is the fixed vocabulary, not the string concatenation.** If any field is left as free text, you will get `linkedin`, `LinkedIn`, `li` and `linked-in` as four distinct sources within a month, and the reporting is worse than before. Every taxonomy field below must be a dropdown. This is the single requirement not to compromise on.

---

## 1. Known limits of the chosen tool

Martin chose Workflow Builder deliberately, over a hosted form and over a real slash command, with these limits accepted:

- Workflow Builder interpolates variables into a message string. It does **not** URL-encode, slugify, lowercase, or validate.
- Therefore a destination URL that already contains `?` produces a malformed double-query link. Mitigated below by instruction, not by code. It cannot be fixed inside this tool.
- Therefore a free-text campaign produces values like `Agentics July`. Mitigated below by making campaign a dropdown.

If either limit starts biting in practice, the upgrade path is section 7.

---

## 2. Trigger

Use a **link trigger** (the shareable-link trigger type), so the workflow can be pinned in a channel and started by anyone who clicks it.

- Workflow name: `UTM link builder`
- Description: `Build a tagged link so PostHog can attribute the traffic.`
- After publishing, pin the workflow link in the channel where marketing links get shared.

If your Workflow Builder version offers a channel shortcut trigger instead, that is equally fine. The trigger type is the one thing you may substitute freely.

---

## 3. Step 1 — Collect info in a form

Form title: `Build a tagged link`

Four questions, in this order.

### Q1. Destination URL
- Type: **Short answer**
- Required: yes
- Label: `Page URL`
- Help text, verbatim: `Paste the plain page URL. It must not already contain a "?" — if it does, strip everything from the "?" onward first.`

### Q2. Source
- Type: **Dropdown** (single select)
- Required: yes
- Label: `Where is the link going? (utm_source)`
- Options, exactly these twelve, lowercase:

```
substack
luma
linkedin
x
slack
whatsapp
email
github
hn
reddit
podcast
partner
```

### Q3. Medium
- Type: **Dropdown** (single select)
- Required: yes
- Label: `What kind of placement? (utm_medium)`
- Options, exactly these six, lowercase:

```
social
email
dm
referral
qr
paid
```

### Q4. Campaign
- Type: **Dropdown** (single select) — **not short answer**
- Required: yes
- Label: `Which push is this part of? (utm_campaign)`
- Seed options:

```
evergreen
launch
newsletter
agentics-2026-07
agentics-2026-08
```

Campaign is a dropdown specifically to stop unslugified free text entering the data. Adding a new campaign is a deliberate act: edit the workflow, add the option, republish. Document that in section 6 so people know the path exists and do not route around it.

---

## 4. Step 2 — Send a message

Send to: **Person who used this workflow.** Not the channel. Keeps the channel clean and means nobody has to see thirty half-built links.

Message body. Type the literal text, and insert each variable with the **Insert a variable** control — do not type the brace placeholders by hand, they will post as literal text:

```
Your tagged link:

[Page URL]?utm_source=[Source]&utm_medium=[Medium]&utm_campaign=[Campaign]

Check before you use it: there should be exactly one "?" in that URL. If you see two, the page URL already had parameters on it — strip them and run this again.
```

Each `[Name]` above is a variable picker insertion referencing the matching form answer, not typed text.

Wrap the URL line in backticks in the Slack message so it renders as code and copies cleanly without smart-quote or autolink mangling.

---

## 5. Step 3 — Log it (optional, recommended)

Add a second **Send a message** step posting to a low-traffic channel, e.g. `#utm-log`:

```
[Person who used this workflow] built a link
source [Source] · medium [Medium] · campaign [Campaign]
[Page URL]
```

Reason to include it: a visible log is the only governance this design has. If someone starts generating `medium=social` for what is plainly an email, you will see it. Without the log, taxonomy drift is invisible until it shows up as a mess in PostHog three months later.

Reason to skip it: it is one more channel. Martin's call.

---

## 6. Verify before you call it done

Run the published workflow four times and check each result by eye:

1. **Happy path.** `https://noriagentic.com/newsletter.html` + luma + social + `agentics-2026-07`.
   Expect exactly: `https://noriagentic.com/newsletter.html?utm_source=luma&utm_medium=social&utm_campaign=agentics-2026-07`
2. **The known break.** Paste `https://noriagentic.com/newsletter.html?referrer=luma` and confirm the output has two `?` and is therefore visibly wrong. You are confirming the failure is *loud*, not that it is absent. If it looks plausible, the help text in Q1 is not strong enough.
3. **Trailing slash.** `https://noriagentic.com/` should produce `https://noriagentic.com/?utm_source=...`, which is valid.
4. **Copy fidelity.** Copy the produced link out of Slack and paste it into a browser. Confirm no smart quotes, no trailing punctuation, and that the page loads.

Then confirm the far end: open PostHog project **532714**, web analytics, Sources tile, and check the tagged visit is attributed to the campaign rather than falling into Direct. That is the only test that matters. Everything above is plumbing.

---

## 7. Upgrade path, if this proves too blunt

Two failure signals to watch for, and what to do about each:

- **Malformed links keep appearing.** Workflow Builder cannot fix this. Move to a Slack slash command backed by a Cloudflare Worker or Vercel function: `/utm <url>` opens a modal with the same dropdowns, and the endpoint does real URL parsing, encoding, and slugification. Roughly an hour of work plus a workspace app install.
- **People stop using it and hand-write links again.** That is a friction problem, not a correctness problem. The hosted-form option (a single self-contained page pinned in the channel) is fewer clicks than a workflow and needs no app approval.

Keep the taxonomy in section 3 identical across any migration. The vocabulary is the asset; the interface is disposable.

---

## 8. Context the next agent may want

- PostHog project `532714`, US region, `us.posthog.com`. Reads `utm_*` natively. No conversion goals defined yet, so tagged traffic will show attribution but not outcomes until one exists.
- Site is noriagentic.com, live about two years, but PostHog tracking only started 2026-07-29. Prior-period comparisons will read zero for a while; that is the measurement age, not the traffic.
- Current channel split over the first 24 hours: Direct 18 visitors, Organic Search 10, Referral 6. The purpose of this build is to move mass out of that first bucket.
- The source list in Q2 was drawn from real values already in the HubSpot contact data (Substack, Luma, three Agentics events, Stripe, Cold) plus the dark-social channels that misattribute to Direct. It is deliberately short. Resist requests to extend it past about fifteen entries; long taxonomies get ignored and people improvise again, which is the original problem.
