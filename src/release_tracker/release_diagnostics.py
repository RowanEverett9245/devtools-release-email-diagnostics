from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class BuildEvent(BaseModel):
    project: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    changelog_url: str


class ReleaseOperation(BaseModel):
    operation_id: str = Field(min_length=8, max_length=120)
    recipient: EmailStr
    build: BuildEvent


class ReleaseReceipt(BaseModel):
    operation_id: str
    message_id: str


class DeliveryDiagnostic(BaseModel):
    message_id: str
    state: Literal["opened", "bounced", "awaiting_open"]
    event_count: int


def render_release_email(build: BuildEvent) -> tuple[str, str]:
    subject = f"{build.project} {build.version} is ready"
    html = (
        f"<h1>{build.project} {build.version}</h1>"
        f'<p>The build is ready. <a href="{build.changelog_url}">Read the changelog</a>.</p>'
    )
    return subject, html


def diagnose_delivery(message_id: str, events: list[dict[str, Any]]) -> DeliveryDiagnostic:
    event_types = {str(event.get("type", "")).lower() for event in events}
    if "bounce" in event_types or "bounced" in event_types:
        state = "bounced"
    elif "open" in event_types or "opened" in event_types:
        state = "opened"
    else:
        state = "awaiting_open"
    return DeliveryDiagnostic(message_id=message_id, state=state, event_count=len(events))
