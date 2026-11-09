# ESRA website

The website of the **European Student Robotics Association**, live at
**[esrarobotics.eu](https://esrarobotics.eu)**.

It is a static site: plain HTML, CSS, images and JavaScript, served by GitHub
Pages straight from this repository. There is nothing to install and nothing to
build.

> **New here?** Read [Before you change anything](#before-you-change-anything).
> One thing about this site is genuinely surprising, and skipping it is how
> people end up shipping changes that do not appear.
>
> Working with an AI coding agent? Point it at [AGENTS.md](AGENTS.md).

---

## Looking at the site locally

```bash
git clone git@github.com:ESRA-Robotics/website.git
cd website
python3 -m http.server 8000
```

Then open <http://localhost:8000>.

Use the server. Opening `index.html` by double-clicking it will not work,
because asset paths start from the site root.

---

## Before you change anything

The site was designed in Framer and exported as static files. Two things follow
from that, and both will bite you otherwise.

**The HTML is generated, not hand-written.** Class names look like
`framer-1jqxlnd`. They are meaningless to read but essential to keep. Do not
reformat or tidy the markup: you will produce a diff nobody can review.

**Every piece of text is stored twice.** Once in the HTML, and once in a
JavaScript file in `assets/js/`. The browser shows the HTML first, then React
re-renders the page from the JavaScript. So if you edit only the HTML, your new
text appears for a split second and is then replaced by the old text.

This is the single most common mistake made on this repository. Use the helper
instead, which changes both copies at once:

```bash
python3 scripts/edit-text.py "We are currently looking for new members" "We are now closed for applications"
```

Add `--dry-run` to see what it would touch. It prints how many replacements it
made in each file, and warns if the two copies would end up disagreeing.

---

## Making a change

1. Branch off `main`.
2. Make the change, using `scripts/edit-text.py` for any wording.
3. Run both checks:

   ```bash
   python3 scripts/check.py            # reads the files
   node scripts/check-breakpoints.mjs  # renders the pages in a browser
   ```

4. Look at the page in a browser, **at a phone width as well as a wide one**,
   and wait for it to finish loading, since that is when text edits come undone.
5. Open a pull request. CI runs the same checks.

### What the checks cover

`scripts/check.py` needs no dependencies and takes about a second. It fails if:

- a required page or file is missing,
- anything points at an asset that is not in the repository,
- a JavaScript bundle no longer parses,
- the site would load anything from Framer or another third party,
- the HTML and the JavaScript disagree about a piece of text,
- the legal page no longer matches `scripts/legal_content.py`.

It warns, without failing, about things a person still has to decide, such as
the leftover `studentrobotics.eu` contact address.

`scripts/check-breakpoints.mjs` opens every page at six widths in headless
Chrome and fails if a page scrolls sideways, if the sections come out in a
different order at one width than another, if the section numbers repeat or go
backwards, or if content that must always be there has gone missing. It needs
Google Chrome, and skips itself with a message if there is none.

This second check exists because of four real faults, all of which looked
perfect on a laptop and perfect in the markup:

- the whole application section, including the only APPLY NOW button, was
  missing on phones,
- every footer link was missing on phones, so the imprint and the privacy
  notice could not be reached at all,
- the partner block rendered underneath the application heading, and the
  university logos fell past the contact section,
- between 634px and 809px the JOIN ESRA heading and the intake date sat
  completely hidden behind the dark panel.

**Please do not judge a change by one window width.** Narrow the browser to
phone size before you call anything done.

---

## How it is published

GitHub Pages serves the `main` branch from the repository root.

**Pushing to `main` publishes to the live site**, normally within a minute.
There is no staging environment, so please work on a branch and use a pull
request.

The custom domain is set by the `CNAME` file. HTTPS is enforced, and
`esrarobotics.eu` and `www.esrarobotics.eu` are both covered by the certificate.

---

## What is where

```
index.html              Home page: hero, pillars, member network, partners, application
imprint/index.html      Imprint and privacy notice, served at /imprint/
404.html                Not-found page. Plain hand-written HTML, easy to edit.
CNAME                   The custom domain
assets/images/          Photos, logos and icons
assets/fonts/           Inter and Intel One Mono, self-hosted
assets/js/              The Framer runtime and the per-page bundles
scripts/check.py        The integrity check
scripts/check-breakpoints.mjs  Renders every page at six widths
scripts/edit-text.py    Changes copy in the HTML and the JavaScript together
scripts/legal_content.py  The text of the imprint and privacy notice
scripts/build-legal.py  Renders that text onto the legal page
docs/content-guide.md   Where each section's text and images live
AGENTS.md               Instructions for AI coding agents
```

For a guide to which file holds which bit of the page, see
[docs/content-guide.md](docs/content-guide.md).

---

## The site is self-contained, please keep it that way

Everything the site needs is committed here: fonts, images, and the JavaScript
runtime. It makes **no requests to Framer or any other third party**, and no
analytics or tracking scripts run on it.

That is deliberate. The original Framer project could be deleted or lapse at any
time, and the site has to keep working. The Framer tracking script and the
leftover editor toolbar were removed for the same reason.

Please do not add CDN links, web-font links or tracking snippets.
`scripts/check.py` will fail if you do.

---

## Legal pages

`/imprint/` carries both the imprint required by § 5 of the German Digital
Services Act (DDG) and the privacy notice required by Articles 13 and 14 GDPR.
The footer links to it twice, as IMPRINT and as PRIVACY, and the second link
jumps straight to the privacy section.

**Do not edit that page by hand.** Its text lives in
[scripts/legal_content.py](scripts/legal_content.py), which is plain readable
Python that anyone, including a lawyer, can edit without touching markup. Then
render it into the site:

```bash
python3 scripts/build-legal.py
python3 scripts/check.py
```

The script writes both copies the page needs, so the text cannot drift.

Two deliberate absences, so nobody "fixes" them later:

- **No link to the EU online dispute resolution platform.** That platform was
  shut down on 20 July 2025. A link to it is now a dead link and a possible
  ground for a warning letter. The page says so explicitly.
- **No cookie banner.** The site sets no cookies and writes nothing to browser
  storage, which has been verified in a browser, so nothing needs consent under
  § 25 TDDDG. If anyone ever adds analytics or an embedded form, that changes
  and a consent solution becomes necessary.

---

## Open items

These need a decision from the ESRA board, not a code change. They are left
alone on purpose so that nobody guesses at a published fact.

**Have a lawyer read the legal page before relying on it.** It was written
carefully against the current rules, but it is not legal advice, and only the
board knows the facts behind some of the entries below.

- **Telephone number.** The imprint currently gives an email address only.
  § 5 (1) no. 2 DDG asks for a means of rapid electronic contact and direct
  communication. The European Court of Justice has accepted email alone where
  enquiries are answered quickly (C-298/07), which is the position the page
  takes. Adding a phone number would remove the argument entirely.

- **Responsible for editorial content.** The page names Florian Schroeders
  under § 18 (2) MStV. This must be a named natural person, so change it if
  someone else should carry that role.

- **Processor agreements.** The privacy notice states that GitHub and Tally
  process data on ESRA's behalf. Confirm that the GitHub data processing
  addendum and Tally's data processing agreement have been accepted.

- **A German version.** The page is in English, matching the rest of the site
  and its pan-European audience, with the German statutory terms given
  alongside. A German translation is worth considering, since the association
  is registered in Germany.

- **Application deadline.** The application section reads *"our first intake by
  14.09.2026"*, which has passed. It needs a new date, or different wording if
  applications have closed.

- **Footer date.** The footer reads "Last Updated: 16-09-26" in `DD-MM-YY` form.
  Worth updating when the content next changes meaningfully.

---

## Credits

Design by [Royce Malonzo](https://www.linkedin.com/in/royce-malonzo-050634263).

## Events

The events listing is at `/events/`, with a dedicated China Trip page at
`/events/china-trip-2027/`. Both are plain static HTML using existing ESRA
branding. See [the events guide](docs/events.md) for adding events, provisional
trip details, and the optional `events.esrarobotics.eu` export/deployment setup.

Event submissions now use public GitHub issues and maintainer-reviewed updates.
Review notifications use GitHub's own email settings. Subscriptions use static
RSS/calendar feeds; no custom backend, SMTP credentials or email-address database
is needed. See the events guide for the review workflow and setup limits.
