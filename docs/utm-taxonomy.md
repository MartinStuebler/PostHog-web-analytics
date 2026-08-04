# UTM taxonomy for noriagentic.com

The vocabulary is the asset. The tool that generates the links is disposable.

If any field is free text, you get `linkedin`, `LinkedIn`, `li` and `linked-in` as four separate sources within a month, and the reporting is worse than before you started. Every field below except campaign is a fixed list on purpose.

PostHog reads standard `utm_*` parameters natively. It reads no other convention. The older `?referrer=luma` pattern found on some links does nothing at all and should be replaced wherever it appears.

---

## The fields

**`utm_source`** — where the link is going. Fixed list:

```
substack  luma  linkedin  x  slack  whatsapp
email     github  hn  reddit  podcast  partner
```

**`utm_medium`** — what kind of placement. Fixed list:

```
social  email  dm  referral  qr  paid
```

Default pairing when someone names a place but not a medium:

- linkedin, x, reddit, hn → `social`
- slack, whatsapp → `dm`
- substack, email → `email`
- luma, github, podcast, partner → `referral`

**`utm_campaign`** — free text, but always slugified and date-stamped. Lowercase, hyphens, no spaces, suffixed `-YYYY-MM` unless the name already carries a date. `Agentics July` becomes `agentics-2026-07`. With no campaign given, use `evergreen`.

**`utm_content`** — **omit it.** This is the field that makes two links to the same page distinguishable, and it is tempting. At roughly 30 to 50 visitors a day, splitting one campaign across content variants produces rows of two and three visitors that cannot support a decision. Add it only when genuinely testing two versions of the same thing, and then use short slugs: `post-1`, `post-2`.

**`utm_term`** — never. Paid search only, not in use.

Parameter order is always `utm_source`, `utm_medium`, `utm_campaign`. Consistent ordering makes links visually comparable at a glance.

---

## Building a link

1. Take the plain page URL. **Drop any existing query string entirely.** This is the main job. A URL that already contains `?` produces a malformed double-query link.
2. Match what the person said to the source list. `LinkedIn`, `Linkedin` and `li` all resolve to `linkedin`. If nothing matches, ask. **Never invent a new source value.**
3. Resolve medium from the pairings above unless told otherwise.
4. Slugify and date-stamp the campaign.
5. Assemble in the fixed order.

Example:

```
https://noriagentic.com/newsletter.html?utm_source=luma&utm_medium=social&utm_campaign=agentics-2026-07
```

---

## Three things that silently destroy the data

**Never tag internal links.** A UTM on a link from one noriagentic.com page to another starts a fresh attribution and overwrites the visitor's original source. Someone who arrived from Luma becomes an internal referral. The site has newsletter pages linking to the homepage, so this is a live risk. UTMs go on inbound links only.

**Never put anything personal in a parameter.** No names, no email addresses, no per-recipient identifiers. URLs get shared, screenshotted and logged. If per-person attribution is needed, that is what PostHog's identify call is for, not a query string.

**Never tag the same destination two ways in one push.** Pick the string once and reuse it exactly. Retyping is how `agentics-2026-07` becomes `agentics-2026-7` and splits into two rows forever.

---

## Delivery

The taxonomy is independent of how links get built. Options considered, in `nori_slack_utm_workflow_spec.md`:

- Slack Workflow Builder form — chosen, then not built. It cannot parse URLs or slugify, so the two failure modes above stay live.
- A hosted form pinned in Slack — no app install, enforces the vocabulary, one click out of Slack.
- A Slack slash command backed by a small function — the real fix, needs hosting plus an app install.

Whichever gets built, keep this vocabulary unchanged. Resist extending the source list past roughly fifteen entries; long taxonomies get ignored and people improvise, which is the original problem.
