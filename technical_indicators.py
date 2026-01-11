# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Technical Indicators Module
============================================================================
Implementazione custom di tutti gli indicatori tecnici necessari:
- Simple Moving Averages (SMA)
- Relative Strength Index (RSI)
- Average True Range (ATR)
- Moving Average Convergence Divergence (MACD)
- Average Directional Index (ADX)
- Bollinger Bands (BB)
- Rate of Change (ROC)
- Z-Score (Statistical)
- Historical Volatility (HVol)

NOTE: Implementazioni custom per evitare dipendenza da TA-Lib
============================================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from config import CONFIG

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# TREND INDICATORS
# ============================================================================

def calculate_sma(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    Calcola Simple Moving Average per multipli periodi.
    
    Args:
        df: DataFrame con colonna 'Close'
        periods: Lista periodi (default: da CONFIG)
    
    Returns:
        DataFrame con colonne SMA_X aggiunte
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG['SMA_PERIODS']
    
    for period in periods:
        df[f'SMA_{period}'] = df['Close'].rolling(window=period).mean()
    
    return df

def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calcola Exponential Moving Average.
    
    Args:
        df: DataFrame con colonna 'Close'
        period: Periodo EMA
    
    Returns:
        Series con EMA
    """
    return df['Close'].ewm(span=period, adjust=False).mean()

# ============================================================================
# MOMENTUM INDICATORS
# ============================================================================

def calculate_rsi(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """
    Calcola Relative Strength Index (RSI).
    
    Formula:
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    
    Args:
        df: DataFrame con colonna 'Close'
        period: Periodo RSI (default: da CONFIG)
    
    Returns:
        DataFrame con colonna 'RSI' aggiunta
    """
    df = df.copy()
    
    if period is None:
        period = CONFIG['RSI_PERIOD']
    
    # Calcola variazioni prezzo
    delta = df['Close'].diff()
    
    # Separa gains e losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calcola medie mobili (Wilder's smoothing)
    avg_gains = gains.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_losses = losses.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # Calcola RS e RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    df['RSI'] = rsi
    
    return df

def calculate_roc(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    Calcola Rate of Change (ROC) per multipli periodi.
    
    Formula:
    ROC = ((Close - Close_n_periods_ago) / Close_n_periods_ago) * 100
    
    Args:
        df: DataFrame con colonna 'Close'
        periods: Lista periodi (default: da CONFIG)
    
    Returns:
        DataFrame con colonne ROC_X aggiunte
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG['ROC_PERIODS']
    
    for period in periods:
        df[f'ROC_{period}'] = ((df['Close'] - df['Close'].shift(period)) / 
                               df['Close'].shift(period)) * 100
    
    return df

def calculate_macd(
    df: pd.DataFrame,
    fast: int = None,
    slow: int = None,
    signal: int = None
) -> pd.DataFrame:
    """
    Calcola MACD (Moving Average Convergence Divergence).
    
    Args:
        df: DataFrame con colonna 'Close'
        fast: Periodo EMA fast (default: da CONFIG)
        slow: Periodo EMA slow (default: da CONFIG)
        signal: Periodo signal line (default: da CONFIG)
    
    Returns:
        DataFrame con colonne MACD, MACD_signal, MACD_histogram
    """
    df = df.copy()
    
    if fast is None:
        fast = CONFIG['MACD_FAST']
    if slow is None:
        slow = CONFIG['MACD_SLOW']
    if signal is None:
        signal = CONFIG['MACD_SIGNAL']
    
    # Calcola EMA fast e slow
    ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
    
    # MACD line
    df['MACD'] = ema_fast - ema_slow
    
    # Signal line
    df['MACD_signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    
    # Histogram
    df['MACD_histogram'] = df['MACD'] - df['MACD_signal']
    
    return df

# ============================================================================
# VOLATILITY INDICATORS
# ============================================================================

def calculate_atr(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """
    Calcola Average True Range (ATR).
    
    True Range = max(H-L, |H-C_prev|, |L-C_prev|)
    ATR = EMA del True Range
    
    Args:
        df: DataFrame con colonne OHLC
        period: Periodo ATR (default: da CONFIG)
    
    Returns:
        DataFrame con colonne 'TR' e 'ATR' aggiunte
    """
    df = df.copy()
    
    if period is None:
        period = CONFIG['ATR_PERIOD']
    
    # Calcola True Range
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift(1)).abs()
    low_close = (df['Low'] - df['Close'].shift(1)).abs()
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    df['TR'] = true_range
    
    # Calcola ATR (Wilder's smoothing)
    df['ATR'] = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # ATR percentage
    df['ATR_pct'] = (df['ATR'] / df['Close']) * 100
    
    return df

def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = None,
    std_dev: float = None
) -> pd.DataFrame:
    """
    Calcola Bollinger Bands.
    
    Args:
        df: DataFrame con colonna 'Close'
        period: Periodo per SMA (default: da CONFIG)
        std_dev: Numero di deviazioni standard (default: da CONFIG)
    
    Returns:
        DataFrame con colonne BB_upper, BB_middle, BB_lower, BB_width
    """
    df = df.copy()
    
    if period is None:
        period = CONFIG['BB_PERIOD']
    if std_dev is None:
        std_dev = CONFIG['BB_STD']
    
    # Middle band (SMA)
    df['BB_middle'] = df['Close'].rolling(window=period).mean()
    
    # Standard deviation
    rolling_std = df['Close'].rolling(window=period).std()
    
    # Upper e Lower bands
    df['BB_upper'] = df['BB_middle'] + (rolling_std * std_dev)
    df['BB_lower'] = df['BB_middle'] - (rolling_std * std_dev)
    
    # Band width (percentage)
    df['BB_width'] = ((df['BB_upper'] - df['BB_lower']) / df['BB_middle']) * 100
    
    # %B indicator (posizione prezzo nelle bande)
    df['BB_percent'] = (df['Close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
    
    return df

def calculate_historical_volatility(
    df: pd.DataFrame,
    periods: List[int] = None
) -> pd.DataFrame:
    """
    Calcola Historical Volatility (annualizzata).
    
    Formula:
    HVol = stdev(log_returns) * sqrt(252)
    
    Args:
        df: DataFrame con colonna 'Close'
        periods: Lista periodi (default: da CONFIG)
    
    Returns:
        DataFrame con colonne HVol_X aggiunte
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG['HVOL_PERIODS']
    
    # Calcola log returns
    log_returns = np.log(df['Close'] / df['Close'].shift(1))
    
    for period in periods:
        # Volatilità rolling annualizzata
        df[f'HVol_{period}'] = (
            log_returns.rolling(window=period).std() * np.sqrt(252) * 100
        )
    
    return df

# ============================================================================
# TREND STRENGTH INDICATORS
# ============================================================================

def calculate_adx(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """
    Calcola Average Directional Index (ADX).
    
    Misura la forza del trend (non la direzione).
    ADX > 25 indica trend forte.
    
    Args:
        df: DataFrame con colonne OHLC
        period: Periodo ADX (default: da CONFIG)
    
    Returns:
        DataFrame con colonne ADX, +DI, -DI
    """
    df = df.copy()
    
    if period is None:
        period = CONFIG['ADX_PERIOD']
    
    # Calcola True Range (se non già presente)
    if 'TR' not in df.columns:
        df = calculate_atr(df, period)
    
    # Directional Movement
    high_diff = df['High'] - df['High'].shift(1)
    low_diff = df['Low'].shift(1) - df['Low']
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    # Smoothed DM e TR
    atr = df['ATR']
    plus_dm_smooth = plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # Directional Indicators
    df['plus_DI'] = (plus_dm_smooth / atr) * 100
    df['minus_DI'] = (minus_dm_smooth / atr) * 100
    
    # Directional Index
    dx = (abs(df['plus_DI'] - df['minus_DI']) / 
          (df['plus_DI'] + df['minus_DI'])) * 100
    
    # ADX (smoothed DX)
    df['ADX'] = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    return df

# ============================================================================
# STATISTICAL INDICATORS
# ============================================================================

def calculate_zscore(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    Calcola Z-Score per multipli periodi.
    
    Formula:
    Z-Score = (Close - Mean) / StdDev
    
    Indica quanto il prezzo è distante dalla media in termini di deviazioni standard.
    
    Args:
        df: DataFrame con colonna 'Close'
        periods: Lista periodi (default: da CONFIG)
    
    Returns:
        DataFrame con colonne ZScore_X aggiunte
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG['ZSCORE_PERIODS']
    
    for period in periods:
        rolling_mean = df['Close'].rolling(window=period).mean()
        rolling_std = df['Close'].rolling(window=period).std()
        
        df[f'ZScore_{period}'] = (df['Close'] - rolling_mean) / rolling_std
    
    return df

def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola returns percentuali per vari periodi.
    
    Args:
        df: DataFrame con colonna 'Close'
    
    Returns:
        DataFrame con colonne return aggiunte
    """
    df = df.copy()
    
    # Daily return
    df['return_1d'] = df['Close'].pct_change() * 100
    
    # Weekly return (5 giorni)
    df['return_5d'] = ((df['Close'] - df['Close'].shift(5)) / 
                       df['Close'].shift(5)) * 100
    
    # Monthly return (21 giorni)
    df['return_21d'] = ((df['Close'] - df['Close'].shift(21)) / 
                        df['Close'].shift(21)) * 100
    
    # Quarterly return (63 giorni)
    df['return_63d'] = ((df['Close'] - df['Close'].shift(63)) / 
                        df['Close'].shift(63)) * 100
    
    return df

# ============================================================================
# VOLUME INDICATORS
# ============================================================================

def calculate_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola indicatori basati su volume.
    
    Args:
        df: DataFrame con colonne 'Close' e 'Volume'
    
    Returns:
        DataFrame con indicatori volume aggiunti
    """
    df = df.copy()
    
    # Volume SMA
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    
    # Volume ratio (vs media)
    df['Volume_ratio'] = df['Volume'] / df['Volume_SMA_20']
    
    # On-Balance Volume (OBV)
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    
    df['OBV'] = obv
    
    return df

# ============================================================================
# SUPPORT/RESISTANCE LEVELS
# ============================================================================

def calculate_pivot_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola Pivot Points classici (daily).
    
    Args:
        df: DataFrame con colonne OHLC
    
    Returns:
        DataFrame con pivot levels aggiunti
    """
    df = df.copy()
    
    # Pivot Point
    df['Pivot'] = (df['High'] + df['Low'] + df['Close']) / 3
    
    # Resistance levels
    df['R1'] = 2 * df['Pivot'] - df['Low']
    df['R2'] = df['Pivot'] + (df['High'] - df['Low'])
    
    # Support levels
    df['S1'] = 2 * df['Pivot'] - df['High']
    df['S2'] = df['Pivot'] - (df['High'] - df['Low'])
    
    return df

# ============================================================================
# MASTER FUNCTION - COMPUTE ALL INDICATORS
# ============================================================================

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola TUTTI gli indicatori tecnici su un DataFrame.
    
    Questa è la funzione principale da chiamare per avere un DataFrame completo.
    
    Args:
        df: DataFrame con colonne OHLC + Volume + Date
    
    Returns:
        DataFrame con tutti gli indicatori calcolati
    """
    logger.info("📊 Calcolo indicatori tecnici...")
    
    df = df.copy()
    
    # Assicurati che sia ordinato per data
    df = df.sort_values('Date').reset_index(drop=True)
    
    try:
        # --- TREND INDICATORS ---
        df = calculate_sma(df)
        
        # --- MOMENTUM INDICATORS ---
        df = calculate_rsi(df)
        df = calculate_roc(df)
        df = calculate_macd(df)
        
        # --- VOLATILITY INDICATORS ---
        df = calculate_atr(df)
        df = calculate_bollinger_bands(df)
        df = calculate_historical_volatility(df)
        
        # --- TREND STRENGTH ---
        df = calculate_adx(df)
        
        # --- STATISTICAL ---
        df = calculate_zscore(df)
        df = calculate_returns(df)
        
        # --- VOLUME ---
        if 'Volume' in df.columns and df['Volume'].sum() > 0:
            df = calculate_volume_indicators(df)
        
        # --- SUPPORT/RESISTANCE ---
        df = calculate_pivot_points(df)
        
        logger.info(f"✅ Indicatori calcolati: {len(df.columns)} colonne totali")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Errore calcolo indicatori: {str(e)}")
        raise

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_indicator_summary(df: pd.DataFrame, ticker: str = "") -> Dict:
    """
    Estrae summary dei principali indicatori (ultima riga).
    
    Args:
        df: DataFrame con indicatori calcolati
        ticker: Nome ticker (per logging)
    
    Returns:
        Dict con valori indicatori chiave
    """
    if df.empty:
        return {}
    
    # Prendi ultima riga (valori più recenti)
    last = df.iloc[-1]
    
    summary = {
        'price': last.get('Close', np.nan),
        'sma_50': last.get('SMA_50', np.nan),
        'sma_200': last.get('SMA_200', np.nan),
        'rsi': last.get('RSI', np.nan),
        'macd': last.get('MACD', np.nan),
        'macd_signal': last.get('MACD_signal', np.nan),
        'adx': last.get('ADX', np.nan),
        'atr': last.get('ATR', np.nan),
        'atr_pct': last.get('ATR_pct', np.nan),
        'bb_upper': last.get('BB_upper', np.nan),
        'bb_lower': last.get('BB_lower', np.nan),
        'bb_width': last.get('BB_width', np.nan),
        'volume': last.get('Volume', np.nan),
        'volume_ratio': last.get('Volume_ratio', np.nan),
    }
    
    return summary

def detect_sma_cross(df: pd.DataFrame) -> Dict[str, str]:
    """
    Rileva crossover recenti delle SMA.
    
    Args:
        df: DataFrame con SMA calcolate
    
    Returns:
        Dict con crossover detected
    """
    if len(df) < 2:
        return {}
    
    crosses = {}
    
    # Golden Cross / Death Cross (50/200)
    if 'SMA_50' in df.columns and 'SMA_200' in df.columns:
        sma50_curr = df['SMA_50'].iloc[-1]
        sma50_prev = df['SMA_50'].iloc[-2]
        sma200_curr = df['SMA_200'].iloc[-1]
        sma200_prev = df['SMA_200'].iloc[-2]
        
        # Golden Cross
        if sma50_prev < sma200_prev and sma50_curr > sma200_curr:
            crosses['golden_cross'] = 'bullish'
        # Death Cross
        elif sma50_prev > sma200_prev and sma50_curr < sma200_curr:
            crosses['death_cross'] = 'bearish'
    
    return crosses

def get_macd_signal(df: pd.DataFrame) -> str:
    """
    Determina segnale MACD (bullish/bearish/neutral).
    
    Args:
        df: DataFrame con MACD calcolato
    
    Returns:
        'bullish', 'bearish', o 'neutral'
    """
    if df.empty or 'MACD' not in df.columns:
        return 'neutral'
    
    last = df.iloc[-1]
    macd = last.get('MACD', 0)
    macd_signal = last.get('MACD_signal', 0)
    
    if macd > macd_signal and macd > 0:
        return 'bullish'
    elif macd < macd_signal and macd < 0:
        return 'bearish'
    else:
        return 'neutral'

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Technical Indicators Test")
    print("="*70)
    
    # Genera dati sample per testing
    print("\n1. Generazione dati sample...")
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)
    
    # Simula random walk con trend
    n = len(dates)
    returns = np.random.normal(0.001, 0.02, n)  # 0.1% mean return, 2% volatility
    prices = 100 * np.exp(np.cumsum(returns))
    
    # Crea DataFrame sample
    df_sample = pd.DataFrame({
        'Date': dates,
        'Open': prices * np.random.uniform(0.98, 1.02, n),
        'High': prices * np.random.uniform(1.00, 1.05, n),
        'Low': prices * np.random.uniform(0.95, 1.00, n),
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, n),
        'Adj Close': prices
    })
    
    print(f"   ✅ Sample data: {len(df_sample)} righe")
    print(f"   Range date: {df_sample['Date'].min()} → {df_sample['Date'].max()}")
    
    # 2. Test calcolo indicatori
    print("\n2. Calcolo tutti gli indicatori...")
    df_with_indicators = compute_all_indicators(df_sample)
    
    print(f"   ✅ DataFrame finale: {len(df_with_indicators.columns)} colonne")
    print(f"\n   Colonne disponibili:")
    indicator_cols = [col for col in df_with_indicators.columns 
                      if col not in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']]
    for col in sorted(indicator_cols):
        print(f"      - {col}")
    
    # 3. Test summary
    print("\n3. Indicator Summary (ultimi valori):")
    summary = get_indicator_summary(df_with_indicators)
    for key, value in summary.items():
        if not np.isnan(value):
            print(f"   {key:20s}: {value:10.2f}")
    
    # 4. Test crossover detection
    print("\n4. Crossover Detection:")
    crosses = detect_sma_cross(df_with_indicators)
    if crosses:
        for cross_type, signal in crosses.items():
            print(f"   {cross_type}: {signal}")
    else:
        print("   Nessun crossover rilevato")
    
    # 5. Test MACD signal
    print("\n5. MACD Signal:")
    macd_sig = get_macd_signal(df_with_indicators)
    print(f"   Current signal: {macd_sig}")
    
    # 6. Visualizza ultime 5 righe con indicatori chiave
    print("\n6. Ultime 5 righe (indicatori chiave):")
    key_cols = ['Date', 'Close', 'SMA_50', 'SMA_200', 'RSI', 'MACD', 'ADX', 'ATR_pct']
    print(df_with_indicators[key_cols].tail().to_string())
    
    print("\n" + "="*70)
    print("✅ Test completato con successo")
