# Design brief: Nori CRM spreadsheet + email outreach logic

Handoff to the chat tasked with designing the spreadsheet CRM and the outreach logic. Everything here was verified in the live HubSpot portal (246881090, `app-na2.hubspot.com`) or computed from the three source files in `~/Downloads/` on 2026-07-28. Inferences are labelled as such.

Companion document: `nori_hubspot_handoff.md` covers the portal state and import mechanics in more detail. This one is the design brief.

---

## 0. Your mission and the one thing that should shape it

Design (a) a spreadsheet that models this CRM correctly and (b) the outreach logic that runs on top of it.

Before anything else, absorb this: **the contact list and the company list are two disjoint populations.** They overlap in exactly one record. This is not a data-quality bug to clean up; it is the actual shape of the business, and it means there are two separate outreach motions, not one. Any design that assumes "contacts work at companies, deals belong to both" will be wrong on contact with this data.

Evidence, verified live:

- 999 contacts span 242 distinct email domains. 644 are `gmail.com`.
- 473 companies span 471 business domains.
- Domains in both sets: **1** (`breezeway.io`).
- Filtering Contacts on `Primary Associated Company ID is known` returns **1 contact of 999**.

---

## 1. Source data profile

Three files in `~/Downloads/`. All figures computed, not estimated.

### `test999_hubspot_import.csv` — 999 rows

Columns: `email, firstname, lastname, company, LinkedIn, lifecyclestage, source`

- 0 blank emails, 0 duplicate emails. Email is a clean natural key.
- 636 rows have `company` free text. 628 have a LinkedIn URL.
- Top email domains: gmail.com 644, icloud.com 18, outlook.com 17, nyu.edu 15, hotmail.com 12, topoteretes.com 10, yahoo.com 8, columbia.edu 5.

`source` crossed with `lifecyclestage` is almost perfectly deterministic:

| source | lifecycle | n |
|---|---|---|
| Agentics: Use Agents Effectively | subscriber | 474 |
| Substack subscribers | subscriber | 335 |
| Agentics Biweekly: Personalizing Agents | subscriber | 144 |
| Luma | lead | 15 |
| Customers | customer | 9 |
| Cold | lead | 7 |
| Agentics: Agent Integrations | subscriber | 7 |
| Stripe | subscriber | 6 |
| Stripe | customer | 1 |
| Gmail | subscriber | 1 |

Totals: 967 subscriber, 22 lead, 10 customer.

**Design implication:** `lifecyclestage` is currently a function of `source`, with one exception. Treat lifecycle as derived, not independently entered, and make the derivation explicit. See the Stripe anomaly in section 8.

### `companies_import_clean.csv` — 487 rows

Columns: `company name, domain, numberofemployees`

- 0 duplicate company names. All 487 have an employee count.
- 17 rows carry a non-company domain: 14 `linkedin.com`, 3 `bit.ly`. HubSpot kept the first of each and rejected the other 15 as duplicate domains, which is why only 473 companies exist.
- **No contact ever attached to any of these companies.** They are a target list with no people in it.

### `deals_import_clean.csv` — 29 rows

Columns: `dealname, pipeline, dealstage, amount, achievable_mrr, optimistic_mrr, expected_conversion_percent, churned, assoc_company_domain, assoc_contact_email`

- 22 distinct deal names. 7 names appear twice. **No unique key exists.**
- Fill rates: amount 10/29, achievable_mrr 19/29, optimistic_mrr 19/29, expected_conversion_percent 19/29.
- Association coverage: 11 have a company domain, 11 have a contact email, 9 have both, **16 have neither**.
- 9 of the 11 contact emails belong to contacts whose lifecycle is `customer`. The link, where it exists, is meaningful.

`dealstage` crossed with `churned` is perfectly collinear:

| dealstage | churned | n |
|---|---|---|
| Closed Won (Paying) | FALSE | 9 |
| Free Trial/Activated | FALSE | 12 |
| Closed Lost | TRUE | 8 |

**Design implication:** `churned` carries zero independent information. Do not model it as a stored column; derive it as `dealstage = "Closed Lost"`. If you keep it as stored data, you have created a field that can disagree with itself.

---

## 2. The structural lesson from HubSpot

Copy this shape. It is the part that mainstream spreadsheet-CRM advice gets wrong.

**Records and keys**

| Object | HubSpot type ID | Dedupe key | Enforced? |
|---|---|---|---|
| Contact | 0-1 | email | yes |
| Company | 0-2 | domain | yes |
| Deal | 0-3 | none | n/a |

**Associations are a separate layer, not a column.** In HubSpot they carry:

- cardinality (Deal↔Company, Deal↔Contact, Contact↔Company are all 1-to-many)
- labels attached to the *link itself*, e.g. `Primary (1-to-1)`, `Deal with Primary Company (1-to-many)`, `Contact with Primary Company`, `Billing Contact (1-to-many)` on Contact↔Contract
- queryability: associations are filterable as properties (`Primary Associated Company ID`, `associations.<typeId>`)

Verified by live test: a deal accepts two contacts simultaneously, no primary is forced, nothing is overwritten. The deals import auto-applied `Primary` to the deal-company link and applied no label to deal-contact links.

**Constraint worth exploiting:** custom association labels are gated behind a plan upgrade on this Starter portal. The spreadsheet can carry a role on every link for free. That is a capability the live CRM does not currently have, and it is a legitimate reason for the spreadsheet to exist.

---

## 3. Spreadsheet spec

Seven tabs. The first five are the CRM; the last two are the outreach machinery.

**`contacts`** — contact_id, email, firstname, lastname, company_name_text, linkedin_url, source, lifecycle_stage, consent_basis, consent_date, email_status, do_not_contact, created_date

**`companies`** — company_id, name, domain, employees, target_tier, has_known_contact, created_date

**`deals`** — deal_id, dealname, pipeline, stage, amount, achievable_mrr, optimistic_mrr, expected_conversion_pct, created_date
(no `churned` column; derive it)

**`deal_contacts`** — deal_id, contact_id, label
**`deal_companies`** — deal_id, company_id, label
**`contact_companies`** — contact_id, company_id, label

**`outreach_log`** — send_id, contact_id, campaign_id, sequence_step, sent_at, channel, outcome, replied_at, unsubscribed_at

Rules, each traceable to something observed above:

1. **Surrogate ids everywhere.** `*_id` are arbitrary, permanent, never reused. Email and domain stay as *match* columns, never as identity. The deals table proves why: 29 rows, 22 names, nothing unique.
2. **One row per link.** A deal with two contacts is two rows in `deal_contacts`. This is the whole point.
3. **`label` on the link, not the record.** This is where `Primary` lives, and where roles like Billing Contact or Champion would live.
4. **Resolve with XLOOKUP wrapped in IFNA, and let misses be loud.** Every IFNA miss is the exact equivalent of one of the 12 errors the real import threw. A miss must never silently write a blank.
5. **`company_name_text` is explicitly not a link.** 636 contacts have it filled; 1 has a real company link. Keeping these visibly separate is the central lesson of this dataset.
6. **Derive, do not store, anything collinear.** `churned` from stage. `lifecycle_stage` from `source` unless deliberately overridden, with the override made visible.
7. **Add a deal dedupe key** or accept that re-imports duplicate. Suggest `dealname + created_date` or an explicit external id.
8. **Validation:** email regex on `contacts.email`; domain-shaped check on `companies.domain` that rejects `linkedin.com`, `bit.ly`, and any known URL shortener or social host. This one rule would have prevented the 15 lost companies.

---

## 4. The outreach picture: two motions, not one

### Motion A — audience nurture (999 contacts, ready today)

This is a newsletter and event audience, not a prospect list. 961 of 999 are `subscriber` lifecycle. 644 have gmail addresses. They arrived from Substack, three Agentics events, and Luma.

- Consent basis is opt-in marketing (newsletter signup, event registration). Martin has confirmed in writing that this list is attested as expecting to hear from Nori.
- This motion can start immediately.
- It is a broadcast/nurture motion. It is not personalised B2B sales outreach, and treating it as such would be both a deliverability mistake and a consent overreach.

### Motion B — company prospecting (473 companies, blocked)

- 473 companies, every one with an employee count, **zero contacts attached to any of them**.
- You cannot email a company. There is nobody to email.
- This motion is blocked on a contact-sourcing step that does not exist yet.
- It is also blocked by the contact cap: the portal is at 999 of 1,000 and the banner reads "You've reached your 1,000 contact limit." Adding a single prospect contact requires deleting one or upgrading.

**Design the two motions separately with separate eligibility rules, separate consent bases, separate templates, and separate suppression logic.** Do not build one funnel and filter it.

### The 7 cold contacts

`source = Cold`, lifecycle `lead`, 7 records. These are the only contacts in the database with no opt-in basis. They need their own handling and must be excluded from anything sent under the marketing-consent attestation.

---

## 5. Email layer, verified state

| Fact | Value | How verified |
|---|---|---|
| Marketing emails created or sent | 0 | Marketing Email tool shows the first-run empty state |
| Contacts unsubscribed from all email | 0 | Advanced filter, `Unsubscribed from all email = True` → 0 contacts |
| Marketing contact tiering | not enabled | No `Marketing contact status` property exists on this portal |
| Contact cap | 999 of 1,000, cap reached | Banner on Contacts index |
| Calls logged | 2 | Data Model Builder |
| Tickets, Quotes, Invoices, Line items, Orders, Payments, Contracts, Notes, Tasks, Meetings, Emails | 0 records each | Data Model Builder |

So: a completely clean sending history and a completely clean suppression list. Everything the outreach design does from here is the first thing that has ever happened on this domain from this tool. Treat the first send as a reputation-establishing event, not a volume event.

---

## 6. Outreach logic the design must specify

Minimum set of decisions to nail down:

**Eligibility gate.** A contact is sendable only if all hold: `email_status` is valid, `do_not_contact` is false, `unsubscribed_at` is blank, `consent_basis` is non-blank and appropriate to the motion, and the contact is not inside a cooldown window from `outreach_log`.

**Suppression.** One suppression list, checked before every send, fed by unsubscribes, bounces, manual DNC, and role-address patterns (`info@`, `support@`, `admin@`, `eng@`). Note that one of the two failed deal-contact emails was `<redacted>@survey-bot.ai`, a role address.

**Frequency caps.** Per contact, per motion, per window. The 999-contact audience has never received anything, so there is no baseline; start conservative.

**Cooldown and reply handling.** A reply must halt the sequence for that contact. `outreach_log.replied_at` is the halt signal.

**Deliverability warm-up.** 644 gmail.com recipients on a domain with zero send history is the highest-risk possible first send. The design should specify a ramp (small batches, engaged-first ordering) rather than a single 999-recipient blast. Order by most recent event source first; the Agentics event cohorts are the freshest signal available.

**Segmentation seeds.** From the real data:
- 474 `Agentics: Use Agents Effectively` — largest single cohort
- 335 `Substack subscribers` — newsletter, likely highest tolerance for regular sending
- 144 + 7 remaining Agentics cohorts
- 15 Luma, 7 Cold — both `lead`, both small enough to handle manually
- 10 customers + 9 Closed Won deals — existing revenue, should be excluded from acquisition messaging entirely
- 12 deals at `Free Trial/Activated` — the highest-intent segment in the entire dataset, and the one most worth a bespoke motion

**Deal-driven triggers.** 12 deals sit at Free Trial/Activated with `churned = FALSE`. 8 are Closed Lost and churned. Trial-to-paid and win-back are the two obvious lifecycle motions, but note that only 9 deals have a contact link at all, so trigger coverage is thin until section 8's issues are fixed.

---

## 7. Hard rules

- **No emails are to be sent from HubSpot** until Martin says otherwise. This was an explicit instruction.
- **Never tick a legal attestation without explicit per-instance confirmation.** The confirmation given for the existing contact list does not extend to any new list, any new import, or any new motion.
- **Never invent data.** Unknown means blank.
- Reply in roughly 50 words. No em-dashes.
- Stop and ask rather than guess when a UI path differs from expectation.

---

## 8. Open issues that constrain the design

**A. Junk company domains, unresolved.** 14 source rows carry `linkedin.com` and 3 carry `bit.ly`. HubSpot kept the first of each and rejected 15. The `linkedin.com` survivor is the record named "FullCircl, an nCino company" (id `337237500636`), now displaying a LinkedIn logo. It has 0 contacts and 0 deals, so the damage is latent, not active. Risks: any future company import with a LinkedIn URL in the domain column dedupes against it, and any contact with a `@linkedin.com` email auto-associates to it. There are currently 0 such contacts. Awaiting Martin's decision. **Your domain-validation rule in section 3.8 is the durable fix.**

**B. One unexplained company record.** 487 rows minus 15 rejected should equal 472. The portal shows 473. Not identified; every company shows a create date of 11:05 AM so nothing stands out. Do not trust company counts to the last unit until resolved.

**C. 10 of 11 deal-company links point at companies that do not exist.** amrok.space, corvusapp.com, toplinepro.com, impilo.health, withlantern.com, layerfi.com, usetelos.ai, survey-bot.ai, revgroup.xyz, pangramlabs.com. Only breezeway.io was ever in the companies file.

**D. 16 of 29 deals have no association data at all.** Source-data gap, not a bug. It caps how much of the deal-triggered outreach can ever fire.

**E. Stripe source anomaly.** 7 contacts have `source = Stripe`, implying payment, but only 1 is lifecycle `customer` and 6 are `subscriber`. Meanwhile 9 have `source = Customers` and all 9 are `customer`. Either the Stripe cohort's lifecycle is stale or the source is being used loosely. Resolve before using lifecycle as a revenue signal in any motion.

**F. 2 deal contact emails matched nothing:** `<redacted>@usetelos.ai`, `<redacted>@survey-bot.ai`. The second is a role address and should probably never have been a contact.

---

## 9. Reference

**Portal:** 246881090, `app-na2.hubspot.com`. Starter tier.

**Pipeline** "Nori Sales Pipeline", 8 stages: Lead 5%, Outreached 10%, Call Scheduled 25%, In Conversation 40%, Free Trial/Activated 60%, Contract Sent 80%, Closed Won (Paying) 100%, Closed Lost 0%. Only three are in use.

**Custom deal properties:** achievable_mrr, optimistic_mrr, expected_conversion_percent, churned.

**Record IDs:** import job `189475673`; deal Breezeway `339257648872`; deal AMROK `339224477391`; contact Marc `527820039916`; company FullCircl/linkedin.com `337237500636`.

**Files:** `~/Downloads/test999_hubspot_import.csv`, `companies_import_clean.csv`, `deals_import_clean.csv`, `nori_hubspot_handoff.md`.

**Portal state is clean.** A test association added during investigation was removed; temporary filters were deleted. No emails sent, no records created or deleted.

**External references used for the spreadsheet design:** [HubSpot's own Sheets CRM guide](https://blog.hubspot.com/sales/crm-google-sheets), [Copper](https://www.copper.com/resources/how-to-use-google-spreadsheet-crm-templates), [Capsule](https://capsulecrm.com/blog/google-sheets-crm-template/) and [NetHunt](https://nethunt.com/blog/google-sheets-crm/) all recommend linking tabs by writing a company name or contact email into the deal row. Follow their tab layout, reject their linking advice: it is a foreign key stored as a display string and cannot express a second contact or a role. On keys, see [natural vs surrogate](https://agiledata.org/essays/keys.html); on why flat sheets accumulate duplicates structurally, see [this](https://www.pipecrush.tech/blog/migrate-spreadsheet-to-crm). HubSpot supports [up to 50 association labels per object pair](https://knowledge.hubspot.com/object-settings/create-and-use-association-labels), which is the layer those templates omit.
