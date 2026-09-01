import os

from release_tracker.infrai_email import InfraiEmail
from release_tracker.release_diagnostics import diagnose_delivery


message_id = os.environ.get("MESSAGE_ID")
if not message_id:
    raise SystemExit("MESSAGE_ID is required")

client = InfraiEmail()
result = diagnose_delivery(message_id, client.list_events(message_id))
print(result.model_dump_json(indent=2))
