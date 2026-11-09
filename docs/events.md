# ESRA Events

The attendee-facing website remains static on GitHub Pages, main branch,
repository root. Event discovery, detail pages, filters and RSS/calendar feeds
work without a backend. The optional mail relay in [mail-gateway](../mail-gateway/README.md)
connects the on-site signup and ESRA organiser sign-in to Brevo and GitHub.
It is prepared but not deployed: events/mail-config.json has an empty endpoint,
so the UI reports unavailable service rather than pretending to save addresses.
No provider account, list, campaign or secrets were configured, and no mail sent.

## Submissions and review

An organiser requests a private sign-in link at /events/submit/ using their
exact @esrarobotics.eu address. The relay validates inbox access with a signed
20-minute link, then accepts a public event proposal into a GitHub issue. Private
organiser email stays out of that issue. The form is unavailable without valid
access. Opening a GitHub issue manually does not bypass this check: the review
workflow verifies the relay's signed payload using EVENT_SUBMISSION_SECRET.

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
separate. Scheduled events are paginated; undated proposals appear separately
under On the drawing board and are excluded from calendars. Original events have
prominent branding; community listings show their club and location. RSS and
calendar feeds remain available as alternatives, including type/club feeds.
The proposed FC Isar robot-football hackathon has no confirmed date or venue.

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
Hosts, route, funding and costs are not confirmed. The unpublished participant
Tally form is not linked as a public application.

The main-site `CNAME` remains `esrarobotics.eu`. An optional static export uses:

```sh
python3 scripts/export-events.py /tmp/esra-events-site
```

The export includes the catalogue, feeds, event pages and local assets, with a
CNAME for `events.esrarobotics.eu`. It needs a separate Pages site/repository and
DNS CNAME `events` → `esra-robotics.github.io`; exporting does not activate either.
Organisation/legal links point back to the main website. Feed URLs use the main
website as their canonical host, avoiding separate subscription identities.
