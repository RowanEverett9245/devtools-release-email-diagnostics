from release_tracker.release_diagnostics import diagnose_delivery


def test_bounce_wins_when_delivery_has_open_and_bounce_events() -> None:
    events = [{"type": "open"}, {"type": "bounce"}, {"type": "open"}]

    diagnostic = diagnose_delivery("msg_release_42", events)

    assert diagnostic.state == "bounced"
    assert diagnostic.event_count == 3
