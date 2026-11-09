# ESRA event service

The website remains a static GitHub Pages site. This optional Python/SQLite API
adds private submissions, trusted review, public approved listings and confirmed
newsletter subscriptions. No frontend framework or build is required.

## Implemented behaviour

- Submissions include club, location, type, timezone-aware dates, public HTTPS
  event URL, description and ESRA relevance. Contact email stays private.
- Every submission creates one HTML review message per trusted reviewer.
  Accept / Decline / Open buttons lead to the ESRA review page. GET never
  changes state; a reviewer confirms the decision by POST. Tokens expire after
  seven days, are scoped to a reviewer/event, and can decide an event only once.
- Accepted events appear immediately through `/api/events` in ESRA styling.
  Community submitters cannot assign the ESRA Original label.
- Newsletter signup requires consent and email confirmation (two-day link).
  Existing preferences are not changed by an unconfirmed request. Digests use
  the same types, network and case-insensitive organiser filter as the listing;
  past events are excluded. Preferences and unsubscribe links last 90 days.
- `prepare-digest` queues at most one newsletter per subscriber per ISO week.
  `deliver` is a separate command, disabled unless explicitly enabled. No
  request handler sends mail. No tracking pixels or third-party client code.
- Rate limits, request-size limits, HTTPS URL validation, escaped output,
  private database permissions and one-time decisions are covered by tests.

## Local development

Python 3.11 or later. No packages are required for local development:

```sh
python3 backend/service.py serve
python3 -m unittest discover -s backend -p 'test_*.py'
```

Create `backend/.env.local` first, using the keys below. The file and
`backend/private/` are ignored by Git. Do not copy either into public hosting.
The local preview serves only the public site paths and API, not repository or
backend files. `serve` is a development server, not a production HTTP host.

```text
ESRA_SECRET=<at-least-32-random-characters>
ESRA_SITE=http://127.0.0.1:8000
ESRA_DB=/absolute/private/path/events.sqlite3
REVIEWER_EMAILS=<comma-separated-trusted-email-addresses>
EMAIL_DELIVERY=disabled
EMAIL_FROM=<verified-sender-address>
SMTP_HOST=<provider-hostname>
SMTP_PORT=587
SMTP_USER=<provider-user>
SMTP_PASSWORD=<provider-secret>
```

The requested reviewer addresses are saved in the ignored local configuration.
Sending stays disabled; no SMTP credentials are present. The user authorised
future deployed automated review/subscription emails, not manual outgoing mail.
The intended sender/provider still needs configuration and verification.

## Production deployment

GitHub Pages cannot run this API. Deploy `backend/wsgi.py` on a persistent Python
host with private SQLite storage and HTTPS. Use a production WSGI server such
as Gunicorn, installed/pinned in that deployment environment, not in the static
website. For example, from this checkout:

```sh
gunicorn --chdir backend --bind 127.0.0.1:8000 --workers 2 wsgi:application
```

Put an HTTPS reverse proxy in front of it. Only expose `/api/`; return 404 for
all other paths on the API host. Set a 20KB request limit and request/header
read timeouts there. Keep the WSGI listener private. Python's `http.server`
[is not recommended for production](https://docs.python.org/3/library/http.server.html).

Set `ESRA_SITE` to the canonical public website origin used for email links,
for example `https://events.esrarobotics.eu`. Set `ESRA_ORIGINS` to the exact
additional allowed frontend origins, such as `https://esrarobotics.eu`.
CORS allows only configured origins; there are no session cookies. Prefer a
separate `https://api.esrarobotics.eu` host for the API and set
`events/config.json` to `{"apiBase":"https://api.esrarobotics.eu"}`.
No credentials belong in this public JSON file.

The rate limiter uses the direct peer by default. For per-visitor limits behind
a proxy, configure the proxy to **overwrite** `X-Real-IP`, keep the app listener
private, and only then set `ESRA_TRUST_PROXY=1`. Never trust client-supplied
forwarding headers on a public listener. Add edge spam/rate controls appropriate
to traffic before opening a public form.

Configure a verified sender/provider (SPF/DKIM/DMARC via that provider), TLS SMTP
credentials and the three trusted reviewer addresses. `deliver` requires
STARTTLS and verified TLS; SMTP credentials remain server-side.
[Python SMTP documentation](https://docs.python.org/3/library/smtplib.html).

After review on a staging host, set `EMAIL_DELIVERY=enabled` in production and
run the following jobs under the same restricted service account/environment:

- Every minute: `python3 backend/service.py deliver`
- Weekly: `python3 backend/service.py prepare-digest` (ISO-week idempotency)
- Daily: `python3 backend/service.py prune`

These are deployment instructions, not jobs installed on the user's computer.
Prune removes pending/declined submissions after 90 days, unconfirmed signups
after seven days, email records after 30 days and expired request-limit entries.

## Operations and limits

Run one delivery worker. It claims a batch before SMTP transmission. A crash or
ambiguous SMTP failure leaves claimed messages for administrator reconciliation;
do not blindly reset them or they may be sent twice. Review provider logs before
retrying. Monitor this queue and maintain private backups of the SQLite database
and signing secret. Restoring/rotating the secret invalidates outstanding links.
Unsubscribe removes the subscription record and pending messages. Claimed mail
may already be in transit, so stop the worker before operational bulk removals.

Approved community events are dynamically fetched. The static seed is in
`events/catalog.json` and remains usable during an API outage; the UI states
when submissions/subscriptions are unavailable. Accepted events do not edit Git
or trigger a Pages deployment. The service is a small deployment-ready reference
implementation; hosting, SMTP delivery, DNS and operational/legal privacy review
have not been activated or verified in production.

Before enabling collection, reconcile the public event privacy supplement with
the controller's actual processor, hosting, retention and contact arrangements.
The generated organisation legal page was not silently rewritten.
