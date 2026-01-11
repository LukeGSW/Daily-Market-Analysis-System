# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Market Analysis Module
============================================================================
Orchestrazione completa del sistema:
- Market Regime Detection (VIX + SPY trend)
- Signal Generation (breakout, overbought, oversold, etc)
- Consolidamento dati per report
- Master analysis function

Questo è il "cervello" che coordina tutti gli altri moduli.
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
    
    Regole:
    - VIX < 15: Low volatility (risk-on)
    - VIX 15-25: Medium volatility (neutral)
    - VIX > 25: High volatility (risk-off)
    
    - SPY > SMA200: Uptrend (bullish)
    - SPY < SMA200: Downtrend (bearish)
    
    Args:
        vix_df: DataFrame VIX con indicatori
        spy_df: DataFrame SPY con indicatori
    
    Returns:
        Dict con market regime info
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
                regime['spy_above_sma200'] = spy_above_sma200
                
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
    Genera segnali operativi per un ticker.
    
    Segnali implementati:
    - Price breakout (high/low)
    - RSI extreme (overbought/oversold)
    - Bollinger Band breakout
    - Volume surge
    - Gap up/down
    - MACD crossover
    - SMA crossover
    
    Args:
        df: DataFrame con indicatori calcolati
        ticker: Symbol ticker
    
    Returns:
        Lista stringhe segnali
    """
    if df.empty or len(df) < 5:
        return []
    
    signals = []
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    try:
        # 1. Price Breakout Signals
        if 'High' in df.columns and len(df) >= 5:
            # Breaking weekly high (5 giorni)
            prev_week_high = df['High'].iloc[-6:-1].max()
            if last['Close'] > prev_week_high:
                signals.append("Breaking above weekly high")
            
            # Breaking weekly low
            prev_week_low = df['Low'].iloc[-6:-1].min()
            if last['Close'] < prev_week_low:
                signals.append("Breaking below weekly low")
        
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
        
        # 3. Bollinger Band Signals
        if all(col in df.columns for col in ['BB_upper', 'BB_lower', 'Close']):
            if not any(pd.isna([last['BB_upper'], last['BB_lower']])):
                # Breakout sopra banda superiore
                if last['Close'] > last['BB_upper']:
                    distance = ((last['Close'] - last['BB_upper']) / 
                              last['BB_upper']) * 100
                    if distance > CONFIG['SIGNAL_THRESHOLDS']['BB_BREAKOUT']:
                        signals.append("BB Upper Breakout")
                
                # Breakout sotto banda inferiore
                elif last['Close'] < last['BB_lower']:
                    distance = ((last['BB_lower'] - last['Close']) / 
                              last['BB_lower']) * 100
                    if distance > CONFIG['SIGNAL_THRESHOLDS']['BB_BREAKOUT']:
                        signals.append("BB Lower Breakout")
        
        # 4. Volume Surge
        if 'Volume_ratio' in df.columns and not pd.isna(last['Volume_ratio']):
            if last['Volume_ratio'] > CONFIG['SIGNAL_THRESHOLDS']['VOLUME_SURGE']:
                signals.append(f"Volume Surge ({last['Volume_ratio']:.1f}x)")
        
        # 5. Gap Signals
        if all(col in df.columns for col in ['Open', 'Close']):
            gap = ((last['Open'] - prev['Close']) / prev['Close']) * 100
            
            if abs(gap) > CONFIG['SIGNAL_THRESHOLDS']['GAP_THRESHOLD'] * 100:
                if gap > 0:
                    signals.append(f"Gap Up ({gap:.1f}%)")
                else:
                    signals.append(f"Gap Down ({gap:.1f}%)")
        
        # 6. MACD Crossover
        if all(col in df.columns for col in ['MACD', 'MACD_signal']):
            if not any(pd.isna([last['MACD'], last['MACD_signal'], 
                              prev['MACD'], prev['MACD_signal']])):
                # Bullish crossover
                if prev['MACD'] < prev['MACD_signal'] and last['MACD'] > last['MACD_signal']:
                    signals.append("MACD Bullish Crossover")
                # Bearish crossover
                elif prev['MACD'] > prev['MACD_signal'] and last['MACD'] < last['MACD_signal']:
                    signals.append("MACD Bearish Crossover")
        
        # 7. SMA Crossover (Golden/Death Cross)
        if all(col in df.columns for col in ['SMA_50', 'SMA_200']):
            if not any(pd.isna([last['SMA_50'], last['SMA_200'], 
                              prev['SMA_50'], prev['SMA_200']])):
                # Golden Cross
                if prev['SMA_50'] < prev['SMA_200'] and last['SMA_50'] > last['SMA_200']:
                    signals.append("Golden Cross (SMA50 > SMA200)")
                # Death Cross
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
    
    Args:
        ticker: Symbol ticker
        df: DataFrame con indicatori
        scores: Dict scores dal scoring system
        signals: Lista segnali generati
    
    Returns:
        Dict strutturato con tutti i dati
    """
    if df.empty:
        return None
    
    last = df.iloc[-1]
    ticker_info = UNIVERSE.get(ticker, {})
    
    # Current price data
    current_data = {
        'price': float(last.get('Close', 0)),
        'change_1d_pct': float(last.get('return_1d', 0)) if 'return_1d' in df.columns else 0.0,
        'volume': int(last.get('Volume', 0))
    }
    
    # Key levels (support/resistance)
    key_levels = {}
    if len(df) >= 5:
        # Previous day high/low
        if len(df) >= 2:
            prev_day = df.iloc[-2]
            key_levels['prev_day_high'] = float(prev_day.get('High', 0))
            key_levels['prev_day_low'] = float(prev_day.get('Low', 0))
        
        # Previous week high/low (5 giorni)
        if len(df) >= 6:
            prev_week = df.iloc[-6:-1]
            key_levels['prev_week_high'] = float(prev_week['High'].max())
            key_levels['prev_week_low'] = float(prev_week['Low'].min())
        
        # Pivot points
        if all(col in df.columns for col in ['R1', 'S1']):
            key_levels['resistance_1'] = float(last.get('R1', 0))
            key_levels['support_1'] = float(last.get('S1', 0))
    
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
    
    Questo è il main entry point che orchestra tutti i moduli:
    1. Download dati EODHD
    2. Calcolo indicatori tecnici
    3. Scoring strumenti
    4. Market regime detection
    5. Signal generation
    6. Ranking generation
    7. Data consolidation
    
    Args:
        progress_callback: Funzione callback(step, message) per progress tracking
    
    Returns:
        Dict completo con tutti i risultati pronti per report
    """
    logger.info("="*70)
    logger.info("🚀 AVVIO ANALISI COMPLETA KRITERION QUANT DMA SYSTEM")
    logger.info("="*70)
    
    analysis_start = datetime.now()
    
    def update_progress(step: str, message: str = ""):
        logger.info(f"\n📍 {step}")
        if message:
            logger.info(f"   {message}")
        if progress_callback:
            progress_callback(step, message)
    
    try:
        # --- STEP 1: DOWNLOAD DATI ---
        update_progress("STEP 1/7", "Download dati EODHD...")
        
        start_date, end_date = get_date_range_for_analysis()
        logger.info(f"   Date range: {start_date} → {end_date}")
        
        raw_data = download_universe_data(start_date, end_date)
        
        if not raw_data:
            raise Exception("Nessun dato scaricato da EODHD")
        
        logger.info(f"   ✅ {len(raw_data)} ticker scaricati")
        
        # --- STEP 2: VALIDAZIONE E PULIZIA ---
        update_progress("STEP 2/7", "Validazione e pulizia dati...")
        
        validated_data = {}
        for ticker, df in raw_data.items():
            if validate_dataframe(df, ticker):
                validated_data[ticker] = clean_dataframe(df)
            else:
                logger.warning(f"   ⚠️ {ticker} scartato (validazione fallita)")
        
        logger.info(f"   ✅ {len(validated_data)} ticker validati")
        
        # --- STEP 3: CALCOLO INDICATORI ---
        update_progress("STEP 3/7", "Calcolo indicatori tecnici...")
        
        processed_data = {}
        for ticker, df in validated_data.items():
            try:
                df_with_indicators = compute_all_indicators(df)
                processed_data[ticker] = df_with_indicators
            except Exception as e:
                logger.error(f"   ❌ Errore indicatori {ticker}: {str(e)}")
        
        logger.info(f"   ✅ {len(processed_data)} ticker processati")
        
        # --- STEP 4: SCORING ---
        update_progress("STEP 4/7", "Calcolo scoring strumenti...")
        
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
                'date_range': {
                    'start': start_date,
                    'end': end_date
                }
            },
            'market_regime': market_regime,
            'instruments': instruments_data,
            'rankings': rankings,
            'processed_data': processed_data  # Per grafici
        }
        
        # --- SUMMARY STATS ---
        elapsed = (datetime.now() - analysis_start).total_seconds()
        
        logger.info("\n" + "="*70)
        logger.info("✅ ANALISI COMPLETATA CON SUCCESSO")
        logger.info("="*70)
        logger.info(f"⏱️  Tempo totale: {elapsed:.1f} secondi")
        logger.info(f"📊 Strumenti analizzati: {len(instruments_data)}")
        logger.info(f"🔔 Segnali totali: {sum(len(s) for s in all_signals.values())}")
        logger.info(f"📈 Market Regime: {market_regime['market_condition']}")
        
        # Top 3
        top3 = get_top_n(rankings, n=3)
        logger.info("\n🏆 Top 3 Composite Score:")
        for item in top3:
            logger.info(f"   {item['ticker']}: {item['composite']:.1f}")
        
        logger.info("="*70)
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"\n❌ ERRORE CRITICO NELL'ANALISI: {str(e)}")
        logger.exception(e)
        raise

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_analysis_summary(analysis_result: Dict) -> Dict:
    """
    Estrae summary compatto da analysis result.
    
    Args:
        analysis_result: Output da run_full_analysis()
    
    Returns:
        Dict summary con metriche chiave
    """
    rankings = analysis_result.get('rankings', {})
    instruments = analysis_result.get('instruments', {})
    market_regime = analysis_result.get('market_regime', {})
    
    # Top/Bottom performers
    top_5 = get_top_n(rankings, n=5)
    bottom_5 = get_bottom_n(rankings, n=5)
    
    # Count signals
    total_signals = sum(
        len(inst.get('signals', [])) 
        for inst in instruments.values()
    )
    
    # Top sector
    top_sector = None
    top_sector_score = -1
    for ticker, data in instruments.items():
        if data['info']['category'] == 'Sector':
            score = data['scores']['composite']
            if score > top_sector_score:
                top_sector_score = score
                top_sector = ticker
    
    summary = {
        'market_regime': market_regime.get('market_condition', 'unknown'),
        'vix_level': market_regime.get('vix_level', 0),
        'spy_trend': market_regime.get('spy_trend', 'unknown'),
        'instruments_count': len(instruments),
        'total_signals': total_signals,
        'top_sector': top_sector,
        'top_5_tickers': [t['ticker'] for t in top_5],
        'bottom_5_tickers': [t['ticker'] for t in bottom_5],
        'avg_composite_score': np.mean([
            inst['scores']['composite'] 
            for inst in instruments.values()
        ])
    }
    
    return summary

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Market Analysis Test")
    print("="*70)
    
    print("\n⚠️  ATTENZIONE: Questo test richiede:")
    print("   - EODHD_API_KEY configurata")
    print("   - Connessione internet attiva")
    print("   - ~5-10 minuti per completare")
    
    response = input("\nVuoi procedere con il test completo? (y/n): ")
    
    if response.lower() == 'y':
        print("\n🚀 Avvio analisi completa...")
        
        try:
            # Progress callback per test
            def progress(step, message):
                print(f"\n>>> {step}")
                if message:
                    print(f"    {message}")
            
            # Run full analysis
            result = run_full_analysis(progress_callback=progress)
            
            # Print summary
            print("\n" + "="*70)
            print("📊 ANALYSIS SUMMARY")
            print("="*70)
            
            summary = get_analysis_summary(result)
            
            print(f"\nMarket Regime: {summary['market_regime']}")
            print(f"VIX Level: {summary['vix_level']:.2f}")
            print(f"SPY Trend: {summary['spy_trend']}")
            print(f"\nInstruments Analyzed: {summary['instruments_count']}")
            print(f"Total Signals: {summary['total_signals']}")
            print(f"Avg Composite Score: {summary['avg_composite_score']:.1f}")
            
            print(f"\nTop Sector: {summary['top_sector']}")
            
            print("\nTop 5 Tickers:")
            for ticker in summary['top_5_tickers']:
                score = result['instruments'][ticker]['scores']['composite']
                print(f"   {ticker}: {score:.1f}")
            
            print("\nBottom 5 Tickers:")
            for ticker in summary['bottom_5_tickers']:
                score = result['instruments'][ticker]['scores']['composite']
                print(f"   {ticker}: {score:.1f}")
            
            print("\n✅ Test completato con successo!")
            
        except Exception as e:
            print(f"\n❌ Test fallito: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("\n⏭️  Test annullato.")
