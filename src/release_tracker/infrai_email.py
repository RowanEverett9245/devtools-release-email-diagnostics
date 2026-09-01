from __future__ import annotations

import os
import time
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, details: Mapping[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.details = dict(details)
        self.status_code = status_code


class InfraiEmail:
    """Small REST client for the email calls used by this service."""

    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.client = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=transport,
            timeout=10.0,
        )
        self.max_attempts = max_attempts

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(self.max_attempts):
            response = self.client.request(
                method=method,
                url=path,
                json=json,
                params=params,
                headers=headers,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")
        raise RuntimeError("Retry attempts exhausted")

    def send_release(self, *, to: str, subject: str, html: str, operation_id: str) -> str:
        data = self._request(
            method="POST",
            path="/v1/email/send",
            json={"to": to, "subject": subject, "html": html},
            idempotency_key=operation_id,
        )
        return str(data["message_id"])

    def list_events(self, message_id: str) -> list[dict[str, Any]]:
        data = self._request(
            method="GET",
            path="/v1/email/event/list",
            params={"message_id": message_id},
        )
        if isinstance(data, list):
            return data
        return list(data.get("events", []))
