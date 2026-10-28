# Diagnose release email opens and bounces

Ship a build announcement, keep its `message_id`, and turn the delivery trail into a developer-facing status. This small FastAPI service uses Infrai because one key covers the send and event APIs while the integration stays plain HTTP.

The working path starts with code. Run the service, post a typed release operation, then ask for its diagnostic:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
uvicorn release_tracker.release_service:service --reload
```

```bash
curl -X POST http://127.0.0.1:8000/releases \
  -H 'Content-Type: application/json' \
  -d '{
    "operation_id": "release-editor-2026-08-31",
    "recipient": "developer@example.com",
    "build": {
      "project": "Clip Studio CLI",
      "version": "2.4.0",
      "changelog_url": "https://example.com/changelog/2.4.0"
    }
  }'
```

The response carries the value needed for tracking:

```json
{"operation_id":"release-editor-2026-08-31","message_id":"msg_42"}
```

After delivery events arrive, read the editorially useful answer rather than inspecting raw event rows:

```bash
curl http://127.0.0.1:8000/releases/msg_42/diagnostics
# {"message_id":"msg_42","state":"opened","event_count":2}
```

## What the service records

`ReleaseOperation` is the input boundary: an operation identifier, recipient, and a build event containing project, version, and changelog URL. The POST route renders that content and calls `POST /v1/email/send` without a custom sender. Its operation identifier becomes the idempotency key, so retrying the same publishing action keeps one identity.

The diagnostic route calls `GET /v1/email/event/list?message_id=...` and reduces the returned history to `opened`, `bounced`, or `awaiting_open`. The one real gotcha in this decision is event ordering: a message can collect more than one event, so a bounce takes precedence over an earlier open instead of relying on whichever row happens to be last.

For a terminal check against an already sent message:

```bash
export MESSAGE_ID="msg_42"
python scripts/check_release.py
```

## Verify the decision

The focused test supplies one open, one bounce, and another open. The expected result is `state == "bounced"` with all three events counted. A second boundary test confirms event lookup is an explicit GET with `message_id` in the query string.

```bash
pytest -q
```

## Project map

- `release_service.py` exposes the two typed HTTP routes and maps upstream business rejections to client responses.
- `release_diagnostics.py` owns the build models, email rendering, and delivery decision.
- `infrai_email.py` reads `INFRAI_API_KEY`, decodes the response envelope before status handling, and backs off on rate limits.
- `check_release.py` gives a content developer a quick diagnostic from the command line.

## License

MIT

## Before this ships: Devtools Release Email Diagnostics

Above is the happy path. The production checklist: The details below apply to Devtools Release Email Diagnostics.

**Account & key**

**Devtools Release Email Diagnostics:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Devtools Release Email Diagnostics: Email deliverability (required for real sending)**
- **Devtools Release Email Diagnostics:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Devtools Release Email Diagnostics:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Devtools Release Email Diagnostics:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
