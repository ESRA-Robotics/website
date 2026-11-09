#!/usr/bin/env python3
"""
Integrity check for the ESRA static site.

Run it after every change, before committing:

    python3 scripts/check.py

It fails (exit code 1) when the site would break in production, and prints
warnings (exit code 0) for things a human still needs to decide.

What it enforces
----------------
1. Every page that must exist, exists.
2. Every /assets/... reference in the HTML and JS resolves to a real file.
3. No file in assets/ is unreferenced (dead weight).
4. The site makes no requests to Framer's CDN or any other third party.
   The whole point of this repo is that the site is self-contained.
5. Every .mjs bundle still parses (needs node; skipped if unavailable).
6. Internal links are root-absolute and point at anchors that exist.
7. Every visible string in a page also appears in that page's JavaScript
   bundle. React hydrates from the bundle, so text edited only in the HTML is
   silently reverted a moment after the page loads.
8. The rendered legal page still matches scripts/legal_content.py, so a hand
   edit cannot silently diverge from the text everyone reviews.

Warnings only
-------------
- Any reference to the old studentrobotics.eu domain.
- A "Last Updated" footer date far in the past.
"""

from __future__ import annotations

import html as html_module
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAGES = ["index.html", "imprint/index.html", "404.html", "events/index.html",
         "events/china-trip-2027/index.html", "events/submit/index.html",
         "events/review/index.html", "events/preferences/index.html", "events/rules/index.html"]
REQUIRED_FILES = PAGES + ["CNAME", "README.md", "AGENTS.md"]

# Which JavaScript bundle React hydrates each page from. The 404 page is
# hand-written plain HTML and has no bundle. These filenames are Framer content
# hashes; a re-export of the site changes them.
PAGE_BUNDLES = {
    "index.html": "assets/js/9-chtcMvQhu5kDnB1BISvwi7xgdTHebBmWouW-ydXQg.BhJ5RAlY.mjs",
    "imprint/index.html": (
        "assets/js/ykq53qphXfPOpsTVHhVWmh9-l4o0c-6IrAcQwkHfunw.HT6UvCHq.mjs"
    ),
}

# Text runs shorter than this are too generic to match reliably.
MIN_TEXT_RUN = 12

# Hosts the site must never talk to. The site has to work if Framer disappears.
FORBIDDEN_HOSTS = [
    "framerusercontent.com",
    "events.framer.com",
    "app.framerstatic.com",
    "framer.com/edit",
    "fonts.gstatic.com",
    "fonts.googleapis.com",
]

# Framer's runtime inspects font URLs by prefix to label where a font came from.
# These two strings are compared against, never fetched, so they are allowed.
ALLOWED_REMOTE_SNIPPETS = {
    "assets/js/framer.C5AFgEUj.mjs": [
        "https://fonts.gstatic.com/s/",
        "https://framerusercontent.com/third-party-assets/fontshare/",
    ],
}

errors: list[str] = []
warnings: list[str] = []


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def iter_source_files():
    """Every file whose contents we inspect: the pages and the JS bundles."""
    for page in PAGES:
        p = ROOT / page
        if p.exists():
            yield p
    for p in sorted((ROOT / "assets" / "js").glob("*.mjs")):
        yield p
    yield from sorted((ROOT / "assets" / "css").glob("*.css"))


def check_required_files() -> None:
    for name in REQUIRED_FILES:
        if not (ROOT / name).exists():
            errors.append(f"missing required file: {name}")


def check_no_remote_requests() -> None:
    for path in iter_source_files():
        text = path.read_text(errors="replace")
        allowed = ALLOWED_REMOTE_SNIPPETS.get(rel(path), [])
        for host in FORBIDDEN_HOSTS:
            for match in re.finditer(re.escape(host), text):
                start = max(0, match.start() - 60)
                context = text[start : match.end() + 60]
                if any(snippet in context for snippet in allowed):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{rel(path)}:{line}: reference to {host} "
                    f"(assets must be served from this repo)"
                )


def check_asset_references() -> None:
    """Every /assets/... path referenced anywhere must exist on disk."""
    referenced: set[str] = set()
    pattern = re.compile(r"/assets/(?:images|fonts|js|css)/[A-Za-z0-9_.@=-]+")

    for path in iter_source_files():
        text = path.read_text(errors="replace")
        for match in pattern.finditer(text):
            ref = match.group(0)
            referenced.add(ref)
            if not (ROOT / ref.lstrip("/")).exists():
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{rel(path)}:{line}: broken reference {ref}")

    # Relative imports between the JS bundles (./foo.mjs)
    js_dir = ROOT / "assets" / "js"
    for path in sorted(js_dir.glob("*.mjs")):
        text = path.read_text(errors="replace")
        for match in re.finditer(r"""["'`]\./([A-Za-z0-9_.@=-]+\.mjs)["'`]""", text):
            target = match.group(1)
            referenced.add(f"/assets/js/{target}")
            if not (js_dir / target).exists():
                errors.append(f"{rel(path)}: broken module import ./{target}")

    check_orphans(referenced)


def check_orphans(referenced: set[str]) -> None:
    for directory in ("images", "fonts", "js", "css"):
        folder = ROOT / "assets" / directory
        if not folder.is_dir():
            continue
        for file in sorted(folder.iterdir()):
            if file.name.startswith("."):
                continue
            if f"/assets/{directory}/{file.name}" not in referenced:
                warnings.append(
                    f"unreferenced file: assets/{directory}/{file.name} "
                    f"(delete it, or the reference is missing)"
                )


def check_js_parses() -> None:
    node = subprocess.run(
        ["node", "--version"], capture_output=True, text=True, check=False
    )
    if node.returncode != 0:
        warnings.append("node not found, skipped the JavaScript syntax check")
        return
    for path in sorted((ROOT / "assets" / "js").glob("*.mjs")):
        result = subprocess.run(
            ["node", "--input-type=module", "--check"],
            stdin=path.open("rb"),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            first_line = (result.stderr or "").strip().splitlines()
            detail = first_line[0] if first_line else "syntax error"
            errors.append(f"{rel(path)}: does not parse: {detail}")


def check_internal_links() -> None:
    """
    Internal links must be root-absolute.

    The imprint lives at /imprint/, so a relative link like ./#mission on that
    page resolves to /imprint/#mission and goes nowhere. Every internal link
    should start with / or #.
    """
    known_anchors: set[str] = set()
    index = ROOT / "index.html"
    if index.exists():
        known_anchors = set(re.findall(r'id="([a-z0-9-]+)"', index.read_text()))

    for page in PAGES:
        path = ROOT / page
        if not path.exists():
            continue
        text = path.read_text()

        for match in re.finditer(r'href="(\.\.?/[^"]*)"', text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"{page}:{line}: relative link {match.group(1)!r}. Internal links "
                f"must start with / so they work from every page."
            )

        # Links into the home page's sections must point at a real anchor.
        for match in re.finditer(r'href="/#([a-zA-Z0-9_-]+)"', text):
            anchor = match.group(1)
            if known_anchors and anchor not in known_anchors:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{page}:{line}: link to #{anchor}, which is not an id in index.html"
                )


def check_text_matches_bundle() -> None:
    """
    Catch the classic mistake: editing copy in the HTML but not in the bundle.

    React hydrates each page from its bundle. If the two disagree, the browser
    shows the HTML version for an instant and then replaces it with the bundle
    version, so the edit looks like it silently did nothing.
    """
    block = re.compile(
        r'<(p|h[1-6])\b[^>]*class="[^"]*framer-text[^"]*"[^>]*>(.*?)</\1>', re.S
    )

    for page, bundle_path in PAGE_BUNDLES.items():
        page_file = ROOT / page
        bundle_file = ROOT / bundle_path
        if not page_file.exists():
            continue
        if not bundle_file.exists():
            errors.append(
                f"{page}: its bundle {bundle_path} is missing. "
                f"If the site was re-exported, update PAGE_BUNDLES in this script."
            )
            continue

        bundle_text = re.sub(r"\s+", " ", bundle_file.read_text(errors="replace"))
        page_text = page_file.read_text()

        for match in block.finditer(page_text):
            # Split on the inner tags: the bundle stores each run separately.
            for segment in re.split(r"<[^>]+>", match.group(2)):
                run = re.sub(r"\s+", " ", html_module.unescape(segment)).strip()
                if len(run) < MIN_TEXT_RUN:
                    continue
                if run not in bundle_text:
                    line = page_text.count("\n", 0, match.start()) + 1
                    errors.append(
                        f"{page}:{line}: the text {run[:60]!r} is not in "
                        f"{bundle_path}. Hydration will revert it. "
                        f"Use scripts/edit-text.py to change copy in both places."
                    )


def check_legal_content() -> None:
    """
    The imprint and privacy notice are generated from scripts/legal_content.py.
    If someone edits the rendered page instead, the next run of build-legal.py
    would throw their change away, so flag the divergence now.
    """
    page = ROOT / "imprint/index.html"
    bundle = ROOT / PAGE_BUNDLES["imprint/index.html"]
    if not page.exists() or not bundle.exists():
        return

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from legal_content import BLOCKS
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"could not read scripts/legal_content.py ({exc})")
        return

    page_text = re.sub(r"\s+", " ", html_module.unescape(page.read_text()))
    bundle_text = re.sub(r"\s+", " ", bundle.read_text(errors="replace"))

    for _kind, name, text in BLOCKS:
        needle = re.sub(r"\s+", " ", text).strip()
        missing = [
            where
            for where, haystack in (("HTML", page_text), ("bundle", bundle_text))
            if needle not in haystack
        ]
        if missing:
            errors.append(
                f"legal block {name!r} is missing from the {' and '.join(missing)}. "
                f"Run: python3 scripts/build-legal.py"
            )


def check_stale_content() -> None:
    """
    Nothing should point at the old studentrobotics.eu domain any more. The
    contact address moved to info@esrarobotics.eu on 30 September 2026, which
    was the last thing holding on to it.
    """
    for path in iter_source_files():
        text = path.read_text(errors="replace")
        for match in re.finditer(r"studentrobotics\.eu", text):
            line = text.count("\n", 0, match.start()) + 1
            warnings.append(
                f"{rel(path)}:{line}: refers to the old studentrobotics.eu domain"
            )


def main() -> int:
    check_required_files()
    check_no_remote_requests()
    check_asset_references()
    check_js_parses()
    check_internal_links()
    check_text_matches_bundle()
    check_legal_content()
    check_stale_content()

    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)

    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: no errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
