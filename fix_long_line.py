import os

path = 'agents/signal_agent.py'
with open(path, 'r') as f:
    lines = f.readlines()

with open(path, 'w') as f:
    for line in lines:
        if 'logger.warning(f"SignalAgent: RANGING regime detected' in line:
            # Split the long warning message into two lines
            f.write('                    logger.warning(\n')
            f.write('                        f"SignalAgent: RANGING regime detected for {symbol}, "\n')
            f.write('                        f"but no pair data. Falling back to EMA Cross."\n')
            f.write('                    )\n')
        else:
            f.write(line)
