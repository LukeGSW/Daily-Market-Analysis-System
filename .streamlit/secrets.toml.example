# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Configuration Module
============================================================================
Definisce:
- Universo strumenti finanziari (29 ticker)
- Parametri operativi (rate limiting, lookback, etc)
- Configurazione indicatori tecnici
- Gestione secrets (EODHD API, Telegram)
============================================================================
"""

import os
import sys
from typing import Dict, Any

# ============================================================================
# SECRETS MANAGEMENT
# ============================================================================

def load_secrets() -> Dict[str, str]:
    """
    Carica secrets da Streamlit secrets.toml oppure da variabili ambiente.
    
    Priority:
    1. Streamlit secrets (st.secrets)
    2. Environment variables
    3. Fallback per testing locale
    
    Returns:
        Dict con EODHD_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    """
    secrets = {}
    
    # Try Streamlit secrets first
    try:
        import streamlit as st
        secrets['EODHD_API_KEY'] = st.secrets.get('EODHD_API_KEY', '')
        secrets['TELEGRAM_BOT_TOKEN'] = st.secrets.get('TELEGRAM_BOT_TOKEN', '')
        secrets['TELEGRAM_CHAT_ID'] = st.secrets.get('TELEGRAM_CHAT_ID', '')
        print("✅ Secrets caricati da Streamlit secrets.toml")
    except:
        # Fallback to environment variables
        secrets['EODHD_API_KEY'] = os.getenv('EODHD_API_KEY', '')
        secrets['TELEGRAM_BOT_TOKEN'] = os.getenv('TELEGRAM_BOT_TOKEN', '')
        secrets['TELEGRAM_CHAT_ID'] = os.getenv('TELEGRAM_CHAT_ID', '')
        print("✅ Secrets caricati da variabili ambiente")
    
    # Validation
    if not secrets['EODHD_API_KEY']:
        print("⚠️ WARNING: EODHD_API_KEY non configurata!")
    
    return secrets

# Carica secrets all'import del modulo
SECRETS = load_secrets()

# ============================================================================
# UNIVERSO STRUMENTI FINANZIARI (29 TICKER)
# ============================================================================

UNIVERSE = {
    # --- EQUITY INDICES (6) ---
    "SPY": {
        "name": "S&P 500 ETF",
        "category": "Equity Index",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "QQQ": {
        "name": "Nasdaq 100 ETF",
        "category": "Equity Index",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "IWM": {
        "name": "Russell 2000 ETF",
        "category": "Equity Index",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "DIA": {
        "name": "Dow Jones ETF",
        "category": "Equity Index",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "EFA": {
        "name": "EAFE Markets ETF",
        "category": "Equity Index",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "EEM": {
        "name": "Emerging Markets ETF",
        "category": "Equity Index",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },

    # --- SECTORS (9) ---
    "XLK": {
        "name": "Technology Select",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLF": {
        "name": "Financial Select",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLE": {
        "name": "Energy Select",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLV": {
        "name": "Health Care Select",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLI": {
        "name": "Industrial Select",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLY": {
        "name": "Consumer Discretionary",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLP": {
        "name": "Consumer Staples",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLU": {
        "name": "Utilities Select",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "XLRE": {
        "name": "Real Estate Select",
        "category": "Sector",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },

    # --- BONDS (4) ---
    "TLT": {
        "name": "20+ Year Treasury",
        "category": "Bond",
        "benchmark": "IEF",
        "eodhd_exchange": "US"
    },
    "IEF": {
        "name": "7-10 Year Treasury",
        "category": "Bond",
        "benchmark": "IEF",
        "eodhd_exchange": "US"
    },
    "HYG": {
        "name": "High Yield Corporate",
        "category": "Bond",
        "benchmark": "LQD",
        "eodhd_exchange": "US"
    },
    "LQD": {
        "name": "Investment Grade Corp",
        "category": "Bond",
        "benchmark": "IEF",
        "eodhd_exchange": "US"
    },

    # --- COMMODITIES (4) ---
    "GLD": {
        "name": "Gold ETF",
        "category": "Commodity",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "SLV": {
        "name": "Silver ETF",
        "category": "Commodity",
        "benchmark": "GLD",
        "eodhd_exchange": "US"
    },
    "USO": {
        "name": "Oil Fund",
        "category": "Commodity",
        "benchmark": "SPY",
        "eodhd_exchange": "US"
    },
    "UNG": {
        "name": "Natural Gas Fund",
        "category": "Commodity",
        "benchmark": "USO",
        "eodhd_exchange": "US"
    },

    # --- VOLATILITY (1) ---
    "^VIX": {
        "name": "CBOE Volatility Index",
        "category": "Volatility",
        "benchmark": "N/A",
        "eodhd_exchange": "INDX"  # Index exchange su EODHD
    },

    # --- CURRENCIES (3) ---
    "UUP": {
        "name": "US Dollar Index ETF",
        "category": "Currency",
        "benchmark": "N/A",
        "eodhd_exchange": "US"
    },
    "FXE": {
        "name": "Euro ETF",
        "category": "Currency",
        "benchmark": "UUP",
        "eodhd_exchange": "US"
    },
    "FXY": {
        "name": "Yen ETF",
        "category": "Currency",
        "benchmark": "UUP",
        "eodhd_exchange": "US"
    },

    # --- CRYPTO (2) ---
    "BTC-USD": {
        "name": "Bitcoin",
        "category": "Crypto",
        "benchmark": "SPY",
        "eodhd_exchange": "CC"  # Cryptocurrency exchange
    },
    "ETH-USD": {
        "name": "Ethereum",
        "category": "Crypto",
        "benchmark": "BTC-USD",
        "eodhd_exchange": "CC"
    },
}

# ============================================================================
# PARAMETRI OPERATIVI
# ============================================================================

CONFIG = {
    # --- DATA REQUIREMENTS ---
    "DATA_LOOKBACK_DAYS": 400,       # Giorni storici da scaricare
    "MIN_REQUIRED_ROWS": 250,        # Minimo righe per analisi valida
    "CHART_LOOKBACK_DAYS": 252,      # Giorni da visualizzare nei grafici
    
    # --- EODHD API RATE LIMITING ---
    # EODHD Free Tier: 20 req/sec, 100k/month
    # EODHD Paid Tier: 1000 req/sec+
    "REQUEST_DELAY_MIN": 0.5,        # Secondi tra richieste (conservative)
    "REQUEST_DELAY_MAX": 1.5,        # Max delay per variabilità
    "BATCH_SIZE": 5,                 # Ticker per batch
    "BATCH_DELAY_MIN": 3.0,          # Pausa tra batch (sec)
    "BATCH_DELAY_MAX": 5.0,          # Max pausa batch
    "MAX_RETRIES": 3,                # Retry su errore
    "TIMEOUT": 30,                   # Timeout richiesta HTTP (sec)
    
    # --- TECHNICAL INDICATORS PARAMETERS ---
    # Simple Moving Averages
    "SMA_PERIODS": [20, 50, 125, 200],
    
    # RSI (Relative Strength Index)
    "RSI_PERIOD": 14,
    "RSI_OVERBOUGHT": 70,
    "RSI_OVERSOLD": 30,
    
    # ATR (Average True Range)
    "ATR_PERIOD": 14,
    
    # Bollinger Bands
    "BB_PERIOD": 20,
    "BB_STD": 2.0,
    
    # MACD (Moving Average Convergence Divergence)
    "MACD_FAST": 12,
    "MACD_SLOW": 26,
    "MACD_SIGNAL": 9,
    
    # ADX (Average Directional Index)
    "ADX_PERIOD": 14,
    "ADX_STRONG_TREND": 25,
    
    # Rate of Change
    "ROC_PERIODS": [10, 20, 60],
    
    # Z-Score (Statistical)
    "ZSCORE_PERIODS": [20, 50, 125],
    
    # Historical Volatility
    "HVOL_PERIODS": [20, 60],
    
    # --- SCORING SYSTEM WEIGHTS ---
    "WEIGHTS": {
        "TREND": 0.30,           # Peso score trend
        "MOMENTUM": 0.30,        # Peso score momentum
        "VOLATILITY": 0.15,      # Peso score volatility (invertito)
        "REL_STRENGTH": 0.25     # Peso relative strength vs benchmark
    },
    
    # --- MARKET REGIME THRESHOLDS ---
    "VIX_LOW": 15,              # VIX < 15 = regime bassa volatilità
    "VIX_MEDIUM": 25,           # 15-25 = media volatilità
    # VIX > 25 = alta volatilità
    
    # --- SIGNAL GENERATION ---
    "SIGNAL_THRESHOLDS": {
        "RSI_EXTREME_OB": 80,   # RSI extremely overbought
        "RSI_EXTREME_OS": 20,   # RSI extremely oversold
        "BB_BREAKOUT": 0.02,    # % oltre banda per segnale breakout
        "VOLUME_SURGE": 2.0,    # Multiplo volume medio per surge
        "GAP_THRESHOLD": 0.02,  # Gap % per segnale gap up/down
    },
    
    # --- VISUAL STYLING (Kriterion Quant Colors) ---
    "COLORS": {
        "PRIMARY": ["#1a365d", "#2d3748", "#4a5568"],
        "ACCENT_GREEN": "#38a169",
        "ACCENT_RED": "#e53e3e",
        "ACCENT_ORANGE": "#d69e2e",
        "BG": "#f7fafc",
        "CARD_BG": "#ffffff",
        "SMA_50": "#3182ce",
        "SMA_200": "#dd6b20",
        "CANDLE_UP": "#38a169",
        "CANDLE_DOWN": "#e53e3e",
        # Score color mapping
        "SCORE_EXCELLENT": "#38a169",  # Verde scuro (70-100)
        "SCORE_GOOD": "#48bb78",       # Verde chiaro (55-70)
        "SCORE_NEUTRAL": "#d69e2e",    # Arancio (40-55)
        "SCORE_POOR": "#ed8936",       # Arancio scuro (25-40)
        "SCORE_BAD": "#e53e3e",        # Rosso (0-25)
    },
    
    # --- EODHD API ENDPOINTS ---
    "EODHD_BASE_URL": "https://eodhistoricaldata.com/api",
    "EODHD_EOD_ENDPOINT": "/eod",           # End-of-day data
    "EODHD_REALTIME_ENDPOINT": "/real-time", # Real-time quote
    
    # --- TELEGRAM SETTINGS ---
    "TELEGRAM_DAILY_HOUR": 8,      # Ora invio messaggio (08:00 IT)
    "TELEGRAM_TIMEZONE": "Europe/Rome",
    "TELEGRAM_MAX_MESSAGE_LENGTH": 4096,  # Telegram limit
    
    # --- CACHE SETTINGS ---
    "CACHE_TTL_SECONDS": 3600,     # 1 ora cache Streamlit
    
    # --- EXPORT SETTINGS ---
    "JSON_INDENT": 2,
    "HTML_TEMPLATE_NAME": "dma_report_template.html",
}

# ============================================================================
# VALIDAZIONE CONFIGURAZIONE
# ============================================================================

def validate_config() -> bool:
    """
    Valida la configurazione e l'universo strumenti.
    
    Returns:
        True se configurazione valida, False altrimenti
    """
    errors = []
    
    # Check universo
    if len(UNIVERSE) < 29:
        errors.append(f"UNIVERSO deve contenere almeno 29 ticker, trovati {len(UNIVERSE)}")
    
    # Check pesi scoring sommano a 1.0
    total_weight = sum(CONFIG['WEIGHTS'].values())
    if abs(total_weight - 1.0) > 0.01:
        errors.append(f"WEIGHTS devono sommare a 1.0, somma attuale: {total_weight}")
    
    # Check secrets critici
    if not SECRETS.get('EODHD_API_KEY'):
        errors.append("EODHD_API_KEY non configurata - richiesta per data fetching")
    
    # Log errori
    if errors:
        print("❌ ERRORI CONFIGURAZIONE:")
        for err in errors:
            print(f"   - {err}")
        return False
    
    print("✅ Configurazione validata con successo")
    return True

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_ticker_info(ticker: str) -> Dict[str, Any]:
    """
    Recupera informazioni per un ticker specifico.
    
    Args:
        ticker: Symbol ticker (es. "SPY")
    
    Returns:
        Dict con info ticker o None se non trovato
    """
    return UNIVERSE.get(ticker)

def get_tickers_by_category(category: str) -> list:
    """
    Filtra ticker per categoria.
    
    Args:
        category: "Equity Index", "Sector", "Bond", etc.
    
    Returns:
        Lista ticker della categoria
    """
    return [t for t, info in UNIVERSE.items() if info['category'] == category]

def get_all_categories() -> list:
    """Ritorna lista di tutte le categorie presenti."""
    return list(set(info['category'] for info in UNIVERSE.values()))

def get_color_for_score(score: float) -> str:
    """
    Mappa score (0-100) a colore appropriato.
    
    Args:
        score: Score numerico 0-100
    
    Returns:
        Hex color code
    """
    if score >= 70:
        return CONFIG['COLORS']['SCORE_EXCELLENT']
    elif score >= 55:
        return CONFIG['COLORS']['SCORE_GOOD']
    elif score >= 40:
        return CONFIG['COLORS']['SCORE_NEUTRAL']
    elif score >= 25:
        return CONFIG['COLORS']['SCORE_POOR']
    else:
        return CONFIG['COLORS']['SCORE_BAD']

# ============================================================================
# AUTO-VALIDATION ON IMPORT
# ============================================================================

if __name__ != "__main__":
    # Valida automaticamente quando importato (ma non quando eseguito direttamente)
    validate_config()

# ============================================================================
# TEST SCRIPT (esegui con: python config.py)
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Configuration Test")
    print("="*70)
    
    # Test validazione
    print("\n1. Validazione configurazione:")
    validate_config()
    
    # Test secrets
    print("\n2. Secrets Status:")
    print(f"   EODHD_API_KEY: {'✅ Configurata' if SECRETS.get('EODHD_API_KEY') else '❌ Mancante'}")
    print(f"   TELEGRAM_BOT_TOKEN: {'✅ Configurata' if SECRETS.get('TELEGRAM_BOT_TOKEN') else '⚠️ Opzionale'}")
    print(f"   TELEGRAM_CHAT_ID: {'✅ Configurata' if SECRETS.get('TELEGRAM_CHAT_ID') else '⚠️ Opzionale'}")
    
    # Test universo
    print(f"\n3. Universo Strumenti:")
    print(f"   Totale ticker: {len(UNIVERSE)}")
    for cat in get_all_categories():
        tickers = get_tickers_by_category(cat)
        print(f"   - {cat}: {len(tickers)} ticker")
    
    # Test color mapping
    print(f"\n4. Test Color Mapping:")
    test_scores = [90, 65, 50, 35, 15]
    for score in test_scores:
        color = get_color_for_score(score)
        print(f"   Score {score} → {color}")
    
    print("\n" + "="*70)
    print("✅ Test completato")
