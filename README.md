# 📊 Kriterion Quant - Daily Market Analysis System


Sistema professionale di analisi quantitativa multi-asset sviluppato da **Kriterion Quant** per il monitoraggio giornaliero di 29 strumenti finanziari attraverso indicatori tecnici avanzati, scoring composito e regime detection.

---

## 🎯 Caratteristiche Principali

### 📈 Analisi Multi-Asset
- **29 Strumenti Finanziari**:
  - 6 Equity Indices (SPY, QQQ, IWM, DIA, EFA, EEM)
  - 9 Sector ETFs (XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLRE)
  - 4 Bond ETFs (TLT, IEF, HYG, LQD)
  - 4 Commodities (GLD, SLV, USO, UNG)
  - 3 Currencies (UUP, FXE, FXY)
  - 2 Crypto (BTC-USD, ETH-USD)
  - 1 Volatility Index (^VIX)

### 🔬 Indicatori Tecnici Avanzati
- **Trend**: SMA (20, 50, 125, 200 periodi)
- **Momentum**: RSI (14), MACD, ROC (10, 20, 60)
- **Volatility**: ATR (14), Bollinger Bands (20,2), Historical Volatility
- **Strength**: Z-Score multi-periodo, Relative Strength vs Benchmark
- **Trend Strength**: ADX (14)

### 🎯 Scoring System Composito
- **Weights Configurabili**:
  - Trend: 30%
  - Momentum: 30%
  - Volatility: 15%
  - Relative Strength: 25%
- **Range Score**: 0-100 (color-coded)

### 📡 Automazione Completa
- **Scheduling**: GitHub Actions (esecuzione automatica ore 08:00 IT)
- **Notifiche**: Bot Telegram con riassunto giornaliero
- **Dashboard**: Streamlit interattiva con grafici real-time

### 📊 Visualizzazione Professionale
- Grafici Candlestick interattivi (Plotly)
- Overlay tecnici (SMA, Bollinger Bands, Volume)
- Ranking tables (Top/Bottom 5)
- Market Regime indicators (VIX, SPY Trend)
- Export JSON per analisi LLM

---

## 🏗️ Architettura Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    EODHD API (Data Source)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Data Fetcher + Technical Indicators            │
│  (Rate Limiting, Retry Logic, SMA/RSI/MACD/ATR/BB/etc)     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Scoring System + Analysis                  │
│     (Composite Score, Market Regime, Signal Generation)     │
└─────────┬───────────────────────────────────┬───────────────┘
          │                                   │
          ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────────┐
│  Streamlit Dashboard │          │   Telegram Notifier      │
│  (Interactive UI)    │          │   (Daily Summary 08:00)  │
└──────────────────────┘          └──────────────────────────┘
          │                                   │
          ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────────┐
│   JSON Export        │          │   GitHub Actions         │
│   (LLM Analysis)     │          │   (Scheduling)           │
└──────────────────────┘          └──────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisiti
- Python 3.9+
- Account EODHD (API Key)
- Telegram Bot (opzionale per notifiche)
- GitHub Account (per deployment)
- Streamlit Cloud Account (per hosting)

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/kriterion-dma-system.git
cd kriterion-dma-system
```

### 2. Installazione Dipendenze
```bash
pip install -r requirements.txt
```

### 3. Configurazione Secrets

#### Per Sviluppo Locale
Crea file `.streamlit/secrets.toml`:
```toml
EODHD_API_KEY = "your_eodhd_api_key_here"
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"
TELEGRAM_CHAT_ID = "your_telegram_chat_id_here"
```

#### Per GitHub Actions
Vai su: `Settings → Secrets and variables → Actions → New repository secret`

Aggiungi:
- `EODHD_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

#### Per Streamlit Cloud
Durante il deployment, aggiungi i secrets in formato TOML nella sezione "Advanced settings".

### 4. Test Locale
```bash
streamlit run app.py
```

Apri browser su: `http://localhost:8501`

---

## 📦 Struttura Progetto

```
kriterion-dma-system/
├── .github/
│   └── workflows/
│       └── daily_analysis.yml       # GitHub Action per scheduling 08:00 IT
├── .streamlit/
│   ├── config.toml                  # Tema e configurazione UI
│   └── secrets.toml.example         # Template secrets
├── data/                            # (opzionale) Storage JSON storici
├── app.py                           # 🌟 MAIN - Dashboard Streamlit
├── config.py                        # Configurazione universo e parametri
├── data_fetcher.py                  # Download dati EODHD con rate limiting
├── technical_indicators.py          # Calcolo indicatori tecnici
├── scoring_system.py                # Sistema scoring composito
├── market_analysis.py               # Orchestrazione analisi + regime detection
├── chart_generator.py               # Generazione grafici Plotly
├── report_generator.py              # Export JSON/HTML
├── telegram_notifier.py             # Invio notifiche Telegram
├── scheduler.py                     # Script per GitHub Actions
├── utils.py                         # Helper functions
├── requirements.txt                 # Dipendenze Python
├── .gitignore                       # File da escludere
├── README.md                        # Questo file
├── DEPLOY_GUIDE.md                  # Guida deployment dettagliata
└── test_eodhd.py                    # Test connessione API (opzionale)
```

---

## 🔧 Configurazione Avanzata

### Modifica Universo Strumenti
Edita `config.py` → sezione `UNIVERSE`:
```python
UNIVERSE = {
    "AAPL": {"name": "Apple Inc.", "category": "Stock", "benchmark": "SPY"},
    # Aggiungi altri ticker...
}
```

### Personalizza Pesi Scoring
Edita `config.py` → sezione `CONFIG["WEIGHTS"]`:
```python
"WEIGHTS": {
    "TREND": 0.35,        # Default: 0.30
    "MOMENTUM": 0.35,     # Default: 0.30
    "VOLATILITY": 0.10,   # Default: 0.15
    "REL_STRENGTH": 0.20  # Default: 0.25
}
```

### Modifica Orario GitHub Action
Edita `.github/workflows/daily_analysis.yml`:
```yaml
schedule:
  - cron: '0 7 * * *'  # 08:00 IT (07:00 UTC) - Modifica come preferisci
```

---

## 📱 Setup Bot Telegram (Opzionale)

### 1. Crea Bot
1. Apri Telegram e cerca `@BotFather`
2. Invia `/newbot` e segui le istruzioni
3. Salva il **Bot Token** (es: `110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`)

### 2. Ottieni Chat ID
1. Aggiungi il bot ad una chat o gruppo
2. Invia un messaggio qualsiasi
3. Visita: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Trova il campo `"chat":{"id":123456789}` nel JSON

### 3. Configura Secrets
Aggiungi `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` nei secrets.

---

## 📊 Utilizzo Dashboard

### Sezioni Principali

#### 1. **Market Regime**
- **VIX Level**: Basso (<15), Medio (15-25), Alto (>25)
- **SPY Trend**: UPTREND (sopra SMA200) / DOWNTREND (sotto SMA200)
- **Top Sector**: Settore con score composito più alto

#### 2. **Rankings**
- **Top 5 Composite Score**: Strumenti più forti
- **Bottom 5 Composite Score**: Strumenti più deboli

#### 3. **Detailed Analysis**
Per ogni ticker:
- Price + Variazione 1D
- Scores (Composite, Trend, Momentum, Volatility, Rel. Strength)
- Segnali attivi (breakout, overbought, oversold, ecc.)
- Grafico interattivo candlestick con overlay tecnici

### Funzionalità Sidebar

#### 🔄 Refresh Data
Forza il download di dati aggiornati (bypassa cache)

#### 📥 Export JSON
Scarica file JSON strutturato per analisi LLM esterna:
```json
{
  "metadata": {...},
  "market_regime": {...},
  "instruments": {
    "SPY": {
      "info": {...},
      "current": {...},
      "indicators": {...},
      "scores": {...},
      "signals": [...]
    }
  },
  "rankings": {...}
}
```

---

## 🤖 Automazione GitHub Actions

Il sistema esegue automaticamente ogni giorno alle **08:00 IT**:

1. Download dati EODHD
2. Calcolo indicatori e scoring
3. Generazione report JSON
4. Invio summary su Telegram
5. (Opzionale) Commit JSON in `/data` per storico

### Workflow File
`.github/workflows/daily_analysis.yml` esegue:
```yaml
- Checkout repository
- Setup Python 3.9
- Install requirements
- Run scheduler.py (analisi + Telegram)
```

### Verifica Esecuzione
- GitHub → Actions tab → Vedi log ultima esecuzione
- Telegram → Ricevi messaggio ore 08:00

---

## 🎨 Personalizzazione UI

### Tema Colori
Edita `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1a365d"
backgroundColor = "#f7fafc"
secondaryBackgroundColor = "#ffffff"
textColor = "#2d3748"
font = "sans serif"
```

### Logo Custom
Aggiungi immagine in `/assets/logo.png` e modifica `app.py`:
```python
st.sidebar.image("assets/logo.png", width=200)
```

---

## 📈 Performance & Ottimizzazione

### Cache Streamlit
Il sistema utilizza `@st.cache_data` per:
- Download dati (TTL: 1 ora)
- Calcolo indicatori (TTL: 1 ora)
- Generazione grafici (TTL: 1 ora)

### Rate Limiting EODHD
Configurato in `config.py`:
```python
"REQUEST_DELAY_MIN": 0.5,      # Secondi tra richieste
"REQUEST_DELAY_MAX": 1.5,
"BATCH_SIZE": 5,               # Ticker per batch
"BATCH_DELAY_MIN": 3.0,        # Pausa tra batch
"MAX_RETRIES": 3
```

---

## 🐛 Troubleshooting

### Errore: "Invalid API Key"
- Verifica che `EODHD_API_KEY` sia corretto in secrets
- Controlla limiti piano EODHD (es: 20 richieste/sec su free tier)

### Errore: "Insufficient Data"
- Alcuni ticker potrebbero non avere storico sufficiente (>250 giorni)
- Sistema skippa automaticamente ticker problematici

### Grafici non si caricano
- Verifica connessione internet
- Controlla console browser per errori JavaScript
- Prova a ricaricare la pagina (Ctrl+F5)

### Telegram non invia messaggi
- Verifica `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`
- Controlla che il bot sia stato aggiunto alla chat
- Testa manualmente con: `python telegram_notifier.py`

---

## 📝 Roadmap Futuri Sviluppi

- [ ] Backtesting strategie basate su score composito
- [ ] Alert personalizzati via email
- [ ] Integrazione dati options (IV, Greeks)
- [ ] Sentiment analysis (news/social)
- [ ] Portfolio optimizer basato su scoring
- [ ] API REST per accesso programmatico
- [ ] Mobile app (React Native)
- [ ] Database PostgreSQL per storico analisi

---

## 🤝 Contributi

Contributi, issues e feature requests sono benvenuti!

1. Fork del progetto
2. Crea branch feature (`git checkout -b feature/AmazingFeature`)
3. Commit modifiche (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

---

## 📄 License

Questo progetto è rilasciato sotto licenza **MIT**. Vedi file `LICENSE` per dettagli.

---

## 👨‍💻 Autore

**Kriterion Quant**  
🌐 Website: [KriterionQuant.com](https://kriterionquant.com)  
📧 Email: info@kriterionquant.com  
💼 LinkedIn: [Kriterion Quant](https://linkedin.com/company/kriterion-quant)

---

## 🙏 Acknowledgments

- **EODHD** per i dati finanziari di qualità
- **Streamlit** per il framework UI eccellente
- **Plotly** per i grafici interattivi
- **Comunità quantitative finance** per feedback e best practices

---

## ⚠️ Disclaimer

Questo software è fornito **esclusivamente a scopo educativo e informativo**. 

**NON costituisce consulenza finanziaria**. Gli utenti sono responsabili delle proprie decisioni di investimento. Il trading comporta rischi significativi di perdita di capitale.

Kriterion Quant e i contributori non si assumono alcuna responsabilità per perdite derivanti dall'uso di questo sistema.

**USE AT YOUR OWN RISK.**

---

## 📞 Supporto

Per supporto tecnico o domande:
- 📧 Email: support@kriterionquant.com
- 💬 Discord: [Kriterion Quant Community](https://discord.gg/kriterion)
- 📖 Documentazione: [docs.kriterionquant.com](https://docs.kriterionquant.com)

---

<div align="center">

**Made with ❤️ by Kriterion Quant**

⭐ Se trovi utile questo progetto, lascia una stella su GitHub! ⭐

</div>
