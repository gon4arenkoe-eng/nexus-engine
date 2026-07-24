import os

def fix_file(path, old, new):
    if os.path.exists(path):
        with open(path, 'r') as f: content = f.read()
        if old in content:
            with open(path, 'w') as f: f.write(content.replace(old, new))

# 1. Fix Orchestrator - add awaits to agent calls
path = 'agents/orchestrator.py'
if os.path.exists(path):
    with open(path, 'r') as f: content = f.read()
    content = content.replace('config_result = self.agents["config"].run(user_id)', 'config_result = await self.agents["config"].run(user_id)')
    content = content.replace('self.agents["market"].run(symbol, timeframe, exchange="bingx")', 'await self.agents["market"].run(symbol, timeframe, exchange="bingx")')
    content = content.replace('signal = self.agents["signal"].run(', 'signal = await self.agents["signal"].run(')
    content = content.replace('if not self.agents["ml"].run(signal, market_data):', 'if not await self.agents["ml"].run(signal, market_data):')
    content = content.replace('risk_result = self.agents["risk"].run(', 'risk_result = await self.agents["risk"].run(')
    content = content.replace('pnl = self.agents["pnl"].run(user_id, positions)', 'pnl = await self.agents["pnl"].run(user_id, positions)')
    with open(path, 'w') as f: f.write(content)

# 2. Fix Statistical Arbitrage signature
path = 'strategies/statistical_arbitrage.py'
if os.path.exists(path):
    with open(path, 'r') as f: content = f.read()
    old_sig = 'def analyze(self, data_a: pd.DataFrame, data_b: pd.DataFrame, **kwargs) -> Dict[str, Any]:'
    new_sig = 'def analyze(self, data: pd.DataFrame, data_b: Optional[pd.DataFrame] = None, **kwargs) -> Dict[str, Any]:'
    if old_sig in content:
        content = content.replace(old_sig, new_sig)
        content = content.replace('df_a = data_a.loc[common_index].copy()', 'df_a = data.loc[common_index].copy()')
        content = content.replace('if not self._validate_data(data_a, min_rows=self.z_score_period + 2) or \\', 'if not self._validate_data(data, min_rows=self.z_score_period + 2) or \\')
    with open(path, 'w') as f: f.write(content)

