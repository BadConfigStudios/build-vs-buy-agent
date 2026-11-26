<!-- Captured 2026-11-26 from a live run of /build-vs-buy:researcher. Point-in-time snapshot: prices, limits and features age. Frozen on purpose. -->

# Evidence: Postal (self-hosted)

All sources were retrieved 2026-11-26. Bracketed numbers refer to section 12. Pages were read through a summarizing fetch tool, so code behavior reflects its summaries of the `main` branch, not a line-by-line audit.

## 1. Identity
- Postal is an open-source mail delivery platform for incoming and outgoing email, positioned as a self-hosted alternative to SendGrid, Mailgun and Postmark [3].
- Type: self-hosted. License: MIT. Copyright holders are Krystal Hosting Ltd (2017–2024), Adam Cooke and Charlie Smurthwaite [3][28].

## 2. Release and staleness
- Latest release: v3.5.0, 2026-11-20 [1].
- Latest commit seen on `main`: 2026-11-20. It includes a feature, per-server message priority [4].
- Cadence from the releases page [1]:
  - 3.3.0 to 3.3.3: March–April 2024.
  - 3.3.4: 2024-06-20.
  - 3.3.5: 2026-02-01, about 19 months after 3.3.4.
  - 3.3.6, 3.3.7, 3.4.0, 3.5.0: 2026-04-28, 06-03, 11-16 and 11-20.
- No release on the page viewed is marked as a prerelease [1].

prerelease: none

## 3. Must-have coverage

**Now**
- **Send from the API:** met out of the box on a running install, using `/api/v1/send/message` or `/send/raw` with an `X-Server-API-Key` header. The app still has to call it when a report finishes [7][20].
- **Own domain with SPF and DKIM:** needs configuration. Each sending domain needs SPF and DKIM records, which Postal generates and checks. The install also needs its own A, MX, SPF, return-path and DKIM records [8].
- **Retry without losing an accepted message:** met out of the box. Messages are queued and retried with backoff of 5 min × 1.3^attempts, with a default maximum of 18 attempts [11][29][30].
  - By my calculation, the retry window is about 24–31 hours.
  - When attempts run out, the message is hard-failed, leaves the queue, and the recipient is suppressed as "too many soft fails" [30].
  - Connection failures and temporary SMTP errors retry. `SMTPFatalError` does not [31].
- **Retry when the app's call to Postal fails:** needs custom code. This is my inference: the app needs its own durable retry, for example a Postgres outbox.
  - No idempotency key or duplicate check appeared in the docs or send controller, so client retries could create duplicates [7][32].
  - In `send/raw`, the controller summary says the result of `save` is not checked, so a failed save could still return an id [32].

**Deferred**
- **Per-user opt-out:** needs custom code.
  - No unsubscribe route or handling was found [12][13].
  - The `/api` routes shown are two send and two message endpoints, with none for suppressions. Suppressions appear only as a nested web route [13].
  - The app would need to store preferences and check them before sending.
- **Bounce handling:** partly met out of the box.
  - Inbound bounces are linked to the original message when the return-path DNS is set up [8][33].
  - A `MessageBounced` webhook is documented [14].
  - Suppressed recipients are held. A recipient is added after repeated hard fails within 24 hours (the code summary requires at least one prior hard fail) [12][15].
  - A user in a project discussion saw suppression only on the second hard fail. A maintainer suspected a race or ordering problem [15].
  - Updating app-side user state needs a webhook receiver.
- **Complaint handling:** no native support found, so it needs custom glue, and feasibility is unverified.
  - An issue requesting it was closed as not planned on 2024-08-08. The reply objected to it duplicating a discussion, so this is not a substantive rejection of the feature [16].
  - A feature request, "Native Feedback Loop (FBL) / Spam Complaint Webhook Support" (2026-07-16), is listed as open [17].
  - The feature list and webhook event list include no complaint item [12][14].
- **Delivery status visibility:** met out of the box through the UI, message and deliveries API, and webhooks (`MessageSent`, `MessageDelayed`, `MessageDeliveryFailed`, `MessageHeld`, `MessageBounced`) [7][12][13][14]. Showing status inside the owner's app needs custom code.

**Nice-to-have**
- **Hosted templates:** not offered, based on no template feature in the feature list or routes [12][13]. Templates would stay in the app.
- **Open and click tracking:** needs configuration: a tracking subdomain, a proxy rule that sets `X-Postal-Track-Host`, and enabling it in the UI [18].

## 4. Features used versus offered
The vendor feature list has 23 items [12], paraphrased here. Automatic retry is not a separate item.

**Used: 9 of 23** (all must-have tiers, my mapping)
- Message history
- Queue view
- Delivery webhooks
- DNS checks for sending domains
- Complete logs
- SMTP or HTTP API sending
- DKIM signing
- Suppression list
- Open and click tracking

**Offered but not mapped: 14**
- Multiple organizations
- Statistics graphs
- Per-server retention and disk limits
- Server-wide search
- Multiple credentials
- Development-mode message holding
- Send limits
- IP pools
- Sender or recipient IP routing
- Message tagging
- Inbound forwarding to HTTP
- Inbound forwarding to SMTP
- Inbound forwarding to email addresses
- Spam and virus checking

For the "now" requirements alone, the directly relevant items are API sending, DKIM signing and DNS checks (3 of 23).

## 5. Install and operations
- **Components:**
  - `web`, `smtp` and `worker` containers, plus a `runner` tool profile [19].
  - MariaDB 10.6 or higher. MySQL is not supported [2].
  - A web or TLS proxy. The docs use Caddy and say other proxies work [6].
  - Optional SpamAssassin, disabled by default. ClamAV is also listed [12][34].
- **No RabbitMQ:** version 3.0.0 removed it, along with the cron and requeuer processes [10].
- **State:**
  - MariaDB holds the main database and a separate database per mail server. The database user needs rights to create and delete databases [2].
  - `signing.key` and `postal.yml` also need to be preserved [6].
  - The existing managed Postgres 16 cannot serve this role, since MariaDB is required. This is a new stateful component, and I found no Postal backup guidance. The guardrail requires a backup story.
- **High availability:** I found no official HA requirement or guide. This is my inference: with single instances, a MariaDB, web or worker outage would stop acceptance or delivery. Upgrades are not zero-downtime [9].
- **Host requirements:** the docs strongly recommend a dedicated server with at least 4 GB RAM, 2 cores and 25 GB disk [2].
- **Network:** outbound port 25 must not be blocked, and the provider's IP may already be blocklisted [2].
  - As one example, DigitalOcean blocks ports 25, 465 and 587 on Droplets [23].
  - Postal supports `smtp_relays`, which take precedence over MX delivery [31]. Using a relay would add an external sending service.
- **Kubernetes:**
  - The install docs describe Docker and Compose. The prerequisites page also says other container software can be used [2].
  - The upgrade page suggests an orchestrator such as Kubernetes for zero-downtime needs [9].
  - I found no official manifests or chart. A community chart, `hoverkraft-tech/helm-chart-postal`, showed 81 commits and 3 stars; its currency is unverified [25].
- **Install time (my estimate, not sourced):** 1–2 days for the documented single-host path with DNS. 3–5 days to adapt it to Kubernetes with backups, secrets and monitoring. This excludes IP reputation warm-up and any provider request to unblock port 25.
- **Expertise:** Docker or Kubernetes, MariaDB operation and backup, DNS (SPF, DKIM, MX, return path, reverse DNS), TLS and proxying, and sender reputation management.
- **Monitoring:** the worker (port 9090) and SMTP server (9091) expose `/health` and Prometheus `/metrics`. `/health` returns OK while the process is running [27].

## 6. Integration facts
- **Auth:** the API uses a random key per mail server [7]. The web UI uses local passwords or OIDC [35].
- **Config:**
  - Infrastructure settings come from YAML v2 or environment variables, and every YAML setting has an environment equivalent. Changes need a restart [21].
  - The documented setup creates organizations, servers, domains and credentials in the web UI [6].
  - The API does not cover all management functions. A v2 API has no ETA, and maintainers do not accept extensions to the current one [7].
  - Resources created in the UI would therefore not live as YAML in the repo.
- **Credentials and network access:**
  - Main and message database credentials, including database create and delete rights [2].
  - The signing key, and a Rails secret key [6][11].
  - Outbound port 25 or a relay [2][31].
  - Inbound SMTP (default port 25) for bounces and MX, and web access through the proxy [8][11].
  - DNS resolution [11]. Outbound HTTP for webhooks [14].
- **Stack fit:** FastAPI can call the HTTP API or use SMTP [7][12]. There is no use of Postgres, and no Redis or broker is needed [2][10].
- **Guardrail conflicts:**
  - **Prefer managed services:** Postal is self-hosted.
  - **No new stateful component without a backup story:** MariaDB and the key files need one.
  - **Secrets only in the secret manager:** database passwords and the signing key can be supplied as environment variables or mounted files, although I did not verify an integration with any secret manager [6][21].
    - The schema stores per-domain DKIM private keys in the database (`domains.dkim_private_key` and `pending_dkim_private_key`) [36].
    - It also has `credentials.key` and `track_certificates.key` columns. The latter is likely a TLS private key [36].
    - These Postal-generated production secrets would sit outside the secret manager, which appears to conflict with the guardrail.
  - **New vendor cost:** the software has no license fee. See section 8 for infrastructure.

## 7. Maintenance facts
- **Upgrade:** run `git pull` in the install helper, then `postal upgrade [version]`. This pulls images, applies schema updates and restarts containers. It is not zero-downtime [9]. A Kubernetes deployment would need its own equivalent.
- **Breaking-change history:**
  - 3.0.0 (2024-03-04) was a major upgrade with an upgrade guide. It removed RabbitMQ and two processes. v1 users must follow a separate upgrade path [9][10].
  - 3.3.1 removed moonrope but kept the legacy API actions. 3.3.5 removed the `version` key from the Compose file [10].
  - 3.3.5 moved to Rails 7.1 and Ruby 3.4, 3.4.0 to Rails 8.1.4, and 3.5.0 to Ruby 3.4.13 [1][10].
  - No entry in the last six months is labeled breaking [1][10].
- **Security fixes:**
  - 3.3.7 (2026-06-03) fixed SSRF and a SQL injection (GHSA-x2hq-rfpg-3xr5) [10].
  - 3.3.6 and 3.3.5 included HTML or redirect hardening [10].
  - The advisories page listed two items: HTML injection (High, 2026-03-12) and SMTP smuggling (Moderate, 2024-03-11). It did not list the SQL injection ID in the changelog [10][22].
- **Maintainers:** the project is under the `postalserver` organization, with community contributions in recent commits [3][4]. Krystal Hosting is a copyright holder [28]. I could not confirm current staffing or a support commitment.
- **Hours per month (my estimate, not sourced):** about 4–8 in steady state for OS and image patching, upgrades, MariaDB backups and restore checks, and blocklist, DNS and bounce monitoring. Delivery or IP reputation incidents would be extra. The basis is the component list, not measured data.

## 8. Cost
- **Software:** $0 under MIT, with no paid tier or feature paywall found. There is no vendor free-tier ceiling; capacity depends on infrastructure and configured limits [3][12].
- **Reference host:** a 4 GiB, 2 vCPU DigitalOcean Basic Droplet is $24/month [24].
  - This is only a price reference. That platform blocks SMTP ports, including 587 and 465, so it does not work for direct delivery as documented [23]. I did not check whether relays on other ports would work there.
  - The owner's cloud provider is unnamed.
- **Not included:** backup storage, a dedicated sending IP, any managed MariaDB, any SMTP relay and engineer time. The total is unverified. Fitting Postal onto the existing cluster could change the compute cost, but the docs recommend a dedicated server [2].
- **Volume:** I found no per-email software fee at 200 or 2,000 emails a month.

## 9. Security facts
- **Secrets:** it holds DKIM private keys, API and SMTP credentials, the signing key, database passwords and likely tracking TLS keys [6][36].
- **Data:** it stores message history, so report email content and recipient addresses would be held there, subject to per-server retention settings [12].
- **New network surface:** a web UI and API, an SMTP server (default port 25, TLS off by default), optional tracking hostnames, and inbound bounce handling [8][11][18].
  - The health server binds to 127.0.0.1 by default for SMTP [11].
- **Permissions:** it needs database create and delete rights [2]. The documented Caddy container uses host networking [6]. I found no documented need for Kubernetes cluster-admin or cloud account permissions.
- **Webhooks:** signed over the request body with `X-Postal-Signature`, `X-Postal-Signature-256` and a key ID header [37]. Delivery is tried six times in total, after delays of 2, 3, 6, 10 and 15 minutes, then the request is destroyed. The timeout is 5 seconds [38]. By my calculation, a receiver outage longer than about 36 minutes, plus request time, could lose events, so reconciliation would be needed.

## 10. Lock-in
- **Formats:** data is in MariaDB, and configuration is YAML or environment variables [2][21].
- **Export:** direct database access is possible because the owner hosts it. I found no documented export tool.
- **API openness:** the source is MIT. The send API is Postal-specific and labeled legacy in the code paths, and webhooks use Postal event formats [7][13][14]. SMTP sending is also supported [12].
- **Switching (my estimate):** about 1–3 days, covering the send adapter, webhook handler and DNS records. Add time if history or suppressions must be moved. Using SMTP could reduce code changes. A new sending service would have its own DNS and reputation setup.

## 11. Scaling
- I found no software volume cap for 200 to 2,000 emails a month, or for 500 to 5,000 monthly active users. I found no vendor throughput benchmark.
- The defaults include 2 worker threads and a main database pool of 5. The maximum message size setting is 14 [11].
- Send limits are configurable per server, and messages over the hourly limit are held [12][15].
- This is my inference: the expected average of about 67 emails a day is unlikely to be limited by the 4 GB, 2-core minimum. Report bursts were not assessed.
- There is no tier change. Growth would mean resizing the host or database, adding worker threads or processes, or using IP pools [11][12]. Deliverability depends on IP reputation, which I could not measure [2].

## 12. Sources
All retrieved 2026-11-26.

1. https://github.com/postalserver/postal/releases
2. https://docs.postalserver.io/getting-started/prerequisites
3. https://github.com/postalserver/postal
4. https://github.com/postalserver/postal/commits/main
5. https://github.com/postalserver/install
6. https://docs.postalserver.io/getting-started/installation
7. https://docs.postalserver.io/developer/api
8. https://docs.postalserver.io/getting-started/dns-configuration
9. https://docs.postalserver.io/getting-started/upgrading
10. https://raw.githubusercontent.com/postalserver/postal/main/CHANGELOG.md
11. https://raw.githubusercontent.com/postalserver/postal/main/doc/config/yaml.yml
12. https://docs.postalserver.io/welcome/feature-list (the outgoing processor code behind the suppression behavior is [39])
13. https://raw.githubusercontent.com/postalserver/postal/main/config/routes.rb
14. https://docs.postalserver.io/developer/webhooks
15. https://github.com/orgs/postalserver/discussions/3535
16. https://github.com/postalserver/postal/issues/3084
17. https://github.com/orgs/postalserver/discussions?discussions_q=feedback+loop (links to /discussions/3609)
18. https://docs.postalserver.io/features/click-and-open-tracking
19. https://raw.githubusercontent.com/postalserver/install/main/templates/docker-compose.v3.yml
20. https://raw.githubusercontent.com/postalserver/postal/main/config/routes.rb (same page as [13])
21. https://docs.postalserver.io/getting-started/configuration
22. https://github.com/postalserver/postal/security/advisories
23. https://docs.digitalocean.com/support/why-is-smtp-blocked/
24. https://www.digitalocean.com/pricing/droplets
25. https://github.com/hoverkraft-tech/helm-chart-postal
26. https://github.com/postalserver/install/tree/main/templates
27. https://docs.postalserver.io/features/health-metrics
28. https://raw.githubusercontent.com/postalserver/postal/main/MIT-LICENCE
29. https://raw.githubusercontent.com/postalserver/postal/main/app/models/concerns/has_locking.rb
30. https://raw.githubusercontent.com/postalserver/postal/main/app/lib/message_dequeuer/single_message_processor.rb
31. https://raw.githubusercontent.com/postalserver/postal/main/app/senders/smtp_sender.rb
32. https://raw.githubusercontent.com/postalserver/postal/main/app/controllers/legacy_api/send_controller.rb
33. https://raw.githubusercontent.com/postalserver/postal/main/app/lib/message_dequeuer/incoming_message_processor.rb
34. https://docs.postalserver.io/features/spam-and-virus-checking
35. https://docs.postalserver.io/features/oidc
36. https://raw.githubusercontent.com/postalserver/postal/main/db/schema.rb
37. https://raw.githubusercontent.com/postalserver/postal/main/lib/postal/http.rb
38. https://raw.githubusercontent.com/postalserver/postal/main/app/services/webhook_delivery_service.rb
39. https://raw.githubusercontent.com/postalserver/postal/main/app/lib/message_dequeuer/outgoing_message_processor.rb

## 13. Could not verify
- **Complaint handling:** I did not read the bodies or replies of discussions 3609 or 1515. I also did not check whether complaint reports could be processed through inbound routes.
- **Suppression management:** I could not confirm any way to add a suppression manually or by API. I checked the routes, the feature list and a GitHub-restricted search. Absence from the summarized routes is not proof.
- **Durability of `send/message`:** I did not inspect the model that writes the message and queue records, so I don't know whether the writes are atomic. I also did not test crash behavior of the worker or MariaDB.
- **Backup and restore:** I found no Postal-specific guidance in one GitHub and docs search. I did not read the Mail Server Settings page, so retention defaults are unverified.
- **Kubernetes:** I found no official support statement, manifests or chart in the pages checked. The community chart's page did not show its latest release, commit date or dependencies. Other charts found by search were not checked. I did not verify the official container image's registry path.
- **Install helper:** its last commit date was not shown [5]. The prerequisites docs and the repo README differ in emphasis: the README describes Ubuntu prerequisite scripts that use insecure default database passwords and are for testing only [5].
- **Reverse DNS:** the DNS page read does not cover PTR records [8].
- **Port 25 and cost:** the owner's cloud provider is unnamed, so its egress policy, IP reputation, compute price and managed MariaDB price are unknown.
- **Maintainer capacity:** the contributors graph did not load, and the contributors API returned 403. I found no support SLA.
- **Release history:** I saw only the 10 most recent releases.
- **Webhook signing:** I did not verify the signing algorithm behind the SHA-256 header or how receivers get the public key.
- **Time estimates and throughput:** install, monthly maintenance and switching hours are my estimates. I found no throughput benchmark.
- **Prompt injection:** I noticed none in the content retrieved. Search results included tool-generated "reminder" text asking for source links, which came from the search tool wrapper rather than from a source page.

I wrote no files.
