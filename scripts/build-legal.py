#!/usr/bin/env python3
"""
Render the imprint and privacy notice into the site.

The text lives in one place, scripts/legal_content.py. This script writes it
into both copies the site needs: the pre-rendered HTML at imprint/index.html,
and the JavaScript bundle React hydrates that page from. Editing only one of
them would mean the text silently reverts a moment after the page loads.

    python3 scripts/build-legal.py
    python3 scripts/check.py

Re-running it is safe: it replaces the generated block rather than appending.
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_content import BLOCKS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "imprint/index.html"
BUNDLE = ROOT / "assets/js/ykq53qphXfPOpsTVHhVWmh9-l4o0c-6IrAcQwkHfunw.HT6UvCHq.mjs"

MONO = '"Intel One Mono", "Intel One Mono Placeholder", monospace'
SEL_REG = "R0Y7SW50ZWwgT25lIE1vbm8tcmVndWxhcg=="   # GF;Intel One Mono-regular
SEL_500 = "R0Y7SW50ZWwgT25lIE1vbm8tNTAw"           # GF;Intel One Mono-500

# padding-top rather than margin-top: padding never collapses out of the
# flex item, so section spacing is predictable.
STYLES = {
    "p":  [("--font-selector", SEL_REG), ("--framer-font-family", MONO),
           ("--framer-line-height", "1.8em"), ("--framer-text-color", "#000000")],
    "h2": [("--font-selector", SEL_500), ("--framer-font-family", MONO),
           ("--framer-font-size", "24px"), ("--framer-font-weight", "500"),
           ("--framer-letter-spacing", "-0.03em"), ("--framer-line-height", "1.3em"),
           ("--framer-text-color", "#000000"), ("padding-top", "34px")],
    "h3": [("--font-selector", SEL_500), ("--framer-font-family", MONO),
           ("--framer-font-size", "17px"), ("--framer-font-weight", "500"),
           ("--framer-letter-spacing", "-0.02em"), ("--framer-line-height", "1.4em"),
           ("--framer-text-color", "#000000"), ("padding-top", "20px")],
}
FONTS = {"p": "GF;Intel One Mono-regular", "h2": "GF;Intel One Mono-500",
         "h3": "GF;Intel One Mono-500"}


def parse(kind):
    tag, _, anchor = kind.partition("#")
    return tag, (anchor or None)


def js_string(text):
    for ch, esc in (("\\", "\\\\"), ("`", "\\`"), ("$", "\\$")):
        text = text.replace(ch, esc)
    return text


def css_camel(prop):
    """padding-top -> paddingTop; CSS custom properties stay as-is."""
    if prop.startswith("--"):
        return prop
    head, *rest = prop.split("-")
    return head + "".join(p.capitalize() for p in rest)


def build_html():
    out = []
    for kind, name, text in BLOCKS:
        tag, anchor = parse(kind)
        style = ";".join(
            f"{p}:{html.escape(v, quote=False).replace(chr(34), '&quot;')}"
            for p, v in STYLES[tag]
        )
        idattr = f' id="{anchor}"' if anchor else ""
        out.append(
            f'<div class="framer-1kvfrc3" data-framer-name="{html.escape(name)}"'
            f' data-framer-component-type="RichTextContainer" style="transform:none">'
            f'<{tag}{idattr} dir="auto" style="{style}" class="framer-text">'
            f'{html.escape(text, quote=False)}</{tag}></div>'
        )
    return (
        '<div class="framer-1qcrww3" data-framer-name="Legal Details">'
        + "".join(out)
        + "</div>"
    )


def build_js():
    parts = []
    for kind, name, text in BLOCKS:
        tag, anchor = parse(kind)
        style = ",".join(f'"{css_camel(p)}":`{js_string(v)}`' for p, v in STYLES[tag])
        idprop = f"id:`{anchor}`," if anchor else ""
        parts.append(
            f"o(T,{{__fromCanvasComponent:!0,children:o(n,{{children:"
            f"o(`{tag}`,{{{idprop}dir:`auto`,style:{{{style}}},"
            f"children:`{js_string(text)}`}})}}),"
            f"className:`framer-1kvfrc3`,\"data-framer-name\":`{js_string(name)}`,"
            f"fonts:[`{FONTS[tag]}`],verticalAlignment:`top`,withExternalLayout:!0}})"
        )
    return (
        "l(`div`,{className:`framer-1qcrww3`,\"data-framer-name\":`Legal Details`,"
        "children:[" + ",".join(parts) + "]})"
    )


def replace_html():
    s = PAGE.read_text()
    i = s.find('<div class="framer-1qcrww3" data-framer-name="Legal Details">')
    assert i != -1, "Legal Details container not found in HTML"
    depth, j = 0, i
    while True:
        m = re.compile(r"</?div\b").search(s, j)
        depth += 1 if s[m.start():m.start() + 5] != "</div" else -1
        j = m.end()
        if depth == 0:
            break
    j = s.index(">", j) + 1
    PAGE.write_text(s[:i] + build_html() + s[j:])
    print(f"HTML: replaced {j - i} bytes with {len(build_html())}")


def replace_js():
    s = BUNDLE.read_text(errors="replace")
    start = s.find("l(`div`,{className:`framer-1qcrww3`")
    assert start != -1, "Legal Details container not found in bundle"
    # Walk forward balancing brackets to find the end of the call expression.
    depth, k, in_tick = 0, start + 1, False
    while k < len(s):
        c = s[k]
        if c == "\\":
            k += 2
            continue
        if c == "`":
            in_tick = not in_tick
        elif not in_tick:
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
                if depth == 0:
                    k += 1
                    break
        k += 1
    new = build_js()
    BUNDLE.write_text(s[:start] + new + s[k:])
    print(f"bundle: replaced {k - start} bytes with {len(new)}")


if __name__ == "__main__":
    replace_html()
    replace_js()
    print(f"blocks written: {len(BLOCKS)}")
    print("\nNow run: python3 scripts/check.py")
