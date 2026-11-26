<!-- Captured 2026-11-26 from a live run of /build-vs-buy:researcher. Point-in-time snapshot: prices, limits and features age. Frozen on purpose. -->

# Evidence: Postmark (hosted)

All sources were retrieved 2026-11-26. Bracketed numbers refer to section 12. "(snippet)" means I saw the fact only in a search-result summary, not on a page I fetched. "(estimate)" means it is my own estimate, not a sourced fact.

## 1. Identity
- Hosted email API and SMTP service with separate transactional and broadcast message streams [1][2][22].
- It is a proprietary SaaS governed by terms of service [14]. ActiveCampaign acquired it (update dated 2022-05-03) [4].
- The official Python SDK, `postmark-python`, is MIT-licensed [6][7].

## 2. Release and staleness
- **Latest vendor update:** 2026-11-05, the first Postmark-specific SOC 2 Type 2 report. This is a compliance item, not a feature [4].
- **Recent product changes:** free-plan 2FA on 2026-09-23. API IP allowlisting and webhook verification, statistics and pausing on 2026-08-27 [4].
- **Cadence:** the updates page shows 10 entries dated 2026, from Feb 18 to Nov 5. These include SDK and tooling posts [4].
- **Python SDK:** the latest version is 0.5.0, uploaded 2026-10-29 [7]. There are 13 PyPI uploads listed from 2026-04-15 to 2026-10-29 [7].
- **Latest meaningful SDK commit:** 2026-10-29 (0.5.0 features and fixes). The later 2026-11-10 commit is a README security note [9].
- **SDK maturity:** the SDK is labelled Beta in its README and PyPI classifier [6][7]. Version 0.5.0 changed behavior [8]:
  - Open and click filters that were previously ignored now apply.
  - `from_date` and `to_date` are no longer sent and raise a `FutureWarning`.
  - Some response fields became optional.
  - `webhooks.edit()` makes an extra GET request.
- **SDK rename:** 0.2.1 (2026-04-14) renamed the PyPI package from `postmark` to `postmark-python` [8].
- The status below applies to the hosted service. The SDK's beta label is a separate fact; the REST API and SMTP can be used without the SDK [2][21].

prerelease: none

## 3. Must-have coverage

| Item | Coverage | Evidence |
|---|---|---|
| Now: send from the API when a report finishes | The send API is available out of the box. The app has to call it when the report finishes. | `POST /email` returns a `MessageID` [5]. |
| Now: own domain with SPF and DKIM | Needs configuration (DNS). | Add a DKIM TXT record and a Return-Path CNAME (`pm_bounces` to `pm.mtasv.net`). The CNAME handles SPF, and the page lists no separate SPF record [11]. The From address needs a confirmed Sender Signature according to the email API page [5]. |
| Now: retry a failed send without losing the message | Needs custom glue for durability. | Postmark has no idempotency key and suggests building safeguards yourself [3]. The SDK retries rate-limit, server and timeout errors up to 3 times with exponential backoff and jitter [10]. Its changelog says timeout retries resend requests [8]. I found nothing saying these retries persist across a process restart. My inference: keeping the message needs app-side storage such as a Postgres outbox, and a retry after an ambiguous timeout could send a duplicate. The API overview says that on a 500 the message is typically lost [2]. |
| Deferred: per-user opt-out | Needs configuration or custom glue. | Unsubscribe links are optional on transactional streams, and suppression applies to the stream. A Subscription Change webhook and a suppression dump are available [17]. Suppressions can also be created by API, up to 50 addresses per call [15]. Per (snippet) [S1], transactional streams default to no unsubscribe handling, and custom handling needs approval. I found no per-user, per-notification-type preference feature, so that would be app logic. |
| Deferred: bounce and complaint handling | Out of the box for suppression. Updating app state needs custom glue. | `HardBounce` and `SpamComplaint` are suppression reasons, and complaint suppressions cannot be deleted [15]. The bounce webhook reports whether the address was deactivated [18]. Complaints use a separate webhook [18]. Automatic suppression on bounce or complaint is stated in (snippet) [S1]. |
| Deferred: delivery status visibility | Out of the box through the API. | Message search and events cover Delivered, Transient, Bounced, Opened and more [16]. Delivery webhooks are available [12]. Retention defaults to 45 days [16]. |
| Nice-to-have: hosted templates | Out of the box. | Templates API with layouts; limit of 100 per server, more through support [19]. |
| Nice-to-have: open and click tracking | Out of the box, enabled per message or by setting. | `TrackOpens` and `TrackLinks` [5]. The per-message opens endpoint keeps only the first open; the webhook captures every open [16]. Link tracking is unavailable before account approval [13]. |

**Account approval:** before approval, an account can send only to domains it has added and verified. Weekday reviews take under 24 hours, and weekend reviews take longer [13].

## 4. Features used versus offered
The counts depend on how I grouped features. The "offered" list comes from the pages I checked and is not a complete vendor catalog.

**Used: 10** across all three priority levels (the grouping and selection are mine):
1. Email send API
2. Domain authentication (DKIM and Return-Path)
3. Transactional message stream
4. Suppressions
5. Bounce handling (API and webhook)
6. Event webhooks (delivery, complaint, subscription change)
7. Message search and events
8. Templates
9. Open tracking
10. Click tracking

Of these, the "now" items use 1–3. SDK retry is optional and not counted.

**Offered: 24** [1][2][4][5][12][15][16][19][20][21][22]:
- The 10 above
- Batch send
- Bulk and broadcast sending
- SMTP
- Inbound processing (Pro and higher on the pricing page)
- Stats and analytics
- Sandbox and test mode
- Server and domain management API
- Official client libraries
- Data Removal API
- MCP server
- API IP allowlisting
- Dedicated IPs (paid add-on)
- DMARC monitoring (paid add-on)
- Custom retention (paid add-on)

## 5. Install and operations
- **Components:** none from Postmark to deploy. You need DNS records, a server token and application code [5][11].
- **App-side components (inference):** the durable retry would need an outbox table and a worker or scheduled loop. The existing Postgres could hold this without a new broker. That state would fall under the existing database's backup arrangements, which I did not check. Deferred webhooks need a public HTTPS endpoint [12].
- **High availability:** the vendor runs the service. I found no uptime percentage or SLA in the terms [14].
- **Install time (estimate):** 0.5–1 day for the account, DNS and send call, plus 1–2 days for the outbox, retry and tests. DNS verification should show within 48 hours [11], and account approval is a separate wait [13]. Deferred webhooks and opt-out would add about 1–3 days.
- **Expertise:** Python, HTTP, DNS editing and Postgres.

## 6. Integration facts
- **Auth:** server token (`X-Postmark-Server-Token`) or account token (`X-Postmark-Account-Token`) over HTTPS [2].
- **SMTP auth:** the server token, or SMTP tokens scoped to one stream. Ports are 25, 2525 and 587. STARTTLS is available and recommended in the docs, which do not describe it as mandatory [21].
- **Configuration:** UI and API (templates, suppressions, domains) [2][19]. IP allowlist ranges can be set only in the UI [20]. I did not find a vendor YAML or Kubernetes operator option, and did not search specifically for one.
- **Network:** outbound HTTPS to `api.postmarkapp.com` [2]. Inbound access is needed only for webhooks [12].
- **Stack fit:** the SDK requires Python 3.10 or later, has async and sync clients, and so is compatible with Python 3.12 [6][7]. `ServerClient` defaults to a 5-second timeout and 3 retries [10].
- **Guardrails:**
  - Managed service: Postmark is hosted.
  - Vendor cost: a free tier exists, and the plan needed at current volume costs under $50 [1].
  - Secret manager: the API token can be kept there and supplied to the app at runtime.
  - **Possible conflict:** webhook authentication puts a username and password in the webhook URL registered with Postmark [12]. Postmark would then hold a copy of that credential outside the secret manager. The owner needs to decide whether this counts under "no tool may hold production secrets outside the secret manager". HMAC signing is not offered; IP allowlisting of Postmark's webhook ranges is the other documented control [12].

## 7. Maintenance facts
- **Maintainer:** the vendor maintains the service and the official SDK under the ActiveCampaign GitHub organization [4][6].
- **Upgrades:** the service has nothing to upgrade on your side. SDK upgrades are dependency bumps, and 0.x releases have changed behavior [8].
- **Breaking-change history** [4]:
  - 2021: TLS and attachment validation changes.
  - 2022: plain HTTP API access ended.
  - 2023: stricter email API validation, and the end of the old API static IP allowlisting.
  - 2023: postmark.js 4.0.0 dropped end-of-life Node versions.
  - 2022–2023: Status API replaced with different endpoints and formats.
- **2026:** none of the entries I read is labelled breaking [4].
- **Webhook behavior change (August 2026):** event types with sustained failures are now marked unverified and paused, and edits require the endpoint to pass verification [4]. The webhook docs describe a warning, then a 48-hour window before the event type is disabled [12].
- **Webhook retries:** six retries over about 51 minutes (my sum of the listed delays), after which the event is dropped. Most 4xx responses are not retried. Duplicates are possible [12].
- **SDK security note:** the README flags CVE-2026-111497, which applies only if the optional Brotli packages are installed [6].
- **Hours per month (estimate):** 0.25–1 at this scale, for checking bounce and complaint rates, failed outbox rows and SDK bumps. There is no measured basis.

## 8. Cost
- **Free tier:** $0 for 100 emails a month, with no overage [1]. The current 200 a month is above that ceiling.
- **At about 200 a month:** Basic, **$15/month**, which includes 10,000 emails [1].
- **At about 2,000 a month:** still **$15/month** [1].
- **Basic limits:** 45-day retention, 5 custom domains and 4 users. Overage is $1.80 per 1,000 [1].
- **Other tiers:** Pro is $16.50 ($1.30 per 1,000 overage) and Platform is $18 ($1.20 per 1,000). Both are listed "from" 10,000 emails [1].
- **Optional add-ons:** DMARC monitoring from $14 per domain, custom retention from $5, and dedicated IPs from $50 (Pro and higher) [1]. None is named in the must-haves.
- **Other:** unused volume does not roll over, and no annual plan is offered [1].

## 9. Security facts
- **Data held:** Postmark processes recipient addresses and email content. Content and metadata are kept 45 days by default, and suppression lists indefinitely [24].
- **Location:** data is hosted near Chicago and on AWS, with no current plan for EU servers [24]. The page may be old.
- **Credentials:** a server token can send and also use server-level endpoints, including suppression changes [2][15]. I found no send-only API token. SMTP tokens are limited to one stream [21].
- **IP allowlist:** optional, up to 10 IPv4 ranges, and it restricts only API sends. SMTP is not checked, and other API calls work from any IP with a valid token. The docs advise against it where egress IPs change often [20]. I did not find which plans include it.
- **Network surface:** none is added for sending. Webhooks add a public endpoint, and payloads are unsigned [12].
- **Cluster or cloud permissions:** the integration as described needs no Postmark component in the cluster and no elevated permissions (inference from [2][5]).
- **Assurance:** SOC 2 Type 2 report announced 2026-11-05. 2FA is on all plans, but SMS 2FA only on paid plans [4].

## 10. Lock-in
- **Export:** message and bounce data can be pulled through the API (snippet) [S2]. The messages API caps results at 500 per request and 10,000 for count plus offset, so larger pulls need date windows [16]. Content expires after the retention period [16][24]. Suppressions can be dumped [15].
- **Templates:** there are get and list endpoints but no dedicated export endpoint. The template syntax is described in Postmark's own support documentation [19]. I did not test portability to other vendors.
- **Account transfer:** data cannot be moved between Postmark accounts (snippet) [S2].
- **Openness:** REST API plus standard SMTP [2][21].
- **On termination:** all account data is lost and terminated accounts are not backed up [14].
- **Switch time (estimate):** 1–2 days for send-only, including new DNS records. With webhooks, suppressions and templates in use, 3–5 days.

## 11. Scaling
- **Expected volume:** 2,000 emails a month is 20% of the 10,000 shown for Basic [1]. This plan does not price by monthly active users.
- **Past the included volume:** paid plans charge overage or can move to a larger volume or tier. This needs no data migration as far as the pricing page indicates (inference) [1]. The free plan allows no overage [1].
- **Daily limit:** none. The sending conditions are a complaint rate below 0.1% and a bounce rate below 10%. Breaches can lead to a pause with messages queued [23].
- **Terms:** the new terms say exceeding either threshold lets Postmark cancel the account. The existing-customer wording describes a possible pause for complaints. Termination can also be without notice at Postmark's discretion [14]. This is harsher than the pause described in the support article [23]. At low volume, one complaint in fewer than 1,000 emails would exceed 0.1% arithmetically; I did not find how the rate window is calculated.
- **API rate limit:** a 429 signals excess use, and the overview gives no number [2].
- **Other limits:** 500 messages and 50 MB per batch, 50 recipients per message [5], and 100 templates per server [19].

## 12. Sources
All retrieved 2026-11-26.

1. https://postmarkapp.com/pricing
2. https://postmarkapp.com/developer/api/overview
3. https://postmarkapp.com/support/article/what-is-an-idempotency-key
4. https://postmarkapp.com/updates (first 100,000 of 157,983 characters)
5. https://postmarkapp.com/developer/api/email-api
6. https://github.com/ActiveCampaign/postmark-python (also https://raw.githubusercontent.com/ActiveCampaign/postmark-python/main/README.md)
7. https://pypi.org/pypi/postmark-python/json
8. https://raw.githubusercontent.com/ActiveCampaign/postmark-python/main/CHANGELOG.md
9. https://github.com/ActiveCampaign/postmark-python/commits/main
10. https://github.com/ActiveCampaign/postmark-python/wiki/Getting-Started
11. https://postmarkapp.com/support/article/how-do-i-verify-a-domain
12. https://postmarkapp.com/developer/webhooks/webhooks-overview
13. https://postmarkapp.com/support/article/1084-how-does-the-account-approval-process-work
14. https://postmarkapp.com/terms-of-service
15. https://postmarkapp.com/developer/api/suppressions-api
16. https://postmarkapp.com/developer/api/messages-api
17. https://postmarkapp.com/support/article/1208-how-to-add-an-unsubscribe-link
18. https://postmarkapp.com/developer/webhooks/bounce-webhook
19. https://postmarkapp.com/developer/api/templates-api
20. https://postmarkapp.com/developer/user-guide/ip-allowlisting
21. https://postmarkapp.com/developer/user-guide/send-email-with-smtp
22. https://postmarkapp.com/email-api and https://postmarkapp.com/llms.txt
23. https://postmarkapp.com/support/article/does-postmark-have-a-daily-send-limit
24. https://postmarkapp.com/eu-privacy

Search-summary sources (snippet):
- **S1:** search limited to postmarkapp.com on unsubscribe handling. Its results included https://postmarkapp.com/developer/api/message-streams-api and https://postmarkapp.com/support/article/1208-how-to-add-an-unsubscribe-link.
- **S2:** search limited to postmarkapp.com on data location and export. Its results included https://postmarkapp.com/support/article/1175-can-i-transfer-a-server-to-a-new-account. The summary did not clearly tie each claim to one URL.

## 13. Could not verify
- **Per-feature availability on Basic:** the pricing summary says all plans include the "core sending features" and analytics [1]. I saw no line-by-line confirmation that webhooks, templates, tracking and suppressions are on Basic. The summary lists inbound processing under Pro and higher. Checked [1].
- **Pricing details:** the fetched text was a model-made summary of the page. Prices for volumes above 10,000 and Pro or Platform volume steps were not checked. Checked [1].
- **Uptime and SLA:** no figure found in the terms [14], the email API page [22] or the status page (https://status.postmarkapp.com/). The status page showed all systems operational and an undescribed incident entry at 15:36 EST on 2026-11-05. I did not review incident history.
- **Price-change notice:** the terms summary showed no set notice period [14]. I did not read the DPA.
- **Postmark's own delivery retries to recipient mail servers** (schedule and duration after the API accepts a message): not researched. The Transient event exists [16].
- **SDK retry details:** the defaults come from the official repo wiki [10]. I did not confirm them in source code; the guessed `base_client.py` path returned 404. I also did not check whether retries honor Retry-After. Third-party wiki mirrors on unrelated domains appeared in search and were not relied on.
- **SPF wording:** `llms.txt` mentions setting up "DKIM and SPF" [22], while the domain page lists no separate SPF record and covers SPF through the Return-Path CNAME [11]. Both are vendor pages. A search summary also said the SPF verification API endpoint is deprecated; I did not fetch that page.
- **Sender requirement:** the email API page says a confirmed Sender Signature is required [5]. I did not confirm on a fetched page that a verified domain alone satisfies this. Checked [5][11].
- **Approval error wording:** a search summary of an older API page said pending accounts can send only to the From address's domain. The approval article says any added and verified domain [13].
- **Cross-stream opt-out:** a search summary said a broadcast opt-out does not block transactional sends. The fetched article does not say this explicitly [17].
- **Send-only API token, IP allowlist plan availability and vendor configuration-as-code:** not found or not specifically searched. Checked [2][20].
- **Current data location and sub-processors:** the vendor pages may be old [24][S2], and I did not check a current sub-processor list.
- **Install, maintenance and switching times:** these are estimates with no measured source.
- **Updates page remainder:** not read beyond the first 100,000 characters. The part read reached back to July 2020.
- **Prompt injection:** I saw no injection attempt in the fetched content, including `llms.txt`.
