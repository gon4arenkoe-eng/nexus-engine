import os

def replace_in_file(path, old, new):
    if os.path.exists(path):
        with open(path, 'r') as f: content = f.read()
        if old in content:
            with open(path, 'w') as f: f.write(content.replace(old, new))

# 1. Fix f-string in signal_agent.py
replace_in_file('agents/signal_agent.py', 'f"Confidence below threshold ({signal_result["confidence"]} < {confidence_threshold})"', "f'Confidence below threshold ({signal_result[\"confidence\"]} < {confidence_threshold})'")

# 2. Fix signatures to match BaseAgent.run(*args, **kwargs)
replace_in_file('agents/notification_agent.py', 'def run(self, event: Dict[str, Any]) -> bool:', 'async def run(self, event: Dict[str, Any], **kwargs) -> bool:')
replace_in_file('agents/ml_agent.py', 'def run(self, signal: Dict[str, Any], market_data: pd.DataFrame) -> bool:', 'async def run(self, signal: Dict[str, Any], market_data: pd.DataFrame, **kwargs) -> bool:')
replace_in_file('agents/risk_agent.py', 'def run(', 'async def run(')
replace_in_file('agents/risk_agent.py', 'open_positions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:', 'open_positions: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Dict[str, Any]:')
replace_in_file('agents/pnl_agent.py', 'def run(self, user_id: int, positions: List[Dict[str, Any]]) -> Optional[Decimal]:', 'async def run(self, user_id: int, positions: List[Dict[str, Any]], **kwargs) -> Optional[Decimal]:')

# 3. Fix signatures to match BaseStrategy.analyze(self, data, **kwargs)
replace_in_file('strategies/ema_cross.py', 'def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:', 'def analyze(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:')
replace_in_file('strategies/mean_reversion.py', 'def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:', 'def analyze(self, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:')

# 4. Fix TradingService empty check
replace_in_file('services/trading_service.py', 'or market_data.empty', 'or getattr(market_data, "empty", False)')

# 5. Fix Orchestrator awaits
replace_in_file('agents/orchestrator.py', 'self.config_agent.run(user_id)', 'await self.config_agent.run(user_id)')
replace_in_file('agents/orchestrator.py', 'self.market_agent.run(symbol, timeframe)', 'await self.market_agent.run(symbol, timeframe)')
replace_in_file('agents/orchestrator.py', 'self.signal_agent.run(', 'await self.signal_agent.run(')
replace_in_file('agents/orchestrator.py', 'self.risk_agent.run(', 'await self.risk_agent.run(')
replace_in_file('agents/orchestrator.py', 'self.execution_agent.run(', 'await self.execution_agent.run(')
replace_in_file('agents/orchestrator.py', 'self.position_agent.run(', 'await self.position_agent.run(')
replace_in_file('agents/orchestrator.py', 'self.pnl_agent.run(', 'await self.pnl_agent.run(')

