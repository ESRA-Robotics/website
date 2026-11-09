#!/usr/bin/env node
/**
 * Render every page at every breakpoint and check that it actually holds up.
 *
 *     node scripts/check-breakpoints.mjs
 *
 * `scripts/check.py` reads the files. This one drives a real browser, because
 * the faults this repository has actually shipped were invisible in the source:
 * a section that rendered only above 634px, and flex `order` values that put
 * the partner block under the application heading on phones. Both looked
 * perfect in a wide window and in the markup.
 *
 * For each width it checks that
 *   - the page does not scroll sideways,
 *   - the sections appear in the same reading order at every width,
 *   - the section numbers run in order with no duplicates,
 *   - content that must never disappear is still on the page,
 *   - nothing threw.
 *
 * It needs Google Chrome. If no Chrome is found it says so and exits 0, so it
 * never blocks someone who just wants to fix a typo.
 */

import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { extname, join, resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '..')
const PORT = 8123

/** One width inside each of the five Framer breakpoints, plus a small phone. */
const WIDTHS = [320, 500, 700, 1000, 1300, 1600]

/**
 * Sections of the home page, in the order a visitor should meet them.
 * Matched as prefixes, because some labels are shortened on narrow screens
 * ("OUR GROWING NETWORK" rather than "OUR GROWING MEMBER NETWORK").
 */
const HOME_ORDER = [
  'WHAT WE DO',
  '3 PILLARS',
  'OUR GROWING',
  'MEMBER NETWORK',
  'STUDENTS FROM',
  'PARTNERS',
  'STRONG PARTNERS',
  'APPLICATION',
  'JOIN ESRA',
  'GET IN CONTACT',
]

/** Text that must be present at every width. */
const HOME_REQUIRED = ['APPLY NOW', 'first intake', 'Who are we looking for?']

/**
 * Footer links. IMPRINT and PRIVACY are not optional: German law wants the
 * imprint reachable from every page, and all six vanished below 634px once.
 */
const FOOTER_LINKS = ['HOME', 'WHO WE ARE', 'PILLARS', 'MEMBER CLUBS', 'EVENTS', 'IMPRINT', 'PRIVACY']

/**
 * Text that must not only exist but be clickable-through, that is, not sitting
 * underneath something else. The JOIN ESRA heading spent its life hidden
 * behind the absolutely positioned dark panel between 634px and 809px.
 */
const MUST_NOT_BE_COVERED = ['JOIN ESRA', 'Who are we looking for?', 'STRONG PARTNERS']
const IMPRINT_REQUIRED = ['Register number: VR 211579', 'DE462819831', 'Privacy Policy', 'Controller']
const EVENT_PAGES = [
  ['/events/', ['EVENTS', 'CHINA', 'TRIP 2027', 'Explore the trip', 'Submit an event', 'YOUR EVENT.']],
  ['/events/china-trip-2027/', ['CHINA', 'TRIP 2027', '14–23 March 2027', 'View on Luma', 'Before making plans', 'Meet your delegation.', 'PROOF OF WORK.', 'READY TO']],
]

const MIME = {
  '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript',
  '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml',
  '.webp': 'image/webp', '.woff2': 'font/woff2', '.json': 'application/json',
}

const CHROMES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  process.env.CHROME_PATH,
].filter(Boolean)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function serve() {
  const server = createServer(async (req, res) => {
    try {
      let p = join(ROOT, decodeURIComponent(req.url.split('?')[0]))
      if ((await stat(p).catch(() => null))?.isDirectory()) p = join(p, 'index.html')
      const body = await readFile(p)
      res.writeHead(200, { 'content-type': MIME[extname(p)] ?? 'application/octet-stream' })
      res.end(body)
    } catch {
      res.writeHead(404).end('not found')
    }
  })
  return new Promise((r) => server.listen(PORT, '127.0.0.1', () => r(server)))
}

async function connect(chromePath) {
  const port = 9210
  // A fresh profile every run. Reusing one lets Chrome serve the previous
  // build from its disk cache, which produces confident, wrong results.
  const profile = mkdtempSync(join(tmpdir(), 'esra-breakpoints-'))
  const proc = spawn(chromePath, [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--hide-scrollbars', '--no-sandbox', '--disable-application-cache',
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank',
  ], { stdio: 'ignore' })

  let target
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
      target = list.find((t) => t.type === 'page')
      if (target) break
    } catch { /* not up yet */ }
    await sleep(250)
  }
  if (!target) { proc.kill(); rmSync(profile, { recursive: true, force: true }); throw new Error('Chrome did not start') }

  const ws = new WebSocket(target.webSocketDebuggerUrl)
  let id = 0
  const pending = new Map()
  const errors = []
  await new Promise((r) => { ws.onopen = r })
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); return }
    if (m.method === 'Runtime.exceptionThrown') {
      errors.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text)
    }
  }
  const send = (method, params = {}) =>
    new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })) })

  await send('Page.enable')
  await send('Runtime.enable')
  await send('Network.enable')
  await send('Network.setCacheDisabled', { cacheDisabled: true })
  const kill = async () => {
    const ended = new Promise((r) => proc.once('exit', r))
    proc.kill()
    await Promise.race([ended, sleep(3000)])
    // Best effort: a leftover temp profile is untidy, not a failure.
    try {
      rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
    } catch { /* ignore */ }
  }
  return { send, errors, kill }
}

/** Runs in the page. Returns what we need to judge one width. */
const PROBE = `JSON.stringify((function () {
  var MUST_NOT_BE_COVERED = ${JSON.stringify(MUST_NOT_BE_COVERED)};
  var texts = [].slice.call(document.querySelectorAll('p,h1,h2,h3,h4'))
    // Anything inside a link is navigation or a footer item, not a section.
    // The top nav repeats the words PARTNERS and APPLICATION.
    .filter(function (e) { return e.offsetParent && !e.closest('a'); })
    .map(function (e) {
      var r = e.getBoundingClientRect();
      return { t: e.textContent.trim(), y: Math.round(r.top + window.scrollY) };
    })
    .sort(function (a, b) { return a.y - b.y; });
  // Footer links: the ones that live in the bottom third of the page.
  var footer = [].slice.call(document.querySelectorAll('a'))
    .filter(function (a) {
      if (!a.offsetParent) return false;
      return (a.getBoundingClientRect().top + window.scrollY) > document.body.scrollHeight * 0.6;
    })
    .map(function (a) { return a.textContent.trim(); });

  // Anything sitting underneath another element. A heading can be present,
  // visible to a DOM query, and still completely hidden behind a panel.
  var covered = [];
  MUST_NOT_BE_COVERED.forEach(function (want) {
    var el = [].slice.call(document.querySelectorAll('h1,h2,h3,p'))
      .filter(function (e) { return e.offsetParent && e.textContent.trim() === want; })[0];
    if (!el) { covered.push(want + ' (not on the page)'); return; }
    el.scrollIntoView({ block: 'center' });
    // Measure the text itself, not its box. These headings sit in very wide
    // boxes whose left edge and centre are empty space, so sampling the box
    // hits whatever is behind it and reads as a false pass.
    var range = document.createRange();
    range.selectNodeContents(el);
    var rects = range.getClientRects();
    var r = rects.length ? rects[0] : el.getBoundingClientRect();
    // Clamp into the viewport: elementFromPoint returns null outside it.
    var clamp = function (v, max) { return Math.max(2, Math.min(v, max - 2)); };
    var x = clamp(r.left + r.width / 2, window.innerWidth);
    var y = clamp(r.top + r.height / 2, window.innerHeight);
    var hit = document.elementFromPoint(x, y);
    // Only the element itself or something inside it counts. Landing on an
    // ancestor means the glyphs are not painted there, so something is on top.
    if (!hit || !(hit === el || el.contains(hit))) {
      var who = hit ? (hit.className || hit.tagName || '?').toString().slice(0, 40) : 'nothing';
      covered.push(want + ' (topmost element over its text is ' + who + ')');
    }
  });

  return {
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    numbers: texts.filter(function (x) { return /^0\\.\\d+\\/$/.test(x.t); }).map(function (x) { return x.t; }),
    labels: texts.map(function (x) { return x.t; }),
    footer: footer,
    eventLinks: [].slice.call(document.querySelectorAll('a[href="/events/"]'))
      .filter(function (a) { return a.offsetParent; })
      .map(function (a) { return a.getBoundingClientRect().top + window.scrollY; }),
    covered: covered,
    body: document.body.innerText
  };
})())`

async function measure(send, url, width) {
  await send('Emulation.setDeviceMetricsOverride',
    { width, height: 900, deviceScaleFactor: 1, mobile: width < 810 })
  await send('Page.navigate', { url })
  await sleep(5500)
  // Scroll the whole page so lazily-rendered sections settle.
  await send('Runtime.evaluate', {
    expression: `(async()=>{for(let y=0;y<document.body.scrollHeight;y+=400){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,25));}window.scrollTo(0,0);})()`,
    awaitPromise: true,
  })
  await sleep(900)
  const r = await send('Runtime.evaluate', { expression: PROBE, returnByValue: true })
  return JSON.parse(r.result.value)
}

function checkHome(width, d, fail) {
  if (!d.eventLinks.some((y) => y < 250)) fail(`${width}px: no Events link near the top of the home page`)
  // Sections must appear in the expected reading order.
  const seen = []
  for (const label of d.labels) {
    const match = HOME_ORDER.find((want) => label.startsWith(want))
    if (match && !seen.includes(match)) seen.push(match)
  }
  const expected = HOME_ORDER.filter((s) => seen.includes(s))
  if (seen.join(' > ') !== expected.join(' > ')) {
    fail(`${width}px: sections are out of order.\n      got      ${seen.join(' > ')}\n      expected ${expected.join(' > ')}`)
  }
  for (const want of HOME_ORDER) {
    if (!seen.includes(want)) fail(`${width}px: section "${want}" is missing from the page`)
  }
  // Section numbers must ascend with no repeats.
  const nums = d.numbers.map((n) => parseFloat(n.replace('/', '')))
  for (let i = 1; i < nums.length; i++) {
    if (nums[i] <= nums[i - 1]) {
      fail(`${width}px: section numbers do not ascend: ${d.numbers.join(' ')}`)
      break
    }
  }
  for (const want of HOME_REQUIRED) {
    if (!d.body.includes(want)) fail(`${width}px: required content missing: ${JSON.stringify(want)}`)
  }
  for (const want of FOOTER_LINKS) {
    if (!d.footer.includes(want)) fail(`${width}px: the footer link "${want}" is not on the page`)
  }
  for (const c of d.covered) {
    fail(`${width}px: ${c} is hidden underneath something else`)
  }
}

async function main() {
  const chromePath = CHROMES.find((p) => existsSync(p))
  if (!chromePath) {
    console.log('No Chrome found, skipped the breakpoint checks.')
    console.log('Install Google Chrome, or set CHROME_PATH, to run them.')
    return 0
  }

  const server = await serve()
  const { send, errors, kill } = await connect(chromePath)
  const failures = []
  const fail = (m) => failures.push(m)

  try {
    for (const width of WIDTHS) {
      const home = await measure(send, `http://127.0.0.1:${PORT}/`, width)
      if (home.overflow) {
        fail(`${width}px: the home page scrolls sideways (content is ${home.scrollWidth}px wide in a ${home.innerWidth}px window)`)
      }
      checkHome(width, home, fail)

      const imprint = await measure(send, `http://127.0.0.1:${PORT}/imprint/`, width)
      if (imprint.overflow) {
        fail(`${width}px: the imprint page scrolls sideways (${imprint.scrollWidth}px in ${imprint.innerWidth}px)`)
      }
      for (const want of IMPRINT_REQUIRED) {
        if (!imprint.body.includes(want)) fail(`${width}px: imprint is missing ${JSON.stringify(want)}`)
      }
      for (const [path, required] of EVENT_PAGES) {
        const event = await measure(send, `http://127.0.0.1:${PORT}${path}`, width)
        if (event.overflow) fail(`${width}px: ${path} scrolls sideways (${event.scrollWidth}px)`)
        for (const want of required) {
          if (!event.body.toLowerCase().includes(want.toLowerCase())) fail(`${width}px: ${path} is missing ${JSON.stringify(want)}`)
        }
        for (const want of ['HOME', 'EVENTS', 'IMPRINT', 'PRIVACY']) {
          if (!event.footer.some((text) => text.toUpperCase() === want)) fail(`${width}px: ${path} footer is missing ${want}`)
        }
      }
      console.log(`  checked ${String(width).padStart(4)}px`)
    }
    for (const e of errors) fail(`uncaught error in the page: ${String(e).split('\n')[0]}`)
  } finally {
    await kill()
    server.close()
  }

  console.log()
  if (failures.length) {
    for (const f of failures) console.error(`error: ${f}`)
    console.error(`\nFAILED: ${failures.length} problem(s) across ${WIDTHS.length} widths`)
    return 1
  }
  console.log(`OK: ${WIDTHS.length} widths checked, no problems`)
  return 0
}

process.exit(await main())
