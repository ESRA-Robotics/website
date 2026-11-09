# ESRA Events: static-only operation

The website stays on the existing GitHub Pages setup: **main branch, repository
root**. There is no public API, database, SMTP server, runtime dependency or new
hosting service. The custom Python backend has been removed from this branch;
its earlier implementation remains recoverable in Git history. Ignored local
private settings/data are not used and must never be published.

## What is currently configured

Read-only inspection confirmed GitHub Pages and the Check site workflow. No mail
integration is declared in repository source. Webhook settings and the Actions
PR-creation policy could not be inspected with current connector permissions;
this is not evidence that an external integration exists or does not exist.
No wider permissions were requested and no live workflows, notifications or
emails were triggered while implementing the static approach.

## Submissions and review

1. A member fills `/events/submit/`. The browser validates the form and prepares
   a public GitHub issue. Nothing is saved or sent until the member reviews and
   submits it on GitHub. A GitHub account is required. Long descriptions can be
   copied as JSON into `.github/ISSUE_TEMPLATE/event.yml` instead of a long URL.
2. Reviewers watch repository Issues and Pull requests and enable GitHub email
   notifications. Each reviewer chooses and verifies their intended ESRA email
   in their own GitHub account. The site does not need a sender account, email
   credentials or a separate mailing list for these native notifications.
3. A maintainer verifies the public organiser, event URL, dates, location, costs
   and ESRA relevance. Run **Review community event** in Actions with the issue
   number and `prepare`, or add an `event:reviewed` label. Decline uses the
   `decline` decision or `event:declined` label and closes the issue.
4. The workflow checks the actor has write/maintain/admin access, reads the issue
   as data, validates and whitelists fields, generates the static catalogue and
   feeds, and opens a **draft event-update PR**. It never executes submitter code
   and never writes directly to main. Submitters cannot grant ESRA Original status.
5. Review the snapshot and checks, mark the PR ready, and merge it. A human merge
   into main uses the site's existing GitHub Pages publication flow.

The workflow becomes available after this branch is merged to the default branch.
Optional labels can be created by a repository maintainer; workflow_dispatch works
without them. The repository policy must permit Actions to create PRs for that
convenience step. That policy was not changed. If it blocks PR creation, the run
preserves prepared catalogue/feed files as an artifact, and a maintainer can open
an update manually. Existing event review branches are never overwritten.

This intentionally replaces custom accept/decline email buttons with GitHub's
authenticated review interface and native notification emails. Publication needs
an actual reviewed merge; receiving or opening an email never publishes an event.
Native GitHub email delivery and verified addresses are user settings; this task
did not change them or send test notifications.

References: [issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms),
[notification settings](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications),
[workflow token behaviour](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Subscriptions without a mailing backend

The event list and follow section share type, network and club filters. Listings
have upcoming, happening-now and past views. Client-side Load more keeps the DOM
bounded while every event comes from the static catalogue. ESRA Originals remain
prominent; community cards show the club, location and type.

- RSS feeds: all events, each type, each network scope, and individual clubs.
- Calendar feeds: corresponding static `.ics` URLs can be added to calendar apps
  that support URL subscriptions. Refresh behaviour depends on the calendar app.
- Filtered calendar download: a snapshot combining the visitor's chosen types,
  network and club. It is not an automatically updating subscription.
- Multiple RSS topics can be followed in the reader. Club feeds include all types
  from that club; the page states this rather than pretending arbitrary filter
  combinations are one server-maintained subscription.
- GitHub Watch can provide repository email notifications. It is not a filtered
  event newsletter. Configure it in GitHub; this site never collects addresses.

A custom email newsletter or custom HTML review emails require an actual mailing
provider or existing integration. None is configured by this implementation.
The UI therefore offers working feeds/calendar subscriptions and does not show a
nonfunctional email signup form. No API keys or tokens are placed in public HTML.

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
