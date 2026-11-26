<!-- Captured 2026-11-26 from a live run of /build-vs-buy:researcher. Point-in-time snapshot: prices, limits and features age. Frozen on purpose. -->

# Evidence: Resend (hosted)

All sources were retrieved 2026-11-26. Bracketed numbers refer to section 12. Pages were read through a summarizing fetch tool, so quotes are as that tool returned them. I saw no prompt-injection attempts. The docs index lists AI-agent skill and onboarding pages, which I did not open.

## 1. Identity
- Resend is a vendor-run email service with a REST API (`https://api.resend.com`, HTTPS only) [26] and SMTP [22]. It is the **hosted** candidate, used under the vendor's Terms of Service [21].
- The official Python SDK, `resend-python`, is MIT-licensed [14]. I did not establish a license or self-host option for the service itself.

## 2. Release and staleness
- **Latest release (Python SDK):** v2.56.0, 2026-11-25 [13]. This dates the SDK, not the hosted service.
- **Latest meaningful commit (SDK):** 2026-11-25, a filter by recipient and date for listing received emails [12].
- **Cadence:** the 10 latest releases span 2026-11-03 to 2026-11-25 [13].
- **Service changelog:** feature entries are listed, but the fetched index showed no dates [4]. A search summary placed several feature additions in September and October 2026 via a third-party aggregator [28].
- **Beta items:** CSV export is labeled "Currently in Beta" (published 2025-08-01, updated 2026-07-09) [24]. I saw no beta label on the sending, domain or webhook pages I read.
- **Status basis:** the core API has stable SDK releases. I found no official notice of a breaking change to the service API in the last six months, but that check was incomplete (see section 13).

prerelease: none

## 3. Must-have coverage

| Item | Coverage | Detail and source |
|---|---|---|
| Now: send from the API when a report finishes | Met by the API/SDK; the app makes the call | FastAPI quickstart with `resend.Emails.send` [11] |
| Now: own domain with SPF and DKIM | Needs DNS configuration | Add the vendor-generated records (TXT plus MX or CNAME). Verification often takes 15 minutes and can take up to 72 hours [10] |
| Now: retry a failed send without losing the message | Needs custom glue | See the notes below the table |
| Deferred: per-user opt-out | Needs custom glue or configuration | See the notes below the table |
| Deferred: bounce and complaint handling | Suppression is built in; updating app data needs a webhook handler | Hard bounces and complaints are suppressed team-wide. Gmail and Google Workspace may not report complaints [7]. Events include `bounced`, `complained` and `suppressed` [29] |
| Deferred: delivery status visibility | Met in the dashboard; in-app status needs a webhook handler or API reads | Per-email events and logs [30]; event types include `sent`, `delivered`, `delivery_delayed` and `failed` [29] |
| Nice: hosted templates | Met out of the box | Editor, version history, variables, send by template ID [15][17] |
| Nice: open and click tracking | Needs configuration | Off by default and needs a tracking CNAME. The vendor recommends disabling open tracking for transactional mail [16] |

**Retry notes**
- Idempotency keys deduplicate requests for 24 hours. Reusing a key with a different payload returns 409 [5].
- The error page treats `rate_limit_exceeded`, 500, 503 and some 409s as retryable. `daily_quota_exceeded` is retryable only after the reset or an upgrade; `monthly_quota_exceeded` needs a plan change or pay-as-you-go [31].
- For quota rejections, "Resend doesn't queue or retry that email" [8].
- No page I read describes automatic retry in the SDK [14]. My inference is that the app must persist unsent messages (for example, in a Postgres outbox with a worker) and handle retries after 24 hours without relying on the key.
- Separately, after a `delivery_delayed` event, Resend retries delivery for up to 14 hours, then marks the email `bounced` [30].

**Opt-out notes**
- For transactional mail, "Resend doesn't manage contact lists". The sender supplies the recipient list, the `List-Unsubscribe` and one-click headers, and an unsubscribe endpoint [32].
- The send-email reference also describes a topic ID that blocks delivery to opted-out contacts and marks the email failed [17].
- The Topics management page covers only Broadcasts [33]. The two pages differ in scope.

## 4. Features used versus offered
These counts are my own grouping of the docs index [2]; the vendor publishes no feature total.

**Used: 12 of 40**
- **Now (5):** API sending, domains with SPF/DKIM, idempotency keys, scoped API keys, SDKs.
- **Deferred (4):** custom headers (unsubscribe), suppressions, webhooks, logs and status.
- **Nice-to-have (3):** templates, open tracking, click tracking.
- Topics would be a 13th if used for opt-out.

**Offered: 40**
1. **Sending:** API send, SMTP, batch, scheduling, attachments and inline images, custom headers, tags, idempotency keys.
2. **Domains:** SPF/DKIM, DMARC, BIMI, custom return path, sending regions, TLS enforcement.
3. **Tracking and content:** open tracking, click tracking, templates.
4. **Audience:** suppressions, topics, unsubscribe page, contacts, segments, contact properties, broadcasts, automations and events.
5. **Inbound:** receiving, inboxes.
6. **Observability:** webhooks, logs, metrics and deliverability insights.
7. **Access and account:** scoped API keys, OAuth, team management, SSO, dedicated IP, CSV export.
8. **Tooling:** SDKs, CLI, MCP server, Forge.

## 5. Install and operations
- **Components:** no vendor component is deployed in the cluster. The app needs the SDK or SMTP, one API key and DNS records [10][11].
- **Added for the must-haves (inference):** durable send state, such as a Postgres table, and a retry worker. The deferred items add a public webhook endpoint and storage for events, unsubscribes and `svix-id` values [34].
- **State:** Resend holds email data for 30 days [34] and the suppression list [7]. The app's unsent-message state would sit in its existing Postgres (inference).
- **High availability:** nothing from Resend to run. The worker and webhook endpoint run as part of the app. Resend's Terms give no SLA [21]; the pricing page lists a 99.99% SLA only for Enterprise [1].
- **Status:** the status page showed all systems operational and 100% component uptime for Oct to Nov 2026 [19]. Its history lists delayed API logs on 2026-11-19 and a Microsoft 365 delivery incident on 2026-11-13, with delayed messages delivered on retry [35].
- **Time to install (my estimate, not sourced):** 1 to 2 hours for a basic send, 0.5 to 1.5 days with the outbox and retry worker, and 1 to 3 more days for the deferred items. DNS wait is extra [10].
- **Expertise:** Python, DNS administration and Postgres. Webhooks also need signature verification and ingress [20]. No production approval or sandbox exit is required [36].

## 6. Integration facts
- **Auth:** Bearer API key over HTTPS. A `User-Agent` header is required (SDKs add it), or the request gets a 403 [26].
- **Key controls:** each key has a permission level and optional domain restriction. The value cannot be viewed after creation [37].
- **SMTP:** `smtp.resend.com`, username `resend`, API key as password; ports 465/2465 (TLS) or 25/587/2587 (STARTTLS) [22].
- **Config model:** dashboard and API, including domain tracking settings [16]; a CLI also exists [2]. I did not verify any vendor Kubernetes operator or YAML config model.
- **Network:** outbound HTTPS to the API [26]. Webhooks need an inbound endpoint. Verification uses `svix-id`, `svix-timestamp`, `svix-signature`, a signing secret and the raw body [20].
- **Stack fit:** there is a FastAPI guide [11] and optional async through `httpx` [14]. The SDK dropped Python 3.7 to 3.9 on 2026-11-05 [12]; I did not confirm 3.12 in package metadata. Resend needs no Redis or broker on the app side.
- **Guardrails:**
  - It is a managed service.
  - The free tier covers current volume at $0 [1].
  - The API key and webhook signing secret can live in the cloud secret manager and reach the app as `RESEND_API_KEY` [11]. Resend issues both, and its API returns the signing secret [20].
  - I found no requirement to give Resend any of the owner's production secrets. Message content does pass to Resend, so a secret or sensitive link placed in an email would be stored there.
  - Any new send-state table would be in the existing Postgres. I did not check that database's backup setup.
- **Residency:** account data, email metadata, logs and API records are stored in the US, whatever the sending region [38]. The stack summary states no residency policy.

## 7. Maintenance facts
- **Maintainer:** the vendor runs the service. The SDK lives in the vendor's GitHub organization and has several commit authors [12].
- **Upgrades:** the service is upgraded by the vendor (inherent to hosting). The SDK is a pip dependency [11].
- **Breaking and deprecation history:**
  - SDK v2.52.0 (2026-11-05) dropped Python 3.7 to 3.9 and raised dependency minimums [3][12].
  - v2.53.0 changed the mapping of 401/403 `validation_error` to `ValidationError`. That this could break existing exception handling is my inference [3][12].
  - The Audiences API is deprecated, following a segmentation change in November 2025. No removal date is given [39].
  - A third-party post reports two silent breaking changes in "Resend SDK v1.0.1", including a response type change [28]. The search summary attributed this to the Python SDK. I did not open the post or confirm it.
- **Documentation mismatch on webhook retries:** one vendor page lists up to eight attempts at 0, 5s, 5m, 30m, 2h, 5h, 10h and 10h [40], which adds up to about 27.6 hours. Another says "up to 24 hours" [34]. Failing endpoints are disabled automatically, and manual replay is available [40].
- **Hours per month (my estimate, not sourced):** about 0.5 to 2 once built. This covers SDK updates, bounce, complaint and quota checks, and failed sends or webhooks.

## 8. Cost

| Volume | Tier | Cost per month |
|---|---|---|
| Now, about 200 emails | Free | $0 [1] |
| In a year, about 2,000 emails | Free, if the daily cap is not hit | $0 [1] |
| If either cap is exceeded | Pro, 50,000 emails | $20 [1] |

- **Free ceiling:** 3,000 emails a month, 100 a day (resets at midnight UTC), 3 domains, 1 webhook and 30-day retention [1][8][9]. Sent and received emails both count [8]. There is no free-tier overage [1].
- **Headroom (my arithmetic):** 2,000 emails is 67% of the monthly cap. It averages about 67 a day over 30 days, or 91 over 22 workdays. Bursts of report completions could pass 100 in a day.
- **Must-haves:** I found none paywalled on the pages read.
- **Paid options:** Pro overage is $0.90 per 1,000 with pay-as-you-go enabled [1]. It is off by default, with a default cap of 400% of quota in overage [8]. The next listed tiers include Pro 100,000 at $35 and Scale at $90 [1]. Turning off message content storage is a $50/month add-on with eligibility rules [41].
- **Conflict:** a third-party guide (Flexprice) reportedly gives Free one domain [27]; the vendor says three [1]. I saw this only in a search summary.
- **Price terms:** fees can change at the end of a billing cycle with "reasonable prior notice". The Free tier can be changed or discontinued without notice [21].

## 9. Security facts
- **Data held:** Resend processes recipients, message content and metadata, stored in the US [38]. The app holds Resend's API key and, with webhooks, the signing secret [20].
- **New network surface:** none inbound for sending only. Webhooks add a public endpoint [20]; self-built one-click unsubscribe adds another that accepts POST and GET [32].
- **Permissions:** I found no need for cluster permissions or cloud account roles. DNS records must be added to the owner's domain [10].
- **Vendor claims:** SOC 2 Type II and GDPR compliance, encryption at rest, row-level encryption for sensitive tables, TLS 1.3 or higher on potentially insecure networks, and 7-day point-in-time backups [42]. I did not review the audit report.

## 10. Lock-in
- **API:** a documented REST API plus standard SMTP [22][26]. SDK calls, idempotency behavior, template IDs, topics and webhook event names are Resend-specific (my assessment) [5][17][29].
- **Export:** admins can export emails, contacts, domains, logs and other data as CSV, still in beta [24][30]. The Suppressions page has its own CSV export [7], and there are suppression and template API endpoints [2].
- **Templates:** React Email and HTML files can be used to create them [15]. I did not verify a bulk export of template source.
- **Termination:** the vendor may suspend or terminate "without prior notice or liability" [21].
- **Switch time (my estimate):** 0.5 to 2 days for sending only through your own wrapper, including DNS. Allow 2 to 5 days with webhooks, hosted templates and topics. Sender reputation or warm-up effects are not included.

## 11. Scaling
- **Monthly and daily volume:** expected growth is within 3,000 a month, but the 100/day cap may bind first. Over quota, the API returns 429 and the email is not queued [8]. Moving to Pro is a tier change that removes the daily cap [1].
- **Rate limit:** 10 requests per second per team across all keys, and the same on all self-serve plans. Trusted senders can ask for an increase [1][43]. Batch requests carry up to 100 emails and count as one request [1].
- **Message limits:** up to 50 `to` addresses and 40 MB of attachments after Base64 encoding [17].
- **Reputation:** sending can be paused if bounce rate exceeds 4% or spam rate exceeds 0.08% [8]. At low volume, a few events could cross these (inference; the calculation window is unverified).
- **Webhooks and retention:** Free allows 1 webhook and Pro 5. Both keep data 30 days [1].
- **Users:** the pricing page limits marketing plans by contacts (1,000 free) [1]. This matters at 5,000 users only if opt-out relies on Resend contacts and that limit applies (see section 13).

## 12. Sources
All retrieved 2026-11-26.

1. https://resend.com/pricing
2. https://resend.com/docs/llms.txt
3. https://github.com/resend/resend-python/releases
4. https://resend.com/changelog (also fetched https://resend.com/changelog.md)
5. https://resend.com/docs/dashboard/emails/idempotency-keys.md
7. https://resend.com/docs/dashboard/emails/email-suppressions.md
8. https://resend.com/docs/knowledge-base/account-quotas-and-limits.md
9. https://resend.com/docs/api-reference/rate-limit.md (daily quota reset)
10. https://resend.com/docs/add-a-domain.md
11. https://resend.com/docs/send-with-fastapi.md
12. https://github.com/resend/resend-python/commits/main.atom
13. https://github.com/resend/resend-python/releases.atom
14. https://raw.githubusercontent.com/resend/resend-python/main/README.md and https://github.com/resend/resend-python
15. https://resend.com/docs/dashboard/templates/introduction.md
16. https://resend.com/docs/dashboard/domains/tracking.md
17. https://resend.com/docs/api-reference/emails/send-email.md
19. https://resend-status.com
20. https://resend.com/docs/webhooks/verify-webhooks-requests.md
21. https://resend.com/legal/terms-of-service
22. https://resend.com/docs/send-with-smtp.md
24. https://resend.com/changelog/exports-as-csv-in-beta.md
26. https://resend.com/docs/api-reference/introduction.md
27. https://flexprice.io/blog/detailed-resend-pricing-guide (third party, search summary only)
28. https://dev.to/nathanhamlett/resend-sdk-v101-has-two-breaking-changes-that-fail-silently-here-is-the-fix-3oih and https://releasebot.io/updates/resend (third party, search summary only)
29. https://resend.com/docs/webhooks/event-types.md
30. https://resend.com/docs/dashboard/emails/manage-emails.md
31. https://resend.com/docs/api-reference/errors.md
32. https://resend.com/docs/dashboard/emails/add-unsubscribe-to-transactional-emails.md
33. https://resend.com/docs/dashboard/contacts/manage-topics.md
34. https://resend.com/docs/webhooks/how-to-store-webhooks-data.md
35. https://resend-status.com/history
36. https://resend.com/docs/knowledge-base/does-resend-require-production-approval.md
37. https://resend.com/docs/dashboard/api-keys/introduction.md
38. https://resend.com/docs/dashboard/domains/regions.md
39. https://resend.com/docs/dashboard/contacts/migrating-from-audiences-to-segments.md
40. https://resend.com/docs/webhooks/retries-and-replays.md
41. https://resend.com/docs/knowledge-base/how-do-i-ensure-sensitive-data-isnt-stored-on-resend.md
42. https://resend.com/docs/security.md
43. https://resend.com/docs/api-reference/rate-limit.md

## 13. Could not verify
- **Service release date and breaking changes over six months:** both changelog index fetches [4] lacked dates, and I did not open each entry. A web search [28] found no official 2026 breaking-change notice. This limits confidence in `prerelease: none`.
- **Recent pricing or limit changes:** third-party reports say overage billing began in December 2025 and 30-day retention in March 2026 [27]; a Nuntly guide, seen only in the same search summary (https://nuntly.com/resend-pricing), reportedly says the retention change was unannounced. I found no vendor confirmation. These fall outside or partly outside the six-month window.
- **Exact DNS record names and values:** not given on the domain pages [10] or https://resend.com/docs/dashboard/domains/introduction.md.
- **Topics with transactional mail:** I did not establish whether topic users count against the marketing contact limit, whether Free supports this fully, or how it relates to the hosted unsubscribe page. I checked [1], [17] and [33].
- **Webhook guarantees:** no formal at-least-once or ordering guarantee [34][40]. The docs advise deduplicating by `svix-id`. I found no source IP list on https://resend.com/docs/webhooks/introduction.md. I did not establish the replay history window.
- **Transient bounce retry:** the 14-hour figure comes from [30]. The delivery-delayed and bounce pages (https://resend.com/docs/webhooks/emails/delivery-delayed.md, https://resend.com/docs/dashboard/emails/email-bounces.md) give no duration.
- **Python 3.12 support and SDK retry behavior:** I did not inspect package metadata or source code; the README [14] answers neither.
- **Data export and deletion at account closure:** not covered by the Terms [21]. I did not read the DPA or Privacy Policy.
- **Bounce and spam rate window and minimum volume:** not stated in what I read from [8].
- **Install time, monthly hours, switch time and feature counts:** these are my estimates or grouping, not sourced facts.

**Files:** I read `/var/folders/cj/wnwkb64s2lnc5sfxhr_m_fbm0000gn/T/drift-neutral/locked-context.md`. I wrote no files.
