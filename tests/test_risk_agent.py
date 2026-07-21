"""Risk agent tests."""
import pytest
from agents.risk_agent import RiskAgent

@pytest.fixture
def risk_agent():
    return RiskAgent()



def test_approve_valid(risk_agent):
    signal = {"signal": "BUY", "confidence": 75, "metadata": {"symbol": "BTCUSDT", "current_price": 65000}}
    result = risk_agent.run(signal=signal, user_id=1, balance=10000, open_positions=[])
    assert result["approved"] is True
    assert result["position_size"] > 0



def test_reject_max_positions(risk_agent):
    signal = {"signal": "BUY", "confidence": 75, "metadata": {"symbol": "ETHUSDT", "current_price": 3500}}
    open_positions = [
        {"symbol": "BTCUSDT", "side": "LONG"}, {"symbol": "SOLUSDT", "side": "LONG"},
        {"symbol": "AVAXUSDT", "side": "SHORT"}, {"symbol": "LINKUSDT", "side": "LONG"},
        {"symbol": "DOTUSDT", "side": "LONG"},
    ]
    result = risk_agent.run(signal=signal, user_id=1, balance=10000, open_positions=open_positions)
    assert result["approved"] is False
    assert "Max positions" in result["reason"]



def test_reject_duplicate(risk_agent):
    signal = {"signal": "BUY", "confidence": 75, "metadata": {"symbol": "BTCUSDT", "current_price": 65000}}
    open_positions = [{"symbol": "BTCUSDT", "side": "LONG"}]
    result = risk_agent.run(signal=signal, user_id=1, balance=10000, open_positions=open_positions)
    assert result["approved"] is False
    assert "already exists" in result["reason"]
