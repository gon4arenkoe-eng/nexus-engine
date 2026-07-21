# NEXUS Engine V10

[![V10 CI/CD](https://github.com/gon4arenkoe-eng/nexus-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/gon4arenkoe-eng/nexus-engine/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

&gt; **Эволюция от монолита к агентной архитектуре**
&gt; 
&gt; NEXUS Engine — это алгоритмическая торговая система на базе 12 автономных агентов,
&gt; асинхронных API-клиентов и многоуровневой системы безопасности.

## 🚀 Ключевые особенности

| Фича | Описание |
|---|---|
| 🤖 **12 Агентов** | Config, Market, Signal, Risk, Execution, Position, PnL, ML, Sentiment, Notification, Orchestrator |
| ⚡ **Async Trading** | Все биржевые API на `aiohttp` — никаких блокировок |
| 🔒 **Безопасность** | PBKDF2 + случайная соль, JWT в `httpOnly` cookies, rate limiting |
| 📊 **Multi-Exchange** | BingX (VST DEMO), Binance, Bybit, OKX |
| 📈 **Стратегии** | EMA Cross + ADX, Mean Reversion (RSI + Bollinger) |
| 🧪 **Тесты** | pytest + coverage, строгий CI/CD |

## 🏗️ Архитектура
