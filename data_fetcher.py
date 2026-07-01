# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Data Fetcher Module - Hybrid (EODHD + Yahoo Finance)
============================================================================
Gestisce:
- Download dati storici da EODHD API (azioni/ETF/indici, incluso VIX.INDX)
- Yahoo Finance usato solo come fallback per il VIX se EODHD non risponde
- Rate limiting intelligente e Retry logic
- Normalizzazione dati
- LOGICA SMART: Richiede dati fino a OGGI, ma li valida rigorosamente.
============================================================================
"""

import requests
import pandas as pd
import numpy as np
import time
import random
import yfinance as yf
import pytz  # Necessario per il fuso orario
from datetime import datetime, timedelta, date, time as dt_time
from typing import Dict, List, Optional, Tuple
import logging

from config import CONFIG, SECRETS, UNIVERSE

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# YAHOO FINANCE HELPER
# ============================================================================

def fetch_from_yahoo(ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    Scarica dati da Yahoo Finance e li normalizza nel formato EODHD.
    Usa 'history' con periodo lungo per evitare buchi nei dati dovuti a feste.
    """
    try:
        logger.info(f"📥 Fetching {ticker} via Yahoo Finance (Max History)...")
        
        # --- FIX: Usiamo history(period="10y") ---
        # Questo garantisce di avere l'ultima candela disponibile (anche di oggi)
        # bypassando problemi di calcolo date e festività.
        
        yf_ticker_name = ticker
        if ticker == "VIX" or (ticker == "^VIX"):
            yf_ticker_name = "^VIX"
            
        ticker_obj = yf.Ticker(yf_ticker_name)
        df = ticker_obj.history(period="10y", auto_adjust=False)
        
        if df.empty:
            logger.warning(f"⚠️ Yahoo Finance ha restituito DataFrame vuoto per {ticker}")
            return None

        # Reset index per avere 'Date' come colonna
        df = df.reset_index()
        
        # Rinomina colonna data se necessario
        if 'Date' not in df.columns and 'index' in df.columns:
            df.rename(columns={'index': 'Date'}, inplace=True)

        # Assicurati formattazione Date e rimozione timezone
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        # Filtro manuale della data di inizio
        df = df[df['Date'] >= pd.to_datetime(start_date)]
        
        # Normalizzazione nomi colonne
        df = df.rename(columns={
            'Open': 'Open', 'High': 'High', 'Low': 'Low', 
            'Close': 'Close', 'Adj Close': 'Adj Close', 'Volume': 'Volume'
        })

        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        
        # Yahoo a volte non ha Volume per indici
        if 'Volume' not in df.columns:
            df['Volume'] = 0
            
        # Aggiungi Adj Close se manca
        if 'Adj Close' not in df.columns:
            df['Adj Close'] = df['Close']
            
        # Verifica colonne presenti
        available_cols = [c for c in required_cols + ['Adj Close'] if c in df.columns]
        df = df[available_cols].copy()
            
        # Ordina per data
        df = df.sort_values('Date').reset_index(drop=True)
        
        logger.info(f"✅ {ticker} (Yahoo): {len(df)} righe scaricate (Ultima: {df['Date'].iloc[-1].date()})")
        return df

    except Exception as e:
        logger.error(f"❌ Errore Yahoo Finance per {ticker}: {str(e)}")
        return None

# ============================================================================
# EODHD API CLIENT
# ============================================================================

class EODHDClient:
    """Client per interagire con EODHD API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or SECRETS.get('EODHD_API_KEY', '')
        
        if not self.api_key:
            logger.warning("⚠️ EODHD_API_KEY non configurata. I download da EODHD falliranno.")
        
        self.base_url = CONFIG['EODHD_BASE_URL']
        self.timeout = CONFIG['TIMEOUT']
        self.max_retries = CONFIG['MAX_RETRIES']
        
        self.request_delay_min = CONFIG['REQUEST_DELAY_MIN']
        self.request_delay_max = CONFIG['REQUEST_DELAY_MAX']
        self.last_request_time = 0
    
    def _apply_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.request_delay_min, self.request_delay_max)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: dict, attempt: int = 1) -> Optional[dict]:
        if not self.api_key: return None
        try:
            self._apply_rate_limit()
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429: # Rate limit
                time.sleep(60 * attempt)
                return self._make_request(url, params, attempt + 1) if attempt < self.max_retries else None
            elif response.status_code >= 500:
                time.sleep(2 ** attempt)
                return self._make_request(url, params, attempt + 1) if attempt < self.max_retries else None
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"❌ Errore richiesta: {str(e)}")
            return None
    
    def get_eod_data(self, ticker: str, exchange: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        symbol = f"{ticker}.{exchange}"
        url = f"{self.base_url}/eod/{symbol}"
        
        params = {
            'api_token': self.api_key,
            'from': start_date,
            'to': end_date,
            'fmt': 'json',
            'period': 'd'
        }
        
        logger.info(f"📥 Fetching {symbol} (EODHD) from {start_date} to {end_date}")
        data = self._make_request(url, params)
        
        if not data: return None
        
        try:
            df = pd.DataFrame(data)
            if df.empty: return None

            # Alcuni strumenti (es. indici come VIX.INDX) possono non avere
            # tutte le colonne standard: le creiamo per sicurezza.
            if 'adjusted_close' not in df.columns:
                df['adjusted_close'] = df['close']
            if 'volume' not in df.columns:
                df['volume'] = 0

            # Conversione numerica
            for col in ['close', 'adjusted_close', 'open', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Calcolo Adjusted Factor
            adj_factor = df['adjusted_close'] / df['close']
            adj_factor = adj_factor.fillna(1.0)
            
            # Rettifica OHLC
            df['Close'] = df['adjusted_close']
            df['Open'] = df['open'] * adj_factor
            df['High'] = df['high'] * adj_factor
            df['Low'] = df['low'] * adj_factor
            
            df['Date'] = pd.to_datetime(df['date'])
            df['Volume'] = df['volume']
            df['Adj Close'] = df['adjusted_close']
            
            return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']].sort_values('Date').reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"❌ Errore conversione DataFrame per {symbol}: {str(e)}")
            return None

# ============================================================================
# HIGH-LEVEL FETCHING FUNCTIONS
# ============================================================================

def download_ticker_data(ticker: str, start_date: str, end_date: str, retries: int = 3) -> Optional[pd.DataFrame]:
    ticker_info = UNIVERSE.get(ticker)
    if not ticker_info: return None

    exchange = ticker_info.get('eodhd_exchange', 'US')
    # Il simbolo EODHD non usa il prefisso '^' (es. VIX.INDX, non ^VIX.INDX)
    eodhd_ticker = ticker.lstrip('^')

    client = EODHDClient()
    df = client.get_eod_data(eodhd_ticker, exchange, start_date, end_date)

    # Fallback su Yahoo solo per il VIX, nel raro caso in cui EODHD non risponda
    if (df is None or df.empty) and ticker in ("^VIX", "VIX"):
        logger.warning("⚠️ VIX non disponibile da EODHD, provo fallback Yahoo Finance...")
        df = fetch_from_yahoo(ticker, start_date, end_date)

    return df

def download_universe_data(start_date: str, end_date: str, progress_callback=None) -> Dict[str, pd.DataFrame]:
    logger.info(f"🚀 Avvio download universo ({len(UNIVERSE)} ticker)")
    results, failed = {}, []
    tickers = list(UNIVERSE.keys())
    
    for i, ticker in enumerate(tickers, 1):
        if progress_callback: progress_callback(i, len(tickers), ticker)
        
        try:
            df = download_ticker_data(ticker, start_date, end_date)
            
            if df is not None and not df.empty:
                # --- CRITICAL STEP: CLEAN & VALIDATE ---
                # Qui avviene la magia: df potrebbe contenere oggi, clean_dataframe decide se tenerlo
                df = clean_dataframe(df)
                
                if validate_dataframe(df, ticker):
                    results[ticker] = df
                else:
                    failed.append(ticker)
            else:
                failed.append(ticker)
            
            if i % CONFIG['BATCH_SIZE'] == 0:
                time.sleep(random.uniform(CONFIG['BATCH_DELAY_MIN'], CONFIG['BATCH_DELAY_MAX']))
                
        except Exception as e:
            logger.error(f"❌ Errore download {ticker}: {e}")
            failed.append(ticker)
            
    logger.info(f"✅ Download completato: {len(results)}/{len(tickers)} ticker OK")
    return results

def get_date_range_for_analysis() -> Tuple[str, str]:
    """
    Calcola range date per analisi.
    """
    # --- FIX CRUCIALE ---
    # Prima era: datetime.now() - timedelta(days=1) -> Fermava la richiesta a Ieri.
    # Ora è: datetime.now() -> Richiede fino a Oggi.
    # Sarà poi 'clean_dataframe' a scartare Oggi se il mercato è aperto.
    end_date = datetime.now()
    
    lookback_days = CONFIG['DATA_LOOKBACK_DAYS']
    start_date = end_date - timedelta(days=lookback_days)
    
    return (
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )

def validate_dataframe(df: pd.DataFrame, ticker: str) -> bool:
    if df is None or df.empty: return False
    if len(df) < CONFIG['MIN_REQUIRED_ROWS']: return False
    return True

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pulisce il DataFrame.
    LOGICA SMART PER LA DATA ODIERNA (NY Time):
    - Se ora NY < 16:15: Rimuove i dati di oggi (candela incompleta).
    - Se ora NY >= 16:15: Mantiene i dati di oggi (candela chiusa).
    """
    df = df.copy().dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # --- SMART DATE TRIMMING ---
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    market_close_time = dt_time(16, 15)
    
    is_market_open = now_ny.time() < market_close_time
    today_date = now_ny.date()
    
    # Assicuriamo che 'Date' sia datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    if is_market_open:
        # Se il mercato è aperto (o appena chiuso ma non consolidato), rimuovi la riga di oggi
        df = df[df['Date'].dt.date < today_date]
    
    # Rimuovi prezzi <= 0 e ordina
    df = df[df['Close'] > 0].sort_values('Date').reset_index(drop=True)
    
    return df

# ============================================================================
# CACHING UTILITIES
# ============================================================================

def get_cached_data_key() -> str:
    """Genera chiave cache giornaliera."""
    return datetime.now().strftime('%Y-%m-%d')

# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Semplice test se eseguito direttamente
    print("Test Data Fetcher...")
    start, end = get_date_range_for_analysis()
    print(f"Range Analisi: {start} -> {end}")
    
    # Test VIX (EODHD -> fallback Yahoo)
    print("\n--- TEST VIX ---")
    vix = download_ticker_data("^VIX", start, end)
    if vix is not None:
        print(f"VIX OK: {len(vix)} righe.")
        print(f"Ultima Data: {vix['Date'].iloc[-1]} (Close: {vix['Close'].iloc[-1]:.2f})")
    else:
        print("VIX Failed")
