# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Data Fetcher Module - EODHD API Integration
============================================================================
Gestisce:
- Download dati storici da EODHD API
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
        if not self.api_key:
            logger.error("❌ EODHD_API_KEY non configurata!")
            raise ValueError("EODHD_API_KEY è richiesta per il data fetching")
        
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
        
        Args:
            url: URL endpoint
            params: Query parameters
            attempt: Numero tentativo corrente
        
        Returns:
            JSON response o None se errore
        """
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
        
        Args:
            ticker: Symbol (es. "SPY", "^VIX", "BTC-USD")
            exchange: Exchange code (es. "US", "INDX", "CC")
            start_date: Data inizio formato YYYY-MM-DD
            end_date: Data fine formato YYYY-MM-DD
        
        Returns:
            DataFrame con colonne [Date, Open, High, Low, Close, Volume, Adj Close]
            o None se errore
        """
        # Costruisci symbol EODHD format
        # Formato: TICKER.EXCHANGE (es. SPY.US, BTC-USD.CC)
        symbol = f"{ticker}.{exchange}"
        
        url = f"{self.base_url}/eod/{symbol}"
        
        params = {
            'api_token': self.api_key,
            'from': start_date,
            'to': end_date,
            'fmt': 'json',
            'period': 'd'  # Daily data
        }
        
        logger.info(f"📥 Fetching {symbol} from {start_date} to {end_date}")
        
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
            
            # Assicurati che Adj Close esista (alcuni ticker potrebbero non averlo)
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
        """
        Ottiene ultima quotazione real-time.
        
        Args:
            ticker: Symbol
            exchange: Exchange code
        
        Returns:
            Dict con quote data o None
        """
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
    Download dati per singolo ticker con retry.
    
    Args:
        ticker: Symbol ticker (es. "SPY")
        start_date: Data inizio YYYY-MM-DD
        end_date: Data fine YYYY-MM-DD
        retries: Numero tentativi
    
    Returns:
        DataFrame o None
    """
    # Recupera info ticker da UNIVERSE
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
    
    Args:
        start_date: Data inizio YYYY-MM-DD
        end_date: Data fine YYYY-MM-DD
        progress_callback: Funzione callback(current, total, ticker) per progress bar
    
    Returns:
        Dict {ticker: DataFrame}
    """
    logger.info(f"🚀 Avvio download universo ({len(UNIVERSE)} ticker)")
    
    results = {}
    failed = []
    
    client = EODHDClient()
    
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
            
            ticker_info = UNIVERSE[ticker]
            exchange = ticker_info.get('eodhd_exchange', 'US')
            
            df = client.get_eod_data(ticker, exchange, start_date, end_date)
            
            if df is not None:
                results[ticker] = df
            else:
                failed.append(ticker)
            
            # Batch delay (ogni N ticker)
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
    
    Returns:
        Tuple (start_date, end_date) formato YYYY-MM-DD
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
    
    Args:
        df: DataFrame da validare
        ticker: Nome ticker (per logging)
    
    Returns:
        True se valido, False altrimenti
    """
    if df is None or df.empty:
        logger.warning(f"⚠️ {ticker}: DataFrame vuoto")
        return False
    
    required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        logger.warning(f"⚠️ {ticker}: Colonne mancanti: {missing_cols}")
        return False
    
    # Check NaN values
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
    
    Args:
        df: DataFrame raw
    
    Returns:
        DataFrame pulito
    """
    df = df.copy()
    
    # Remove NaN rows
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # Ensure positive prices
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
    
    Returns:
        String key formato YYYY-MM-DD
    """
    return datetime.now().strftime('%Y-%m-%d')

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_connection() -> bool:
    """
    Testa connessione EODHD API.
    
    Returns:
        True se connessione OK
    """
    logger.info("🔍 Test connessione EODHD API...")
    
    try:
        client = EODHDClient()
        
        # Test con SPY (dovrebbe sempre funzionare)
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        df = client.get_eod_data('SPY', 'US', start_date, end_date)
        
        if df is not None and not df.empty:
            logger.info(f"✅ Connessione OK - SPY: {len(df)} righe")
            return True
        else:
            logger.error("❌ Connessione fallita - Nessun dato ricevuto")
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore test connessione: {str(e)}")
        return False

def download_sample_data(ticker: str = "SPY") -> Optional[pd.DataFrame]:
    """
    Scarica dati sample per testing.
    
    Args:
        ticker: Ticker da testare (default: SPY)
    
    Returns:
        DataFrame o None
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
    print("KRITERION QUANT - Data Fetcher Test")
    print("="*70)
    
    # 1. Test connessione
    print("\n1. Test Connessione EODHD:")
    if test_connection():
        print("   ✅ API Key valida e funzionante")
    else:
        print("   ❌ Problemi con API Key o connessione")
        exit(1)
    
    # 2. Test download singolo ticker
    print("\n2. Test Download Singolo Ticker (SPY):")
    df_spy = download_sample_data("SPY")
    if df_spy is not None:
        print(f"   ✅ SPY downloaded: {len(df_spy)} righe")
        print(f"\n   Prime 3 righe:")
        print(df_spy.head(3).to_string())
    
    # 3. Test download ticker speciali
    print("\n3. Test Ticker Speciali:")
    
    # VIX (Index)
    print("\n   a) VIX (Volatility Index):")
    df_vix = download_ticker_data(
        "^VIX",
        (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    )
    if df_vix is not None:
        print(f"      ✅ VIX: {len(df_vix)} righe")
    
    # BTC (Crypto)
    print("\n   b) BTC-USD (Cryptocurrency):")
    df_btc = download_ticker_data(
        "BTC-USD",
        (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    )
    if df_btc is not None:
        print(f"      ✅ BTC-USD: {len(df_btc)} righe")
    
    # 4. Test batch download (sample 5 ticker)
    print("\n4. Test Batch Download (sample 5 ticker):")
    sample_tickers = ['SPY', 'QQQ', 'GLD', 'TLT', 'IWM']
    
    # Temporary universe override
    import config
    original_universe = config.UNIVERSE
    config.UNIVERSE = {k: v for k, v in original_universe.items() if k in sample_tickers}
    
    start, end = get_date_range_for_analysis()
    results = download_universe_data(start, end)
    
    print(f"\n   ✅ Downloaded: {len(results)}/{len(sample_tickers)} ticker")
    for ticker, df in results.items():
        print(f"      - {ticker}: {len(df)} righe")
    
    # Restore universe
    config.UNIVERSE = original_universe
    
    print("\n" + "="*70)
    print("✅ Test completato con successo")
