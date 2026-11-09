# Optional ESRA mail relay

The website stays on GitHub Pages. This dependency-free Cloudflare Worker keeps
Brevo and GitHub credentials off the static site. Brevo stores the mailing list;
there is no custom subscriber database. The popup and organiser sign-in remain
inside the ESRA UI. **Not deployed or enabled by this branch. No email was sent.**

## Activation by the account owner

1. Create/select ESRA's Brevo account, verify its sender/domain, create an events
   list and a double-opt-in template. Include the provider confirmation link in
   that template. Configure unsubscribe links and the ESRA identity/contact in
   every campaign. Confirm provider terms, processing agreement and privacy copy
   before enabling collection.
2. Deploy `worker.mjs` using `wrangler.toml` with Wrangler 4.36 or later. Choose
   an unused rate-limit namespace in the account. Store BREVO_API_KEY,
   BREVO_LIST_ID, BREVO_DOI_TEMPLATE_ID, EMAIL_FROM, ACCESS_SECRET,
   EVENT_SUBMISSION_SECRET and GITHUB_TOKEN as Worker secrets (see the example).
   Generate independent random secrets of at least 32 characters. The GitHub
   token needs only Issues write on ESRA-Robotics/website; no Contents permission.
3. Set the identical EVENT_SUBMISSION_SECRET in repository Actions secrets.
   It authenticates the exact public event payload before the moderation workflow
   prepares a publication PR. Keep both copies private and rotate together.
4. Set SITE_ORIGIN to https://esrarobotics.eu and ALLOWED_ORIGINS to the actual
   permitted website origins. Add the optional events subdomain only when active.
   Set EMAIL_ENABLED=true only after these steps. Put the deployed HTTPS Worker
   origin (no trailing slash) into events/mail-config.json as `endpoint`.
5. Configure Brevo's RSS Campaign integration for the confirmed events list,
   using https://esrarobotics.eu/events/feeds/all.xml. Choose the desired cadence
   and review the email template; the integration supports up to ten feed items
   per campaign. Account access is required to activate the campaign. Publishing
   a catalogue update alone does not send a newsletter until this is configured.
6. Test confirmation, unsubscribe, organiser sign-in and a reviewed submission
   with an explicitly authorised test recipient. This implementation has only
   exercised mocked provider requests, never real delivery.

## Behaviour and limits

POST /subscribe requests provider-managed double opt-in; it never silently adds
unconfirmed contacts. POST /organiser/request-link permits the exact
@esrarobotics.eu domain and emails a signed 20-minute access link. The token is
read from a URL fragment and removed from the address bar. It is reusable until
expiry (stateless, not a one-time token); protect it like a password. Sign-in
links should not be forwarded. No private email is copied into public issues.

POST /organiser/submit validates the token and event, strips untrusted extra
fields, and creates a public GitHub review issue with a seven-day signed payload.
Review it within that period or request a fresh submission. Submitters cannot
assign ESRA Original status. A maintainer still reviews and merges the update.
Review notifications use GitHub settings; custom accept/decline HTML emails are
not implemented. Configure the three trusted reviewers' verified notification
addresses in their own GitHub accounts; never assume their account names.

Cloudflare's per-IP limiter is an approximate ten requests/minute per location;
shared networks may hit it, and distributed abuse can exceed it. Use provider
quotas and Cloudflare abuse controls for production traffic. No request bodies,
addresses or tokens are logged in application code; Worker observability is
disabled in the supplied config. CORS is a browser boundary, not authentication.
No cookies or local subscriber storage are used. Frontend errors never report
that an address was saved when the service is unavailable.

## Offline verification

`node --test mail-gateway/test-worker.mjs` stubs every network request. Run
`python3 -m unittest discover -s scripts -p 'test_event_access.py'` for moderation
attestation checks. Do not substitute real provider credentials into tests.

References: [Brevo double opt-in](https://developers.brevo.com/reference/create-doi-contact),
[transactional mail](https://developers.brevo.com/reference/send-transac-email),
[RSS campaigns](https://help.brevo.com/hc/en-us/articles/360013130059-RSS-Campaign-integration-Automatically-share-your-blog-posts-with-your-subscribers),
[Cloudflare rate limiting](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/).
