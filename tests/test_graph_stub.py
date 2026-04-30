"""Smoke test: stub pipeline runs end-to-end."""

from trade_validator.graph.pipeline import run_pipeline_once
from trade_validator.schemas.routing import RouterAction, RouterDecision


def test_pipeline_invokes_all_nodes():
    out = run_pipeline_once(thread_id="pytest-thread")
    assert "extraction" in out
    assert "validation" in out
    assert "router_decision" in out
    decision = RouterDecision.model_validate(out["router_decision"])
    assert decision.action == RouterAction.human_review
