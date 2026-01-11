# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Market Analysis Module (Enhanced Signals)
============================================================================
Orchestrazione completa del sistema:
- Market Regime Detection (VIX + SPY trend)
- Signal Generation (Breaking + Testing logic)
- Consolidamento dati per report (JSON/HTML)
- Master analysis function

Coordina: Data Fetcher (Hybrid) -> Indicators (Fixed) -> Scoring (Hybrid)
============================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from config import CONFIG, UNIVERSE
from data_fetcher import (
    download_universe_data,
    get_date_range_for_analysis,
    validate_dataframe,
    clean_dataframe
)
from technical_indicators import (
    compute_all_indicators,
    get_indicator_summary,
    get_macd_signal
)
from scoring_system import (
    score_universe,
    generate_rankings,
    get_top_n,
    get_bottom_n
)

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# MARKET REGIME DETECTION
# ============================================================================

def detect_market_regime(
    vix_df: pd.DataFrame,
    spy_df: pd.DataFrame
) -> Dict[str, any]:
    """
    Rileva regime di mercato basato su VIX e SPY.
    """
    logger.info("🔍 Detecting market regime...")
    
    regime = {
        'vix_level': None,
        'vix_regime': 'unknown',
        'spy_trend': 'unknown',
        'spy_above_sma200': None,
        'market_condition': 'unknown',
        'risk_appetite': 'neutral'
    }
    
    try:
        # 1. VIX Analysis
        if not vix_df.empty:
            vix_current = vix_df['Close'].iloc[-1]
            regime['vix_level'] = float(vix_current)
            
            if vix_current < CONFIG['VIX_LOW']:
                regime['vix_regime'] = 'low'
                regime['risk_appetite'] = 'risk-on'
            elif vix_current < CONFIG['VIX_MEDIUM']:
                regime['vix_regime'] = 'medium'
                regime['risk_appetite'] = 'neutral'
            else:
                regime['vix_regime'] = 'high'
                regime['risk_appetite'] = 'risk-off'
        
        # 2. SPY Trend Analysis
        if not spy_df.empty and 'SMA_200' in spy_df.columns:
            spy_current = spy_df['Close'].iloc[-1]
            spy_sma200 = spy_df['SMA_200'].iloc[-1]
            
            if not pd.isna(spy_sma200):
                spy_above_sma200 = spy_current > spy_sma200
                regime['spy_above_sma200'] = bool(spy_above_sma200) # Ensure native bool
                
                if spy_above_sma200:
                    regime['spy_trend'] = 'uptrend'
                else:
                    regime['spy_trend'] = 'downtrend'
        
        # 3. Combined Market Condition
        if regime['vix_regime'] == 'low' and regime['spy_trend'] == 'uptrend':
            regime['market_condition'] = 'bullish'
        elif regime['vix_regime'] == 'high' and regime['spy_trend'] == 'downtrend':
            regime['market_condition'] = 'bearish'
        elif regime['vix_regime'] == 'high' and regime['spy_trend'] == 'uptrend':
            regime['market_condition'] = 'volatile_bullish'
        elif regime['vix_regime'] == 'low' and regime['spy_trend'] == 'downtrend':
            regime['market_condition'] = 'quiet_bearish'
        else:
            regime['market_condition'] = 'neutral'
        
        logger.info(f"   VIX: {regime['vix_level']:.2f} ({regime['vix_regime']})")
        logger.info(f"   SPY: {regime['spy_trend']} (SMA200: {regime['spy_above_sma200']})")
        logger.info(f"   Condition: {regime['market_condition']}")
        
    except Exception as e:
        logger.error(f"❌ Errore market regime detection: {str(e)}")
    
    return regime

# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signals(df: pd.DataFrame, ticker: str) -> List[str]:
    """
    Genera segnali operativi avanzati (Breaking & Testing).
    """
    if df.empty or len(df) < 5:
        return []
    
    signals = []
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    try:
        close = last['Close']
        high = last['High']
        low = last['Low']
        
        # 1. Price Levels (Breaking & Testing)
        # Usa le colonne pre-calcolate da technical_indicators.py
        pwh = last.get('prev_week_high')
        pwl = last.get('prev_week_low')
        pdh = last.get('prev_day_high')
        pdl = last.get('prev_day_low')
        
        # Weekly High
        if not pd.isna(pwh):
            if close > pwh:
                signals.append("Breaking above weekly high")
            elif high > pwh:
                signals.append("Testing weekly high")
        
        # Weekly Low
        if not pd.isna(pwl):
            if close < pwl:
                signals.append("Breaking below weekly low")
            elif low < pwl:
                signals.append("Testing weekly low")
        
        # Daily High
        if not pd.isna(pdh):
            if close > pdh:
                signals.append("Breaking above daily high")
            elif high > pdh:
                signals.append("Testing daily high")
        
        # Daily Low
        if not pd.isna(pdl):
            if close < pdl:
                signals.append("Breaking below daily low")
            elif low < pdl:
                signals.append("Testing daily low")
        
        # 2. RSI Signals
        if 'RSI' in df.columns and not pd.isna(last['RSI']):
            rsi = last['RSI']
            
            if rsi >= CONFIG['SIGNAL_THRESHOLDS']['RSI_EXTREME_OB']:
                signals.append(f"RSI Extremely Overbought ({rsi:.1f})")
            elif rsi >= CONFIG['RSI_OVERBOUGHT']:
                signals.append(f"RSI Overbought ({rsi:.1f})")
            elif rsi <= CONFIG['SIGNAL_THRESHOLDS']['RSI_EXTREME_OS']:
                signals.append(f"RSI Extremely Oversold ({rsi:.1f})")
            elif rsi <= CONFIG['RSI_OVERSOLD']:
                signals.append(f"RSI Oversold ({rsi:.1f})")
        
        # 3. Bollinger Band Signals (Breaking & Testing)
        if all(col in df.columns for col in ['BB_upper', 'BB_lower']):
            bb_upper = last['BB_upper']
            bb_lower = last['BB_lower']
            
            if not pd.isna(bb_upper):
                if close > bb_upper:
                    signals.append("BB Upper Breakout")
                elif high >= bb_upper * 0.995: # Within 0.5%
                    signals.append("Testing upper Bollinger Band")
            
            if not pd.isna(bb_lower):
                if close < bb_lower:
                    signals.append("BB Lower Breakout")
                elif low <= bb_lower * 1.005:
                    signals.append("Testing lower Bollinger Band")
        
        # 4. Volume Surge
        if 'Volume_ratio' in df.columns and not pd.isna(last['Volume_ratio']):
            if last['Volume_ratio'] > CONFIG['SIGNAL_THRESHOLDS']['VOLUME_SURGE']:
                signals.append(f"Volume Surge ({last['Volume_ratio']:.1f}x)")
        
        # 5. Gap Signals
        if all(col in df.columns for col in ['Open', 'Close']):
            gap = ((last['Open'] - prev['Close']) / prev['Close']) * 100
            if abs(gap) > CONFIG['SIGNAL_THRESHOLDS']['GAP_THRESHOLD'] * 100:
                direction = "Up" if gap > 0 else "Down"
                signals.append(f"Gap {direction} ({gap:.1f}%)")
        
        # 6. MACD Crossover
        if all(col in df.columns for col in ['MACD', 'MACD_signal']):
            if prev['MACD'] < prev['MACD_signal'] and last['MACD'] > last['MACD_signal']:
                signals.append("Bullish MACD crossover")
            elif prev['MACD'] > prev['MACD_signal'] and last['MACD'] < last['MACD_signal']:
                signals.append("Bearish MACD crossover")
        
        # 7. SMA Crossover (Golden/Death Cross)
        if all(col in df.columns for col in ['SMA_50', 'SMA_200']):
            if prev['SMA_50'] < prev['SMA_200'] and last['SMA_50'] > last['SMA_200']:
                signals.append("Golden Cross (SMA50 > SMA200)")
            elif prev['SMA_50'] > prev['SMA_200'] and last['SMA_50'] < last['SMA_200']:
                signals.append("Death Cross (SMA50 < SMA200)")
        
        # 8. ADX Strong Trend
        if 'ADX' in df.columns and not pd.isna(last['ADX']):
            if last['ADX'] > CONFIG['ADX_STRONG_TREND']:
                signals.append(f"Strong Trend (ADX {last['ADX']:.1f})")
        
    except Exception as e:
        logger.warning(f"Errore signal generation per {ticker}: {str(e)}")
    
    return signals

# ============================================================================
# DATA CONSOLIDATION
# ============================================================================

def consolidate_instrument_data(
    ticker: str,
    df: pd.DataFrame,
    scores: Dict[str, float],
    signals: List[str]
) -> Dict:
    """
    Consolida tutti i dati di un ticker in struttura JSON.
    Include TUTTI i livelli chiave calcolati per il report.
    """
    if df.empty: return None
    
    last = df.iloc[-1]
    ticker_info = UNIVERSE.get(ticker, {})
    
    # Current price data
    current_data = {
        'price': float(last.get('Close', 0)),
        'change_1d_pct': float(last.get('return_1d', 0)) if 'return_1d' in df.columns else 0.0,
        'volume': int(last.get('Volume', 0))
    }
    
    # Key levels (estratti dalle colonne pre-calcolate)
    key_levels = {
        'prev_day_high': float(last.get('prev_day_high', 0)),
        'prev_day_low': float(last.get('prev_day_low', 0)),
        'prev_week_high': float(last.get('prev_week_high', 0)),
        'prev_week_low': float(last.get('prev_week_low', 0)),
        'pivot_point': float(last.get('pivot_point', 0)),
        'resistance_1': float(last.get('resistance_1', 0)),
        'resistance_2': float(last.get('resistance_2', 0)),
        'support_1': float(last.get('support_1', 0)),
        'support_2': float(last.get('support_2', 0))
    }
    
    # Technical indicators summary
    indicators = {
        'rsi_14': float(last.get('RSI', 0)) if 'RSI' in df.columns else None,
        'macd_signal': get_macd_signal(df),
        'adx_14': float(last.get('ADX', 0)) if 'ADX' in df.columns else None,
        'sma_200_dist': None,
        'atr_pct': float(last.get('ATR_pct', 0)) if 'ATR_pct' in df.columns else None,
        'bb_width': float(last.get('BB_width', 0)) if 'BB_width' in df.columns else None
    }
    
    # Distance from SMA200
    if 'SMA_200' in df.columns and not pd.isna(last['SMA_200']):
        indicators['sma_200_dist'] = ((last['Close'] - last['SMA_200']) / 
                                     last['SMA_200']) * 100
    
    # Consolidate all
    instrument_data = {
        'info': {
            'name': ticker_info.get('name', ticker),
            'category': ticker_info.get('category', 'Unknown'),
            'benchmark': ticker_info.get('benchmark', 'SPY')
        },
        'current': current_data,
        'key_levels': key_levels,
        'indicators': indicators,
        'scores': scores,
        'signals': signals
    }
    
    return instrument_data

# ============================================================================
# MASTER ANALYSIS FUNCTION
# ============================================================================

def run_full_analysis(progress_callback=None) -> Dict:
    """
    Esegue analisi completa del sistema.
    """
    logger.info("="*70)
    logger.info("🚀 AVVIO ANALISI COMPLETA KRITERION QUANT DMA SYSTEM")
    logger.info("="*70)
    
    analysis_start = datetime.now()
    
    def update_progress(step: str, message: str = ""):
        logger.info(f"\n📍 {step}")
        if message: logger.info(f"   {message}")
        if progress_callback: progress_callback(step, message)
    
    try:
        # --- STEP 1: DOWNLOAD DATI ---
        update_progress("STEP 1/7", "Download dati (Hybrid Mode)...")
        start_date, end_date = get_date_range_for_analysis()
        logger.info(f"   Date range: {start_date} → {end_date}")
        
        # Questa chiamata ora usa la logica ibrida in data_fetcher.py
        raw_data = download_universe_data(start_date, end_date)
        
        if not raw_data:
            raise Exception("Nessun dato scaricato")
        
        logger.info(f"   ✅ {len(raw_data)} ticker scaricati")
        
        # --- STEP 2: VALIDAZIONE E PULIZIA ---
        update_progress("STEP 2/7", "Validazione e pulizia dati...")
        validated_data = {}
        for ticker, df in raw_data.items():
            if validate_dataframe(df, ticker):
                # clean_dataframe ora applica il fix delle date (rimuove Oggi)
                validated_data[ticker] = clean_dataframe(df)
            else:
                logger.warning(f"   ⚠️ {ticker} scartato (validazione fallita)")
        
        logger.info(f"   ✅ {len(validated_data)} ticker validati")
        
        # --- STEP 3: CALCOLO INDICATORI ---
        update_progress("STEP 3/7", "Calcolo indicatori tecnici & livelli...")
        processed_data = {}
        for ticker, df in validated_data.items():
            try:
                # compute_all_indicators ora calcola anche i Livelli e Pivot
                df_with_indicators = compute_all_indicators(df)
                processed_data[ticker] = df_with_indicators
            except Exception as e:
                logger.error(f"   ❌ Errore indicatori {ticker}: {str(e)}")
        
        logger.info(f"   ✅ {len(processed_data)} ticker processati")
        
        # --- STEP 4: SCORING ---
        update_progress("STEP 4/7", "Calcolo scoring strumenti...")
        # Usa il nuovo scoring system ibrido
        all_scores = score_universe(processed_data)
        logger.info(f"   ✅ {len(all_scores)} ticker scored")
        
        # --- STEP 5: MARKET REGIME ---
        update_progress("STEP 5/7", "Market regime detection...")
        vix_df = processed_data.get('^VIX', pd.DataFrame())
        spy_df = processed_data.get('SPY', pd.DataFrame())
        market_regime = detect_market_regime(vix_df, spy_df)
        
        # --- STEP 6: SIGNAL GENERATION ---
        update_progress("STEP 6/7", "Generazione segnali operativi...")
        all_signals = {}
        for ticker, df in processed_data.items():
            signals = generate_signals(df, ticker)
            all_signals[ticker] = signals
            if signals:
                logger.info(f"   🔔 {ticker}: {len(signals)} segnali")
        
        # --- STEP 7: CONSOLIDAMENTO FINALE ---
        update_progress("STEP 7/7", "Consolidamento dati finali...")
        instruments_data = {}
        for ticker in processed_data.keys():
            df = processed_data[ticker]
            scores = all_scores.get(ticker, {})
            signals = all_signals.get(ticker, [])
            
            instrument_data = consolidate_instrument_data(
                ticker, df, scores, signals
            )
            
            if instrument_data:
                instruments_data[ticker] = instrument_data
        
        # Generate rankings
        rankings = generate_rankings(all_scores)
        
        # --- RESULT PACKAGE ---
        analysis_result = {
            'metadata': {
                'analysis_date': end_date,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': '1.0',
                'generated_by': 'Kriterion Quant DMA System',
                'instruments_analyzed': len(instruments_data),
                'date_range': {'start': start_date, 'end': end_date}
            },
            'market_regime': market_regime,
            'instruments': instruments_data,
            'rankings': rankings,
            'processed_data': processed_data,
            'notable_events': [] # Placeholder per eventi futuri
        }
        
        # --- SUMMARY STATS ---
        elapsed = (datetime.now() - analysis_start).total_seconds()
        logger.info("\n" + "="*70)
        logger.info("✅ ANALISI COMPLETATA CON SUCCESSO")
        logger.info("="*70)
        logger.info(f"⏱️  Tempo totale: {elapsed:.1f} secondi")
        logger.info(f"📈 Market Regime: {market_regime['market_condition']}")
        
        top3 = get_top_n(rankings, n=3)
        logger.info("\n🏆 Top 3 Composite Score:")
        for item in top3:
            logger.info(f"   {item['ticker']}: {item['composite']:.1f}")
        logger.info("="*70)
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"\n❌ ERRORE CRITICO NELL'ANALISI: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_analysis_summary(analysis_result: Dict) -> Dict:
    """Estrae summary compatto da analysis result."""
    rankings = analysis_result.get('rankings', {})
    instruments = analysis_result.get('instruments', {})
    market_regime = analysis_result.get('market_regime', {})
    
    top_5 = get_top_n(rankings, n=5)
    bottom_5 = get_bottom_n(rankings, n=5)
    
    total_signals = sum(len(inst.get('signals', [])) for inst in instruments.values())
    
    top_sector = None
    top_sector_score = -1
    for ticker, data in instruments.items():
        if data['info']['category'] == 'Sector':
            score = data['scores']['composite']
            if score > top_sector_score:
                top_sector_score = score
                top_sector = ticker
    
    all_composites = [inst['scores']['composite'] for inst in instruments.values()]
    avg_score = np.mean(all_composites) if all_composites else 0
    
    summary = {
        'market_regime': market_regime.get('market_condition', 'unknown'),
        'vix_level': market_regime.get('vix_level', 0),
        'spy_trend': market_regime.get('spy_trend', 'unknown'),
        'instruments_count': len(instruments),
        'total_signals': total_signals,
        'top_sector': top_sector,
        'top_5_tickers': [t['ticker'] for t in top_5],
        'bottom_5_tickers': [t['ticker'] for t in bottom_5],
        'avg_composite_score': avg_score
    }
    
    return summary

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("Market Analysis Test...")
    # (Codice di test omesso per brevità, non necessario per l'esecuzione dell'app)
