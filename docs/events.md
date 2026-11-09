# Events

The main site stays a static GitHub Pages site with no build or new dependencies.

- `/events/` lists announced events; currently the China Trip is the only one.
- `/events/china-trip-2027/` is its dedicated detail page.
- `assets/css/events.css` reuses the site's local fonts, monochrome styling,
  rules and pale yellow accent. The new pages are plain HTML, with no hydration.
- `assets/images/esra-china-trip-cover.png` is the existing ESRA trip artwork.

The homepage Events links are present in **both** `index.html` and the home
JavaScript bundle so React hydration preserves them. The original Framer router
has no event routes; these are ordinary anchors and load the static pages directly.

## Content updates

Edit the two event HTML files directly. To add an event, create another folder
under `events/` with an `index.html`, copy the detail page's navigation, metadata
and stylesheet, and add its card to `events/index.html`. Update the page lists in
`scripts/check.py` and `scripts/check-breakpoints.mjs`, then run both checks.
Do not invent events to fill the listing.

Dates for the China Trip are **provisional** (14–23 March 2027). The Luma copy
and the Notion planning hub disagree about the cities, so this page leaves the
route unconfirmed. Hosts, costs and funding remain unconfirmed too.

The existing Luma event is https://luma.com/m5dh07ac (unlisted/private when
reviewed). The page links there for current registration information. The
separate Tally participant form was last verified as a draft; its public link
must be verified before replacing the Luma call to action with an application
button. Club membership uses its existing, separate Tally form.

## Optional events.esrarobotics.eu

The branch already works at `https://esrarobotics.eu/events/` after a normal
merge and Pages deployment. **Do not change the root CNAME:** that would move
the whole organisation website. GitHub Pages configures a custom domain per
site, so an independent events host needs a second Pages site/repository.

An optional export helper prepares the same pages for that second site:

```bash
python3 scripts/export-events.py /tmp/esra-events-site
```

Use a new or empty directory outside this checkout. The export contains the
listing at `/`, retains `/events/` as an alias, includes the trip detail page
and local assets, and directs organisation/legal navigation to the main site.
Canonical URLs continue pointing to the main site's `/events/` pages so there
is one canonical copy. The export alone does not publish or modify DNS.

To activate the subdomain:

1. Create a separate GitHub Pages repository and publish the exported contents.
2. Verify domain ownership in the ESRA GitHub organisation and set that site's
   custom domain to `events.esrarobotics.eu`.
3. At the DNS provider, set a CNAME for `events` to `esra-robotics.github.io`
   (no repository name or URL path).
4. Once GitHub verifies DNS and issues the certificate, enable Enforce HTTPS.
5. Verify the listing, detail page, images and links on the new host. Re-export
   and deploy this second site whenever event content changes.

Keep the main navigation pointed to `/events/` until the subdomain is live;
then change its href in both homepage copies if the subdomain is preferred.

GitHub reference: [Custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages).

## Community submissions and newsletters

`/events/submit/` accepts event details and the organiser's private contact email.
`/events/rules/` explains relevance, organiser attribution, review and the service
privacy supplement. `/events/review/` uses expiring links from trusted-reviewer
HTML emails; accepting publishes through the API without changing Git. The
previous GitHub-issue-only submission path is superseded.

The static site stays independently usable. `events/catalog.json` defines the
shared event types and ESRA's seed event; `events/config.json` optionally points
to the API host. Community listings are fetched only from the approved feed.
Organiser, location and event type are visible; ESRA Original remains a prominent
label reserved for ESRA programming. Filters support multiple types, network and
club, plus separate upcoming, happening-now and past views. Matching filter state
can be copied to newsletter signup. Filters are shareable in the URL, not cookies.

Newsletter signup uses explicit consent and email confirmation. Preferences and
unsubscribe are managed at `/events/preferences/` through secure emailed links.
Weekly digests exclude past events and use the subscriber's selected filters.

See [the backend deployment guide](../backend/README.md) for the persistent API,
trusted reviewers, sender/provider setup, SMTP dispatcher, digest and retention
jobs. No production service, SMTP delivery or scheduling has been activated.
Do not deploy private configuration, databases or test email previews to Pages.

## China content

See [source reconciliation](china-trip-content.md). Notion's academic/company
names are outreach targets, not confirmed visits. ESRA network logos are not
selected-fellow or host endorsements. Destination photos do not imply past visits.
