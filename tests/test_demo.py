from alumina.services.demo import build_demo_scenario
from alumina.services.domain import current_stock, ready_experiment_codes


def test_full_demo_has_three_workflow_stages():
    d = build_demo_scenario("full")
    statuses = {e["status"] for e in d["experiments"].values()}
    assert "Planificado" in statuses
    assert "Listo para horno" in statuses
    assert "Cocido" in statuses
    assert d["kilns"]
    assert d["firings"]


def test_kiln_demo_can_be_closed():
    d = build_demo_scenario("kiln_ready")
    fid = d["active_firing"]
    assert fid
    assert d["firings"][fid]["status"] == "Enfriando"
    assert d["firings"][fid]["current_temp_c"] == 45


def test_demo_stock_never_negative():
    d = build_demo_scenario("full")
    stock = current_stock(d["inventory"], d["movements"])
    assert min(stock.values()) >= 0


def test_full_demo_keeps_one_ready_experiment():
    d = build_demo_scenario("full")
    assert ready_experiment_codes(d["experiments"])
