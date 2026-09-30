# Content guide

Where each piece of the site lives, and how to change it safely.

Read [Before you change anything](../README.md#before-you-change-anything) in
the README first. The short version: every string exists twice, in the HTML and
in a JavaScript bundle, and editing only the HTML does nothing.

---

## The two copies, and why it is worse than it sounds

The page has five breakpoints, listed under
[Five breakpoints, five layouts](#five-breakpoints-five-layouts) below.

The HTML holds **one** rendered copy of a given string. The JavaScript bundle
holds **one copy per breakpoint that uses it**, so the same sentence can appear
five times in the bundle. The heading "ADVANCING EUROPEAN ROBOTICS" appears once
in `index.html` and three times in the home bundle.

So a hand-edit that fixes the first match it finds will leave the other
breakpoints showing the old text, and the bug only appears at certain window
widths. That is miserable to debug.

`scripts/edit-text.py` replaces every occurrence in both files, which is why it
exists:

```bash
python3 scripts/edit-text.py "OLD TEXT" "NEW TEXT" --dry-run   # see what it would do
python3 scripts/edit-text.py "OLD TEXT" "NEW TEXT"
python3 scripts/check.py
```

---

## Which file holds what

| What you want to change | HTML | JavaScript |
| --- | --- | --- |
| Home page copy and images | `index.html` | `assets/js/9-chtcMvQhu5kDnB1BISvwi7xgdTHebBmWouW-ydXQg.BhJ5RAlY.mjs` |
| Imprint and privacy notice | generated, see below | generated, see below |
| 404 page | `404.html` | none, edit the HTML directly |
| Page title, description, favicon, social preview | `<meta>` tags in each page head | `assets/js/shared-lib.BxkTlGRE.mjs` |
| Canonical URL and routing | `<link rel="canonical">` in each page | `assets/js/script_main.Cg7ZvyF6.mjs` |

The bundle filenames are Framer content hashes. If the site is ever re-exported
they change, and the tables in `scripts/check.py`, `scripts/edit-text.py` and
this file all have to be updated.

---

## The legal page is generated

`/imprint/` holds two documents: the imprint required by § 5 of the German
Digital Services Act, and the privacy notice required by Articles 13 and 14
GDPR. The privacy part starts at the `#privacy` anchor, which the footer's
PRIVACY link jumps to.

Its body is **generated**. The text lives in
[../scripts/legal_content.py](../scripts/legal_content.py) as a list of blocks:

```python
("h2", "Heading Contact", "Contact"),
("p",  "Contact Details", "Email: info@esrarobotics.eu"),
```

`h2` is a section heading, `h3` a numbered subsection and `p` body text.
Newlines inside the text become line breaks, because the container is styled
`white-space: pre-wrap`. To change any of it:

```bash
# edit scripts/legal_content.py, then
python3 scripts/build-legal.py
python3 scripts/check.py
```

The script rewrites both the HTML and the bundle, so the two cannot drift, and
re-running it is safe. Do not edit the rendered page by hand: the next run of
the script will discard your change.

Everything outside the generated block, meaning the page header, the "Imprint"
title and the footer, is ordinary Framer markup and follows the usual two-copy
rule.

---

## Five breakpoints, five layouts

| Breakpoint | Applies at |
| --- | --- |
| `8n5ift` | 1500px and wider |
| `1debav8` | 1200px to 1499px |
| `aykcs0` | 810px to 1199px |
| `1om0o44` | 634px to 809px |
| `k9cdc1` | up to 633px |

These are not one layout that reflows. They are five layouts, and a section can
exist in one and not in another. Two mechanisms decide that, and you have to
check both:

- a `hidden-<breakpoint>` class in the HTML, for example
  `class="framer-fokffn hidden-k9cdc1"`, and
- a gate in the bundle, for example `Y()&&s(\`div\`, ...)`, where `Y` is
  defined near the top of the bundle as something like
  `()=>!N()||T!==\`w_xMJuVPg\``.

The sections are also flex siblings whose visual order comes from a CSS `order`
value, not from their position in the document. So the markup can be in perfect
order and the page can still render scrambled.

Four separate faults came from this, all now fixed:

| Fault | Where | Cause |
| --- | --- | --- |
| The application section was missing, including the only APPLY NOW button | below 634px | a `hidden-k9cdc1` class **and** a `Y()` gate |
| Partner content rendered under the APPLICATION heading, university logos fell past the contact section | below 634px | wrong flex `order` values |
| The footer links all vanished, so the imprint and privacy notice were unreachable | below 634px | a `hidden-k9cdc1` class **and** a `Y()` gate on `framer-zomv1h` |
| The JOIN ESRA heading and intake date sat completely hidden behind the dark panel | 634px to 809px | heading fixed at 1044px wide, panel `position: absolute` over it |

There was also a content slip in the same section: the panel asked "Who are we
looking for?" and answered with the CONNECT pillar's text between 634px and
1199px, because the breakpoint overrides in the bundle carried the wrong
string while the default was right.

The layout fixes live in the `esra-mobile-fixes` stylesheet in the head of
`index.html`, which is commented and has two blocks: one for phones only, and
one for everything up to 809px. The gates were removed from the bundle and the
markup.

Run `node scripts/check-breakpoints.mjs` after any layout change. When you add
or move a section, add it to `HOME_ORDER` in that script.

---

## Do not remove the `<base href="/">` on the imprint page

`imprint/index.html` has `<base href="/">` near the top of its `<head>`, with a
comment explaining why. It is load-bearing.

The Framer router builds internal links relative to the current directory, so
the navigation renders as `./#mission` and `./imprint` no matter which page you
are on. From the home page at `/` that is correct. From the imprint page at
`/imprint/` it would resolve to `/imprint/#mission`, and every navigation link
would go nowhere.

The router regenerates those links during hydration, so editing the `href`
values in the HTML does not fix it. The `<base>` element does, and it needs no
changes to the minified bundle.

Any new page placed in a subdirectory needs the same line.

---

## Sections of the home page

In document order, with the anchor used by the navigation:

| Number | Anchor | Section |
| --- | --- | --- |
| 0.1/ | `#home` | Hero: the ESRA wordmark, the dotted Europe map, "ENABLING EUROPEAN STUDENT ROBOTICS", and the three statistics |
| 0.2/ | `#whatwedo` | "ADVANCING EUROPEAN ROBOTICS" and the member club logo strip |
| 0.3/ | `#mission` | The three pillars: Connect, Enable, Promote |
| 0.4/ | `#network` | "OUR GROWING MEMBER NETWORK", the logo grid and the university logos |
| 0.5/ | `#partners` | "STRONG PARTNERS" and the partner logos |
| 0.6/ | `#partners-1` | "JOIN ESRA", the intake date and the APPLY NOW panel |
| 0.7/ | — | "GET IN CONTACT" and the footer |

The numbers used to run 0.1, 0.2, 0.3, 0.4, 0.4, 0.5, 0.6, with partners
repeating the member network's 0.4 and everything after it one short. They were
renumbered to the sequence above. `scripts/check-breakpoints.mjs` now fails if
they ever repeat or go backwards again.

Anchors ending in `-1` and `-2`, such as `#whatwedo-1` or `#network-2`, are the
same section re-emitted for a different breakpoint. They are not separate
content.

The three statistics in the hero, currently 13 universities, 8 countries and
2,500+ students, are plain text. Change them with `edit-text.py` like any other
copy, and remember they are claims the association is making publicly.

---

## The application form

The "APPLY NOW" buttons and the application section link to an external Tally
form at `https://tally.so/r/5BAxlN`. The form itself is not in this repository
and is edited on tally.so. The link appears five times in `index.html`.

---

## Member club and university logos

Each logo is an `<img>` wrapped in a link to that organisation. The filenames
are content hashes and carry no meaning, so here is the map:

| Image | Links to |
| --- | --- |
| `24XbMZtBnJsehUafYBCk9VHWg.svg` | ethrobotics.ch |
| `6BnrmbQTUy5vnEljxSRzK8WUWA.svg` | cybair.put.poznan.pl |
| `BArNBUtF7jyKQugQxQst5LBPY.png` | psl.eu |
| `C7aSBcLeWMPtW2ChSiBDffcs4KA.png` | robotum.info |
| `DrrhYssFAdHKNTVZ2GzKJU4ZUvs.svg` | rsadelft.nl |
| `HrY0Rd024TQaYBHtgumE8TTETM.webp` | aeapolimi.it |
| `Mbysiry5NUq1D2wPCjUX8XqGE.png` | rwth-aachen.de |
| `N5VcDLzPA5S6aUp6vbVwKa9Cs.png` | kthais.com |
| `PLfFk3pH8dRbtz0MF401kHC0io.png` | tudelft.nl |
| `QAGaOdNf0Qh5mc7eBcVWGOLxjNU.png` | tue.nl |
| `RKWvN4glrqxD4vtnfZl6J8Bec.png` | epflaiteam.ch |
| `Sd5iG8xnvsiMnmG8Pt1aOvyfvcA.svg` | put.poznan.pl |
| `Txkkf2vVMfDsBdSIJmhzCx8x6o.svg` | tum.de |
| `X6r9SEF1SAFhuRD3sU2JxllyN9o.png` | epfl.ch |
| `ZrjFz4SDLI0WGD3lSxVzGrWlKpI.png` | universite-paris-saclay.fr |
| `aiJQGq0VueAOIV9b1fAIxzGAz54.png` | tuwien.at |
| `ed6vwa3G2YhJgE9RbrrbXtxuU.png` | embark.law |
| `f8IrJ0geUXg3ZdvOArk5kHBZK4E.png` | tuwrc.at |
| `fjWsQDYhAzWgwoD0jNMPzT1ec0.png` | unaite.fr |
| `lAP2RNMmaseucxT6irw5C6W38M.png` | ethz.ch |
| `rMR2rqzjM6x2Mc5ZKqDBIZM6Sw.png` | roboticscollective.org |
| `sH8dvx8LXj7vYqzNC3FHSRqY.png` | teampolar.org |
| `vevCTNW8fK9EZfGUBFxMtEriVQ.png` | ip-paris.fr |

`sB4uRcxfpt5K2ulBtDdwfwjLNY4.png` is the ESRA mark used in the navigation and
in each section header, so it appears many times. The favicons and the social
preview image are `mvNehTD46OVNZp0IWWv0jzUprWM.png` (light),
`bqBTNplWTl4pu9ntGxEZoztqpY.png` (dark), `GwSGShFpPZ7jSxQvuWMsMtGgKI.png`
(Apple touch icon) and `gJD0i2kuQtMhopbDOO9rz0W288I.png` (Open Graph and X).

### Adding or replacing a logo

1. Put the file in `assets/images/`. Keep the aspect ratio close to the one it
   replaces: the `width` and `height` attributes are baked into the markup and
   drive the layout.
2. Change the `src` in `index.html` **and** in the home bundle.
3. Change the surrounding `href` in both places if the link changes too.
4. Run `python3 scripts/check.py`. It reports broken paths, and warns about the
   old image if nothing references it any more, in which case delete it.
5. Look at the logo grid at several window widths.

Adding a brand new logo means duplicating a block of markup in both files. It is
fiddly and there is no shortcut. Copy a neighbouring entry and adjust it.

---

## Fonts

Inter and Intel One Mono are self-hosted in `assets/fonts/` as WOFF2, declared
by `@font-face` rules in each page's inline stylesheet and referenced again in
the bundles. The site loads no fonts from Google or anywhere else, and it should
stay that way.

The files are content-hashed and split by character range, so several files back
one family. `scripts/check.py` warns about any that nothing references.

---

## Images and responsive loading

The original export used Framer's image CDN, which generated resized copies on
demand via `?scale-down-to=` URLs. Those URLs are gone along with the rest of
the Framer dependency, and each `<img>` now loads a single local file.

Every image is committed at its original size. All 33 come to roughly 570 KB
together, so this is not a performance problem, but if a large photo is ever
added it is worth resizing it before committing rather than reaching for a CDN.
