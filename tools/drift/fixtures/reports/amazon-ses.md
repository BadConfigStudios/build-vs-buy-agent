<!-- Captured 2026-11-26 from a live run of /build-vs-buy:researcher. Point-in-time snapshot: prices, limits and features age. Frozen on purpose. -->

# Evidence: Amazon SES (hosted)

All sources were retrieved on 2026-11-26. Bracketed numbers refer to section 12. Items marked "estimate" or "inference" are mine and are not vendor facts.

## 1. Identity
- Amazon Simple Email Service is AWS's email service. It sends through an API (v2) or SMTP and also handles inbound mail [10][21].
- **Type:** hosted. This research found no self-hosted edition.
- **License:** it is a paid, usage-billed service [1]. I did not retrieve the governing terms. The docs refer to the AWS Service Terms [15].
- **Python client:** boto3. A PyPI fetch reported Apache-2.0 [29].

## 2. Release and staleness
- **Releases:** none of the pages I read shows version numbers for the service.
- **Latest documented change:** 2026-11-09, "To and CC rule conditions", which concerns Mail Manager [5]. This is a documentation date, not a code commit.
- **Recent sending-related changes:** per-message tracking overrides on 2026-10-14, S/MIME signing on 2026-08-27, and pricing plans on 2026-07-21 [5][3].
- **Cadence:** the doc history has several entries a month in most recent months, including a cluster in October 2026 [5].
- **Pricing movement:** plans were introduced within the last six months [3][5].

prerelease: none

This value is my classification. SES is sold with production pricing and production access [1][4], and I saw no beta label on it.

## 3. Must-have coverage

**Now**
- **Send from the API when a report finishes:** needs custom glue. `SendEmail` v2 is available [10], but the app has to call it from the report-completion path.
- **Own domain with DKIM:** needs configuration. Easy DKIM signs every message once the domain identity and DNS records are set up [12].
- **Own domain with SPF:** needs configuration. The default `amazonses.com` MAIL FROM domain passes SPF. Using your own domain for SPF takes a dedicated subdomain with exactly one MX record and an SPF TXT record. DMARC alignment through SPF also requires the From domain to match the MAIL FROM domain, as the vendor page words it [13].
- **Prerequisite for real recipients:** new accounts start in a per-Region sandbox: verified recipients only, 200 messages per 24 hours, 1 per second. AWS gives an initial response to a production access request within 96 hours, and it can take longer. The request includes agreeing that you have a bounce and complaint process [4].
- **Retry without losing the message:** needs custom glue.
  - If a send request fails, SES "responds to the sender with an error and drops the email" [14].
  - After accepting a message, SES retries soft bounces for an extended period [14].
  - boto3's default `standard` mode makes 3 total attempts with backoff, including on `TooManyRequestsException` and 500/502/503/504 [27]. Inference: these retries run inside the calling process, so surviving restarts or long outages needs durable app-side storage, such as a Postgres table and worker.
  - SES may accept a message even though the request errors or times out, so a retry can send a duplicate. AWS advises message tags for correlation [14][19].
  - The v2 `SendEmail` request syntax shows no idempotency token [10].
  - A daily quota overrun means waiting for the next 24-hour period [19].

**Deferred**
- **Per-user opt-out:** needs configuration, plus glue if the app is the system of record.
  - SES subscription management adds unsubscribe headers and links, hosts a preferences page, and bounces sends to unsubscribed contacts [11][22].
  - Limits are one contact list per account and 20 topics [22].
  - Links and headers are added only for single-recipient sends. Footer links need the `{{amazonSESUnsubscribeUrl}}` placeholder. SES cannot add the links if you DKIM-sign messages yourself [11].
- **Bounce and complaint handling:** suppression works out of the box or with configuration; app-side handling needs glue.
  - The account-level suppression list covers bounces and complaints by default for accounts started after 2019-11-25. Only hard bounces are added [7].
  - Gmail sends SES no complaint data [7].
  - Feedback can arrive by email, SNS or event publishing [8].
- **Delivery status visibility:** needs configuration for the console view, or glue to show status in the app.
  - Event publishing covers send, delivery, bounce, complaint, reject, delivery delay, rendering failure, subscription, open and click. Destinations are CloudWatch, Firehose, Pinpoint, SNS and EventBridge [9].
  - Virtual Deliverability Manager (VDM) offers per-message search and history for the last 30 days. It must be enabled, shows at most 100 results per console search (a random sample beyond that), and does not count multi-recipient messages in dashboard metrics [23]. It is included in all plans and costs extra à la carte [1].
  - Pinpoint's end of support was reported as 2026-10-30, from a search summary, so that destination should not be assumed usable [28].

**Nice-to-have**
- **Hosted templates:** met with configuration through the API or CLI. Limits are 20,000 per Region and 500 KB each. Invalid template data can be accepted and then not delivered, so AWS recommends rendering-failure events [2][24].
- **Open and click tracking:** needs configuration through configuration sets and events. Custom tracking domains are supported [9][5]. VDM docs warn that Apple Mail Privacy Protection inflates engagement figures [23].

## 4. Features used versus offered
This count is my own grouping of capabilities. It is not a vendor feature count, and the offered list may be incomplete.

**Used: 9**
1. API sending
2. Domain identity verification
3. Easy DKIM
4. Custom MAIL FROM (SPF)
5. Suppression list
6. Event publishing and notifications
7. List and subscription management
8. Stored templates
9. Open and click tracking

VDM message insights would make it 10 if chosen for status visibility.

**Offered: 29.** The 9 used above, plus these 20:
1. SMTP interface
2. Inbound receiving
3. Mail Manager
4. VDM deliverability insights, including message insights
5. Global deliverability (inbox placement and blocklists)
6. Managed dedicated IPs
7. Standard dedicated IPs
8. BYOIP
9. Email validation
10. Global endpoints
11. Tenants
12. Archiving
13. Third-party email add-ons
14. BYODKIM
15. Deterministic Easy DKIM
16. S/MIME signing
17. Bulk and inline templated sending
18. Attachments
19. VPC endpoints
20. Mailbox simulator

Sources: [1][5][9][10][12][21][24].

## 5. Install and operations
- **Components for sending:** the SES identity and DNS records, IAM credentials, app code, and production access [4][12][13][18]. A durable outbox and retry worker in the app is my inference from section 3.
- **Components added for deferred items:** a configuration set and an event destination [9], plus an app consumer. SQS would sit behind SNS or EventBridge; I did not verify that wiring on a vendor page.
- **Nothing from SES runs in the cluster.**
- **State:** SES holds the suppression list, contact list and templates for each account (suppression, templates and plans are per Region) [2][7][17][22]. Any outbox would live in the existing Postgres, so it falls under that database's backup arrangement, which the stack summary does not describe.
- **High availability:** there is nothing for the owner to cluster. Global endpoints offer optional two-Region failover [5][1].
- **Install time (estimate):** 1 to 2 engineer-days for the "now" items, based on identity and DNS setup, IAM, one API call, and an outbox worker with tests. Allow separately for up to 72 hours of MAIL FROM MX detection [13] and the 96-hour access response [4]. Deferred items add about 2 to 4 days, mostly the event pipeline and opt-out integration.
- **Expertise:** AWS account administration, IAM and DNS.

## 6. Integration facts
- **Auth:** IAM. Policies can restrict actions, identities, From address, recipients, source IP and VPC [18].
- **Outside AWS:** IAM Roles Anywhere gives temporary credentials using X.509 certificates, which requires a certificate authority [26]. SMTP uses credentials derived from IAM [18].
- **Config model:** console, API or CLI [4][7][24]. I did not research infrastructure-as-code or Kubernetes operator support.
- **Credentials needed:** a send-only identity needs `ses:SendEmail` (and `ses:SendRawEmail` for raw or SMTP use) [18]. Setup and any event consumer need further permissions.
- **Network:** outbound HTTPS to `email.<region>.amazonaws.com` [20]. SNS pushing to a webhook would need a public endpoint, while queue polling would stay outbound only (inference).
- **Stack fit:** boto3 works from the Python API [27]. Postgres can hold the outbox, and no Redis or broker is needed for sending (inference).
- **Guardrails:**
  - *Managed preferred:* SES is hosted.
  - *Stateful components:* SES adds none in the cluster. An outbox adds tables to the existing database.
  - *Vendor cost:* the estimate in section 8 is under 50 USD.
  - *Secrets:* any static access key or SMTP password would need to stay in the secret manager. The cloud provider is not named. If it is AWS, workload roles may apply (not checked for this cluster). If not, AWS may count as a new vendor, and the choice is a stored static key or Roles Anywhere, whose certificate private key also has to be stored in line with this rule.

## 7. Maintenance facts
- **Maintainer:** the vendor, AWS. There is no service to upgrade yourself; the boto3 dependency still needs updates.
- **Breaking and behavior changes found:**
  - New accounts, or ones defaulted this way, can be placed on Essentials instead of à la carte [17]. A third-party page dates this to 2026-07-21 and includes account-Region pairs with no metered SES activity since 2025-06-01 [30].
  - The free tier appears to have changed (see section 8).
  - Old SigV2 SMTP credentials, created before 2019-01-10, are flagged for replacement [19].
  - Recent docs moved examples to API v2. `SendBounce` exists only in v1 [5][18].
- The doc history pages I read showed no announced removal of v2 sending features. It is a documentation log, not a breaking-change log [5].
- **Sender enforcement** [15]:

| Rate | Account review at | Possible sending pause at |
|---|---|---|
| Bounce | 5% | 10% |
| Complaint | 0.1% | 0.5% |

  - At low volume, rates use a "representative volume" rather than a fixed time window.
  - An account-level pause emits no EventBridge event. Detecting it means polling `GetAccount.EnforcementStatus` or watching AWS Health [15].
  - If sending stays paused, the suppression list is deleted after 90 days [7].
- **Hours per month (estimate):** 0.5 to 1 in steady state, covering reputation metrics, failed outbox rows, dependency updates and credential upkeep. It rests on the low volume and no self-run SES components, not on measured data.

## 8. Cost
**Rates per 1,000 outbound emails, first 10 million a month** [1]:

| Option | Per 1,000 | Fixed monthly fee | About 200 emails/month | About 2,000 emails/month |
|---|---|---|---|---|
| À la carte | $0.10 | none | $0.02 | $0.20 |
| À la carte with VDM | $0.10 + $0.07 | none | $0.034 | $0.34 |
| Essentials (includes VDM insights) | $0.16 | none | $0.032 | $0.32 |
| Pro | $0.22 | $105 per account per Region | about $105 | about $105.44 |

- **Tier that meets the must-haves:** neither Pro nor Enterprise is needed. Sending, DKIM and SPF work à la carte or on Essentials. Plans are optional, and you can cancel back to à la carte [1][17]. Inference: suppression, events, templates, tracking and subscription management show no separate plan charge on the pricing page.
- **Extras not in the table:** attachments cost $0.12 per GB [1]. VDM queries cost $0.0005 per 1,000 with the first 5,000 free, as the fetch summary worded it [1]. SNS, SQS, EventBridge, CloudWatch, data transfer and any Private CA charges are also excluded. VDM history at 30 days needs no storage of your own, but longer retention would.
- **Free tier, vendor pages disagree:**
  - The pricing page offers new AWS accounts up to $200 in general credits. The free plan lasts six months, and credits must be used within 12 months [1].
  - The SES FAQ still says new customers get 3,000 message charges free each month for 12 months [25].
  - A third-party page says the 3,000 offer is closed to new customers and the FAQ is out of date [30].
  - Neither version is a permanent free allowance.

## 9. Security facts
- **Secrets:** SES does not need the app's other production secrets. The app needs AWS credentials to call it (temporary role or static key) [18][26].
- **Data:** SES processes recipient addresses and message content. VDM exposes recipient, subject and event history [23].
- **Network surface:** sending is outbound only. A webhook consumer would add an inbound endpoint (inference). Open and click tracking routes recipients through AWS or custom tracking domains [20][5].
- **Permissions:** no Kubernetes cluster permissions follow from the design above (inference). IAM can scope the sender by identity and From address [18]. A leaked key with broad send rights could send mail as the domain (inference).
- **Transport:** TLS 1.2 and above is supported. Delivery is opportunistic by default and can be set to require TLS [25]. The doc history says TLS 1.3 is the default delivery method [5].

## 10. Lock-in
- **Formats:** sending uses an AWS-specific API with simple, raw MIME or templated content [10]. SMTP is the more portable option [21]. Templates use `{{tag}}` placeholders [24]. DNS records, event payloads and IAM policies are provider-specific.
- **Export:** the suppression list can be listed through the API [7], and contacts through `ListContacts` [22]. VDM message and metric results export to CSV or JSON, with a random sample above 10,000 messages [23]. I did not check template export; `GetEmailTemplate` was not fetched.
- **API openness:** the API is documented and AWS SDKs cover many languages [10]. It is proprietary.
- **Switch time (estimate):** 1 to 2 days for sending only (new adapter and DNS records, with the outbox staying in the app). It is 3 to 5 days if events, suppression, opt-out and templates are in use. Moving to a new sender may also affect deliverability.

## 11. Scaling
- **Expected volume:** about 2,000 emails a month is roughly 67 a day on average. That is below even the 200-per-day sandbox cap, but report bursts could exceed 200 a day or 1 per second [2].
- **Production limits:** daily and per-second quotas vary by account and use case, and increases can be requested. Quotas count recipients [2].
- **Other limits:** 50 recipients per message and 40 MB per message with v2 or SMTP [2]. Non-send API actions are generally throttled to 1 request per second [2], which may matter for syncing contacts (inference).
- **List limits:** one contact list and 20 topics [22]. Needing more preference categories would mean managing preferences in the app.
- **When a quota is hit:** request an increase; no data migration is involved [2]. Growth to 5,000 monthly active users does not require a plan change on price grounds.

## 12. Sources
All retrieved 2026-11-26.
1. https://aws.amazon.com/ses/pricing/
2. https://docs.aws.amazon.com/ses/latest/dg/quotas.html
3. https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-ses-pricing-plans/
4. https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html
5. https://docs.aws.amazon.com/ses/latest/dg/doc-history.html
7. https://docs.aws.amazon.com/ses/latest/dg/sending-email-suppression-list.html
8. https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity-using-notifications.html
9. https://docs.aws.amazon.com/ses/latest/dg/monitor-using-event-publishing.html
10. https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_SendEmail.html
11. https://docs.aws.amazon.com/ses/latest/dg/sending-email-subscription-management.html
12. https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dkim.html
13. https://docs.aws.amazon.com/ses/latest/dg/mail-from.html
14. https://docs.aws.amazon.com/ses/latest/dg/send-email-concepts-process.html
15. https://docs.aws.amazon.com/ses/latest/dg/faqs-enforcement.html
17. https://docs.aws.amazon.com/ses/latest/dg/pricing-plans.html
18. https://docs.aws.amazon.com/ses/latest/dg/control-user-access.html
19. https://docs.aws.amazon.com/ses/latest/dg/troubleshoot-error-messages.html
20. https://docs.aws.amazon.com/general/latest/gr/ses.html
21. https://aws.amazon.com/ses/faqs/ (feature list; same page as 25)
22. https://docs.aws.amazon.com/ses/latest/dg/sending-email-list-management.html
23. https://docs.aws.amazon.com/ses/latest/dg/vdm-dashboard.html
24. https://docs.aws.amazon.com/ses/latest/dg/send-personalized-email-api.html
25. https://aws.amazon.com/ses/faqs/ (free tier, TLS)
26. https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html
27. https://docs.aws.amazon.com/boto3/latest/guide/retries.html
28. https://docs.aws.amazon.com/pinpoint/latest/userguide/migrate.html (seen only through a search summary)
29. https://pypi.org/pypi/boto3/json (partial read)
30. https://akalcloud.ai/blog/amazon-ses-pricing/ (third party; the publisher sells a cost-management product)

Numbers 6 and 16 are unused.

## 13. Could not verify
- **SES uptime SLA and service credits:** https://aws.amazon.com/ses/sla/ returned 404. A search limited to aws.amazon.com found SLAs for other services only.
- **SNS charges:** https://aws.amazon.com/sns/pricing/ did not render its rate tables.
- **SQS charges:** https://aws.amazon.com/sqs/pricing/ showed 1 million free requests a month but no per-request rate.
- **EventBridge, CloudWatch, Private CA and data transfer charges:** not fetched.
- **Which free tier applies to a new account:** the two vendor pages conflict [1][25].
- **Default plan and effective date:** the vendor docs confirm that some accounts are defaulted to Essentials [17] but do not say which. The July 21 announcement page did not say either [3]. The criteria come from third-party pages [30]. A search summary said one source gives 2026-10-15 instead; I did not open that source. For this owner, check the console's Pricing plan page.
- **Production quota that would be granted:** no default is published [2].
- **boto3 latest release date:** the PyPI page was truncated before the upload date. The version it reported (1.44.12) was not confirmed as current.
- **Latest service code change:** the doc history was the only staleness signal found.
- **How long SES retries soft bounces:** [14] says only "an extended period". The doc history mentions a configurable maximum delivery duration of 300 to 50,400 seconds [5].
- **SNS or EventBridge to SQS wiring, infrastructure-as-code support and template export:** not checked on vendor pages.
- **Compliance and data processing terms:** not researched. The FAQ fetch showed no HIPAA statement [25].
- **Owner's cloud provider:** not named, so the credential method and whether AWS is a new vendor are undetermined.
- **Prompt injection:** I saw no attempts in the fetched content. The doc history entry about setting up an AI coding agent is an ordinary changelog line, and I did not follow it [5].

I created and modified no files. The context file I read is `/var/folders/cj/wnwkb64s2lnc5sfxhr_m_fbm0000gn/T/drift-neutral/locked-context.md`.
