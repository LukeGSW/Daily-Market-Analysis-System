# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Data Fetcher Module - Hybrid (EODHD + Yahoo Finance)
============================================================================
Gestisce:
- Download dati storici da EODHD API (Default)
- Download dati VIX da Yahoo Finance (Fallback/Override)
- Rate limiting intelligente
- Retry logic con exponential backoff
- Conversione formato EODHD → DataFrame compatibile
- Batch processing per universo completo
============================================================================
"""

import requests
import pandas as pd
import numpy as np
import time
import random
import yfinance as yf
from datetime import datetime, timedelta
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
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if df.empty:
            logger.warning(f"⚠️ Yahoo Finance ha restituito DataFrame vuoto per {ticker}")
            return None

        # Reset index per avere 'Date' come colonna
        df = df.reset_index()
        
        # Fix per le versioni recenti di yfinance che ritornano MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Rinomina colonna data se necessario (a volte è 'index' o 'Date')
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
        """
        Inizializza client EODHD.
        
        Args:
            api_key: EODHD API Key (default: da config.SECRETS)
        """
        self.api_key = api_key or SECRETS.get('EODHD_API_KEY', '')
        # Non solleviamo eccezione qui se manca la key, perché potremmo usare solo Yahoo
        if not self.api_key:
            logger.warning("⚠️ EODHD_API_KEY non configurata. I download da EODHD falliranno.")
        
        self.base_url = CONFIG['EODHD_BASE_URL']
        self.timeout = CONFIG['TIMEOUT']
        self.max_retries = CONFIG['MAX_RETRIES']
        
        # Rate limiting settings
        self.request_delay_min = CONFIG['REQUEST_DELAY_MIN']
        self.request_delay_max = CONFIG['REQUEST_DELAY_MAX']
        self.last_request_time = 0
        
        logger.info("✅ EODHD Client inizializzato")
    
    def _apply_rate_limit(self):
        """Applica rate limiting tra richieste."""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.request_delay_min, self.request_delay_max)
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: dict, attempt: int = 1) -> Optional[dict]:
        """
        Esegue richiesta HTTP con retry logic.
        """
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
                # Rate limit exceeded
                wait_time = 60 * attempt  # Exponential backoff
                logger.warning(f"⚠️ Rate limit exceeded, wait {wait_time}s...")
                time.sleep(wait_time)
                
                if attempt < self.max_retries:
                    return self._make_request(url, params, attempt + 1)
                return None
            
            elif response.status_code >= 500:
                # Server error - retry
                logger.warning(f"⚠️ Server error {response.status_code}, retry {attempt}/{self.max_retries}")
                
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
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
        """
        Scarica dati End-of-Day da EODHD.
        """
        # Costruisci symbol EODHD format
        symbol = f"{ticker}.{exchange}"
        
        url = f"{self.base_url}/eod/{symbol}"
        
        params = {
            'api_token': self.api_key,
            'from': start_date,
            'to': end_date,
            'fmt': 'json',
            'period': 'd'  # Daily data
        }
        
        logger.info(f"📥 Fetching {symbol} (EODHD) from {start_date} to {end_date}")
        
        data = self._make_request(url, params)
        
        if not data:
            logger.error(f"❌ Nessun dato ricevuto per {symbol}")
            return None
        
        # Converti in DataFrame
        try:
            df = pd.DataFrame(data)
            
            if df.empty:
                logger.warning(f"⚠️ DataFrame vuoto per {symbol}")
                return None
            
            # Rinomina colonne per compatibilità
            column_mapping = {
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'adjusted_close': 'Adj Close'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Converti Date in datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Assicurati che Adj Close esista
            if 'Adj Close' not in df.columns:
                df['Adj Close'] = df['Close']
            
            # Ordina per data crescente
            df = df.sort_values('Date').reset_index(drop=True)
            
            # Validazione dati
            if len(df) < CONFIG['MIN_REQUIRED_ROWS']:
                logger.warning(
                    f"⚠️ {symbol}: solo {len(df)} righe, "
                    f"minimo richiesto {CONFIG['MIN_REQUIRED_ROWS']}"
                )
                return None
            
            logger.info(f"✅ {symbol}: {len(df)} righe scaricate")
            return df
            
        except Exception as e:
            logger.error(f"❌ Errore conversione DataFrame per {symbol}: {str(e)}")
            return None
    
    def get_latest_quote(self, ticker: str, exchange: str) -> Optional[dict]:
        """Ottiene ultima quotazione real-time."""
        symbol = f"{ticker}.{exchange}"
        url = f"{self.base_url}/real-time/{symbol}"
        
        params = {
            'api_token': self.api_key,
            'fmt': 'json'
        }
        
        data = self._make_request(url, params)
        return data

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
    
    # Per tutti gli altri, proseguiamo con EODHD come da configurazione
    ticker_info = UNIVERSE.get(ticker)
    if not ticker_info:
        logger.error(f"❌ Ticker {ticker} non trovato in UNIVERSE")
        return None
    
    exchange = ticker_info.get('eodhd_exchange', 'US')
    
    # Inizializza client
    client = EODHDClient()
    
    # Scarica dati
    df = client.get_eod_data(ticker, exchange, start_date, end_date)
    
    return df

def download_universe_data(
    start_date: str,
    end_date: str,
    progress_callback=None
) -> Dict[str, pd.DataFrame]:
    """
    Scarica dati per tutti i ticker dell'universo con batch processing.
    """
    logger.info(f"🚀 Avvio download universo ({len(UNIVERSE)} ticker)")
    
    results = {}
    failed = []
    
    tickers = list(UNIVERSE.keys())
    total_tickers = len(tickers)
    
    # Batch processing
    batch_size = CONFIG['BATCH_SIZE']
    batch_delay_min = CONFIG['BATCH_DELAY_MIN']
    batch_delay_max = CONFIG['BATCH_DELAY_MAX']
    
    for i, ticker in enumerate(tickers, 1):
        try:
            # Progress callback
            if progress_callback:
                progress_callback(i, total_tickers, ticker)
            
            # Utilizza la funzione wrapper che gestisce la logica Ibrida
            df = download_ticker_data(ticker, start_date, end_date)
            
            if df is not None and not df.empty:
                results[ticker] = df
            else:
                failed.append(ticker)
            
            # Batch delay (ogni N ticker)
            # Applichiamo il delay anche se usiamo Yahoo per mantenere il ritmo del loop uniforme
            if i % batch_size == 0 and i < total_tickers:
                delay = random.uniform(batch_delay_min, batch_delay_max)
                logger.info(f"⏸️ Batch delay: {delay:.1f}s (completati {i}/{total_tickers})")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"❌ Errore download {ticker}: {str(e)}")
            failed.append(ticker)
    
    # Summary
    success_count = len(results)
    fail_count = len(failed)
    
    logger.info("="*70)
    logger.info(f"✅ Download completato: {success_count}/{total_tickers} ticker OK")
    
    if failed:
        logger.warning(f"⚠️ Failed: {fail_count} ticker")
        logger.warning(f"   {', '.join(failed)}")
    
    return results

def get_date_range_for_analysis() -> Tuple[str, str]:
    """
    Calcola range date per analisi (oggi - LOOKBACK_DAYS fino a ieri).
    """
    # End date = ieri (per avere dati completi)
    end_date = datetime.now() - timedelta(days=1)
    
    # Start date = end_date - lookback
    lookback_days = CONFIG['DATA_LOOKBACK_DAYS']
    start_date = end_date - timedelta(days=lookback_days)
    
    return (
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )

def validate_dataframe(df: pd.DataFrame, ticker: str) -> bool:
    """
    Valida DataFrame scaricato.
    """
    if df is None or df.empty:
        logger.warning(f"⚠️ {ticker}: DataFrame vuoto")
        return False
    
    required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        logger.warning(f"⚠️ {ticker}: Colonne mancanti: {missing_cols}")
        return False
    
    # Check NaN values (escludiamo Volume che può essere 0 o NaN su indici)
    if df[['Open', 'High', 'Low', 'Close']].isnull().any().any():
        logger.warning(f"⚠️ {ticker}: Contiene NaN nei prezzi")
        return False
    
    # Check min rows
    if len(df) < CONFIG['MIN_REQUIRED_ROWS']:
        logger.warning(
            f"⚠️ {ticker}: Solo {len(df)} righe, "
            f"minimo {CONFIG['MIN_REQUIRED_ROWS']}"
        )
        return False
    
    return True

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pulisce e prepara DataFrame per analisi.
    """
    df = df.copy()
    
    # Remove NaN rows
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # Ensure positive prices (escludiamo VIX dai controlli stretti se necessario, ma Close > 0 è sicuro)
    price_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close']
    for col in price_cols:
        if col in df.columns:
            df = df[df[col] > 0]
    
    # Sort by date
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Convert Volume to numeric (handle strings)
    if 'Volume' in df.columns:
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
    
    return df

# ============================================================================
# CACHING UTILITIES (for Streamlit)
# ============================================================================

def get_cached_data_key() -> str:
    """
    Genera chiave unica per cache basata su data corrente.
    Cache viene invalidata ogni giorno.
    """
    return datetime.now().strftime('%Y-%m-%d')

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_connection() -> bool:
    """
    Testa connessione EODHD API.
    """
    logger.info("🔍 Test connessione EODHD API...")
    
    try:
        client = EODHDClient()
        
        # Test con SPY (dovrebbe sempre funzionare se API key ok)
        if client.api_key:
            end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
            
            df = client.get_eod_data('SPY', 'US', start_date, end_date)
            
            if df is not None and not df.empty:
                logger.info(f"✅ Connessione OK - SPY: {len(df)} righe")
                return True
            else:
                logger.error("❌ Connessione fallita - Nessun dato ricevuto")
                return False
        else:
            logger.warning("⚠️ API Key mancante - Test EODHD saltato")
            return True # Ritorniamo True se vogliamo testare solo Yahoo
            
    except Exception as e:
        logger.error(f"❌ Errore test connessione: {str(e)}")
        return False

def download_sample_data(ticker: str = "SPY") -> Optional[pd.DataFrame]:
    """
    Scarica dati sample per testing.
    """
    start_date, end_date = get_date_range_for_analysis()
    
    logger.info(f"📊 Download sample data: {ticker}")
    logger.info(f"   Range: {start_date} → {end_date}")
    
    df = download_ticker_data(ticker, start_date, end_date)
    
    if df is not None:
        logger.info(f"✅ Sample data downloaded: {len(df)} rows")
        logger.info(f"   Date range: {df['Date'].min()} → {df['Date'].max()}")
        logger.info(f"   Columns: {list(df.columns)}")
        return df
    else:
        logger.error(f"❌ Failed to download sample data")
        return None

# ============================================================================
# MAIN TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Data Fetcher Test (Hybrid)")
    print("="*70)
    
    # 1. Test connessione
    print("\n1. Test Connessione EODHD:")
    if test_connection():
        print("   ✅ Test connessione OK")
    else:
        print("   ❌ Problemi con API Key o connessione")
    
    # 2. Test download singolo ticker EODHD
    print("\n2. Test Download Singolo Ticker (SPY - EODHD):")
    df_spy = download_sample_data("SPY")
    if df_spy is not None:
        print(f"   ✅ SPY downloaded: {len(df_spy)} righe")
        print(f"\n   Prime 3 righe:")
        print(df_spy.head(3).to_string())
    
    # 3. Test download ticker speciali (Yahoo)
    print("\n3. Test Ticker Speciali (^VIX - Yahoo):")
    
    # VIX (Index) - Dovrebbe usare Yahoo
    print("\n   a) VIX (Volatility Index):")
    start, end = get_date_range_for_analysis()
    df_vix = download_ticker_data("^VIX", start, end)
    
    if df_vix is not None:
        print(f"      ✅ VIX: {len(df_vix)} righe")
        print(f"      Source: Yahoo Finance")
        print(df_vix.head(3).to_string())
    else:
        print("      ❌ VIX download fallito")
    
    # 4. Test batch download (sample)
    print("\n4. Test Batch Download (sample misto):")
    sample_tickers = ['SPY', '^VIX']
    
    # Override temporaneo universe per test
    import config
    original_universe = config.UNIVERSE
    config.UNIVERSE = {k: v for k, v in original_universe.items() if k in sample_tickers}
    # Assicuriamo che VIX sia nell'universo se non c'era
    if "^VIX" not in config.UNIVERSE:
        config.UNIVERSE["^VIX"] = {"name": "Volatility Index", "category": "Volatility", "eodhd_exchange": "INDX"}
    
    results = download_universe_data(start, end)
    
    print(f"\n   ✅ Downloaded: {len(results)}/{len(sample_tickers)} ticker")
    for ticker, df in results.items():
        print(f"      - {ticker}: {len(df)} righe")
    
    # Restore universe
    config.UNIVERSE = original_universe
    
    print("\n" + "="*70)
    print("✅ Test completato")
