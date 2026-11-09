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

Python 3.11 or later with SQLite 3.38+ (JSON functions). No packages are required for local development:

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

Delivery workers atomically claim one message at a time, process at most 50 per
invocation (configurable with `deliver --batch-size 100`, maximum 500), and never
claim the entire queue. Multiple workers may run against the same private SQLite
file on one host. An SMTP failure marks only that message `uncertain`; a crash
can leave one message `claimed`. Neither state is retried automatically. Review
provider logs before retrying, because SMTP acceptance may already have occurred.
`python3 backend/service.py stats` prints aggregate event, subscription and queue
counts without addresses or tokens. Monitor uncertain/claimed counts and maintain
private backups of the SQLite database and signing secret. Restoring/rotating the secret invalidates outstanding links.
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

## Growth and maintainability

The public event API uses server-side filters and keyset pagination:
`GET /api/events?type=Trips&type=Hackathons&origin=community&period=upcoming&limit=25`.
Optional filters are `club` and `period` (`upcoming`, `current`, `past`). Page size
is capped at 100. Reuse `next_cursor` as `cursor` with the same filters for the
next page. `featured` contains matching curated ESRA Originals independently
of the community page, so original programming stays visible even as clubs add
more events. The browser has a Load more action, debounces filtering and ignores
out-of-order responses. Static-only fallback uses the separately tested matching
module. Adding an event type still starts in `events/catalog.json`.

SQLite runs in WAL mode with indexed public-event and queue queries and a busy
timeout for concurrent workers. Startup applies an additive migration to existing
event records in bounded batches; back up the database before first deployment
of this version. Never run schema migration with a delivery worker active. Digest
preparation reads 200 subscribers at a time, uses short queue-write transactions
and rechecks consent/preferences before queuing. It reads only ongoing/upcoming
events, excluding the historical archive from newsletter matching.

This remains a **single-host** service with a private local SQLite file. Do not
put the file on a shared network filesystem or run independent hosts against it.
Multi-host deployment requires a shared transactional database and queue with
matching claim/idempotency guarantees; that migration has not been implemented
or load-tested. No throughput or recipient-volume target is claimed here.

Public event-page header/footer markup lives in `templates/events/`. Run
`python3 scripts/sync-events-shell.py` after a template edit; commit the rendered
HTML. The `--check` mode detects drift in CI without adding a website build step.
Environment keys are listed in `backend/.env.example`; actual secrets and trusted
reviewer addresses stay in ignored private configuration. CI tests filtering,
API pagination, old-schema migration, concurrent claims and failed SMTP isolation.
