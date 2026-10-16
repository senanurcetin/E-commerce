# GA4 Source Registry & First-party Commerce Lab Activation

Date: 2026-10-16. This document distinguishes the legacy ToyStore stream from the new NEXUS Commerce Lab. It is a configuration checklist, **not evidence of an active Google Analytics connection**.

## Existing sources — verified versus pending

| Entity | Source identity | What has been verified | Not established |
| --- | --- | --- | --- |
| Legacy **ToyStore Website** | GitHub Pages at `https://senanurcetin.github.io/GTM/`, source repo [senanurcetin/GTM](https://github.com/senanurcetin/GTM) | User's GA4 Data streams screenshot showed a ToyStore Website web stream; a later account detail confirmed it has an existing `G-...` Measurement ID. GitHub repo includes `GTM-T5RLNJ6H` and GA4-compatible dataLayer events. | Active GA4 event delivery, past visitor volume, ownership of old historical commerce records, or correct published GTM event tags |
| **NEXUS-Web** | Another web stream in the same Analytics Data streams list | A web stream named NEXUS-Web exists | Its site URL was not shown; **do not assert it is the portfolio** without inspecting the stream details |
| **NEXUS Commerce Lab** | Our separately deployed `https://nexus-commerce-lab.vercel.app/` | Vercel production HTTPS served HTTP 200; standalone storefront/consent-first `lab_*` event logic and CI verified | **New `G-F0B2EQVC8M` configured on Vercel production and `/config.js` verified**; GA4 event receipt, read-only API access and GSC ownership remain unverified |
| Historical **E-Commerce / TheLook-style dataset** | Existing `events`, `order_items`, `products`, `users` warehouse | dbt models and CI test contracts | No evidence that either ToyStore or Commerce Lab generated historical warehouse transactions |

**Preserve the old ToyStore stream unchanged.** It is valuable as a separate past instrumentation prototype but is not a compatible first-party Commerce Lab identity. Do not repoint its web URL, place its `G-...` ID into the Commerce Lab Vercel build, or copy the old GTM container as a workaround.

### Why not reuse the old GTM container?

The legacy ToyStore layout loads `GTM-T5RLNJ6H` in the page head, and its source events are mapped to `add_to_cart`, `remove_from_cart` and `begin_checkout`. The actual GA4 configuration and event-routing tags live **inside GTM**, outside the GitHub repo. Thus they cannot be audited from source alone. The legacy contact-form `dataLayer` can include a name/email: do not forward that payload to GA4, as personal data transmission would be inappropriate. The new Lab uses an independent direct GA4 integration that stays off until explicit visitor consent.

## Recommended new owner-controlled GA4 property

To keep property-wide acquisition/conversion reports unambiguous, **create a separate GA4 property**, not merely another stream within an existing portfolio property.

1. In [Google Analytics](https://analytics.google.com/), open **Admin → Create → Property**. Set name to `NEXUS Commerce Lab`, choose the relevant Turkey time zone and report currency. Currency configuration does **not** authorize real revenue claims.
2. Complete the property wizard, then under **Data collection and modification → Data streams → Add stream → Web**, set the Website URL to `https://nexus-commerce-lab.vercel.app/` and the stream name to `Commerce Lab Web`.
3. Copy the new **Measurement ID** (format `G-...`). It is different from the purely numeric **Stream ID** and numeric **Property ID**. Share the new Measurement ID for deployment; **do not send account passwords, service-account files, private keys, or cookies**.
4. The publisher configures `NEXUS_GA4_MEASUREMENT_ID` on the **nexus-commerce-lab** Vercel project and redeploys that project only. No editing of legacy ToyStore or personal portfolio deployments is necessary.
5. After deployment, check public `/config.js` displays **only the new public `G-...` ID** (and never the ToyStore measurement ID), and verify default analytics status remains disabled for visitors who have not consented.
6. Open the public Lab, explicitly **Allow analytics**, and perform a manual browse → add cart → remove cart → test checkout sequence. Check the correct **new GA4 property** in Realtime (or DebugView with a debug-enabled client) for `lab_*` events. Google reporting can take time; do not invent event counts or claim success before they appear.
7. Confirm `purchase`, `transaction_id`, `value`, real payment and customer PII are **not** sent. Lab completion is an independent, clearly labeled testing event.
8. When authorized, configure the read-only GA4 collector using the new **numeric GA4 Property ID**, with least-privilege credentials, and reconcile date/time zone and custom events. Source labels must distinguish real consenting visitors to the Lab from historical TheLook seed transactions.

## Release acceptance gates

- [x] Separate ToyStore site and stream identified by user account UI and matching source repo
- [x] New Lab source served on first-party Vercel production alias with valid HTTPS
- [x] New Lab code/CI verifies consent gating and `lab_*` event limitations
- [x] New **Commerce Lab** GA4 web stream created and `G-F0B2EQVC8M` provided by owner
- [x] Production-only Vercel environment configured with new ID; Git deployment READY
- [x] Public `/config.js` verified with new ID and old ID absent; no-tag-before-opt-in contract covered by CI (independent browser QA pending)
- [ ] New GA4 Realtime/DebugView confirms at least one genuine opted-in `lab_*` event
- [ ] Read-only data extraction authorized and dashboard aggregates reconciled
- [ ] Separate Search Console property verified (optional); indexability decision explicitly made
- [ ] Final case-study screenshot review includes collection date, GA4 property and `LAB / TEST` disclaimers

No step above licenses mixing the personal portfolio, old ToyStore, external demo stores or historical warehouse sources.
