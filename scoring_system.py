# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Scoring System Module
============================================================================
Implementa sistema di scoring multi-dimensionale:
- Trend Score (30%)
- Momentum Score (30%)
- Volatility Score (15% - invertito)
- Relative Strength Score (25%)

Ogni score è normalizzato 0-100, poi combinato con pesi configurabili.
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
# INDIVIDUAL SCORE CALCULATIONS
# ============================================================================

def calculate_trend_score(df: pd.DataFrame) -> float:
    """
    Calcola Trend Score (0-100).
    
    Componenti:
    - Posizione prezzo vs SMA (20, 50, 125, 200)
    - Slope delle SMA (trending up/down)
    - SMA alignment (bullish/bearish configuration)
    
    Args:
        df: DataFrame con SMA calcolate
    
    Returns:
        Score 0-100 (100 = trend fortemente rialzista)
    """
    if df.empty or len(df) < 2:
        return 50.0  # Neutral default
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    score = 0.0
    max_score = 100.0
    
    try:
        price = last['Close']
        
        # 1. Price vs SMA (40 punti)
        sma_scores = []
        for period in CONFIG['SMA_PERIODS']:
            col = f'SMA_{period}'
            if col in df.columns and not pd.isna(last[col]):
                if price > last[col]:
                    # Prezzo sopra SMA - calcola distanza percentuale
                    distance = ((price - last[col]) / last[col]) * 100
                    # Cap al 10% per evitare outlier
                    sma_score = min(distance * 10, 10)  # Max 10 punti per SMA
                    sma_scores.append(sma_score)
                else:
                    # Prezzo sotto SMA - penalità
                    sma_scores.append(0)
        
        if sma_scores:
            score += sum(sma_scores)  # Max 40 punti (4 SMA * 10)
        
        # 2. SMA Slope (30 punti)
        # SMA in salita = bullish
        slope_scores = []
        for period in CONFIG['SMA_PERIODS']:
            col = f'SMA_{period}'
            if col in df.columns and not pd.isna(last[col]) and not pd.isna(prev[col]):
                slope = ((last[col] - prev[col]) / prev[col]) * 100
                # Normalizza slope: +1% = 7.5 punti
                slope_score = min(max(slope * 750, 0), 7.5)
                slope_scores.append(slope_score)
        
        if slope_scores:
            score += sum(slope_scores)  # Max 30 punti (4 SMA * 7.5)
        
        # 3. SMA Alignment (30 punti)
        # Configurazione ideale: prezzo > SMA20 > SMA50 > SMA125 > SMA200
        alignment_score = 0
        sma_values = []
        for period in CONFIG['SMA_PERIODS']:
            col = f'SMA_{period}'
            if col in df.columns and not pd.isna(last[col]):
                sma_values.append(last[col])
        
        if len(sma_values) >= 2:
            # Check se sono in ordine decrescente (bullish)
            is_aligned = all(sma_values[i] > sma_values[i+1] 
                           for i in range(len(sma_values)-1))
            if is_aligned:
                alignment_score = 30
            else:
                # Partial credit per allineamento parziale
                aligned_pairs = sum(1 for i in range(len(sma_values)-1) 
                                  if sma_values[i] > sma_values[i+1])
                alignment_score = (aligned_pairs / (len(sma_values)-1)) * 30
        
        score += alignment_score
        
        # Normalizza a 0-100
        normalized_score = min(max(score, 0), max_score)
        
        return normalized_score
        
    except Exception as e:
        logger.warning(f"Errore calcolo trend score: {str(e)}")
        return 50.0

def calculate_momentum_score(df: pd.DataFrame) -> float:
    """
    Calcola Momentum Score (0-100).
    
    Componenti:
    - RSI (not overbought/oversold = good)
    - MACD (bullish crossover = good)
    - ROC multi-period
    
    Args:
        df: DataFrame con indicatori momentum
    
    Returns:
        Score 0-100 (100 = momentum fortemente positivo)
    """
    if df.empty:
        return 50.0
    
    last = df.iloc[-1]
    score = 0.0
    
    try:
        # 1. RSI Score (40 punti)
        if 'RSI' in df.columns and not pd.isna(last['RSI']):
            rsi = last['RSI']
            
            if 40 <= rsi <= 60:
                # Range neutrale = massimo score
                rsi_score = 40
            elif 30 < rsi < 40 or 60 < rsi < 70:
                # Range moderato
                rsi_score = 30
            elif 20 < rsi <= 30 or 70 <= rsi < 80:
                # Vicino a oversold/overbought
                rsi_score = 20
            else:
                # Estremi (< 20 o > 80) = basso score
                rsi_score = 10
            
            score += rsi_score
        
        # 2. MACD Score (30 punti)
        if all(col in df.columns for col in ['MACD', 'MACD_signal', 'MACD_histogram']):
            macd = last['MACD']
            signal = last['MACD_signal']
            histogram = last['MACD_histogram']
            
            if not any(pd.isna([macd, signal, histogram])):
                # MACD sopra signal = bullish
                if macd > signal:
                    macd_score = 20
                    # Bonus se histogram in crescita
                    if len(df) >= 2:
                        prev_hist = df.iloc[-2]['MACD_histogram']
                        if histogram > prev_hist:
                            macd_score += 10
                else:
                    macd_score = 5
                
                score += macd_score
        
        # 3. ROC Score (30 punti)
        roc_scores = []
        for period in CONFIG['ROC_PERIODS']:
            col = f'ROC_{period}'
            if col in df.columns and not pd.isna(last[col]):
                roc = last[col]
                # ROC positivo = good, normalizza
                if roc > 0:
                    # +5% ROC = 10 punti
                    roc_score = min(roc * 2, 10)
                else:
                    # ROC negativo = 0 punti
                    roc_score = 0
                
                roc_scores.append(roc_score)
        
        if roc_scores:
            score += sum(roc_scores)  # Max 30 punti (3 periodi * 10)
        
        # Normalizza a 0-100
        normalized_score = min(max(score, 0), 100)
        
        return normalized_score
        
    except Exception as e:
        logger.warning(f"Errore calcolo momentum score: {str(e)}")
        return 50.0

def calculate_volatility_score(df: pd.DataFrame) -> float:
    """
    Calcola Volatility Score (0-100).
    
    NOTA: Questo score è INVERTITO nel composite score.
    Bassa volatilità = score alto (desiderabile per ridurre rischio).
    
    Componenti:
    - ATR percentuale
    - Bollinger Band width
    - Historical Volatility
    
    Args:
        df: DataFrame con indicatori volatilità
    
    Returns:
        Score 0-100 (100 = bassa volatilità, stabile)
    """
    if df.empty:
        return 50.0
    
    last = df.iloc[-1]
    score = 0.0
    
    try:
        # 1. ATR Percentage Score (40 punti)
        if 'ATR_pct' in df.columns and not pd.isna(last['ATR_pct']):
            atr_pct = last['ATR_pct']
            
            # ATR < 1% = bassa volatilità = high score
            # ATR > 5% = alta volatilità = low score
            if atr_pct < 1.0:
                atr_score = 40
            elif atr_pct < 2.0:
                atr_score = 30
            elif atr_pct < 3.0:
                atr_score = 20
            elif atr_pct < 4.0:
                atr_score = 10
            else:
                atr_score = 0
            
            score += atr_score
        
        # 2. Bollinger Band Width Score (30 punti)
        if 'BB_width' in df.columns and not pd.isna(last['BB_width']):
            bb_width = last['BB_width']
            
            # BB width < 3% = bassa volatilità
            # BB width > 10% = alta volatilità
            if bb_width < 3.0:
                bb_score = 30
            elif bb_width < 5.0:
                bb_score = 20
            elif bb_width < 7.0:
                bb_score = 10
            else:
                bb_score = 0
            
            score += bb_score
        
        # 3. Historical Volatility Score (30 punti)
        hvol_scores = []
        for period in CONFIG['HVOL_PERIODS']:
            col = f'HVol_{period}'
            if col in df.columns and not pd.isna(last[col]):
                hvol = last[col]
                
                # HVol < 15% = bassa volatilità annualizzata
                # HVol > 50% = alta volatilità
                if hvol < 15:
                    hvol_score = 15
                elif hvol < 25:
                    hvol_score = 10
                elif hvol < 35:
                    hvol_score = 5
                else:
                    hvol_score = 0
                
                hvol_scores.append(hvol_score)
        
        if hvol_scores:
            score += sum(hvol_scores)  # Max 30 punti (2 periodi * 15)
        
        # Normalizza a 0-100
        normalized_score = min(max(score, 0), 100)
        
        return normalized_score
        
    except Exception as e:
        logger.warning(f"Errore calcolo volatility score: {str(e)}")
        return 50.0

def calculate_relative_strength_score(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    ticker: str
) -> float:
    """
    Calcola Relative Strength Score vs Benchmark (0-100).
    
    Componenti:
    - Return 1 mese vs benchmark
    - Return 3 mesi vs benchmark
    - Correlation con benchmark
    
    Args:
        df: DataFrame ticker
        benchmark_df: DataFrame benchmark
        ticker: Nome ticker (per logging)
    
    Returns:
        Score 0-100 (100 = outperformance massima vs benchmark)
    """
    if df.empty or benchmark_df is None or benchmark_df.empty:
        return 50.0
    
    try:
        # Allinea date tra ticker e benchmark
        merged = pd.merge(
            df[['Date', 'Close']].rename(columns={'Close': 'ticker_close'}),
            benchmark_df[['Date', 'Close']].rename(columns={'Close': 'bench_close'}),
            on='Date',
            how='inner'
        )
        
        if len(merged) < 63:  # Minimo per calcolare 3 mesi
            return 50.0
        
        score = 0.0
        
        # 1. Relative Return 1 mese (21 giorni) - 40 punti
        if len(merged) >= 21:
            ticker_ret_1m = ((merged['ticker_close'].iloc[-1] - 
                            merged['ticker_close'].iloc[-21]) / 
                           merged['ticker_close'].iloc[-21]) * 100
            bench_ret_1m = ((merged['bench_close'].iloc[-1] - 
                           merged['bench_close'].iloc[-21]) / 
                          merged['bench_close'].iloc[-21]) * 100
            
            rel_ret_1m = ticker_ret_1m - bench_ret_1m
            
            # Outperformance > 5% = max score
            if rel_ret_1m > 5:
                score += 40
            elif rel_ret_1m > 2:
                score += 30
            elif rel_ret_1m > 0:
                score += 20
            elif rel_ret_1m > -2:
                score += 10
            else:
                score += 0
        
        # 2. Relative Return 3 mesi (63 giorni) - 40 punti
        if len(merged) >= 63:
            ticker_ret_3m = ((merged['ticker_close'].iloc[-1] - 
                            merged['ticker_close'].iloc[-63]) / 
                           merged['ticker_close'].iloc[-63]) * 100
            bench_ret_3m = ((merged['bench_close'].iloc[-1] - 
                           merged['bench_close'].iloc[-63]) / 
                          merged['bench_close'].iloc[-63]) * 100
            
            rel_ret_3m = ticker_ret_3m - bench_ret_3m
            
            # Outperformance > 10% = max score
            if rel_ret_3m > 10:
                score += 40
            elif rel_ret_3m > 5:
                score += 30
            elif rel_ret_3m > 0:
                score += 20
            elif rel_ret_3m > -5:
                score += 10
            else:
                score += 0
        
        # 3. Beta/Correlation (20 punti)
        # Beta < 1 = meno volatile del mercato (bonus)
        ticker_returns = merged['ticker_close'].pct_change().dropna()
        bench_returns = merged['bench_close'].pct_change().dropna()
        
        if len(ticker_returns) > 20:
            correlation = ticker_returns.corr(bench_returns)
            
            # Correlation moderata = diversification benefit
            if 0.5 <= correlation <= 0.8:
                score += 20
            elif 0.3 <= correlation < 0.5 or 0.8 < correlation <= 0.9:
                score += 15
            elif correlation > 0.9:
                score += 10  # Troppo correlato
            else:
                score += 5   # Bassa/negativa correlation
        
        # Normalizza a 0-100
        normalized_score = min(max(score, 0), 100)
        
        return normalized_score
        
    except Exception as e:
        logger.warning(f"Errore calcolo relative strength score per {ticker}: {str(e)}")
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
    """
    Calcola Composite Score con pesi configurabili.
    
    Formula:
    Composite = (Trend * w1) + (Momentum * w2) + (Volatility * w3) + (RelStrength * w4)
    
    Args:
        trend_score: Score trend (0-100)
        momentum_score: Score momentum (0-100)
        volatility_score: Score volatility (0-100) - già invertito se necessario
        relative_strength_score: Score relative strength (0-100)
        weights: Dict pesi custom (default: da CONFIG)
    
    Returns:
        Composite score (0-100)
    """
    if weights is None:
        weights = CONFIG['WEIGHTS']
    
    # NOTA: volatility_score è già "invertito" (alta volatilità = score basso)
    # quindi non serve invertirlo qui
    
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
    """
    Calcola tutti gli score per un singolo strumento.
    
    Args:
        df: DataFrame strumento con indicatori calcolati
        ticker: Symbol ticker
        benchmark_data: Dict {ticker: DataFrame} con benchmark data
    
    Returns:
        Dict con tutti gli score
    """
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
    """
    Calcola score per tutti gli strumenti nell'universo.
    
    Args:
        data_dict: Dict {ticker: DataFrame con indicatori}
        progress_callback: Funzione callback(current, total, ticker)
    
    Returns:
        Dict {ticker: scores_dict}
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
            # Default neutral scores
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
        scores_dict: Dict {ticker: scores}
    
    Returns:
        Dict con liste ranking ordinate
    """
    # Converti in lista di dict per sorting
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
    """
    Estrae top N ticker per criterio specifico.
    
    Args:
        rankings: Dict da generate_rankings()
        criterion: Chiave criterio ('by_composite_score', etc)
        n: Numero ticker da estrarre
    
    Returns:
        Lista top N ticker
    """
    return rankings.get(criterion, [])[:n]

def get_bottom_n(rankings: Dict[str, List], criterion: str = 'by_composite_score', n: int = 5) -> List:
    """
    Estrae bottom N ticker per criterio specifico.
    
    Args:
        rankings: Dict da generate_rankings()
        criterion: Chiave criterio
        n: Numero ticker da estrarre
    
    Returns:
        Lista bottom N ticker
    """
    return rankings.get(criterion, [])[-n:]

def get_score_distribution(scores_dict: Dict[str, Dict[str, float]]) -> Dict:
    """
    Calcola statistiche distribuzione score.
    
    Args:
        scores_dict: Dict {ticker: scores}
    
    Returns:
        Dict con stats (mean, median, std, min, max)
    """
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
    print("KRITERION QUANT - Scoring System Test")
    print("="*70)
    
    # 1. Test calcolo score individuali
    print("\n1. Test Score Individuali (dati sample):")
    
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
        'HVol_60': 20.0
    })
    
    trend = calculate_trend_score(df_test)
    momentum = calculate_momentum_score(df_test)
    volatility = calculate_volatility_score(df_test)
    
    print(f"   Trend Score:      {trend:.2f}")
    print(f"   Momentum Score:   {momentum:.2f}")
    print(f"   Volatility Score: {volatility:.2f}")
    
    # 2. Test composite score
    print("\n2. Test Composite Score:")
    composite = calculate_composite_score(trend, momentum, volatility, 50.0)
    print(f"   Composite Score:  {composite:.2f}")
    
    # 3. Test weights personalizzati
    print("\n3. Test Custom Weights:")
    custom_weights = {
        'TREND': 0.40,
        'MOMENTUM': 0.30,
        'VOLATILITY': 0.10,
        'REL_STRENGTH': 0.20
    }
    composite_custom = calculate_composite_score(
        trend, momentum, volatility, 50.0, custom_weights
    )
    print(f"   Composite (custom): {composite_custom:.2f}")
    
    # 4. Test ranking
    print("\n4. Test Ranking Generation:")
    sample_scores = {
        'SPY': {'composite': 65, 'trend': 70, 'momentum': 60, 'volatility': 60, 'relative_strength': 0},
        'QQQ': {'composite': 75, 'trend': 80, 'momentum': 70, 'volatility': 70, 'relative_strength': 80},
        'GLD': {'composite': 55, 'trend': 50, 'momentum': 55, 'volatility': 80, 'relative_strength': 40},
        'TLT': {'composite': 45, 'trend': 40, 'momentum': 45, 'volatility': 85, 'relative_strength': 35},
        'IWM': {'composite': 70, 'trend': 75, 'momentum': 65, 'volatility': 65, 'relative_strength': 70},
    }
    
    rankings = generate_rankings(sample_scores)
    
    print("\n   Top 3 by Composite Score:")
    for item in get_top_n(rankings, n=3):
        print(f"      {item['ticker']}: {item['composite']:.1f}")
    
    print("\n   Bottom 2 by Composite Score:")
    for item in get_bottom_n(rankings, n=2):
        print(f"      {item['ticker']}: {item['composite']:.1f}")
    
    # 5. Test distribuzione
    print("\n5. Score Distribution Stats:")
    stats = get_score_distribution(sample_scores)
    for key, value in stats.items():
        print(f"   {key:10s}: {value:.2f}")
    
    print("\n" + "="*70)
    print("✅ Test completato con successo")
