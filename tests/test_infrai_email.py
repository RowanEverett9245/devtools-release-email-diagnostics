import httpx

from release_tracker.infrai_email import InfraiEmail


def test_event_lookup_uses_get_with_message_id_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/email/event/list"
        assert request.url.params["message_id"] == "msg_42"
        return httpx.Response(200, json={"ok": True, "data": [{"type": "open"}], "metadata": {}})

    client = InfraiEmail(api_key="test-key", transport=httpx.MockTransport(handler))

    assert client.list_events("msg_42") == [{"type": "open"}]
