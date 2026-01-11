# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Scoring System Module (Hybrid Logic)
============================================================================
Implementa sistema di scoring allineato alla logica del Notebook "Daily Market Analysis",
ma corretto matematicamente (SMA reali) e robusto.

- Trend Score (30%): SMA Pos + ADX + ROC + Pattern (Breakouts)
- Momentum Score (30%): RSI + MACD + ROC Composite
- Volatility Score (15%): Invertito (ATR, BB, HVol)
- Relative Strength Score (25%): Performance vs Benchmark

Ogni score è normalizzato 0-100.
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
# HELPER FUNCTIONS
# ============================================================================

def normalize_val(val: float, min_val: float, max_val: float) -> float:
    """Normalizza un valore tra 0 e 100 basandosi su un range min/max."""
    if pd.isna(val): return 50.0
    clipped = max(min(val, max_val), min_val)
    return ((clipped - min_val) / (max_val - min_val)) * 100

# ============================================================================
# INDIVIDUAL SCORE CALCULATIONS
# ============================================================================

def calculate_trend_score(df: pd.DataFrame) -> float:
    """
    Calcola Trend Score (0-100) - Logica Ibrida (Notebook + Fixes).
    
    Componenti:
    1. SMA Positioning (30%): Prezzo sopra le medie (20, 50, 125, 200).
    2. ADX Strength/Dir (25%): Forza del trend.
    3. ROC (25%): Momentum puro del prezzo (20 periodi).
    4. Pattern (20%): Breakout settimanali/giornalieri (Logica Notebook).
    """
    if df.empty or len(df) < 5:
        return 50.0
    
    last = df.iloc[-1]
    
    try:
        price = last['Close']
        
        # 1. SMA Positioning (30%)
        # +25 punti per ogni SMA superata (Logic Notebook corretta con SMA reali)
        sma_points = 0
        sma_count = 0
        for period in CONFIG['SMA_PERIODS']: # [20, 50, 125, 200]
            col = f'SMA_{period}'
            if col in df.columns and not pd.isna(last[col]):
                if price > last[col]:
                    sma_points += 25
                sma_count += 1
        
        # Normalizza se mancano alcune SMA
        if sma_count > 0:
            sma_comp = (sma_points / (sma_count * 25)) * 100
        else:
            sma_comp = 50.0
            
        # 2. ADX Direction (25%)
        # Base 50 +/- forza ADX
        adx = last.get('ADX', 20)
        p_di = last.get('plus_DI', 0)
        m_di = last.get('minus_DI', 0)
        
        # Clamp ADX a 50 per evitare eccessi
        adx_clamped = min(adx, 50)
        direction = 1 if p_di > m_di else -1
        
        # Formula: 50 + (Strenght * Direction)
        adx_comp = 50 + ((adx_clamped - 25) * 2 * direction)
        adx_comp = max(0, min(100, adx_comp))
        
        # 3. ROC Score (25%)
        # Usa ROC_20 come proxy principale, range +/- 10%
        roc = last.get('ROC_20', 0)
        roc_comp = normalize_val(roc, -10, 10)
        
        # 4. Pattern Score (20%) - Logica Notebook
        # "Breakout Score" basato su livelli weekly/daily calcolati in tech_indicators
        pattern_val = 50.0
        
        pwh = last.get('prev_week_high')
        pwl = last.get('prev_week_low')
        pdh = last.get('prev_day_high')
        pdl = last.get('prev_day_low')
        pivot = last.get('pivot_point') # o 'Pivot'
        
        # Gerarchia segnali
        if not pd.isna(pwh) and price > pwh:
            pattern_val = 100 # Breakout settimanale (Strong Bull)
        elif not pd.isna(pdh) and price > pdh:
            pattern_val = 75  # Breakout giornaliero
        elif not pd.isna(pivot) and price > pivot:
            pattern_val = 60  # Sopra Pivot
        elif not pd.isna(pdl) and price < pdl:
            pattern_val = 25  # Breakdown giornaliero
        elif not pd.isna(pwl) and price < pwl:
            pattern_val = 0   # Breakdown settimanale (Strong Bear)
            
        # SCORE FINALE PONDERATO
        final_score = (
            (sma_comp * 0.30) +
            (adx_comp * 0.25) +
            (roc_comp * 0.25) +
            (pattern_val * 0.20)
        )
        
        return min(max(final_score, 0), 100)
        
    except Exception as e:
        logger.warning(f"Errore calcolo trend score: {str(e)}")
        return 50.0

def calculate_momentum_score(df: pd.DataFrame) -> float:
    """
    Calcola Momentum Score (0-100).
    
    Componenti:
    1. RSI (35%): Diretto (0-100)
    2. MACD (35%): Trend istogramma e crossover
    3. ROC Composite (30%): Mix 10/20/60 periodi
    """
    if df.empty: return 50.0
    last = df.iloc[-1]
    
    try:
        # 1. RSI (35%)
        rsi = last.get('RSI', 50)
        rsi_score = rsi # RSI è già nativamente uno score 0-100
        
        # 2. MACD (35%)
        # Logica: Bullish > 50, Bearish < 50
        macd = last.get('MACD', 0)
        sig = last.get('MACD_signal', 0)
        hist = last.get('MACD_histogram', 0)
        
        # Base score su Crossover
        if macd > sig:
            macd_base = 60
            # Momentum bonus se istogramma cresce
            if len(df) >= 2 and hist > df.iloc[-2].get('MACD_histogram', 0):
                macd_base += 20 # Strong Momentum
        else:
            macd_base = 40
            # Momentum malus se istogramma scende
            if len(df) >= 2 and hist < df.iloc[-2].get('MACD_histogram', 0):
                macd_base -= 20 # Strong Negative Momentum
                
        macd_score = max(0, min(100, macd_base))
        
        # 3. ROC Composite (30%)
        roc10 = last.get('ROC_10', 0)
        roc20 = last.get('ROC_20', 0)
        roc60 = last.get('ROC_60', 0)
        
        # Media pesata ROC
        avg_roc = (roc10 * 0.5) + (roc20 * 0.3) + (roc60 * 0.2)
        # Normalizza su range +/- 15%
        roc_score = normalize_val(avg_roc, -15, 15)
        
        final_score = (
            (rsi_score * 0.35) +
            (macd_score * 0.35) +
            (roc_score * 0.30)
        )
        
        return min(max(final_score, 0), 100)
        
    except Exception as e:
        logger.warning(f"Errore momentum score: {e}")
        return 50.0

def calculate_volatility_score(df: pd.DataFrame) -> float:
    """
    Calcola Volatility Score (0-100).
    INVERTITO: 100 = Bassa Volatilità (Safe), 0 = Alta Volatilità (Risky).
    """
    if df.empty: return 50.0
    last = df.iloc[-1]
    
    try:
        # 1. ATR % (40%)
        atr_pct = last.get('ATR_pct', 2.0)
        # < 1% = 100 punti, > 5% = 0 punti
        atr_score = 100 - normalize_val(atr_pct, 1.0, 5.0)
        
        # 2. BB Width (35%)
        bbw = last.get('BB_width', 5.0)
        # < 5% = 100 punti, > 15% = 0 punti
        bb_score = 100 - normalize_val(bbw, 5.0, 15.0)
        
        # 3. HVol (25%)
        hvol = last.get('HVol_20', 15.0)
        # < 10% = 100 punti, > 40% = 0 punti
        hv_score = 100 - normalize_val(hvol, 10.0, 40.0)
        
        final_score = (atr_score * 0.40) + (bb_score * 0.35) + (hv_score * 0.25)
        
        return min(max(final_score, 0), 100)
        
    except Exception as e:
        logger.warning(f"Errore volatility score: {e}")
        return 50.0

def calculate_relative_strength_score(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    ticker: str
) -> float:
    """
    Calcola Relative Strength Score vs Benchmark (0-100).
    Logica robusta basata su Differenziale Rendimenti.
    """
    if df.empty or benchmark_df is None or benchmark_df.empty:
        return 50.0
    
    try:
        # Allinea date
        merged = pd.merge(
            df[['Date', 'Close']].rename(columns={'Close': 'ticker_close'}),
            benchmark_df[['Date', 'Close']].rename(columns={'Close': 'bench_close'}),
            on='Date',
            how='inner'
        )
        
        if len(merged) < 63: return 50.0
        
        score = 0.0
        
        # 1. Relative Return 1 mese (40%)
        t_ret_1m = merged['ticker_close'].pct_change(21).iloc[-1] * 100
        b_ret_1m = merged['bench_close'].pct_change(21).iloc[-1] * 100
        diff_1m = t_ret_1m - b_ret_1m
        
        # > +5% diff = 40 punti, < -5% = 0 punti
        score_1m = normalize_val(diff_1m, -5, 5) * 0.4 # max 40
        score += score_1m
        
        # 2. Relative Return 3 mesi (40%)
        t_ret_3m = merged['ticker_close'].pct_change(63).iloc[-1] * 100
        b_ret_3m = merged['bench_close'].pct_change(63).iloc[-1] * 100
        diff_3m = t_ret_3m - b_ret_3m
        
        # > +10% diff = 40 punti
        score_3m = normalize_val(diff_3m, -10, 10) * 0.4 # max 40
        score += score_3m
        
        # 3. Correlazione (20%)
        # Premia decorrelazione moderata (diversificazione)
        corr = merged['ticker_close'].pct_change().corr(merged['bench_close'].pct_change())
        
        if 0.5 <= corr <= 0.8:
            corr_score = 20 # Sweet spot
        elif 0.2 <= corr < 0.5 or 0.8 < corr <= 0.9:
            corr_score = 10
        else:
            corr_score = 5 # Troppo correlato o correlazione negativa estrema
            
        score += corr_score
        
        return min(max(score, 0), 100)
        
    except Exception as e:
        logger.warning(f"Errore RS score per {ticker}: {e}")
        return 50.0

# ============================================================================
# COMPOSITE SCORE CALCULATION
# ============================================================================

def calculate_composite_score(
    trend_score: float,
    momentum_score: float,
    volatility_score: float,
    relative_strength_score: float,
    weights: Dict[str, float] = None
) -> float:
    """Calcola Composite Score con pesi configurabili."""
    if weights is None:
        weights = CONFIG['WEIGHTS']
    
    composite = (
        trend_score * weights['TREND'] +
        momentum_score * weights['MOMENTUM'] +
        volatility_score * weights['VOLATILITY'] +
        relative_strength_score * weights['REL_STRENGTH']
    )
    
    return round(composite, 2)

# ============================================================================
# SCORING FOR SINGLE INSTRUMENT
# ============================================================================

def score_instrument(
    df: pd.DataFrame,
    ticker: str,
    benchmark_data: Dict[str, pd.DataFrame]
) -> Dict[str, float]:
    """Calcola tutti gli score per un singolo strumento."""
    logger.info(f"📊 Scoring {ticker}...")
    
    # Recupera benchmark
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
        'volatility': round(volatility_score, 2),
        'relative_strength': round(relative_strength_score, 2)
    }
    
    logger.info(f"   ✅ {ticker} Composite: {composite_score:.1f}")
    
    return scores

# ============================================================================
# BATCH SCORING & RANKING
# ============================================================================

def score_universe(
    data_dict: Dict[str, pd.DataFrame],
    progress_callback=None
) -> Dict[str, Dict[str, float]]:
    """Calcola score per tutti gli strumenti nell'universo."""
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
            all_scores[ticker] = {
                'composite': 50.0, 'trend': 50.0, 'momentum': 50.0,
                'volatility': 50.0, 'relative_strength': 50.0
            }
    
    return all_scores

def generate_rankings(scores_dict: Dict[str, Dict[str, float]]) -> Dict[str, List]:
    """Genera ranking ordinati per vari criteri."""
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
        'by_volatility': sorted(items, key=lambda x: x['volatility'], reverse=True),
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
    print("KRITERION QUANT - Scoring System Test (Hybrid Logic)")
    print("="*70)
    
    # Crea sample DataFrame
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    n = len(dates)
    
    df_test = pd.DataFrame({
        'Date': dates,
        'Close': 100 + np.cumsum(np.random.randn(n) * 0.5),
        'SMA_20': 100,
        'SMA_50': 99,
        'SMA_125': 98,
        'SMA_200': 97,
        'RSI': 55,
        'MACD': 0.5,
        'MACD_signal': 0.3,
        'MACD_histogram': 0.2,
        'ROC_10': 2.0,
        'ROC_20': 3.5,
        'ROC_60': 5.0,
        'ATR_pct': 1.5,
        'BB_width': 4.0,
        'HVol_20': 18.0,
        'HVol_60': 20.0,
        'prev_week_high': 105,
        'pivot_point': 100
    })
    
    print("\n1. Test Score Individuali:")
    trend = calculate_trend_score(df_test)
    momentum = calculate_momentum_score(df_test)
    volatility = calculate_volatility_score(df_test)
    
    print(f"   Trend Score:      {trend:.2f}")
    print(f"   Momentum Score:   {momentum:.2f}")
    print(f"   Volatility Score: {volatility:.2f}")
    
    print("\n2. Test Composite:")
    composite = calculate_composite_score(trend, momentum, volatility, 50.0)
    print(f"   Composite Score:  {composite:.2f}")
    
    print("\n" + "="*70)
    print("✅ Test completato")
