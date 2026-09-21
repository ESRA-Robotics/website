#!/usr/bin/env python3
"""
Change a piece of copy on the ESRA site, in every place it lives.

Why this script exists
----------------------
The site is a Framer export. Every visible string is stored twice: once in the
pre-rendered HTML, and once inside the JavaScript bundle that React hydrates
from. If you edit only the HTML, the change is visible for a fraction of a
second and then hydration silently puts the old text back. This has been
confirmed in a browser, it is not a theoretical concern.

This script edits both copies at once, so the change actually sticks.

Usage
-----
    python3 scripts/edit-text.py "OLD TEXT" "NEW TEXT"
    python3 scripts/edit-text.py "OLD" "NEW" --page imprint
    python3 scripts/edit-text.py "OLD" "NEW" --dry-run

Afterwards, always run:

    python3 scripts/check.py

and look at the page in a browser (see README) to confirm the text stays put
after the page finishes loading.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each page's copy lives in its HTML file and in one JavaScript bundle.
# The bundle filenames are content hashes produced by Framer; if the site is
# ever re-exported they change, and this table has to be updated.
PAGES: dict[str, dict[str, str]] = {
    "index": {
        "html": "index.html",
        "bundle": "assets/js/9-chtcMvQhu5kDnB1BISvwi7xgdTHebBmWouW-ydXQg.BhJ5RAlY.mjs",
    },
    "imprint": {
        "html": "imprint/index.html",
        "bundle": "assets/js/ykq53qphXfPOpsTVHhVWmh9-l4o0c-6IrAcQwkHfunw.HT6UvCHq.mjs",
    },
    # The 404 page is hand-written plain HTML with no bundle behind it.
    "404": {
        "html": "404.html",
        "bundle": "",
    },
}


def variants(text: str) -> list[str]:
    """The forms a string can take in the HTML: literal and HTML-escaped."""
    escaped = html.escape(text, quote=False)
    return [text] if escaped == text else [text, escaped]


def replace_in_file(path: Path, old: str, new: str, dry_run: bool) -> int:
    if not path.exists():
        print(f"  {path}: does not exist, skipped")
        return 0

    original = path.read_text()
    updated = original
    total = 0

    for old_form, new_form in zip(variants(old), variants(new)):
        count = updated.count(old_form)
        if count:
            updated = updated.replace(old_form, new_form)
            total += count

    if total and not dry_run:
        path.write_text(updated)

    verb = "would replace" if dry_run else "replaced"
    print(f"  {path.relative_to(ROOT)}: {verb} {total}")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace a string in the HTML and the JavaScript bundle together."
    )
    parser.add_argument("old", help="the exact text to find")
    parser.add_argument("new", help="the text to put in its place")
    parser.add_argument(
        "--page",
        default="all",
        choices=[*PAGES.keys(), "all"],
        help="which page to edit (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing anything",
    )
    args = parser.parse_args()

    # A backtick or ${ in the replacement would break the JavaScript template
    # literals the bundle stores its text in.
    for forbidden in ("`", "${", "\\"):
        if forbidden in args.new:
            print(
                f"error: the replacement text contains {forbidden!r}, which would "
                f"corrupt the JavaScript bundle. Edit the files by hand instead.",
                file=sys.stderr,
            )
            return 1

    targets = list(PAGES) if args.page == "all" else [args.page]
    html_hits = 0
    bundle_hits = 0

    for name in targets:
        entry = PAGES[name]
        print(f"{name}:")
        html_hits += replace_in_file(
            ROOT / entry["html"], args.old, args.new, args.dry_run
        )
        if entry["bundle"]:
            bundle_hits += replace_in_file(
                ROOT / entry["bundle"], args.old, args.new, args.dry_run
            )

    print()
    if html_hits == 0 and bundle_hits == 0:
        print(f"Nothing matched {args.old!r}. Check the exact spelling and casing.")
        return 1

    if bundle_hits == 0 and any(PAGES[n]["bundle"] for n in targets):
        print(
            "WARNING: the text was found in the HTML but not in any bundle.\n"
            "         Hydration may put the old text back. Check the page in a\n"
            "         browser before committing."
        )
    elif html_hits == 0:
        print(
            "WARNING: the text was found in a bundle but not in the HTML.\n"
            "         The old text will be visible until the page finishes loading."
        )
    else:
        print(f"Done: {html_hits} in HTML, {bundle_hits} in bundles.")

    print("\nNow run: python3 scripts/check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
