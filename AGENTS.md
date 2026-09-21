# Instructions for coding agents

This file tells an AI coding agent how to work on the ESRA website without
breaking it. Humans should read [README.md](README.md) first; everything here
applies to them too.

If you follow one thing from this file, make it the golden rule below.

---

## What this repository is

A **static export of a Framer site**, served directly by GitHub Pages. There is
no build step, no package manager, no framework to run. The HTML you see is what
the browser gets.

The original site was designed in Framer and hosted at `studentrobotics.eu`. It
now lives here, is hand-maintained, and serves `esrarobotics.eu`. Framer is no
longer involved, and the site must never depend on Framer's servers again.

Two consequences shape everything:

- The HTML is **machine-generated and minified**. Class names look like
  `framer-1jqxlnd`. They are meaningless but load-bearing. Do not tidy them.
- The page is **React, server-rendered once and then hydrated** in the browser
  from a JavaScript bundle in `assets/js/`.

---

## The golden rule: every string exists twice

Each visible string is stored in two places:

1. the pre-rendered HTML, which is what the visitor sees first, and
2. the JavaScript bundle, which React hydrates from a moment later.

**If you change only the HTML, your edit is silently reverted.** The new text
flashes up, React re-renders from the bundle, and the old text returns. This has
been verified in a real browser. It is the single most common way to "fix"
something on this site and ship nothing.

So do not hand-edit copy. Use the helper, which changes both copies together:

```bash
python3 scripts/edit-text.py "OLD TEXT" "NEW TEXT"
python3 scripts/edit-text.py "OLD" "NEW" --page imprint
python3 scripts/edit-text.py "OLD" "NEW" --dry-run
```

`scripts/check.py` fails the build if the HTML and the bundle ever disagree, so
a mistake here is caught rather than shipped.

Which bundle belongs to which page:

| Page | HTML | Bundle React hydrates from |
| --- | --- | --- |
| Home | `index.html` | `assets/js/9-chtcMvQhu5kDnB1BISvwi7xgdTHebBmWouW-ydXQg.BhJ5RAlY.mjs` |
| Imprint and privacy | `imprint/index.html` | `assets/js/ykq53qphXfPOpsTVHhVWmh9-l4o0c-6IrAcQwkHfunw.HT6UvCHq.mjs` |
| 404 | `404.html` | none, it is hand-written plain HTML |

The legal page is the exception to editing copy with `edit-text.py`: its body is
generated, see the rule about the legal page below.

Site-wide metadata such as the page title, description, favicon and social
image lives in `assets/js/shared-lib.BxkTlGRE.mjs`. Routing and the canonical
URL live in `assets/js/script_main.Cg7ZvyF6.mjs`.

---

## Always verify before you finish

```bash
python3 scripts/check.py          # reads the files
node scripts/check-breakpoints.mjs  # renders the pages in a real browser
```

Run **both**. They catch different things and neither is optional.

`check.py` is fast and has no dependencies. It fails when the site would break:
a missing file, a reference to an asset that is not there, a bundle that no
longer parses, a request to a third-party host, or HTML and bundle text that
disagree. It warns about things a human still has to decide.

`check-breakpoints.mjs` loads every page at six widths and checks that the page
does not scroll sideways, that the sections appear in the same reading order at
every width, that the section numbers ascend without duplicates, and that
content which must never disappear is still there. It needs Google Chrome and
skips itself politely if there is none.

**Neither check replaces looking at the page.** For anything visual:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

Wait for the page to finish loading before judging it. Hydration is exactly
where text edits come undone, and it happens after first paint.

Do not open `index.html` as a `file://` URL. Asset paths are root-absolute
(`/assets/...`) and will not resolve.

---

## Rules

**Check every change at every width, not just the one on your screen.** This is
the rule that this repository learned the hard way, so take it literally.

The page has five breakpoints. Each one is a separate layout, and a section can
be present in one and completely absent from another. Four faults shipped here
because nobody looked at a narrow window:

- The entire application section, including the only APPLY NOW button, was
  excluded below 634px. Phones saw an APPLICATION heading with nothing under it
  and no way to apply. It looked perfect on a laptop.
- Every footer link was excluded below 634px too, so on a phone there was no
  navigation at all and no way to reach the imprint or the privacy notice.
- The sections are flex siblings ordered by a CSS `order` value, and below
  634px those values were wrong, so the partner block rendered underneath the
  application heading and the university logos fell past the contact section.
- Between 634px and 809px the JOIN ESRA heading was fixed at 1044px wide and
  the dark panel was absolutely positioned on top of it, so the heading and the
  intake date were completely covered. Present in the DOM, invisible on screen.

None of these were visible in the markup. The DOM order was correct all along,
and in three of the four cases the content was present and would have answered
a DOM query happily. Reading the HTML would not have found any of them. Only
rendering does.

So, before you call any change done:

```bash
node scripts/check-breakpoints.mjs
```

and for anything you changed visually, look at it yourself at a phone width as
well as a wide one. When you add or move content, add it to the lists at the top
of that script, `HOME_ORDER`, `HOME_REQUIRED`, `FOOTER_LINKS` or
`MUST_NOT_BE_COVERED`, so the next person cannot lose it.

Traps worth knowing:

- A `hidden-<breakpoint>` class in the markup, or a gate like `Y()&&` in the
  bundle, means that element does not exist at that breakpoint. Search for both
  before assuming content is everywhere.
- Fixed pixel widths and `position: absolute` are everywhere in this export.
  They are fine at the width they were designed for, and at any other width
  they overflow or cover what is underneath. The hand-written rules live in the
  `esra-mobile-fixes` stylesheet in `index.html`, which is commented and is the
  right place to add more.
- Content being "present" is not the same as being visible. Three of the four
  faults above left the markup intact and the text reachable from a DOM query.
  The breakpoint check therefore hit-tests key headings with
  `elementFromPoint` rather than trusting that they exist.
- If you write your own browser probe, give Chrome a **fresh** profile
  directory. A reused one serves the previous build from its disk cache and
  will tell you your fix did not work when it did. That wasted real time here.

**Never re-introduce a third-party dependency.** No `framerusercontent.com`,
no `events.framer.com`, no Google Fonts, no CDN script tags. Every font, image
and script is committed to this repository, and that is the point: the site
must keep working if Framer deletes the original project. `scripts/check.py`
enforces this.

**Never reformat, prettify or re-indent the generated HTML or the `.mjs`
bundles.** They are minified build output. A formatter will produce an enormous
diff that no one can review, and can break the bundles. Make the smallest edit
that does the job.

**Never add a build step, a package manager, a framework or a dependency**
unless a human explicitly asks for one. There is no `package.json` and that is
deliberate. Anyone with a text editor can fix a typo here.

**Do not re-export from Framer** over the top of this repository. It would undo
the localisation and re-add the tracking script. If the design genuinely has to
change in Framer, that is a human decision and a fresh migration.

**Do not remove the `<base href="/">` from `imprint/index.html`.** The Framer
router builds internal links relative to the current directory, so on a page in
a subdirectory they would all point into that subdirectory. It is regenerated
during hydration, so editing the `href` values does not help. Any new page in a
subdirectory needs the same line. See
[docs/content-guide.md](docs/content-guide.md).

**Keep hashed filenames as they are.** Names like
`sB4uRcxfpt5K2ulBtDdwfwjLNY4.png` are referenced from the HTML and from inside
the bundles. Renaming one means finding every reference. If you must, run
`scripts/check.py` afterwards, which will tell you what you missed.

**Never hand-edit the legal page.** `/imprint/` carries the imprint required by
§ 5 DDG and the privacy notice required by Articles 13 and 14 GDPR. Its text
lives in `scripts/legal_content.py`; run `python3 scripts/build-legal.py` to
render it into the HTML and the bundle. Editing the page directly will be
overwritten the next time anyone runs that script.

Two things on that page are deliberate and must not be "fixed": there is no
link to the EU online dispute resolution platform, because it shut down on
20 July 2025 and a dead link invites a warning letter, and there is no cookie
banner, because the site sets no cookies and stores nothing in the browser. If
you ever add analytics or embed a form, both of those facts change and the
privacy notice is no longer accurate.

**Ask before changing published facts.** Legal details in the imprint, the
contact address, the application deadline and the membership numbers are the
association's to decide, not yours. See the open items in the README. Fix the
mechanism; leave the facts to a human.

---

## Layout

```
index.html              Home page: hero, pillars, network, partners, application
                        (its <head> also holds the esra-mobile-fixes stylesheet)
imprint/index.html      Imprint and privacy notice, served at /imprint/
404.html                Not-found page, hand-written, no bundle
CNAME                   Custom domain for GitHub Pages (esrarobotics.eu)
assets/
  images/               PNG, SVG and WebP, referenced by hashed filename
  fonts/                Inter and Intel One Mono, self-hosted WOFF2
  js/                   Framer runtime and page bundles, minified
scripts/
  check.py              Integrity check. Run it before every commit.
  check-breakpoints.mjs Renders every page at six widths and checks the layout.
  edit-text.py          Change copy in the HTML and the bundle together.
  legal_content.py      Text of the imprint and privacy notice.
  build-legal.py        Renders that text onto the legal page.
docs/
  content-guide.md      Where each piece of text and every image lives
.github/workflows/      CI that runs scripts/check.py on every push
```

---

## Deployment

GitHub Pages serves the `main` branch from the repository root. **A push to
`main` is a publish to the live site**, usually within a minute. There is no
staging environment.

Work on a branch and open a pull request. CI runs `scripts/check.py`.

---

## Common tasks

**Change some wording.** `python3 scripts/edit-text.py "old" "new"`, then
`python3 scripts/check.py`, then `node scripts/check-breakpoints.mjs`, then look
at the page in a browser at a narrow width and a wide one.

**Replace an image.** Put the new file in `assets/images/`. Point the reference
at it in both the page HTML and the page's bundle. Keep the pixel dimensions
close to the original, since the `width` and `height` attributes are baked into
the markup and control layout. Run the check, which will catch a broken path or
a now-unreferenced old file.

**Add a member club or partner logo.** These are repeating blocks in
`index.html` with matching structure in the home bundle. Copy an existing block
in both files and adjust the image and link. This is fiddly; budget time for it.

**Fix a link.** Links are plain `href` attributes in the HTML and `href:` values
in the bundle. Change both.

**Change the page title or social preview image.**
`assets/js/shared-lib.BxkTlGRE.mjs` plus the `<meta>` tags in the page head.

---

## When something is genuinely too hard

The Framer markup makes real layout changes expensive: hashed class names, five
responsive breakpoints, and duplicated structure between HTML and bundle. If a
request amounts to a redesign, say so plainly and explain the cost rather than
producing a half-working layout. Rebuilding a section as clean hand-written HTML
is sometimes the cheaper answer, and that is a conversation to have with a human
first.
