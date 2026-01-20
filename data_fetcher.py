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
- LOGICA SMART T-1: Accetta la data odierna SOLO se il mercato NY è chiuso.
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
        
        # --- FIX: Usiamo history(period="10y") invece di date specifiche ---
        # Questo garantisce di avere l'ultima candela disponibile (anche di oggi)
        # bypassando problemi di calcolo date e festività (es. MLK Day).
        
        # Gestione simbolo per Yahoo (aggiunge ^ se manca e se sembra un indice)
        yf_ticker_name = ticker
        if ticker == "VIX" or (ticker == "^VIX"):
            yf_ticker_name = "^VIX"
            
        ticker_obj = yf.Ticker(yf_ticker_name)
        df = ticker_obj.history(period="10y", auto_adjust=False)
        # -------------------------------------------------------------------
        
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
        
        # Filtro manuale della data di inizio (la fine la lasciamo aperta per prendere l'ultimo dato)
        df = df[df['Date'] >= pd.to_datetime(start_date)]
        
        # Filtra e ordina colonne richieste
        # Yahoo restituisce: Open, High, Low, Close, Volume (e a volte Adj Close separato)
        
        # Normalizzazione nomi colonne (Yahoo Capitalizza, noi vogliamo coerenza)
        df = df.rename(columns={
            'Open': 'Open', 'High': 'High', 'Low': 'Low', 
            'Close': 'Close', 'Adj Close': 'Adj Close', 'Volume': 'Volume'
        })

        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        
        # Yahoo a volte non ha Volume per indici (es. VIX), gestiamo l'assenza
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
        
        logger.info(f"✅ {ticker} (Yahoo): {len(df)} righe scaricate (Ultima: {df['Date'].iloc[-1].date()})")
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
            
            # --- FIX STOCK SPLIT / ADJUSTED PRICES ---
            # 1. Convertiamo in numeri gestendo eventuali errori
            df['close'] = pd.to_numeric(df['close'], errors='coerce').fillna(0)
            df['adjusted_close'] = pd.to_numeric(df['adjusted_close'], errors='coerce').fillna(0)
            df['open'] = pd.to_numeric(df['open'], errors='coerce').fillna(0)
            df['high'] = pd.to_numeric(df['high'], errors='coerce').fillna(0)
            df['low'] = pd.to_numeric(df['low'], errors='coerce').fillna(0)
            
            # 2. Calcoliamo il fattore di rettifica
            adj_factor = df['adjusted_close'] / df['close']
            adj_factor = adj_factor.fillna(1.0)
            
            # 3. Rettifichiamo OHLC
            df['Close'] = df['adjusted_close']
            df['Open'] = df['open'] * adj_factor
            df['High'] = df['high'] * adj_factor
            df['Low'] = df['low'] * adj_factor
            
            # 4. Altre colonne
            df['Date'] = pd.to_datetime(df['date'])
            df['Volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
            df['Adj Close'] = df['adjusted_close']
            
            # 5. Pulizia finale
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']]
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
    if ticker == "^VIX" or ticker == "VIX":
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
                # Pulisce i dati applicando la logica oraria per la data odierna
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
    Calcola range date per analisi.
    """
    # End date nominale = ieri (come fallback)
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
    Pulisce il DataFrame.
    
    LOGICA SMART PER LA DATA ODIERNA:
    - Se ora NY < 16:15: Rimuove i dati di oggi (candela incompleta).
    - Se ora NY >= 16:15: Mantiene i dati di oggi (candela chiusa).
    - Se oggi è weekend: Non ci sono dati di oggi, mantiene l'ultimo disponibile.
    """
    df = df.copy()
    
    # Remove NaN rows
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # --- SMART DATE TRIMMING ---
    # Verifichiamo se il mercato USA è chiuso
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    
    # Definizione orario chiusura (16:15 buffer)
    market_close_time = dt_time(16, 15)
    
    is_market_open = now_ny.time() < market_close_time
    today_date = now_ny.date()
    
    # Identifichiamo i dati con data >= oggi (locale NY)
    # Attenzione: df['Date'] è timestamp senza timezone, lo assumiamo compatibile
    
    if is_market_open:
        # Mercato APERTO: Rimuoviamo la data di oggi se presente (perché incompleta)
        # Convertiamo la colonna date in date object per confronto
        df = df[df['Date'].dt.date < today_date]
    else:
        # Mercato CHIUSO: Accettiamo tutto (inclusa la candela di oggi se c'è)
        # Non facciamo nulla, teniamo tutto.
        pass
        
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
    print("\n--- TEST VIX ---")
    vix = download_ticker_data("^VIX", start, end)
    if vix is not None:
        print(f"VIX OK: {len(vix)} righe.")
        print(f"Ultima Data: {vix['Date'].iloc[-1]} (Close: {vix['Close'].iloc[-1]:.2f})")
    else:
        print("VIX Failed")
