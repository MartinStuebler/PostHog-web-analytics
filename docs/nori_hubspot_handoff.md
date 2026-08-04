# Nori HubSpot: structure handoff

Written 2026-07-28. Everything below was verified in the live portal or computed from the source files on this date. Where something is inferred rather than observed, it says so.

---

## 1. Portal facts

- Portal 246881090, account "Nori"
- Host is `app-na2.hubspot.com`. Direct URLs on `app.hubspot.com` 404.
- Plan tier is Starter. Custom association labels are gated behind an upgrade (verified: the label picker shows only "Upgrade your plan to create and use custom labels").
- Contact cap 1,000. Currently 999, and the banner now reads "You've reached your 1,000 contact limit."

### Record counts, observed

| Object | Type ID | Records | Properties |
|---|---|---|---|
| Contacts | 0-1 | 999 | 217 |
| Companies | 0-2 | 473 | 118 |
| Deals | 0-3 | 29 | 80 |
| Calls | 0-48 | 2 | 39 |

Everything else (Tickets, Quotes, Invoices, Line items, Orders, Payments, Carts, Contracts, Notes, Tasks, Meetings, Emails) is at 0 records. The portal is three objects deep, not more.

### Useful record IDs

- Import job: `189475673`
- Deal "Breezeway": `339257648872`
- Deal "AMROK": `339224477391`
- Contact "Marc" (<redacted>@breezeway.io): `527820039916`
- Company "FullCircl, an nCino company" holding domain `linkedin.com`: `337237500636`

---

## 2. The model

Three record tables and a separate association layer. The association layer is not a column on any record. It is its own thing, and that is the single most important structural fact.

**Keys**

- Contact: `email`. Enforced. 999 rows, 0 duplicate emails, 0 blank emails.
- Company: `domain`. Enforced. This is what rejected 15 rows on the companies import.
- Deal: none. HubSpot has no natural key for deals. 29 deals carry only 22 distinct names, so 7 names appear twice. Re-running the import would create 29 more deals, not update the existing ones.

**Association cardinality and labels, read from the Data Model Builder**

- Deal to Company: 1-to-many, labels available `Deal with Primary Company (1-to-many)` and `Primary (1-to-1)`
- Deal to Contact: 1-to-many, no labels
- Contact to Company: 1-to-many, labels `Contact with Primary Company` and `Primary (1-to-1)`
- Contact to Contract: label `Billing Contact (1-to-many)`
- Deal to Deal is also a valid association

"Primary" is not a field on the record. It is a label attached to the link itself. That distinction is what a flat spreadsheet cannot express.

**Associations are queryable as properties.** Filtering contacts by `Primary Associated Company ID is known` works, and the "view all associated" links build temporary views using `associations.<objectTypeId>`. In spreadsheet terms, the join is a first-class citizen you can filter on.

---

## 3. The finding that matters

The contact layer and the company layer are two almost entirely disjoint populations.

- 999 contacts span 242 distinct email domains. 644 of them are `gmail.com`. Others in the top set: icloud.com 18, outlook.com 17, nyu.edu 15, hotmail.com 12, topoteretes.com 10, yahoo.com 8, columbia.edu 5.
- 473 companies span 471 business domains.
- Domains present in both sets: **exactly one**, `breezeway.io`.

Verified live: filtering Contacts on `Primary Associated Company ID is known` returns **1 contact out of 999** (Marc). The other 998 contacts are attached to nothing.

This is not an import defect. The two lists were never the same population:

- Contact `source` values are events and newsletters: "Agentics: Use Agents Effectively" 474, "Substack subscribers" 335, "Agentics Biweekly: Personalizing Agents" 144, Luma 15, Customers 9, Stripe 7, Cold 7, "Agentics: Agent Integrations" 7, Gmail 1.
- Contact `lifecyclestage`: subscriber 967, lead 22, customer 10.
- Companies are a B2B target list, every row carrying an employee count.

So: an audience list and a prospect list, sitting in the same CRM, touching in one place.

The contacts file does carry a free-text `company` column (636 of 999 rows filled), but text is not a link. HubSpot only auto-associated the one contact whose email domain matched a real company domain.

---

## 4. What the deals import proved about import mechanics

Result: 29 rows in, 29 deals created, 10 existing records updated, 11 new associations, 12 errors. Contacts stayed at 999, none created.

The `assoc_company_domain` and `assoc_contact_email` columns are **not stored as data**. HubSpot reads the value, looks up the record whose key equals it exactly, writes a link row, and discards the text. Three things govern the outcome:

1. **The object must be selected at step 1.** With only Deals selected, the "Import as" dropdown offers only "Deal properties" or "Don't import". Selecting Contacts and Companies too is what unlocks mapping the column to `Company / Company Domain Name` and `Contact / Email`.
2. **Import mode decides what a miss does.** Update-only means a miss is skipped silently as an error row. Create-or-update would have created junk records and, for Contacts, eaten the last slot under the 1,000 cap.
3. **Matching is exact.** No fuzzy match, no name match.

All 12 errors were "update only import", i.e. lookup found nothing:

- 10 company domains: amrok.space, corvusapp.com, toplinepro.com, impilo.health, withlantern.com, layerfi.com, usetelos.ai, survey-bot.ai, revgroup.xyz, pangramlabs.com. Cross-checked against `companies_import_clean.csv`: only breezeway.io was ever in that file. Those 10 companies do not exist in the CRM.
- 2 contact emails: <redacted>@usetelos.ai, <redacted>@survey-bot.ai.

Coverage ceiling worth knowing: of 29 deals, only 11 carry a company domain and 11 carry a contact email, 9 carry both, and **16 carry neither**. Even with perfect data, 16 deals would still link to nothing.

Also: a contact-consent attestation checkbox is mandatory at step 4 whenever the file pulls Contacts into the import, even when contacts are update-only and none are created. It was ticked on Martin's explicit confirmation that these are the same already-attested contacts.

---

## 5. Live test performed and reverted

To confirm the association layer behaves as a join table rather than a field:

1. Added a second contact (Alphalex) to the Breezeway deal. It accepted both, no "primary contact" forced, no overwrite. Many-to-many confirmed.
2. Opened the label picker on that link. Only built-in labels exist; custom labels require a plan upgrade.
3. Removed the association. Confirmed the dialog wording: "Alphalex will no longer be associated with Breezeway." The contact record itself is untouched. Removing a link is not deleting a record.

Breezeway deal is back to exactly its prior state: 1 contact (Marc), 1 company (Breezeway, badged Primary).

A temporary Advanced Filter was added to the All Contacts view during the count above and then deleted. The view is back to 999 with no advanced filters. No emails were sent. No records were created or deleted.

Notable: the deals import applied the `Primary` label to the deal-company link automatically, but applied no label to the deal-contact links.

---

## 6. How people usually DIY this, and where that advice is wrong

Mainstream guides ([HubSpot](https://blog.hubspot.com/sales/crm-google-sheets), [Copper](https://www.copper.com/resources/how-to-use-google-spreadsheet-crm-templates), [Capsule](https://capsulecrm.com/blog/google-sheets-crm-template/), [NetHunt](https://nethunt.com/blog/google-sheets-crm/)) converge on the same shape: tabs for Contacts, Companies, Deals, Activities, plus a dashboard, linked by writing a company name or contact email directly into the deal row. Copper's guidance is literally one row per deal linked to one contact.

That is a foreign key stored as a display string, and it is where the model diverges from what HubSpot actually does. It cannot represent a deal with two contacts, and it cannot carry a role on the link.

The failure modes are well documented and match what happened here:

- Flat sheets have [no concept of one record per contact and no validation](https://www.pipecrush.tech/blog/migrate-spreadsheet-to-crm), which is how duplicates accumulate structurally rather than by carelessness.
- Key choice is the root cause. [Overusing natural keys](https://agiledata.org/essays/keys.html) breaks as soon as the business value changes; a company renames, an email changes, and every reference silently rots. The counter-trap is a table with a surrogate key and no real key at all, which makes duplicates undetectable. Our deals table is exactly that trap: 29 rows, 22 distinct names, no key.
- HubSpot itself supports [up to 50 association labels per object pair](https://knowledge.hubspot.com/object-settings/create-and-use-association-labels) and configurable per-label limits, which is precisely the layer the spreadsheet guides drop.

Practical conclusion: follow the mainstream tab layout, but do not follow the mainstream linking advice. Use IDs and join tabs.

---

## 7. Spreadsheet rebuild spec

Five tabs.

**`contacts`** — contact_id, email, firstname, lastname, company_name_text, linkedin, lifecyclestage, source
**`companies`** — company_id, name, domain, employees
**`deals`** — deal_id, dealname, pipeline, dealstage, amount, achievable_mrr, optimistic_mrr, expected_conversion_pct, churned
**`deal_contacts`** — deal_id, contact_id, label
**`deal_companies`** — deal_id, company_id, label

Rules that carry over from what was verified above:

1. `*_id` columns are yours, arbitrary, permanent, never reused. Do not key on name, email, or domain. Keep email and domain as the *match* columns, not as the identity.
2. One row per link in the join tabs. A deal with two contacts is two rows. This is the part the mainstream templates get wrong.
3. The `label` column is where `Primary` lives. It belongs on the link, not on the deal and not on the company. Note that this gives the spreadsheet a capability the current Starter plan does not have, since custom labels are upgrade-gated in HubSpot.
4. Build the join tabs with XLOOKUP on email or domain to resolve an id, wrapped in IFNA. Every IFNA miss is the exact equivalent of one of the 12 import errors. Do not let a miss write a blank; let it write an error marker so it stays visible.
5. `company_name_text` on contacts stays free text and is explicitly not a link. 636 contacts have it filled and only 1 has a real company link. Keeping the two visibly separate is the whole lesson.
6. Add a `dedupe_key` column to `deals` if deals should be unique on something. Right now nothing makes them unique, which is why a re-import duplicates rather than updates.

---

## 8. Open issues for the next session

**A. Junk company domains, unresolved and still live.** The companies source file had 17 rows carrying a non-company domain: 14 with `linkedin.com`, 3 with `bit.ly`. HubSpot kept the first of each and rejected the other 15 as duplicate domains. The survivor holding `linkedin.com` is the record named "FullCircl, an nCino company" (id 337237500636), which now displays with a LinkedIn logo and lifecycle stage Lead. It currently has 0 associated contacts and 0 deals, so no wrong link exists *yet*. The live risks are (i) any future company import with a real LinkedIn URL in the domain column dedupes against it, and (ii) any contact with a `@linkedin.com` email would auto-associate to "FullCircl". There are currently 0 such contacts. Fixing this means blanking the domain on those 17 source rows and re-importing the 15 lost companies. Not done, awaiting Martin's decision.

**B. One unexplained company record.** 487 source rows minus 15 rejected duplicates should give 472 companies. The portal shows 473. The extra record has not been identified. Sorting by create date shows every company created at 11:05 AM, so nothing stands out. Worth resolving before trusting company counts.

**C. The 10 missing companies.** The companies behind 10 of the 11 deal-company links do not exist in the CRM at all. Options: add them to a companies import, or accept that those deals stay company-less. Related to A, since fixing A frees up domain slots.

**D. 16 deals have no association data.** Nothing to fix technically; it is a source-data gap. Flagging it so nobody hunts for a bug.

---

## 9. Working agreements

- Reply in roughly 50 words. No em-dashes.
- Never invent data. Unknown means blank.
- Stop and ask rather than guess when a UI path differs from expectation.
- Do not tick legal attestations without explicit confirmation. The confirmation given for the contact list does not extend to anything new.
- Do not send email from HubSpot.
- Screenshot after every dropdown selection and verify the label before moving on. The mode dropdowns land one row off often enough to matter.
- Panels animate in. Wait 5 seconds after navigation, then use `find` to get refs rather than raw coordinates. The viewport also resizes between 1050x728 and 1316x912 mid-flow, which invalidates coordinates.
