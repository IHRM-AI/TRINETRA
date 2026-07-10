from trinetra.api.portfolio import next_action


def test_grade_e_routes_to_exit_rfa():
    action, reason = next_action("E", "Watchlist / RFA review", 0.24)
    assert action == "Exit / RFA review"
    assert "24.0%" in reason
    assert "Red-Flagged-Account" in reason


def test_grade_d_routes_to_restructure():
    action, reason = next_action("D", "Watchlist", 0.13)
    assert action == "Restructure or collateral top-up"
    assert "collateral top-up" in reason


def test_grade_c_routes_to_enhanced_monitoring():
    action, reason = next_action("C", "Monitor", 0.08)
    assert action == "Enhanced monitoring + covenant check"
    assert "covenant" in reason


def test_grade_a_and_b_route_to_standard_review():
    for grade in ("A", "B"):
        action, reason = next_action(grade, "Standard", 0.01)
        assert action == "Standard annual review"
        assert "standard annual review" in reason


def test_action_reason_carries_the_pd_percentage():
    _, reason = next_action("C", "Monitor", 0.075)
    assert "7.5%" in reason
