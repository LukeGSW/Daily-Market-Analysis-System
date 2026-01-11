# 📊 Kriterion Quant - Daily Market Analysis System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.31+-red.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Sistema professionale di analisi quantitativa giornaliera per monitoraggio automatico di **29 strumenti finanziari** attraverso algoritmi di scoring multi-dimensionale e notifiche automatiche.

![Dashboard Preview](https://via.placeholder.com/800x400/1a365d/ffffff?text=Kriterion+Quant+DMA+Dashboard)

---

## 🎯 Overview

Il **Daily Market Analysis (DMA) System** è una piattaforma completa che combina:

- 📈 **Analisi Quantitativa** - 50+ indicatori tecnici custom
- 🤖 **Automazione Completa** - GitHub Actions + Telegram
- 📊 **Dashboard Interattiva** - Streamlit con grafici Plotly
- 🎯 **Scoring Multi-dimensionale** - Trend, Momentum, Volatility, Relative Strength
- 🌍 **Market Regime Detection** - VIX + SPY trend analysis
- 📱 **Notifiche Daily** - Summary formattati via Telegram

### Universo Analizzato (29 Strumenti)

| Categoria | Ticker | Descrizione |
|-----------|--------|-------------|
| **Equity Indices** (6) | SPY, QQQ, IWM, DIA, EFA, EEM | US + International |
| **Sectors** (9) | XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLRE | S&P sectors |
| **Bonds** (4) | TLT, IEF, HYG, LQD | Treasury + Corporate |
| **Commodities** (4) | GLD, SLV, USO, UNG | Metalli + Energia |
| **Volatility** (1) | ^VIX | CBOE VIX Index |
| **Currencies** (3) | UUP, FXE, FXY | USD, EUR, JPY |
| **Crypto** (2) | BTC-USD, ETH-USD | Bitcoin + Ethereum |

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-username/dma-system.git
cd dma-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit with your EODHD_API_KEY

# 4. Run Streamlit dashboard
streamlit run app.py
```

### First Run

1. Open browser at `http://localhost:8501`
2. Wait for initial data load (~5-10 minutes)
3. Explore dashboard sections:
   - Market Regime Overview
   - Top/Bottom Rankings
   - Detailed Instrument Analysis

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     KRITERION QUANT DMA SYSTEM                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
           ┌────────▼────────┐       ┌───────▼────────┐
           │   STREAMLIT     │       │ GITHUB ACTIONS │
           │   DASHBOARD     │       │   SCHEDULER    │
           └────────┬────────┘       └───────┬────────┘
                    │                        │
                    └────────────┬───────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   MARKET ANALYSIS       │
                    │   (Orchestration)       │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
    ┌────▼─────┐        ┌───────▼────────┐      ┌──────▼──────┐
    │  DATA    │        │  TECHNICAL     │      │  SCORING    │
    │ FETCHER  │───────▶│  INDICATORS    │─────▶│   SYSTEM    │
    │ (EODHD)  │        │  (50+ Calcs)   │      │ (4 Scores)  │
    └──────────┘        └────────────────┘      └──────┬──────┘
                                                        │
                         ┌──────────────────────────────┤
                         │                              │
                  ┌──────▼──────┐              ┌────────▼────────┐
                  │   CHART     │              │    REPORT       │
                  │ GENERATOR   │              │   GENERATOR     │
                  │  (Plotly)   │              │  (JSON+HTML)    │
                  └─────────────┘              └─────────────────┘
```

---

## ✨ Features

### 📊 Analisi Quantitativa

**50+ Indicatori Tecnici:**
- Trend: SMA (20/50/125/200)
- Momentum: RSI, MACD, ROC
- Volatility: ATR, Bollinger Bands, Historical Vol
- Volume: OBV, Volume Ratio
- Support/Resistance: Pivot Points

**Scoring Multi-dimensionale (0-100):**
- **Trend** (30%): Price vs SMA, slope, alignment
- **Momentum** (30%): RSI, MACD, ROC multi-period
- **Volatility** (15%): ATR%, BB width, HVol (invertito)
- **Relative Strength** (25%): Performance vs benchmark

**Market Regime Detection:**
- VIX: Low (<15), Medium (15-25), High (>25)
- SPY: Uptrend/Downtrend vs SMA200
- Conditions: Bullish, Bearish, Volatile_Bullish, Quiet_Bearish, Neutral

### 🔔 Signal Generation

8 tipi automatici:
1. Price breakout (weekly high/low)
2. RSI extremes (>80, <20)
3. Bollinger Band breakout
4. Volume surge (>2x)
5. Gap up/down (>2%)
6. MACD crossover
7. Golden/Death Cross (SMA 50/200)
8. Strong trend (ADX >25)

### 🤖 Automazione

- **GitHub Actions**: Daily execution ore 08:00 IT
- **Telegram Bot**: Summary formattato automatico
- **Report Generation**: JSON (LLM-ready) + HTML (dashboard)
- **Artifact Storage**: 90 giorni retention

### 📱 Dashboard Features

- Market regime overview (3 metrics)
- Top/Bottom 5 performers
- Detailed analysis per instrument:
  - Score boxes colorati
  - Active signals
  - Interactive Plotly charts
- Category filtering
- View modes: Expandable/Tabs
- JSON export
- Telegram integration

---

## 📁 Project Structure

```
dma-system/
├── app.py                      # Streamlit dashboard (800 LOC)
├── scheduler.py                # GitHub Actions script (350 LOC)
├── config.py                   # Configuration (250 LOC)
│
├── 📊 Data & Analysis
│   ├── data_fetcher.py        # EODHD integration (400 LOC)
│   ├── technical_indicators.py # 50+ indicators (600 LOC)
│   ├── scoring_system.py      # Scoring algorithms (500 LOC)
│   └── market_analysis.py     # Orchestration (450 LOC)
│
├── 📈 Visualization & Output
│   ├── chart_generator.py     # Plotly charts (400 LOC)
│   ├── report_generator.py    # JSON/HTML (600 LOC)
│   ├── telegram_notifier.py   # Telegram bot (400 LOC)
│   └── utils.py               # Helpers (500 LOC)
│
├── ⚙️ Configuration
│   ├── requirements.txt
│   ├── .gitignore
│   ├── .streamlit/
│   │   ├── config.toml        # Theme
│   │   └── secrets.toml.example
│   └── .github/workflows/
│       └── daily_analysis.yml
│
└── 📚 Documentation
    ├── README.md              # This file
    └── DEPLOY_GUIDE.md        # Deployment instructions
```

**Total:** ~5,250 LOC (senza commenti)

---

## 🚢 Deployment

### Streamlit Cloud

```bash
1. Push to GitHub
2. Go to share.streamlit.io
3. New app → Select repository
4. Configure secrets (TOML format)
5. Deploy automatically
```

**Access:** `https://your-username-dma-system.streamlit.app`

### GitHub Actions

```bash
1. Add secrets to repository
   Settings → Secrets → Actions
   - EODHD_API_KEY (required)
   - TELEGRAM_BOT_TOKEN (optional)
   - TELEGRAM_CHAT_ID (optional)

2. Workflow runs daily at 07:00 UTC
   (08:00 Italy time)

3. Manual trigger:
   Actions → Daily Market Analysis → Run workflow
```

**📖 Full guide:** [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)

---

## 🔧 Configuration

### Customize Universe

Edit `config.py`:

```python
UNIVERSE = {
    'YOUR_TICKER': {
        'name': 'Description',
        'category': 'Equity Index',  # or Sector, Bond, etc
        'benchmark': 'SPY',
        'eodhd_exchange': 'US'  # US, CC, INDX
    },
    # Add more...
}
```

### Adjust Parameters

```python
CONFIG = {
    'SMA_PERIODS': [20, 50, 125, 200],
    'RSI_PERIOD': 14,
    'LOOKBACK_DAYS': 400,  # Data history
    'WEIGHTS': {
        'TREND': 0.30,
        'MOMENTUM': 0.30,
        'VOLATILITY': 0.15,
        'REL_STRENGTH': 0.25
    }
}
```

---

## 📊 Usage Examples

### Command Line

```bash
# Full analysis
python scheduler.py

# Skip Telegram
python scheduler.py --no-telegram

# Skip reports
python scheduler.py --no-reports

# Commit to git
python scheduler.py --commit

# Help
python scheduler.py --help
```

### Streamlit Dashboard

```python
# Launch
streamlit run app.py

# Features:
# - 🔄 Refresh Data (clear cache)
# - 📥 Export JSON
# - 📱 Send Telegram
# - 🔍 Filter by category
# - 📊 Expandable/Tabs view
```

### Telegram Bot

```
📊 KRITERION QUANT - Daily Market Analysis
📅 2024-12-31

🌍 MARKET REGIME
🟢 VIX: 14.50 (LOW)
📈 SPY: UPTREND (Above SMA200)
💼 Condition: Bullish

🏆 TOP 5 PERFORMERS
🟢 `QQQ   ` Score: 75.0 (Trend: 80)
...

🔔 CRITICAL SIGNALS
• QQQ (3 signals):
  → MACD Bullish Crossover
  → Volume Surge (2.5x)
```

---

## 🧪 Testing

```bash
# Test modules individually
python config.py                # Config validation
python data_fetcher.py          # EODHD connection
python technical_indicators.py  # Indicator calculations
python scoring_system.py        # Scoring algorithms
python chart_generator.py       # Chart generation
python telegram_notifier.py     # Telegram bot

# Integration test
python scheduler.py --no-telegram

# Expected:
# ✅ 28-29 ticker downloaded
# ✅ 50+ indicators calculated
# ✅ 5 scores per instrument
# ✅ Market regime detected
# ✅ Signals generated
# ✅ Reports saved
# ⏱️ ~5-7 minutes total
```

---

## 📈 Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Execution Time** | 5-7 min | Full analysis 29 ticker |
| **RAM Usage** | 500-800 MB | Peak during analysis |
| **API Calls** | 30-35 | EODHD requests |
| **Data Volume** | ~10 MB | Per ticker (400 days) |
| **Cache TTL** | 1 hour | Streamlit caching |

**Optimization:**
- Reduce `LOOKBACK_DAYS` (400 → 200)
- Increase `REQUEST_DELAY` (0.5s → 1s)
- Remove less important tickers
- Extend cache TTL (1h → 2h)

---

## 🔒 Security

### Secrets Management

❌ **NEVER commit:**
- API keys
- Bot tokens
- `.streamlit/secrets.toml`
- `.env` files

✅ **Use:**
- GitHub Secrets (Actions)
- Streamlit Secrets (Cloud)
- Environment variables (local)

### API Key Security

```bash
# Check .gitignore
cat .gitignore | grep secrets

# Verify no secrets in commits
git log --all | grep -i "api"

# Rotate keys periodically
```

---

## 🔧 Troubleshooting

### EODHD API Errors

**401 Unauthorized:**
```bash
# Check key
python -c "from config import SECRETS; print(SECRETS.get('EODHD_API_KEY'))"
```

**Rate Limit:**
```
Free: 20 req/day (insufficient)
Need: 30-35 req
Solution: Upgrade $9.99/month
```

### Streamlit Issues

**Won't Deploy:**
- Check requirements.txt syntax
- Verify secrets TOML format
- Review deployment logs

**Out of Memory:**
```python
# config.py
LOOKBACK_DAYS = 200  # Reduce from 400
```

### Charts Not Displaying

```bash
# Check Plotly version
pip show plotly

# Browser console
F12 → Console → Check errors
```

**📖 Full guide:** [DEPLOY_GUIDE.md#troubleshooting](DEPLOY_GUIDE.md#troubleshooting)

---

## 📚 Documentation

- **Main Guide**: This README
- **Deployment**: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)
- **Code Comments**: Inline docstrings
- **Test Scripts**: `if __name__ == "__main__"` blocks

---

## 🤝 Contributing

Contributions welcome!

```bash
1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request
```

**Guidelines:**
- Follow existing code style
- Add tests for features
- Update documentation

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

**Summary:**
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ❌ Liability
- ❌ Warranty

---

## ⚠️ Disclaimer

**EDUCATIONAL PURPOSE ONLY**

- ❌ NOT financial advice
- ❌ NOT investment recommendations
- ❌ NOT trading signals

**Risk Warning:**
- Trading involves substantial risk
- Past performance ≠ future results
- Consult licensed advisor
- Use at your own risk

---

## 🙏 Acknowledgments

**Technologies:**
- [Streamlit](https://streamlit.io) - Dashboard
- [Plotly](https://plotly.com) - Charts
- [Pandas](https://pandas.pydata.org) - Data analysis
- [EODHD](https://eodhistoricaldata.com) - Financial data
- [GitHub Actions](https://github.com/features/actions) - Automation
- [Telegram](https://telegram.org) - Notifications

---

## 📞 Support

### Help

- **Issues**: [GitHub Issues](https://github.com/your-username/dma-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/dma-system/discussions)
- **Email**: support@kriterionquant.com

### Community

- **Website**: https://kriterionquant.com
- **Telegram**: [@KriterionQuant](https://t.me/kriterionquant)
- **Twitter**: [@KriterionQuant](https://twitter.com/kriterionquant)

---

## 📊 Project Stats

![GitHub stars](https://img.shields.io/github/stars/your-username/dma-system?style=social)
![GitHub forks](https://img.shields.io/github/forks/your-username/dma-system?style=social)

- **Lines of Code**: ~5,250
- **Files**: 19
- **Modules**: 11
- **Documentation**: 2 guides

---

## 🎓 About Kriterion Quant

Piattaforma educativa per finanza quantitativa e trading sistematico.

**Mission:** Democratizzare strumenti quantitativi professionali.

**Offerings:**
- Educational content
- Open-source tools
- Quantitative research
- Training courses

**Learn More:** https://kriterionquant.com

---

<div align="center">

**Made with ❤️ by Kriterion Quant**

⭐ **Star this repo if useful!** ⭐

[Website](https://kriterionquant.com) | [GitHub](https://github.com/your-username) | [Twitter](https://twitter.com/kriterionquant)

*Version 1.0.0 - Last updated: 2024-12-31*

</div>
