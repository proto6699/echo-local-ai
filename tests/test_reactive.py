from neco.reactive import choose_reactive_line


def test_network_loss_wins() -> None:
    line, state = choose_reactive_line(
        {"net_ok": True, "last_uptime_milestone": 0},
        hour=12,
        net_ok=False,
        uptime_hours=2,
        cpu_temp_c=40,
        owner_name="Echo",
        random_value=1.0,
    )
    assert line == "Oh. The outside disappeared."
    assert state["net_ok"] is False


def test_uptime_milestone_is_only_emitted_once() -> None:
    state = {"net_ok": True, "last_uptime_milestone": 0}
    line, state = choose_reactive_line(
        state,
        hour=12,
        net_ok=True,
        uptime_hours=25.2,
        cpu_temp_c=40,
        owner_name="Echo",
        random_value=1.0,
    )
    assert line == "We've been awake for 24 hours."
    assert state["last_uptime_milestone"] == 24
    line, _ = choose_reactive_line(
        state,
        hour=12,
        net_ok=True,
        uptime_hours=25.2,
        cpu_temp_c=40,
        owner_name="Echo",
        random_value=1.0,
    )
    assert line is None
