# Worked example 2: a customer notifier (email now, portal later)

Context: a notifier reads ready events from a job queue and emails the customer; it must send late rather than never if a failed job recovers. Declared: email is a must-have now, the portal is a deferred must-have, re-notify is a nice-to-have, at-least-once delivery is acceptable. Environment: production. Stage: pre-revenue (cost modifier minus one). Owner's gut before scoring: build it, keep it small and simple.

Options scored (rough, first pass, before the stage, maturity, and scaling modifiers were final):
- Custom build (small service reading the queue and sending through an email provider): about 89%.
- Resend (hosted email API, free for 3,000 emails a month; it only sends, so the queue-reading glue is still written by the owner): about 88%.
- Novu self-hosted (open source notification platform with a portal inbox, but needs its own databases and workers, so large baggage and several stateful dependencies): about 60%.
- Cloudflare Email Service from a Worker (fits a Cloudflare-based stack; sending needs the paid Workers plan at about $5 a month, 3,000 emails included; still in beta with pricing not finalized): about 91% on the first pass.

After the later rules: the pre-revenue stage modifier takes a point off the paid options' cost, and the maturity modifier takes a point off Cloudflare's maintenance because pricing was not final. That puts the simple build on top at about 89%, with the top three close enough to call a judgment call.

Scaling note: the free-tier ceiling is about 3,000 emails a month. At the owner's current volume that is a long way off, so the scaling modifier is zero for the hosted options (a plan change, not a migration), and the build sits behind an interface the owner controls so a swap stays cheap.

Result: the matrix agreed with the owner's gut. Build the simplest notifier now, behind an interface the owner controls, and mature into the hosted option (Cloudflare or Resend) once there is revenue or volume nears the free-tier ceiling. Novu's portal inbox is the one thing that could change this later. Novu cloud was not scored separately; do that if the portal comes forward. Prices and free-tier limits came from web searches whose sources disagreed in places, so verify them on the vendors' own pages.
