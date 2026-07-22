"""Risk agent tests."""
import pytest
from unittest.mock import patch, MagicMock
from agents.risk_agent import RiskAgent


@pytest.fixture
def risk_agent():
    """Create risk agent fixture."""
    return RiskAgent()


@patch("agents.risk_agent.BotSettings")
def test_approve_valid(mock_settings, risk_agent):
    """Test approval of valid signal."""
    mock_settings.query.filter_by.return_value.first.return_value = MagicMock(
        max_positions=10,
        max_leverage=10,
        daily_loss_limit=500,
        position_size_pct=10,
    )
    signal = {
        "signal": "BUY",
        "confidence": 75,
        "metadata": {"symbol": "BTCUSDT", "current_price": 65000},
    }
    result = risk_agent.run(
        signal=signal, user_id=1, balance=10000, open_positions=[]
    )
    assert result["approved"] is True
    assert result["position_size"] > 0


@patch("agents.risk_agent.BotSettings")
def test_reject_max_positions(mock_settings, risk_agent):
    """Test rejection when max positions reached."""
    mock_settings.query.filter_by.return_value.first.return_value = MagicMock(
        max_positions=5,
        max_leverage=10,
        daily_loss_limit=500,
        position_size_pct=10,
    )
    signal = {
        "signal": "BUY",
        "confidence": 75,
        "metadata": {"symbol": "ETHUSDT", "current_price": 3500},
    }
    open_positions = [
        {"symbol": "BTCUSDT", "side": "LONG"},
        {"symbol": "SOLUSDT", "side": "LONG"},
        {"symbol": "AVAXUSDT", "side": "SHORT"},
        {"symbol": "LINKUSDT", "side": "LONG"},
        {"symbol": "DOTUSDT", "side": "LONG"},
    ]
    result = risk_agent.run(
        signal=signal, user_id=1, balance=10000, open_positions=open_positions
    )
    assert result["approved"] is False
    assert "Max positions" in result["reason"]


@patch("agents.risk_agent.BotSettings")
def test_reject_duplicate(mock_settings, risk_agent):
    """Test rejection of duplicate symbol+side."""
    mock_settings.query.filter_by.return_value.first.return_value = MagicMock(
        max_positions=10,
        max_leverage=10,
        daily_loss_limit=500,
        position_size_pct=10,
    )
    signal = {
        "signal": "BUY",
        "confidence": 75,
        "metadata": {"symbol": "BTCUSDT", "current_price": 65000},
    }
    open_positions = [{"symbol": "BTCUSDT", "side": "LONG"}]
    result = risk_agent.run(
        signal=signal, user_id=1, balance=10000, open_positions=open_positions
    )
    assert result["approved"] is False
    assert "already exists" in result["reason"]
