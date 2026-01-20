# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Scoring System Module (ALIGNED TO NOTEBOOK)
============================================================================
Implementazione degli algoritmi di scoring IDENTICA alla logica del Notebook 
"Daily Market Analysis" Colab.

- Trend Score (30%): SMA Pos + ADX Dir + ROC + Pattern
- Momentum Score (30%): RSI + MACD Percentile Rank + ROC Composite
- Volatility Score (15%): Percentile Rank (ATR, BB, HVol Ratio)
- Relative Strength Score (25%): RS Ratio Percentile + Momentum Adjustment

Ogni score è normalizzato 0-100.
NOTA: Volatility Score è DIRETTO (alto=alta volatilità), l'inversione
      avviene nel Composite Score come da notebook.
============================================================================
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from config import CONFIG, UNIVERSE

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS (FROM NOTEBOOK)
# ============================================================================

def normalize_val(value: float, min_val: float, max_val: float) -> float:
    """
    Normalizza un valore tra 0 e 100 basandosi su un range min/max fisso.
    Identico al notebook.
    """
    if pd.isna(value):
        return 50.0
    clipped = max(min(value, max_val), min_val)
    return ((clipped - min_val) / (max_val - min_val)) * 100


def rolling_percentile_rank(series: pd.Series, window: int = 252) -> pd.Series:
    """
    Calcola il percentile rank rolling (0-100) dell'ultimo valore.
    CRITICO: Questa funzione è usata nel notebook per normalizzazione dinamica.
    
    Formula: (count of values < current) / total * 100
    
    Args:
        series: Serie pandas di valori
        window: Finestra rolling (default 252 = 1 anno trading)
    
    Returns:
        Serie con percentile rank per ogni punto
    """
    return series.rolling(window=window, min_periods=50).apply(
        lambda x: (x < x.iloc[-1]).mean() * 100 if len(x) > 0 else 50.0,
        raw=False
    )


def get_percentile_rank_single(current: float, history: pd.Series) -> float:
    """
    Calcola il percentile rank di un singolo valore rispetto a una storia.
    
    Args:
        current: Valore corrente
        history: Serie storica per confronto
    
    Returns:
        Percentile rank 0-100
    """
    if len(history) < 2 or pd.isna(current):
        return 50.0
    valid_history = history.dropna()
    if len(valid_history) < 2:
        return 50.0
    return (valid_history < current).mean() * 100

# ============================================================================
# TREND SCORE (Sezione 4.1 Notebook)
# ============================================================================

def calculate_trend_score(df: pd.DataFrame) -> float:
    """
    Calcola Trend Score (0-100) - LOGICA IDENTICA AL NOTEBOOK.
    
    Componenti (Sez 4.1):
    1. SMA Positioning (30%): +25 per ogni SMA sotto il prezzo
    2. ADX Direction (25%): 50 +/- (ADX-25)*2 * direction
    3. ROC Score (25%): ROC_20 normalizzato [-20%, +20%]
    4. Pattern Score (20%): Posizione vs livelli weekly/daily
    """
    if df.empty or len(df) < 5:
        return 50.0
    
    last = df.iloc[-1]
    
    try:
        close = last['Close']
        
        # =====================================================================
        # 1. SMA POSITIONING (30%) - Identico al notebook
        # +25 punti per ogni SMA superata
        # =====================================================================
        sma_score = 0
        sma_columns = ['SMA_20', 'SMA_50', 'SMA_125', 'SMA_200']
        
        for sma_col in sma_columns:
            # Prova anche nomi lowercase (sma_20, sma_50, etc.)
            col = sma_col if sma_col in df.columns else sma_col.lower()
            if col in df.columns and not pd.isna(last.get(col)):
                if close > last[col]:
                    sma_score += 25
        
        # sma_score è già 0-100 (0, 25, 50, 75, o 100)
        
        # =====================================================================
        # 2. ADX DIRECTION (25%) - Identico al notebook
        # Base 50, +/- forza ADX in base alla direzione
        # =====================================================================
        adx_col = 'ADX' if 'ADX' in df.columns else 'adx_14'
        plus_di_col = 'plus_DI' if 'plus_DI' in df.columns else 'plus_di_14'
        minus_di_col = 'minus_DI' if 'minus_DI' in df.columns else 'minus_di_14'
        
        adx = last.get(adx_col, 20)
        plus_di = last.get(plus_di_col, 50)
        minus_di = last.get(minus_di_col, 50)
        
        if pd.isna(adx):
            adx = 20
        if pd.isna(plus_di):
            plus_di = 50
        if pd.isna(minus_di):
            minus_di = 50
        
        # Clamp ADX tra 0 e 50 per non sforare
        adx_clamped = max(0, min(adx, 50))
        
        # Direzione: +1 se bullish (+DI > -DI), -1 se bearish
        direction_mult = 1 if plus_di > minus_di else -1
        
        # Formula notebook: 50 + (adx_clamped - 25) * 2 * direction
        adx_comp_score = 50 + ((adx_clamped - 25) * 2 * direction_mult)
        adx_comp_score = max(0, min(100, adx_comp_score))
        
        # =====================================================================
        # 3. ROC SCORE (25%) - Notebook usa range [-20, +20]
        # =====================================================================
        roc_col = 'ROC_20' if 'ROC_20' in df.columns else 'roc_20'
        roc_20 = last.get(roc_col, 0)
        if pd.isna(roc_20):
            roc_20 = 0
        
        # Normalizza ROC_20 su range [-20%, +20%] -> 0-100
        roc_score = normalize_val(roc_20, -20, 20)
        
        # =====================================================================
        # 4. PATTERN SCORE (20%) - Logica notebook con livelli
        # Close > prev_week_high = 100 (Breakout)
        # Close > prev_day_high = 75
        # Close > pivot = 50 (Base) <-- QUESTO MANCAVA NEL REPO
        # Close < prev_day_low = 25
        # Close < prev_week_low = 0 (Breakdown)
        # =====================================================================
        pattern_score = 50.0  # Default: neutro
        
        # Recupera livelli
        pwh = last.get('prev_week_high')
        pwl = last.get('prev_week_low')
        pdh = last.get('prev_day_high')
        pdl = last.get('prev_day_low')
        pivot = last.get('pivot_point') or last.get('Pivot')
        
        # Applica logica gerarchica (dal più forte al più debole)
        # L'ordine è importante: prima i più estremi
        if not pd.isna(pwl) and close < pwl:
            pattern_score = 0.0    # Breakdown settimanale (Strong Bear)
        elif not pd.isna(pdl) and close < pdl:
            pattern_score = 25.0   # Breakdown giornaliero
        elif not pd.isna(pwh) and close > pwh:
            pattern_score = 100.0  # Breakout settimanale (Strong Bull)
        elif not pd.isna(pdh) and close > pdh:
            pattern_score = 75.0   # Breakout giornaliero
        elif not pd.isna(pivot) and close > pivot:
            pattern_score = 60.0   # Sopra Pivot (leggermente bullish)
        # else: rimane 50 (neutro)
        
        # =====================================================================
        # TREND SCORE FINALE - Pesi dal notebook
        # =====================================================================
        trend_score = (
            (sma_score * 0.30) +
            (adx_comp_score * 0.25) +
            (roc_score * 0.25) +
            (pattern_score * 0.20)
        )
        
        return max(0, min(100, trend_score))
        
    except Exception as e:
        logger.warning(f"Errore calcolo trend score: {str(e)}")
        return 50.0

# ============================================================================
# MOMENTUM SCORE (Sezione 4.2 Notebook)
# ============================================================================

def calculate_momentum_score(df: pd.DataFrame) -> float:
    """
    Calcola Momentum Score (0-100) - LOGICA IDENTICA AL NOTEBOOK.
    
    Componenti (Sez 4.2):
    1. RSI 14 (35%): Valore diretto 0-100
    2. MACD Histogram (35%): PERCENTILE RANK su 252 giorni
    3. ROC Composite (30%): Media pesata ROC 10/20/60, normalizzata [-20,+20]
    
    NOTA CRITICA: Il notebook usa percentile rank per MACD, NON logica crossover!
    """
    if df.empty or len(df) < 50:
        return 50.0
    
    last = df.iloc[-1]
    
    try:
        # =====================================================================
        # 1. RSI SCORE (35%) - Diretto, già 0-100
        # =====================================================================
        rsi_col = 'RSI' if 'RSI' in df.columns else 'rsi_14'
        rsi = last.get(rsi_col, 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_score = max(0, min(100, rsi))
        
        # =====================================================================
        # 2. MACD HISTOGRAM PERCENTILE RANK (35%)
        # CRITICO: Notebook usa percentile rank, NON logica crossover!
        # =====================================================================
        macd_hist_col = 'MACD_histogram' if 'MACD_histogram' in df.columns else 'macd_histogram'
        
        if macd_hist_col in df.columns:
            # Calcola percentile rank rolling su 252 giorni
            macd_percentile_series = rolling_percentile_rank(df[macd_hist_col], window=252)
            macd_rank = macd_percentile_series.iloc[-1]
            if pd.isna(macd_rank):
                macd_rank = 50.0
        else:
            macd_rank = 50.0
        
        macd_score = max(0, min(100, macd_rank))
        
        # =====================================================================
        # 3. ROC COMPOSITE (30%)
        # Media pesata: ROC_10 * 0.5 + ROC_20 * 0.3 + ROC_60 * 0.2
        # Normalizzata su range [-20, +20]
        # =====================================================================
        roc10_col = 'ROC_10' if 'ROC_10' in df.columns else 'roc_10'
        roc20_col = 'ROC_20' if 'ROC_20' in df.columns else 'roc_20'
        roc60_col = 'ROC_60' if 'ROC_60' in df.columns else 'roc_60'
        
        roc10 = last.get(roc10_col, 0)
        roc20 = last.get(roc20_col, 0)
        roc60 = last.get(roc60_col, 0)
        
        if pd.isna(roc10): roc10 = 0
        if pd.isna(roc20): roc20 = 0
        if pd.isna(roc60): roc60 = 0
        
        # Media pesata come da notebook
        roc_composite_val = (roc10 * 0.5) + (roc20 * 0.3) + (roc60 * 0.2)
        
        # Normalizza su [-20, +20] come da notebook
        roc_comp_score = normalize_val(roc_composite_val, -20, 20)
        
        # =====================================================================
        # MOMENTUM SCORE FINALE - Pesi dal notebook
        # =====================================================================
        momentum_score = (
            (rsi_score * 0.35) +
            (macd_score * 0.35) +
            (roc_comp_score * 0.30)
        )
        
        return max(0, min(100, momentum_score))
        
    except Exception as e:
        logger.warning(f"Errore calcolo momentum score: {str(e)}")
        return 50.0

# ============================================================================
# VOLATILITY SCORE (Sezione 4.3 Notebook)
# ============================================================================

def calculate_volatility_score(df: pd.DataFrame) -> float:
    """
    Calcola Volatility Score (0-100) - LOGICA IDENTICA AL NOTEBOOK.
    
    NOTA: Score ALTO = ALTA volatilità = ALTO rischio
    L'inversione (100-vol) avviene nel Composite Score, NON qui!
    
    Componenti (Sez 4.3):
    1. ATR Percentile (40%): Percentile rank su 252 giorni
    2. BB Width Percentile (35%): Percentile rank su 252 giorni
    3. HVol Ratio (25%): hvol_20 / hvol_60 normalizzato [0.5, 1.5]
    """
    if df.empty or len(df) < 50:
        return 50.0
    
    last = df.iloc[-1]
    
    try:
        # =====================================================================
        # 1. ATR PERCENTILE RANK (40%)
        # =====================================================================
        atr_pct_col = 'ATR_pct' if 'ATR_pct' in df.columns else 'atr_pct'
        
        if atr_pct_col in df.columns:
            atr_percentile_series = rolling_percentile_rank(df[atr_pct_col], window=252)
            atr_rank = atr_percentile_series.iloc[-1]
            if pd.isna(atr_rank):
                atr_rank = 50.0
        else:
            atr_rank = 50.0
        
        # =====================================================================
        # 2. BB WIDTH PERCENTILE RANK (35%)
        # =====================================================================
        bb_width_col = 'BB_width' if 'BB_width' in df.columns else 'bb_width'
        
        if bb_width_col in df.columns:
            bb_percentile_series = rolling_percentile_rank(df[bb_width_col], window=252)
            bb_rank = bb_percentile_series.iloc[-1]
            if pd.isna(bb_rank):
                bb_rank = 50.0
        else:
            bb_rank = 50.0
        
        # =====================================================================
        # 3. HVOL RATIO (25%)
        # Notebook: hvol_20 / hvol_60, normalizzato [0.5, 1.5]
        # Se > 1: volatilità in espansione
        # Se < 1: volatilità in contrazione
        # =====================================================================
        hvol20_col = 'HVol_20' if 'HVol_20' in df.columns else 'hvol_20'
        hvol60_col = 'HVol_60' if 'HVol_60' in df.columns else 'hvol_60'
        
        hvol_20 = last.get(hvol20_col, 20)
        hvol_60 = last.get(hvol60_col, 20)
        
        if pd.isna(hvol_20): hvol_20 = 20
        if pd.isna(hvol_60) or hvol_60 == 0: hvol_60 = 20
        
        # Calcola ratio
        hv_ratio = hvol_20 / hvol_60 if hvol_60 != 0 else 1.0
        
        # Normalizza su range [0.5, 1.5]
        hv_score = normalize_val(hv_ratio, 0.5, 1.5)
        
        # =====================================================================
        # VOLATILITY SCORE FINALE - Pesi dal notebook
        # NOTA: Score DIRETTO (alto = alta volatilità)
        # =====================================================================
        volatility_score = (
            (atr_rank * 0.40) +
            (bb_rank * 0.35) +
            (hv_score * 0.25)
        )
        
        return max(0, min(100, volatility_score))
        
    except Exception as e:
        logger.warning(f"Errore calcolo volatility score: {str(e)}")
        return 50.0

# ============================================================================
# RELATIVE STRENGTH SCORE (Sezione 4.4 Notebook)
# ============================================================================

def calculate_relative_strength_score(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    ticker: str
) -> float:
    """
    Calcola Relative Strength Score (0-100) - LOGICA IDENTICA AL NOTEBOOK.
    
    Componenti (Sez 4.4):
    1. RS Ratio Percentile Rank (Base): Percentile rank del rapporto Price/Benchmark
    2. RS Momentum Adjustment: rs_momentum * 100 * 0.5
    
    Formula: rs_score = rs_rank + (rs_momentum * 100 * 0.5), clipped 0-100
    """
    if df.empty:
        return 50.0
    
    # Gestione casi speciali
    ticker_info = UNIVERSE.get(ticker, {})
    benchmark_ticker = ticker_info.get('benchmark', 'SPY')
    
    # Se benchmark è se stesso o N/A
    if benchmark_ticker in ['Self', ticker, 'N/A'] or benchmark_df is None or benchmark_df.empty:
        return 50.0
    
    try:
        # =====================================================================
        # ALLINEAMENTO DATE E CALCOLO RS RATIO
        # =====================================================================
        # Merge su Date
        df_close = df[['Date', 'Close']].copy()
        df_close.columns = ['Date', 'ticker_close']
        
        bench_close = benchmark_df[['Date', 'Close']].copy()
        bench_close.columns = ['Date', 'bench_close']
        
        merged = pd.merge(df_close, bench_close, on='Date', how='inner')
        
        if len(merged) < 50:
            return 50.0
        
        # Calcola RS Ratio = Price / Benchmark
        merged['rs_ratio'] = merged['ticker_close'] / merged['bench_close']
        
        # =====================================================================
        # 1. RS RATIO PERCENTILE RANK (Base)
        # =====================================================================
        rs_percentile_series = rolling_percentile_rank(merged['rs_ratio'], window=252)
        rs_rank = rs_percentile_series.iloc[-1]
        
        if pd.isna(rs_rank):
            rs_rank = 50.0
        
        # =====================================================================
        # 2. RS MOMENTUM ADJUSTMENT
        # Notebook: rs_momentum = pct_change(10) del rs_ratio
        # Adjustment: rs_momentum * 100 * 0.5
        # =====================================================================
        merged['rs_momentum'] = merged['rs_ratio'].pct_change(periods=10)
        rs_momentum = merged['rs_momentum'].iloc[-1]
        
        if pd.isna(rs_momentum):
            rs_momentum = 0.0
        
        # Adjustment: converti in punti
        # Se rs_momentum = 0.05 (+5%), adjustment = 0.05 * 100 * 0.5 = 2.5 punti
        momentum_adjustment = rs_momentum * 100 * 0.5
        
        # =====================================================================
        # RS SCORE FINALE
        # =====================================================================
        rs_score = rs_rank + momentum_adjustment
        
        return max(0, min(100, rs_score))
        
    except Exception as e:
        logger.warning(f"Errore calcolo RS score per {ticker}: {str(e)}")
        return 50.0

# ============================================================================
# COMPOSITE SCORE (Sezione 4.5 Notebook)
# ============================================================================

def calculate_composite_score(
    trend_score: float,
    momentum_score: float,
    volatility_score: float,
    relative_strength_score: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Calcola Composite Score - LOGICA IDENTICA AL NOTEBOOK.
    
    Formula (Sez 4.5):
    composite = trend*0.30 + momentum*0.30 + (100-volatility)*0.15 + rs*0.25
    
    NOTA: Volatility score è INVERTITO qui perché "bassa volatilità è positiva"
    """
    if weights is None:
        weights = CONFIG['WEIGHTS']
    
    # Inversione volatility come da notebook
    # Alto volatility_score = alta volatilità = NEGATIVO per composite
    volatility_inverted = 100 - volatility_score
    
    composite = (
        trend_score * weights['TREND'] +
        momentum_score * weights['MOMENTUM'] +
        volatility_inverted * weights['VOLATILITY'] +
        relative_strength_score * weights['REL_STRENGTH']
    )
    
    return round(max(0, min(100, composite)), 2)

# ============================================================================
# SCORING FOR SINGLE INSTRUMENT
# ============================================================================

def score_instrument(
    df: pd.DataFrame,
    ticker: str,
    benchmark_data: Dict[str, pd.DataFrame]
) -> Dict[str, float]:
    """
    Calcola tutti gli score per un singolo strumento.
    
    Args:
        df: DataFrame con indicatori calcolati
        ticker: Symbol ticker
        benchmark_data: Dict con DataFrames di tutti i ticker (per benchmark lookup)
    
    Returns:
        Dict con composite, trend, momentum, volatility, relative_strength
    """
    logger.info(f"📊 Scoring {ticker}...")
    
    # Recupera benchmark DataFrame
    ticker_info = UNIVERSE.get(ticker, {})
    benchmark_ticker = ticker_info.get('benchmark', 'SPY')
    benchmark_df = benchmark_data.get(benchmark_ticker)
    
    # Calcola score individuali
    trend_score = calculate_trend_score(df)
    momentum_score = calculate_momentum_score(df)
    volatility_score = calculate_volatility_score(df)
    relative_strength_score = calculate_relative_strength_score(
        df, benchmark_df, ticker
    )
    
    # Calcola composite
    composite_score = calculate_composite_score(
        trend_score,
        momentum_score,
        volatility_score,
        relative_strength_score
    )
    
    scores = {
        'composite': composite_score,
        'trend': round(trend_score, 2),
        'momentum': round(momentum_score, 2),
        'volatility': round(volatility_score, 2),  # Score diretto (alto=volatile)
        'relative_strength': round(relative_strength_score, 2)
    }
    
    logger.info(f"   ✅ {ticker} Composite: {composite_score:.1f} "
                f"(T:{trend_score:.0f} M:{momentum_score:.0f} "
                f"V:{volatility_score:.0f} RS:{relative_strength_score:.0f})")
    
    return scores

# ============================================================================
# BATCH SCORING & RANKING
# ============================================================================

def score_universe(
    data_dict: Dict[str, pd.DataFrame],
    progress_callback=None
) -> Dict[str, Dict[str, float]]:
    """
    Calcola score per tutti gli strumenti nell'universo.
    
    Args:
        data_dict: Dict ticker -> DataFrame con indicatori
        progress_callback: Callback per progress bar (opzionale)
    
    Returns:
        Dict ticker -> Dict scores
    """
    logger.info(f"🚀 Scoring universe: {len(data_dict)} strumenti")
    
    all_scores = {}
    total = len(data_dict)
    
    for i, (ticker, df) in enumerate(data_dict.items(), 1):
        try:
            if progress_callback:
                progress_callback(i, total, ticker)
            
            scores = score_instrument(df, ticker, data_dict)
            all_scores[ticker] = scores
            
        except Exception as e:
            logger.error(f"❌ Errore scoring {ticker}: {str(e)}")
            # Fallback scores
            all_scores[ticker] = {
                'composite': 50.0,
                'trend': 50.0,
                'momentum': 50.0,
                'volatility': 50.0,
                'relative_strength': 50.0
            }
    
    logger.info(f"✅ Scoring completato: {len(all_scores)} strumenti")
    
    return all_scores


def generate_rankings(scores_dict: Dict[str, Dict[str, float]]) -> Dict[str, List]:
    """
    Genera ranking ordinati per vari criteri.
    
    Args:
        scores_dict: Output da score_universe()
    
    Returns:
        Dict con liste ordinate per ogni criterio
    """
    items = []
    for ticker, scores in scores_dict.items():
        items.append({
            'ticker': ticker,
            'composite': scores.get('composite', 0),
            'trend': scores.get('trend', 0),
            'momentum': scores.get('momentum', 0),
            'volatility': scores.get('volatility', 0),
            'relative_strength': scores.get('relative_strength', 0)
        })
    
    rankings = {
        'by_composite_score': sorted(items, key=lambda x: x['composite'], reverse=True),
        'by_trend': sorted(items, key=lambda x: x['trend'], reverse=True),
        'by_momentum': sorted(items, key=lambda x: x['momentum'], reverse=True),
        # Volatility: ordine inverso (bassa vol = meglio)
        'by_volatility': sorted(items, key=lambda x: x['volatility'], reverse=False),
        'by_relative_strength': sorted(items, key=lambda x: x['relative_strength'], reverse=True),
    }
    
    return rankings

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_top_n(rankings: Dict[str, List], criterion: str = 'by_composite_score', n: int = 5) -> List:
    """Estrae top N ticker per criterio."""
    return rankings.get(criterion, [])[:n]


def get_bottom_n(rankings: Dict[str, List], criterion: str = 'by_composite_score', n: int = 5) -> List:
    """Estrae bottom N ticker per criterio."""
    return rankings.get(criterion, [])[-n:]


def get_score_distribution(scores_dict: Dict[str, Dict[str, float]]) -> Dict:
    """Calcola statistiche distribuzione score."""
    composite_scores = [s['composite'] for s in scores_dict.values()]
    
    if not composite_scores:
        return {}
    
    return {
        'mean': np.mean(composite_scores),
        'median': np.median(composite_scores),
        'std': np.std(composite_scores),
        'min': np.min(composite_scores),
        'max': np.max(composite_scores),
        'count': len(composite_scores)
    }

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Scoring System Test (ALIGNED TO NOTEBOOK)")
    print("="*70)
    
    # Crea sample DataFrame con tutti gli indicatori necessari
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    n = len(dates)
    
    # Simula prezzo con trend
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    
    df_test = pd.DataFrame({
        'Date': dates,
        'Close': prices,
        # SMA
        'SMA_20': pd.Series(prices).rolling(20).mean(),
        'SMA_50': pd.Series(prices).rolling(50).mean(),
        'SMA_125': pd.Series(prices).rolling(125).mean(),
        'SMA_200': pd.Series(prices).rolling(200).mean(),
        # Momentum
        'RSI': 55 + np.random.randn(n) * 10,
        'MACD_histogram': np.random.randn(n) * 0.5,
        'ROC_10': np.random.randn(n) * 3,
        'ROC_20': np.random.randn(n) * 4,
        'ROC_60': np.random.randn(n) * 5,
        # ADX
        'ADX': 25 + np.random.randn(n) * 5,
        'plus_DI': 30 + np.random.randn(n) * 5,
        'minus_DI': 25 + np.random.randn(n) * 5,
        # Volatility
        'ATR_pct': 1.5 + np.abs(np.random.randn(n) * 0.5),
        'BB_width': 4 + np.abs(np.random.randn(n) * 1),
        'HVol_20': 18 + np.random.randn(n) * 3,
        'HVol_60': 20 + np.random.randn(n) * 2,
        # Price Levels
        'prev_week_high': prices * 1.02,
        'prev_week_low': prices * 0.98,
        'prev_day_high': prices * 1.01,
        'prev_day_low': prices * 0.99,
        'pivot_point': prices,
    })
    
    # Fill NaN
    df_test = df_test.fillna(method='ffill').fillna(50)
    
    print("\n1. Test Score Individuali (ultima riga):")
    trend = calculate_trend_score(df_test)
    momentum = calculate_momentum_score(df_test)
    volatility = calculate_volatility_score(df_test)
    
    print(f"   Trend Score:      {trend:.2f}")
    print(f"   Momentum Score:   {momentum:.2f}")
    print(f"   Volatility Score: {volatility:.2f} (alto = alta volatilità)")
    
    print("\n2. Test Composite (con RS=50 mock):")
    composite = calculate_composite_score(trend, momentum, volatility, 50.0)
    print(f"   Composite Score:  {composite:.2f}")
    
    print("\n3. Formula Composite verificata:")
    vol_inv = 100 - volatility
    manual_composite = trend*0.30 + momentum*0.30 + vol_inv*0.15 + 50*0.25
    print(f"   Manual calc:      {manual_composite:.2f}")
    print(f"   Match: {'✅' if abs(composite - manual_composite) < 0.1 else '❌'}")
    
    print("\n4. Test Rolling Percentile Rank:")
    test_series = pd.Series(np.random.randn(300))
    pct_rank = rolling_percentile_rank(test_series, 252)
    print(f"   Last percentile rank: {pct_rank.iloc[-1]:.2f}")
    
    print("\n" + "="*70)
    print("✅ Test completato - Logica allineata al Notebook!")
