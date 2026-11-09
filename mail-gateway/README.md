# Optional ESRA mail relay

The website remains on GitHub Pages. This dependency-free Cloudflare Worker
keeps Brevo and GitHub credentials off the static site. Brevo owns the mailing
list; there is no custom subscriber database. **Not deployed or enabled by this
branch. No emails or live submissions were sent during implementation.**

## Activation

1. Select ESRA's Brevo account, verify its sender/domain, create an events list
   and a double-opt-in template containing the provider confirmation link.
   Configure unsubscribe links, ESRA identity and privacy information. Confirm
   provider terms and processing arrangements before enabling collection.
2. Deploy worker.mjs using wrangler.toml with Wrangler 4.36 or later. Choose an
   unused rate-limit namespace. Set BREVO_API_KEY, BREVO_LIST_ID,
   BREVO_DOI_TEMPLATE_ID, EVENT_SUBMISSION_SECRET and GITHUB_TOKEN privately.
   Generate a random submission secret of at least 32 characters. The GitHub
   token needs only Issues write on ESRA-Robotics/website.
3. Set the same EVENT_SUBMISSION_SECRET in repository Actions secrets. It signs
   the exact public proposal so manual issues cannot bypass input validation.
   It does not prove the organiser's identity or ownership of their inbox.
4. Set SITE_ORIGIN and ALLOWED_ORIGINS to the actual website origins. Set
   EMAIL_ENABLED=true after configuration and put the deployed HTTPS Worker
   origin in events/mail-config.json as endpoint. No credentials belong there.
5. Configure Brevo's RSS Campaign integration against
   https://esrarobotics.eu/events/feeds/all.xml for the confirmed list, with the
   desired cadence and template. The integration supports up to ten items per
   campaign. Without account configuration, publishing does not send newsletters.
6. Test double opt-in, unsubscribe and reviewed submission with an explicitly
   authorised test recipient. Current tests mock every external request.

## Initial event submission flow

There is one visible ESRA organiser form, with no sign-in or emailed access link.
POST /organiser/submit checks the entered email has the exact @esrarobotics.eu
domain, validates the event and prepares a public GitHub review issue. The email
is omitted from the issue. The proof and issue explicitly say self-declared:
**anyone can type an ESRA address; inbox ownership is not verified.** Maintainers
must verify the actual club/organiser before approving. Authentication can be
added later. There is no automatic publication or ability to assign Original
status. A signed issue expires after seven days; request a fresh proposal if
review takes longer. GitHub notifications and human-reviewed merge remain the
publication workflow. Custom accept/decline HTML review emails are not active.

POST /subscribe requests provider-managed double opt-in and never silently adds
unconfirmed contacts. No browser address storage, cookies or subscriber files.
The application does not log request bodies or tokens; Worker observability is
disabled in the supplied config. The approximate limiter allows ten requests
per minute per IP per Cloudflare location; shared networks can hit it and
multi-location abuse can exceed it. Use provider quotas/abuse controls at launch.
CORS is a browser boundary, not authentication. Unavailable service returns an
error instead of reporting a saved submission.

China applications go directly to https://luma.com/m5dh07ac. The native
participant form and its private-mail endpoint have been removed.

## Offline checks

`node --test mail-gateway/test-worker.mjs` mocks all requests. Run
`python3 -m unittest discover -s scripts -p 'test_event_access.py'` for signed
proposal checks. Never substitute live provider credentials into these tests.

References: [Brevo double opt-in](https://developers.brevo.com/reference/create-doi-contact),
[RSS campaigns](https://help.brevo.com/hc/en-us/articles/360013130059-RSS-Campaign-integration-Automatically-share-your-blog-posts-with-your-subscribers),
[Cloudflare rate limiting](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/).
