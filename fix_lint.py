import os
import re


def fix_file(path):
    with open(path, "r") as f:
        content = f.read()

    # Fix E302 (expected 2 blank lines)
    content = re.sub(r"(\nclass )", r"\n\n\1", content)
    content = re.sub(r"(\ndef )", r"\n\n\1", content)
    # Remove duplicate blank lines created
    content = re.sub(r"\n{3,}", r"\n\n", content)

    # Fix E261 (at least two spaces before inline comment)
    content = re.sub(r"([^ ])#", r"\1  #", content)

    # Fix W293 (blank line contains whitespace)
    content = re.sub(r"\n +\n", r"\n\n", content)

    with open(path, "w") as f:
        f.write(content)


files_to_fix = [
    "agents/base_agent.py",
    "agents/config_agent.py",
    "agents/market_data_agent.py",
    "agents/market_regime_agent.py",
    "agents/signal_agent.py",
    "nexus_bus.py",
    "services/trading_service.py",
    "strategies/base.py",
    "strategies/bollinger_squeeze.py",
    "strategies/statistical_arbitrage.py",
    "strategies/trend_following_chop.py",
    "utils/indicators.py",
]

for f in files_to_fix:
    if os.path.exists(f):
        fix_file(f)
