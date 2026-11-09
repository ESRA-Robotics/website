# ESRA Events

The attendee-facing website remains static on GitHub Pages, main branch,
repository root. Event discovery, detail pages, filters and RSS/calendar feeds
work without a backend. The optional mail relay in [mail-gateway](../mail-gateway/README.md)
connects the on-site signup and ESRA organiser submissions to Brevo and GitHub.
It is prepared but not deployed: events/mail-config.json has an empty endpoint,
so the UI reports unavailable service rather than pretending to save addresses.
No provider account, list, campaign or secrets were configured, and no mail sent.

## Submissions and review

An organiser fills one visible form at /events/submit/ using an
@esrarobotics.eu address. No sign-in link is required in this initial setup.
The relay checks the declared domain and signs the exact validated public event
payload before creating a GitHub review issue. This is not inbox verification:
anyone can type an ESRA address. The issue labels it self-declared, and reviewers
must verify the actual organiser before approval. Private email is omitted from
the issue. Manually created or altered issues cannot bypass the payload signature.

A maintainer checks relevance, organiser, dates, registration, costs and accuracy.
Run Review community event with the issue number and prepare, or apply the
maintainer-only event:reviewed decision. The workflow checks actor permissions,
validates and whitelists fields, updates catalogue/feeds and prepares a draft PR.
It never executes submitter code or directly publishes to main. Submitters cannot
grant Original status. Decline closes the issue. Publication requires a reviewed
human merge and the existing Pages flow. Actions must be permitted to create PRs;
otherwise the prepared files remain available as an artifact. These workflows
become available after merging the branch to the default branch.

Review notification delivery remains GitHub-native. The trusted reviewers are
fschroeders@esrarobotics.eu, lwitte@esrarobotics.eu and pvoelker@esrarobotics.eu;
each must configure a verified notification address in their own GitHub account.
This task did not configure those accounts. Custom HTML accept/decline emails
are not implemented; authenticated GitHub review remains required.

## Subscriptions and discovery

The primary Subscribe to all events button opens a simple email/consent dialog.
The relay requests Brevo double opt-in; confirmed contacts live in the provider,
not the repository. Configure a Brevo RSS campaign against /events/feeds/all.xml
for recurring updates. Neither the campaign nor live collection is activated.
Provider-managed unsubscribe links handle removal. Activation and privacy
requirements are documented with the relay.

Filters sit inside a quiet disclosure. Upcoming, ongoing and past events stay
separate. Scheduled events are paginated. Original events have
prominent branding; community listings show their club and location. RSS and
calendar feeds remain available as alternatives, including type/club feeds.
The planned FC Isar Booster T2 hackathon is part of the China delegation, not a
separate event. It has no independently published date or venue.

## Content maintenance

`events/catalog.json` contains approved public events and the shared event types.
Add an event there (or use the reviewed-issue workflow), then run:

```sh
python3 scripts/build-event-feeds.py
python3 scripts/build-event-feeds.py --check
python3 scripts/sync-events-shell.py --check
python3 -m unittest discover -s scripts -p 'test_static_events.py'
node --test scripts/test-event-matching.mjs
python3 scripts/check.py
node scripts/check-breakpoints.mjs
```

Commit the rendered files in `events/feeds/`. No build runs for a website visitor.
The generator uses standard-library Python and preserves retired club-feed URLs
as empty feeds so existing subscriptions do not break. RSS contains up to 100
recently published entries per feed, retaining past announcements as history; calendar feeds contain the matching events.
Feed refresh is tied to published catalogue updates, not a background service.

Navigation/footer templates live in `templates/events/`. Edit them and run
`python3 scripts/sync-events-shell.py` before committing the rendered HTML.
The existing Framer homepage still needs edits in both HTML and its hydration
bundle. The standalone event pages do not hydrate.

## China and optional subdomain

`/events/china-trip-2027/` retains the ESRA Original delegation page and provisional
Notion-grounded outreach targets. See [source reconciliation](china-trip-content.md).
Hosts, route, funding and costs are not confirmed. China applications link
directly to Luma. The native participant application form and endpoint have been
removed. The user added a planned 12–24-hour Booster T2 humanoid hackathon with
FC Isar Robotics; final delivery details remain to be confirmed.

The main-site `CNAME` remains `esrarobotics.eu`. An optional static export uses:

```sh
python3 scripts/export-events.py /tmp/esra-events-site
```

The export includes the catalogue, feeds, event pages and local assets, with a
CNAME for `events.esrarobotics.eu`. It needs a separate Pages site/repository and
DNS CNAME `events` → `esra-robotics.github.io`; exporting does not activate either.
Organisation/legal links point back to the main website. Feed URLs use the main
website as their canonical host, avoiding separate subscription identities.
