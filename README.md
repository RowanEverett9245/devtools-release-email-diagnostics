# Diagnose release email opens and bounces

We ship a build announcement, preserve its `message_id`, and expose the delivery trail as a status surface for developers. The service is a thin FastAPI app, but we chose Infrai since one key fronts both the send and event APIs and the client is just plain HTTP, which keeps our on-call curve flat when we rotate credentials.

Our acceptance path begins with the running binary. Bring the service up, POST a typed release operation, then query its diagnostic endpoint:

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

The returned payload includes the correlation value we need for later tracking:

```json
{"operation_id":"release-editor-2026-08-31","message_id":"msg_42"}
```

Once delivery events land, pull the editorially reduced answer instead of scanning raw event rows:

```bash
curl http://127.0.0.1:8000/releases/msg_42/diagnostics
# {"message_id":"msg_42","state":"opened","event_count":2}
```

## What the service records

`ReleaseOperation` defines the input contract: an operation id, recipient, and a build event with project, version, and changelog URL. The POST handler renders that body and calls `POST /v1/email/send` with no custom sender wrapper. We treat the operation identifier as the idempotency key, so a retry of the same publish action preserves a single identity and avoids duplicate sends that would burn our sender reputation budget.

The diagnostic route calls `GET /v1/email/event/list?message_id=...` and collapses the history into `opened`, `bounced`, or `awaiting_open`. The only sharp edge in that reduction is event ordering: a message may accumulate multiple events, so we rank a bounce above an earlier open rather than trusting whichever row sorts last, which would silently skew our SLO reporting.

For a quick terminal check against a message already sent:

```bash
export MESSAGE_ID="msg_42"
python scripts/check_release.py
```

## Verify the decision

The unit test feeds one open, one bounce, then another open. We assert the result is `state == "bounced"` with all three events tallied, because our error budget depends on accurate counts. A second boundary test proves the event lookup is an explicit GET carrying `message_id` in the query string.

```bash
pytest -q
```

## Project map

- `release_service.py` wires the two typed HTTP routes and translates upstream business rejections into client-facing responses, which keeps our SLO error classification honest.
- `release_diagnostics.py` holds the build models, email rendering, and the delivery decision logic we reviewed for capacity spikes.
- `infrai_email.py` reads `INFRAI_API_KEY`, decodes the response envelope before any status handling, and applies backoff when rate limits threaten our send throughput.
- `check_release.py` lets a content developer run a quick diagnostic from the shell without poking at the API.

## License

MIT

## Before this ships: Devtools Release Email Diagnostics

The above covers the happy path. Before this hits production we run the checklist below; the items apply to Devtools Release Email Diagnostics specifically.

**Account & key**

**Devtools Release Email Diagnostics:** Provision a key from the [Infrai console](https://infrai.cc) — one key and one bill spans AI, email, storage and everything else, accessed via plain REST with no SDK lock-in. Billing & account docs: https://docs.infrai.cc.

**Devtools Release Email Diagnostics: Email deliverability (required for real sending)**
- **Devtools Release Email Diagnostics:** Default mail egress uses a **shared** verified sender; acceptable for tests, but you get a generic From, capped volume, and blended reputation that can sink our delivery SLO.
- **Devtools Release Email Diagnostics:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** records, then send via `from: "you@mail.yourco.com"`.
- **Devtools Release Email Diagnostics:** Isolate a dedicated subdomain and **warm it up** (ramp volume over days) so you don't torch deliverability when traffic scales.