# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Data Fetcher Module - Hybrid (EODHD + Yahoo Finance)
============================================================================
Gestisce:
- Download dati storici da EODHD API (Default per azioni/ETF)
- Download dati VIX da Yahoo Finance (Fallback/Override)
- Rate limiting intelligente e Retry logic
- Normalizzazione dati
- FIX DATE: Taglio rigoroso alla data di ieri (T-1) per coerenza analisi
============================================================================
"""

import requests
import pandas as pd
import numpy as np
import time
import random
import yfinance as yf
from datetime import datetime, timedelta, date
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
    Utile per ^VIX o altri indici non disponibili su EODHD.
    """
    try:
        logger.info(f"📥 Fetching {ticker} via Yahoo Finance...")
        
        # Yahoo Finance download
        # Nota: yfinance scarica fino a end_date escluso.
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if df.empty:
            logger.warning(f"⚠️ Yahoo Finance ha restituito DataFrame vuoto per {ticker}")
            return None

        # Reset index per avere 'Date' come colonna
        df = df.reset_index()
        
        # Fix per le versioni recenti di yfinance che ritornano MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Rinomina colonna data se necessario
        if 'Date' not in df.columns and 'index' in df.columns:
            df.rename(columns={'index': 'Date'}, inplace=True)

        # Assicurati formattazione Date e rimozione timezone
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        # Filtra e ordina colonne richieste
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        
        # Yahoo a volte non ha Volume per indici, gestiamo l'assenza
        if 'Volume' not in df.columns:
            df['Volume'] = 0
            
        # Aggiungi Adj Close se manca (copia Close)
        if 'Adj Close' not in df.columns:
            df['Adj Close'] = df['Close']
            
        # Verifica colonne presenti
        available_cols = [c for c in required_cols + ['Adj Close'] if c in df.columns]
        df = df[available_cols].copy()
            
        # Ordina per data
        df = df.sort_values('Date').reset_index(drop=True)
        
        logger.info(f"✅ {ticker} (Yahoo): {len(df)} righe scaricate")
        return df

    except Exception as e:
        logger.error(f"❌ Errore Yahoo Finance per {ticker}: {str(e)}")
        return None

# ============================================================================
# EODHD API CLIENT
# ============================================================================

class EODHDClient:
    """
    Client per interagire con EODHD API.
    Gestisce rate limiting, retry e errori.
    """
    
    def __init__(self, api_key: str = None):
        """Inizializza client EODHD."""
        self.api_key = api_key or SECRETS.get('EODHD_API_KEY', '')
        
        if not self.api_key:
            logger.warning("⚠️ EODHD_API_KEY non configurata. I download da EODHD falliranno.")
        
        self.base_url = CONFIG['EODHD_BASE_URL']
        self.timeout = CONFIG['TIMEOUT']
        self.max_retries = CONFIG['MAX_RETRIES']
        
        # Rate limiting settings
        self.request_delay_min = CONFIG['REQUEST_DELAY_MIN']
        self.request_delay_max = CONFIG['REQUEST_DELAY_MAX']
        self.last_request_time = 0
    
    def _apply_rate_limit(self):
        """Applica rate limiting tra richieste."""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.request_delay_min, self.request_delay_max)
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: dict, attempt: int = 1) -> Optional[dict]:
        """Esegue richiesta HTTP con retry logic."""
        if not self.api_key:
            return None

        try:
            self._apply_rate_limit()
            
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            # Check HTTP status
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 401:
                logger.error(f"❌ 401 Unauthorized - Verifica EODHD_API_KEY")
                return None
            
            elif response.status_code == 429:
                wait_time = 60 * attempt
                logger.warning(f"⚠️ Rate limit exceeded, wait {wait_time}s...")
                time.sleep(wait_time)
                if attempt < self.max_retries:
                    return self._make_request(url, params, attempt + 1)
                return None
            
            elif response.status_code >= 500:
                logger.warning(f"⚠️ Server error {response.status_code}, retry {attempt}/{self.max_retries}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    return self._make_request(url, params, attempt + 1)
                return None
            
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.Timeout:
            logger.warning(f"⚠️ Timeout, retry {attempt}/{self.max_retries}")
            if attempt < self.max_retries:
                time.sleep(2 ** attempt)
                return self._make_request(url, params, attempt + 1)
            return None
            
        except Exception as e:
            logger.error(f"❌ Errore richiesta: {str(e)}")
            return None
    
    def get_eod_data(
        self,
        ticker: str,
        exchange: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Scarica dati End-of-Day da EODHD."""
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
        
        if not data:
            logger.error(f"❌ Nessun dato ricevuto per {symbol}")
            return None
        
        try:
            df = pd.DataFrame(data)
            
            if df.empty:
                logger.warning(f"⚠️ DataFrame vuoto per {symbol}")
                return None
            
            # Rinomina colonne
            column_mapping = {
                'date': 'Date', 'open': 'Open', 'high': 'High', 
                'low': 'Low', 'close': 'Close', 'volume': 'Volume', 
                'adjusted_close': 'Adj Close'
            }
            df = df.rename(columns=column_mapping)
            
            # Converti Date
            df['Date'] = pd.to_datetime(df['Date'])
            
            if 'Adj Close' not in df.columns:
                df['Adj Close'] = df['Close']
            
            df = df.sort_values('Date').reset_index(drop=True)
            return df
            
        except Exception as e:
            logger.error(f"❌ Errore conversione DataFrame per {symbol}: {str(e)}")
            return None
    
    def get_latest_quote(self, ticker: str, exchange: str) -> Optional[dict]:
        """Ottiene ultima quotazione real-time."""
        symbol = f"{ticker}.{exchange}"
        url = f"{self.base_url}/real-time/{symbol}"
        params = {'api_token': self.api_key, 'fmt': 'json'}
        return self._make_request(url, params)

# ============================================================================
# HIGH-LEVEL FETCHING FUNCTIONS
# ============================================================================

def download_ticker_data(
    ticker: str,
    start_date: str,
    end_date: str,
    retries: int = 3
) -> Optional[pd.DataFrame]:
    """
    Download dati per singolo ticker con logica Ibrida (EODHD + Yahoo).
    """
    # --- LOGICA IBRIDA ---
    # Se il ticker è VIX, usiamo Yahoo Finance
    if ticker == "^VIX":
        return fetch_from_yahoo(ticker, start_date, end_date)
    
    # Per tutti gli altri, usiamo EODHD
    ticker_info = UNIVERSE.get(ticker)
    if not ticker_info:
        logger.error(f"❌ Ticker {ticker} non trovato in UNIVERSE")
        return None
    
    exchange = ticker_info.get('eodhd_exchange', 'US')
    
    # Inizializza client
    client = EODHDClient()
    return client.get_eod_data(ticker, exchange, start_date, end_date)

def download_universe_data(
    start_date: str,
    end_date: str,
    progress_callback=None
) -> Dict[str, pd.DataFrame]:
    """
    Scarica dati per tutti i ticker dell'universo.
    """
    logger.info(f"🚀 Avvio download universo ({len(UNIVERSE)} ticker)")
    
    results = {}
    failed = []
    tickers = list(UNIVERSE.keys())
    total_tickers = len(tickers)
    
    # Batch processing parameters
    batch_size = CONFIG['BATCH_SIZE']
    batch_delay_min = CONFIG['BATCH_DELAY_MIN']
    batch_delay_max = CONFIG['BATCH_DELAY_MAX']
    
    for i, ticker in enumerate(tickers, 1):
        try:
            if progress_callback:
                progress_callback(i, total_tickers, ticker)
            
            # Download
            df = download_ticker_data(ticker, start_date, end_date)
            
            if df is not None and not df.empty:
                # --- CRITICAL STEP: CLEAN & VALIDATE ---
                # Pulisce i dati e, soprattutto, rimuove la data odierna
                df = clean_dataframe(df)
                
                if validate_dataframe(df, ticker):
                    results[ticker] = df
                else:
                    failed.append(ticker)
            else:
                failed.append(ticker)
            
            # Batch delay
            if i % batch_size == 0 and i < total_tickers:
                delay = random.uniform(batch_delay_min, batch_delay_max)
                logger.info(f"⏸️ Batch delay: {delay:.1f}s")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"❌ Errore download {ticker}: {str(e)}")
            failed.append(ticker)
    
    # Summary
    logger.info("="*70)
    logger.info(f"✅ Download completato: {len(results)}/{total_tickers} ticker OK")
    if failed:
        logger.warning(f"⚠️ Failed: {', '.join(failed)}")
    
    return results

def get_date_range_for_analysis() -> Tuple[str, str]:
    """
    Calcola range date per analisi (T-1).
    End date è rigorosamente IERI.
    """
    # End date = ieri
    end_date = datetime.now() - timedelta(days=1)
    
    # Start date = end_date - lookback
    lookback_days = CONFIG['DATA_LOOKBACK_DAYS']
    start_date = end_date - timedelta(days=lookback_days)
    
    return (
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )

def validate_dataframe(df: pd.DataFrame, ticker: str) -> bool:
    """Valida integrità DataFrame."""
    if df is None or df.empty:
        logger.warning(f"⚠️ {ticker}: DataFrame vuoto")
        return False
    
    required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        logger.warning(f"⚠️ {ticker}: Colonne mancanti: {missing_cols}")
        return False
    
    if len(df) < CONFIG['MIN_REQUIRED_ROWS']:
        logger.warning(f"⚠️ {ticker}: Solo {len(df)} righe (min {CONFIG['MIN_REQUIRED_ROWS']})")
        return False
    
    return True

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pulisce il DataFrame e rimuove rigorosamente la data odierna se presente.
    Garantisce consistenza T-1 (analisi sui dati di chiusura ieri).
    """
    df = df.copy()
    
    # Remove NaN rows
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # --- DATE TRIMMING LOGIC ---
    # Rimuoviamo qualsiasi riga che abbia data >= Oggi (es. EODHD potrebbe dare dati intraday)
    today = pd.Timestamp(date.today())
    df = df[df['Date'] < today]
    
    # Ensure positive prices
    price_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close']
    for col in price_cols:
        if col in df.columns:
            df = df[df[col] > 0]
    
    # Sort by date
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Convert Volume
    if 'Volume' in df.columns:
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
    
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
    
    # Test VIX (Yahoo)
    vix = download_ticker_data("^VIX", start, end)
    if vix is not None:
        print(f"VIX OK: {len(vix)} righe. Ultima: {vix['Date'].iloc[-1]}")
    else:
        print("VIX Failed")
