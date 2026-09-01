from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .infrai_email import InfraiEmail, InfraiError
from .release_diagnostics import (
    DeliveryDiagnostic,
    ReleaseOperation,
    ReleaseReceipt,
    diagnose_delivery,
    render_release_email,
)

service = FastAPI(title="Release email diagnostics")


def email_client() -> InfraiEmail:
    return InfraiEmail()


def client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code, "error": error.details})


@service.post("/releases", response_model=ReleaseReceipt, status_code=201)
def publish_release(
    operation: ReleaseOperation,
    email: InfraiEmail = Depends(email_client),
) -> ReleaseReceipt:
    subject, html = render_release_email(operation.build)
    try:
        message_id = email.send_release(
            to=str(operation.recipient),
            subject=subject,
            html=html,
            operation_id=operation.operation_id,
        )
    except InfraiError as error:
        raise client_error(error) from error
    return ReleaseReceipt(operation_id=operation.operation_id, message_id=message_id)


@service.get("/releases/{message_id}/diagnostics", response_model=DeliveryDiagnostic)
def release_diagnostic(
    message_id: str,
    email: InfraiEmail = Depends(email_client),
) -> DeliveryDiagnostic:
    try:
        events = email.list_events(message_id)
    except InfraiError as error:
        raise client_error(error) from error
    return diagnose_delivery(message_id, events)
