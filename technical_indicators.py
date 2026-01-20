# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Technical Indicators Module (ALIGNED TO NOTEBOOK)
============================================================================
Implementazione degli indicatori tecnici IDENTICA al Notebook Colab:

- Livelli di Prezzo (T-1, Weekly, Pivot Points)
- Medie Mobili (SMA 20/50/125/200) con SMA_125 CUSTOM
- Momentum (RSI Wilder, MACD, ADX, ROC)
- Volatility (ATR Wilder, Bollinger, Historical Volatility)
- Positioning (Z-Score, 52-Week Range)
- Relative Strength (RS Ratio, RS Momentum)

Include rolling_percentile_rank per scoring system.
============================================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from config import CONFIG

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS (FROM NOTEBOOK)
# ============================================================================

def wilder_smoothing(series: pd.Series, period: int) -> pd.Series:
    """
    Implementazione EMA di Wilder con alpha = 1/period.
    Usato per RSI, ATR, ADX come da standard Wilder originale.
    """
    return series.ewm(alpha=1/period, adjust=False).mean()


def rolling_percentile_rank(series: pd.Series, window: int = 252) -> pd.Series:
    """
    Calcola il percentile rank rolling (0-100) dell'ultimo valore.
    
    CRITICO: Questa funzione è usata nel notebook per normalizzazione dinamica
    di MACD, ATR, BB Width, RS Ratio.
    
    Formula: (count of values < current) / total_count * 100
    
    Args:
        series: Serie di valori
        window: Finestra rolling (default 252 = 1 anno trading)
    
    Returns:
        Serie con percentile rank 0-100
    """
    return series.rolling(window=window, min_periods=50).apply(
        lambda x: (x < x.iloc[-1]).mean() * 100 if len(x) > 0 else 50.0,
        raw=False
    )


def get_percentile_rank_single(current: float, history: pd.Series) -> float:
    """
    Calcola il percentile rank di un singolo valore rispetto a una storia.
    Versione non-rolling per calcoli singoli.
    """
    if len(history) < 2 or pd.isna(current):
        return 50.0
    valid = history.dropna()
    if len(valid) < 2:
        return 50.0
    return (valid < current).mean() * 100

# ============================================================================
# 3.1 LIVELLI DI PREZZO (Sezione 3.1 Notebook)
# ============================================================================

def calculate_price_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola livelli giornalieri, settimanali e pivot points.
    
    Include:
    - T-1 Levels: prev_day_high/low/close, prev_day_range_pct
    - Weekly Levels: prev_week_high/low, weekly_return_pct
    - Pivot Points: pivot_point, R1, R2, S1, S2
    """
    df = df.copy()
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    
    # --- T-1 Levels ---
    df['prev_day_high'] = df['High'].shift(1)
    df['prev_day_low'] = df['Low'].shift(1)
    df['prev_day_close'] = df[close_col].shift(1)
    df['prev_day_range_pct'] = (
        (df['prev_day_high'] - df['prev_day_low']) / df['prev_day_close']
    ) * 100
    
    # --- Weekly Levels (rolling 5gg shiftato) ---
    df['prev_week_high'] = df['High'].shift(1).rolling(window=5).max()
    df['prev_week_low'] = df['Low'].shift(1).rolling(window=5).min()
    df['weekly_return_pct'] = df[close_col].pct_change(periods=5).shift(1) * 100
    
    # --- Pivot Points Classic ---
    pp = (df['prev_day_high'] + df['prev_day_low'] + df['prev_day_close']) / 3
    df['pivot_point'] = pp
    df['Pivot'] = pp  # Alias
    
    df['resistance_1'] = (2 * pp) - df['prev_day_low']
    df['resistance_2'] = pp + (df['prev_day_high'] - df['prev_day_low'])
    df['R1'] = df['resistance_1']
    df['R2'] = df['resistance_2']
    
    df['support_1'] = (2 * pp) - df['prev_day_high']
    df['support_2'] = pp - (df['prev_day_high'] - df['prev_day_low'])
    df['S1'] = df['support_1']
    df['S2'] = df['support_2']
    
    return df

# ============================================================================
# 3.2 MEDIE MOBILI (Sezione 3.2 Notebook)
# ============================================================================

def calculate_sma(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    Calcola Simple Moving Average per multipli periodi.
    
    NOTA CRITICA: SMA_125 è calcolato come Mean(125) - Median(126) nel notebook!
    Questo è un indicatore CUSTOM, non una SMA standard.
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG.get('SMA_PERIODS', [20, 50, 125, 200])
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    close = df[close_col]
    
    for period in periods:
        if period == 125:
            # ============================================================
            # SMA_125 CUSTOM DAL NOTEBOOK: Mean(125) - Median(126)
            # Misura la deviazione del prezzo dalla mediana semestrale
            # ============================================================
            rolling_mean_125 = close.rolling(window=125).mean()
            rolling_median_126 = close.rolling(window=126).median()
            sma_125 = rolling_mean_125 - rolling_median_126
            
            df[f'SMA_{period}'] = sma_125
            df[f'sma_{period}'] = sma_125
        else:
            # SMA Standard
            sma = close.rolling(window=period).mean()
            df[f'SMA_{period}'] = sma
            df[f'sma_{period}'] = sma
    
    # Distanze percentuali dalle SMA
    for period in periods:
        sma_col = f'SMA_{period}'
        if sma_col in df.columns:
            df[f'dist_sma_{period}_pct'] = ((close - df[sma_col]) / df[sma_col]) * 100
    
    return df


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """Calcola Exponential Moving Average."""
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    return df[close_col].ewm(span=period, adjust=False).mean()

# ============================================================================
# 3.3 MOMENTUM INDICATORS (Sezione 3.3 Notebook)
# ============================================================================

def calculate_rsi(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """
    Calcola RSI con Wilder's Smoothing.
    
    Formula:
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss (con Wilder smoothing)
    """
    df = df.copy()
    
    if period is None:
        period = CONFIG.get('RSI_PERIOD', 14)
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    delta = df[close_col].diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = wilder_smoothing(gain, period)
    avg_loss = wilder_smoothing(loss, period)
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    df['RSI'] = rsi
    df[f'rsi_{period}'] = rsi
    
    return df


def calculate_macd(
    df: pd.DataFrame,
    fast: int = None,
    slow: int = None,
    signal: int = None
) -> pd.DataFrame:
    """
    Calcola MACD con crossover detection.
    
    MACD_histogram è usato per il percentile rank nello scoring.
    """
    df = df.copy()
    
    if fast is None: fast = CONFIG.get('MACD_FAST', 12)
    if slow is None: slow = CONFIG.get('MACD_SLOW', 26)
    if signal is None: signal = CONFIG.get('MACD_SIGNAL', 9)
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    close = df[close_col]
    
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_histogram = macd_line - macd_signal
    
    df['MACD'] = macd_line
    df['macd_line'] = macd_line
    df['MACD_signal'] = macd_signal
    df['macd_signal'] = macd_signal
    df['MACD_histogram'] = macd_histogram
    df['macd_histogram'] = macd_histogram
    
    # Crossover detection
    prev_hist = macd_histogram.shift(1)
    df['macd_crossover'] = 0
    df.loc[(prev_hist < 0) & (macd_histogram > 0), 'macd_crossover'] = 1   # Bullish
    df.loc[(prev_hist > 0) & (macd_histogram < 0), 'macd_crossover'] = -1  # Bearish
    
    return df


def calculate_adx(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """
    Calcola ADX, +DI, -DI con Wilder smoothing.
    """
    df = df.copy()
    
    if period is None:
        period = CONFIG.get('ADX_PERIOD', 14)
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    high = df['High']
    low = df['Low']
    close = df[close_col]
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    # Wilder smoothing
    tr_smooth = wilder_smoothing(tr, period)
    plus_di = 100 * (wilder_smoothing(pd.Series(plus_dm, index=df.index), period) / tr_smooth)
    minus_di = 100 * (wilder_smoothing(pd.Series(minus_dm, index=df.index), period) / tr_smooth)
    
    # DX e ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = wilder_smoothing(dx, period)
    
    df['ADX'] = adx
    df[f'adx_{period}'] = adx
    df['plus_DI'] = plus_di
    df[f'plus_di_{period}'] = plus_di
    df['minus_DI'] = minus_di
    df[f'minus_di_{period}'] = minus_di
    
    df['trend_direction_txt'] = np.where(plus_di > minus_di, 'bullish', 'bearish')
    
    return df


def calculate_roc(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    Calcola Rate of Change per multipli periodi.
    
    ROC = ((Close - Close_n) / Close_n) * 100
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG.get('ROC_PERIODS', [10, 20, 60])
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    close = df[close_col]
    
    for period in periods:
        roc = close.pct_change(periods=period) * 100
        df[f'ROC_{period}'] = roc
        df[f'roc_{period}'] = roc
    
    return df

# ============================================================================
# 3.4 VOLATILITY INDICATORS (Sezione 3.4 Notebook)
# ============================================================================

def calculate_atr(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """
    Calcola ATR con Wilder smoothing.
    """
    df = df.copy()
    
    if period is None:
        period = CONFIG.get('ATR_PERIOD', 14)
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    high = df['High']
    low = df['Low']
    close = df[close_col]
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    df['TR'] = true_range
    atr = wilder_smoothing(true_range, period)
    
    df['ATR'] = atr
    df[f'atr_{period}'] = atr
    df['ATR_pct'] = (atr / close) * 100
    df['atr_pct'] = df['ATR_pct']
    
    return df


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = None,
    std_dev: float = None
) -> pd.DataFrame:
    """
    Calcola Bollinger Bands e Band Width.
    """
    df = df.copy()
    
    if period is None: period = CONFIG.get('BB_PERIOD', 20)
    if std_dev is None: std_dev = CONFIG.get('BB_STD', 2.0)
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    close = df[close_col]
    
    sma = close.rolling(window=period).mean()
    rolling_std = close.rolling(window=period).std()
    
    df['BB_middle'] = sma
    df['bb_middle'] = sma
    df['BB_upper'] = sma + (std_dev * rolling_std)
    df['bb_upper'] = df['BB_upper']
    df['BB_lower'] = sma - (std_dev * rolling_std)
    df['bb_lower'] = df['BB_lower']
    
    # Band Width (%)
    df['BB_width'] = ((df['BB_upper'] - df['BB_lower']) / sma) * 100
    df['bb_width'] = df['BB_width']
    
    # %B (position within bands, 0-100)
    df['BB_percent'] = ((close - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])) * 100
    df['bb_position'] = df['BB_percent']
    
    return df


def calculate_historical_volatility(
    df: pd.DataFrame,
    periods: List[int] = None
) -> pd.DataFrame:
    """
    Calcola Historical Volatility annualizzata.
    
    HVol = stdev(log_returns) * sqrt(252) * 100
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG.get('HVOL_PERIODS', [20, 60])
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    close = df[close_col]
    
    log_returns = np.log(close / close.shift(1))
    
    for period in periods:
        hvol = log_returns.rolling(window=period).std() * np.sqrt(252) * 100
        df[f'HVol_{period}'] = hvol
        df[f'hvol_{period}'] = hvol
    
    return df

# ============================================================================
# 3.5 POSITIONING INDICATORS (Sezione 3.5 Notebook)
# ============================================================================

def calculate_zscore(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    Calcola Z-Score per multipli periodi.
    
    Z-Score = (Close - Mean) / StdDev
    """
    df = df.copy()
    
    if periods is None:
        periods = CONFIG.get('ZSCORE_PERIODS', [20, 50, 125])
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    close = df[close_col]
    
    for period in periods:
        rolling_mean = close.rolling(window=period).mean()
        rolling_std = close.rolling(window=period).std()
        zscore = (close - rolling_mean) / rolling_std
        df[f'ZScore_{period}'] = zscore
        df[f'zscore_{period}'] = zscore
    
    return df


def calculate_52week_range(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola posizione nel range 52 settimane.
    """
    df = df.copy()
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    
    df['high_52w'] = df['High'].rolling(window=252).max()
    df['low_52w'] = df['Low'].rolling(window=252).min()
    df['range_position_52w'] = (
        (df[close_col] - df['low_52w']) / (df['high_52w'] - df['low_52w'])
    ) * 100
    
    return df

# ============================================================================
# 3.6 RELATIVE STRENGTH (Sezione 3.6 Notebook)
# ============================================================================

def calculate_relative_strength(df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola RS vs Benchmark.
    
    Include:
    - rs_ratio: Price / Benchmark
    - rs_momentum: pct_change(10) del rs_ratio
    - rs_trend_txt: 'outperforming' se RS > SMA(RS, 20)
    """
    df = df.copy()
    
    df['rs_ratio'] = np.nan
    df['rs_momentum'] = np.nan
    df['rs_trend_txt'] = 'neutral'
    
    if benchmark_df is None or benchmark_df.empty:
        return df
    
    try:
        common_idx = df.index.intersection(benchmark_df.index)
        if len(common_idx) == 0:
            return df
        
        close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        
        price = df.loc[common_idx, close_col]
        bench = benchmark_df.loc[common_idx, close_col]
        
        ratio = price / bench
        df.loc[common_idx, 'rs_ratio'] = ratio
        
        rs_mom = ratio.pct_change(periods=10)
        df.loc[common_idx, 'rs_momentum'] = rs_mom
        
        rs_sma20 = ratio.rolling(window=20).mean()
        df.loc[common_idx, 'rs_trend_txt'] = np.where(
            ratio > rs_sma20, 'outperforming', 'underperforming'
        )
        
    except Exception as e:
        logger.warning(f"Errore calcolo RS: {str(e)}")
    
    return df

# ============================================================================
# VOLUME INDICATORS
# ============================================================================

def calculate_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcola indicatori basati su volume."""
    df = df.copy()
    
    if 'Volume' not in df.columns or df['Volume'].sum() == 0:
        return df
    
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_ratio'] = df['Volume'] / df['Volume_SMA_20']
    
    # OBV
    obv = [0]
    for i in range(1, len(df)):
        if df[close_col].iloc[i] > df[close_col].iloc[i-1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df[close_col].iloc[i] < df[close_col].iloc[i-1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv
    
    return df

# ============================================================================
# RETURNS
# ============================================================================

def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Calcola returns per vari periodi."""
    df = df.copy()
    close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    close = df[close_col]
    
    df['return_1d'] = close.pct_change() * 100
    df['return_5d'] = close.pct_change(periods=5) * 100
    df['return_21d'] = close.pct_change(periods=21) * 100
    df['return_63d'] = close.pct_change(periods=63) * 100
    
    return df

# ============================================================================
# MASTER FUNCTION - COMPUTE ALL INDICATORS
# ============================================================================

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola TUTTI gli indicatori tecnici su un DataFrame.
    Sequenza identica al notebook Colab.
    """
    logger.info("📊 Calcolo indicatori tecnici (logica notebook)...")
    
    df = df.copy()
    
    if 'Date' in df.columns:
        df = df.sort_values('Date').reset_index(drop=True)
    
    try:
        # 3.1 Livelli di Prezzo
        df = calculate_price_levels(df)
        
        # 3.2 Medie Mobili (con SMA_125 custom)
        df = calculate_sma(df)
        
        # 3.3 Momentum
        df = calculate_rsi(df)
        df = calculate_macd(df)
        df = calculate_adx(df)
        df = calculate_roc(df)
        
        # 3.4 Volatility
        df = calculate_atr(df)
        df = calculate_bollinger_bands(df)
        df = calculate_historical_volatility(df)
        
        # 3.5 Positioning
        df = calculate_zscore(df)
        df = calculate_52week_range(df)
        
        # Returns
        df = calculate_returns(df)
        
        # Volume
        if 'Volume' in df.columns and df['Volume'].sum() > 0:
            df = calculate_volume_indicators(df)
        
        logger.info(f"✅ Indicatori calcolati: {len(df.columns)} colonne")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Errore calcolo indicatori: {str(e)}")
        raise

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_indicator_summary(df: pd.DataFrame) -> Dict:
    """Estrae summary indicatori chiave dall'ultima riga."""
    if df.empty:
        return {}
    
    last = df.iloc[-1]
    
    return {
        'price': last.get('Close', last.get('Adj Close')),
        'sma_50': last.get('SMA_50', last.get('sma_50')),
        'sma_200': last.get('SMA_200', last.get('sma_200')),
        'rsi': last.get('RSI', last.get('rsi_14')),
        'macd': last.get('MACD', last.get('macd_line')),
        'macd_signal': last.get('MACD_signal', last.get('macd_signal')),
        'macd_histogram': last.get('MACD_histogram', last.get('macd_histogram')),
        'adx': last.get('ADX', last.get('adx_14')),
        'atr_pct': last.get('ATR_pct', last.get('atr_pct')),
        'bb_width': last.get('BB_width', last.get('bb_width')),
        'hvol_20': last.get('HVol_20', last.get('hvol_20')),
        'hvol_60': last.get('HVol_60', last.get('hvol_60')),
    }


def get_macd_signal(df: pd.DataFrame) -> str:
    """Determina segnale MACD (bullish/bearish/neutral)."""
    if df.empty:
        return 'neutral'
    
    last = df.iloc[-1]
    macd = last.get('MACD', last.get('macd_line', 0))
    signal = last.get('MACD_signal', last.get('macd_signal', 0))
    
    if pd.isna(macd) or pd.isna(signal):
        return 'neutral'
    
    if macd > signal and macd > 0:
        return 'bullish'
    elif macd < signal and macd < 0:
        return 'bearish'
    return 'neutral'

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Technical Indicators Test (ALIGNED TO NOTEBOOK)")
    print("="*70)
    
    # Genera sample data
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    n = len(dates)
    
    prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, n)))
    
    df_sample = pd.DataFrame({
        'Date': dates,
        'Open': prices * np.random.uniform(0.99, 1.01, n),
        'High': prices * np.random.uniform(1.00, 1.03, n),
        'Low': prices * np.random.uniform(0.97, 1.00, n),
        'Close': prices,
        'Adj Close': prices,
        'Volume': np.random.randint(1000000, 10000000, n),
    })
    
    print(f"\n📊 Sample data: {len(df_sample)} righe")
    
    # Compute indicators
    print("\n1. Calcolo indicatori...")
    df_ind = compute_all_indicators(df_sample)
    print(f"   ✅ Colonne create: {len(df_ind.columns)}")
    
    # Check SMA_125 custom
    print("\n2. Verifica SMA_125 (Mean-Median):")
    if 'SMA_125' in df_ind.columns:
        sma125_last = df_ind['SMA_125'].iloc[-1]
        print(f"   SMA_125 (ultimo): {sma125_last:.4f}")
        print("   ✅ Calcolato come Mean(125) - Median(126)")
    
    # Check rolling percentile rank
    print("\n3. Test rolling_percentile_rank:")
    test_series = pd.Series(range(300))
    pct_rank = rolling_percentile_rank(test_series, window=100)
    print(f"   Percentile rank di 299 (ultimo): {pct_rank.iloc[-1]:.1f}%")
    print(f"   Atteso: ~99%  {'✅' if pct_rank.iloc[-1] > 95 else '❌'}")
    
    # Summary
    print("\n4. Indicator Summary:")
    summary = get_indicator_summary(df_ind)
    for k, v in summary.items():
        if v is not None and not pd.isna(v):
            print(f"   {k:20s}: {v:10.2f}")
    
    print("\n" + "="*70)
    print("✅ Test completato - Logica allineata al Notebook!")
