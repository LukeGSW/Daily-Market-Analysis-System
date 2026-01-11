# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Main Streamlit Application
============================================================================
Dashboard interattiva per visualizzazione analisi giornaliera.

Features:
- Market regime overview
- Top/Bottom performers
- Detailed instrument analysis con grafici
- Export JSON per LLM analysis
- Manual refresh trigger
============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging
import traceback

# Setup page config (MUST be first Streamlit command)
st.set_page_config(
    page_title="Kriterion Quant - DMA System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://kriterionquant.com',
        'Report a bug': 'https://github.com/kriterionquant/dma-system/issues',
        'About': '# Kriterion Quant DMA System v1.0\n\nDaily Market Analysis powered by quantitative algorithms.'
    }
)

# Import moduli DMA System
from config import CONFIG, SECRETS, UNIVERSE
from market_analysis import run_full_analysis, get_analysis_summary
from report_generator import generate_json_report
from telegram_notifier import send_daily_summary, validate_telegram_config
from chart_generator import create_candlestick_chart
from utils import (
    format_number, format_percentage, format_currency,
    get_score_color, setup_logger
)

# Setup logger
logger = setup_logger('streamlit_app', logging.INFO)

# ============================================================================
# CUSTOM CSS
# ============================================================================

def inject_custom_css():
    """Inietta CSS personalizzato per styling avanzato."""
    st.markdown("""
    <style>
        /* Main container */
        .main {
            max-width: 1400px;
            padding: 2rem;
        }
        
        /* Header styling */
        h1 {
            color: #1a365d;
            font-weight: 800;
            margin-bottom: 0.5rem;
        }
        
        h2 {
            color: #2d3748;
            font-weight: 600;
            border-bottom: 3px solid #38a169;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
        }
        
        h3 {
            color: #4a5568;
            font-weight: 600;
        }
        
        /* Metric cards enhancement */
        [data-testid="stMetric"] {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.9rem;
            color: #4a5568;
            font-weight: 600;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 800;
        }
        
        /* Button styling */
        .stButton > button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            transition: all 0.3s;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(56, 161, 105, 0.3);
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%);
        }
        
        /* Dataframe styling */
        .dataframe {
            font-size: 0.9rem;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        /* Success/Warning/Error messages */
        .stSuccess {
            background-color: #f0fff4;
            border-left: 4px solid #38a169;
        }
        
        .stWarning {
            background-color: #fffbeb;
            border-left: 4px solid #d69e2e;
        }
        
        .stError {
            background-color: #fff5f5;
            border-left: 4px solid #e53e3e;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-weight: 600;
            padding: 0.75rem 1.5rem;
        }
        
        /* Loading spinner */
        .stSpinner > div {
            border-top-color: #38a169 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Inizializza session state."""
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None
    
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_market_data():
    """
    Carica dati market analysis con caching.
    
    Cache TTL: 1 ora (3600 secondi)
    """
    logger.info("🔄 Loading market data...")
    
    try:
        result = run_full_analysis()
        logger.info("✅ Market data loaded successfully")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error loading market data: {str(e)}")
        raise

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Render header con logo e info."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("📊 KRITERION QUANT")
        st.markdown("**Daily Market Analysis System** - Quantitative Intelligence")
    
    with col2:
        if st.session_state.last_update:
            st.info(f"🕐 Last Update\n\n{st.session_state.last_update}")

def render_market_regime(market_regime):
    """Render market regime section."""
    st.header("🌍 Market Regime")
    
    col1, col2, col3 = st.columns(3)
    
    # VIX
    with col1:
        # FIX: Gestione sicura del valore VIX
        raw_vix = market_regime.get('vix_level')
        vix_level = float(raw_vix) if raw_vix is not None else 0.0
        
        vix_regime = market_regime.get('vix_regime', 'unknown').upper()
        
        # Color based on regime
        if vix_regime == 'LOW':
            vix_color = "normal"
            vix_icon = "🟢"
        elif vix_regime == 'MEDIUM':
            vix_color = "normal"
            vix_icon = "🟡"
        else:
            vix_color = "inverse"
            vix_icon = "🔴"
        
        st.metric(
            label=f"{vix_icon} VIX Level",
            value=f"{vix_level:.2f}",
            delta=vix_regime,
            delta_color=vix_color
        )
    
    # SPY Trend
    with col2:
        spy_trend = market_regime.get('spy_trend', 'unknown').upper()
        spy_above_sma = market_regime.get('spy_above_sma200', False)
        
        trend_icon = "📈" if spy_trend == "UPTREND" else "📉"
        trend_color = "normal" if spy_trend == "UPTREND" else "inverse"
        
        st.metric(
            label=f"{trend_icon} SPY Trend",
            value=spy_trend,
            delta="Above SMA200" if spy_above_sma else "Below SMA200",
            delta_color=trend_color
        )
    
    # Market Condition
    with col3:
        condition = market_regime.get('market_condition', 'unknown')
        condition_display = condition.replace('_', ' ').title()
        
        # Icon based on condition
        if 'bullish' in condition:
            cond_icon = "💼"
            cond_color = "normal"
        elif 'bearish' in condition:
            cond_icon = "⚠️"
            cond_color = "inverse"
        else:
            cond_icon = "➖"
            cond_color = "off"
        
        st.metric(
            label=f"{cond_icon} Market Condition",
            value=condition_display,
            delta=None
        )

def render_rankings(rankings):
    """Render rankings section."""
    st.header("🏆 Performance Rankings")
    
    col1, col2 = st.columns(2)
    
    # Top 5
    with col1:
        st.subheader("Top 5 Performers")
        
        top_5 = rankings.get('by_composite_score', [])[:5]
        
        if top_5:
            # Create DataFrame
            df_top = pd.DataFrame([
                {
                    'Ticker': item['ticker'],
                    'Score': item['composite'],
                    'Trend': item['trend'],
                    'Momentum': item['momentum']
                }
                for item in top_5
            ])
            
            # Style DataFrame
            def style_score(val):
                color = get_score_color(val)
                return f'background-color: {color}; color: white; font-weight: bold;'
            
            styled_df = df_top.style.applymap(
                style_score,
                subset=['Score']
            ).format({
                'Score': '{:.1f}',
                'Trend': '{:.0f}',
                'Momentum': '{:.0f}'
            })
            
            st.dataframe(styled_df, width="stretch", hide_index=True)
        else:
            st.warning("No data available")
    
    # Bottom 5
    with col2:
        st.subheader("Bottom 5 Performers")
        
        all_scores = rankings.get('by_composite_score', [])
        bottom_5 = all_scores[-5:] if len(all_scores) >= 5 else []
        bottom_5.reverse()
        
        if bottom_5:
            df_bottom = pd.DataFrame([
                {
                    'Ticker': item['ticker'],
                    'Score': item['composite'],
                    'Trend': item['trend'],
                    'Momentum': item['momentum']
                }
                for item in bottom_5
            ])
            
            styled_df = df_bottom.style.applymap(
                style_score,
                subset=['Score']
            ).format({
                'Score': '{:.1f}',
                'Trend': '{:.0f}',
                'Momentum': '{:.0f}'
            })
            
            st.dataframe(styled_df, width="stretch", hide_index=True)
        else:
            st.warning("No data available")

def render_instrument_detail(ticker, data, processed_df):
    """Render dettaglio singolo strumento."""
    
    # Header con prezzo
    col1, col2 = st.columns([3, 1])
    
    with col1:
        info = data.get('info', {})
        st.markdown(f"### {ticker} - {info.get('name', 'N/A')}")
        st.caption(f"Category: {info.get('category', 'N/A')}")
    
    with col2:
        current = data.get('current', {})
        price = current.get('price', 0)
        change = current.get('change_1d_pct', 0)
        
        st.metric(
            label="Price",
            value=format_currency(price, decimals=2),
            delta=format_percentage(change, decimals=2)
        )
    
    # Scores
    st.markdown("**Scores**")
    scores = data.get('scores', {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    score_items = [
        (col1, 'Composite', scores.get('composite', 0)),
        (col2, 'Trend', scores.get('trend', 0)),
        (col3, 'Momentum', scores.get('momentum', 0)),
        (col4, 'Volatility', scores.get('volatility', 0)),
        (col5, 'Rel. Strength', scores.get('relative_strength', 0))
    ]
    
    for col, label, value in score_items:
        with col:
            color = get_score_color(value)
            st.markdown(f"""
            <div style='text-align: center; padding: 10px; background: {color}; 
                        border-radius: 8px; color: white;'>
                <div style='font-size: 0.8rem; opacity: 0.9;'>{label}</div>
                <div style='font-size: 1.5rem; font-weight: bold;'>{value:.0f}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Signals
    signals = data.get('signals', [])
    if signals:
        st.warning(f"⚠️ **Active Signals:** {', '.join(signals)}")
    
    # Chart
    # Chart
    if processed_df is not None and not processed_df.empty:
        try:
            # Estrai key_levels dal dizionario dati per passarli al grafico
            key_levels = data.get('key_levels', {})
            
            # Chiama la nuova versione che accetta key_levels
            fig = create_candlestick_chart(processed_df, ticker, key_levels=key_levels)
            
            st.plotly_chart(fig, width="stretch")
        except Exception as e:
            st.error(f"Error generating chart: {str(e)}")
    else:
        st.info("Chart data not available")
    
    st.divider()

def render_detailed_analysis(instruments, processed_data):
    """Render detailed analysis section."""
    st.header("📈 Detailed Analysis")
    
    # Filters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        categories = ['All'] + sorted(set(
            data['info']['category'] 
            for data in instruments.values()
        ))
        selected_category = st.selectbox(
            "Filter by Category",
            categories,
            key='category_filter'
        )
    
    with col2:
        view_mode = st.radio(
            "View Mode",
            ["Expandable", "Tabs"],
            horizontal=True,
            key='view_mode'
        )
    
    # Filter instruments
    if selected_category == 'All':
        filtered_instruments = instruments
    else:
        filtered_instruments = {
            ticker: data 
            for ticker, data in instruments.items()
            if data['info']['category'] == selected_category
        }
    
    if not filtered_instruments:
        st.warning("No instruments match the selected filter")
        return
    
    # Sort by composite score
    sorted_tickers = sorted(
        filtered_instruments.keys(),
        key=lambda t: filtered_instruments[t]['scores'].get('composite', 0),
        reverse=True
    )
    
    # Render based on view mode
    if view_mode == "Expandable":
        for ticker in sorted_tickers:
            data = filtered_instruments[ticker]
            processed_df = processed_data.get(ticker)
            
            with st.expander(
                f"{ticker} - {data['info']['name']} (Score: {data['scores'].get('composite', 0):.1f})",
                expanded=False
            ):
                render_instrument_detail(ticker, data, processed_df)
    
    else:  # Tabs
        tabs = st.tabs(sorted_tickers)
        
        for i, ticker in enumerate(sorted_tickers):
            with tabs[i]:
                data = filtered_instruments[ticker]
                processed_df = processed_data.get(ticker)
                render_instrument_detail(ticker, data, processed_df)

# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar con controlli."""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/1a365d/ffffff?text=KRITERION+QUANT", 
                 width="stretch")
        
        st.header("⚙️ Controls")
        
        # Refresh button
        if st.button("🔄 Refresh Data", type="primary", width="stretch"):
            with st.spinner("Loading market data..."):
                try:
                    # Clear cache
                    st.cache_data.clear()
                    
                    # Reload data
                    result = load_market_data()
                    st.session_state.analysis_result = result
                    st.session_state.last_update = datetime.now().strftime('%Y-%m-%d %H:%M')
                    
                    st.success("✅ Data refreshed successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    logger.error(traceback.format_exc())
        
        st.divider()
        
        # Export section
        st.header("📥 Export")
        
        if st.session_state.analysis_result:
            # JSON export
            try:
                json_content = generate_json_report(st.session_state.analysis_result)
                
                st.download_button(
                    label="📄 Download JSON",
                    data=json_content,
                    file_name=f"dma_data_{datetime.now().strftime('%Y-%m-%d')}.json",
                    mime="application/json",
                    width="stretch"
                )
            except Exception as e:
                st.error(f"Export error: {str(e)}")
        else:
            st.info("Load data first to enable export")
        
        st.divider()
        
        # Telegram section
        st.header("📱 Telegram")
        
        telegram_status = validate_telegram_config()
        
        if telegram_status['ready']:
            st.success("✅ Telegram configured")
            
            if st.button("📤 Send Notification", width="stretch"):
                if st.session_state.analysis_result:
                    with st.spinner("Sending..."):
                        try:
                            success = send_daily_summary(st.session_state.analysis_result)
                            
                            if success:
                                st.success("✅ Notification sent!")
                            else:
                                st.error("❌ Send failed")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                else:
                    st.warning("Load data first")
        else:
            st.warning("⚠️ Telegram not configured")
            with st.expander("Setup Instructions"):
                st.markdown("""
                1. Create bot with @BotFather
                2. Get Bot Token
                3. Add bot to chat
                4. Get Chat ID
                5. Configure in Settings → Secrets
                """)
        
        st.divider()
        
        # Info section
        st.header("ℹ️ Info")
        
        if st.session_state.analysis_result:
            metadata = st.session_state.analysis_result.get('metadata', {})
            
            st.metric("Instruments", metadata.get('instruments_analyzed', 'N/A'))
            st.caption(f"Analysis Date: {metadata.get('analysis_date', 'N/A')}")
        
        st.caption("v1.0 - Kriterion Quant")
        st.caption("[Documentation](https://kriterionquant.com)")

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application logic."""
    
    # Initialize
    initialize_session_state()
    inject_custom_css()
    
    # Render sidebar
    render_sidebar()
    
    # Main content
    render_header()
    
    # Debug: Check secrets loading (remove in production)
    api_key_exists = bool(SECRETS.get('EODHD_API_KEY'))
    
    # Check if EODHD API key is configured
    if not api_key_exists:
        st.error("❌ **EODHD API Key Not Configured**")
        
        # Debug info
        with st.expander("🔍 Debug Info"):
            st.write("Checking secrets loading...")
            st.write(f"SECRETS dict keys: {list(SECRETS.keys())}")
            st.write(f"API Key present: {api_key_exists}")
            st.write(f"API Key length: {len(SECRETS.get('EODHD_API_KEY', ''))}")
            
            # Use global st instead of local import
            try:
                st.write(f"st.secrets available: {hasattr(st, 'secrets')}")
                if hasattr(st, 'secrets'):
                    st.write(f"st.secrets keys: {list(st.secrets.keys())}")
            except Exception as e:
                st.write(f"Error checking st.secrets: {e}")
        
        st.warning("""
        Please configure your EODHD API key to use this application.
        
        **For Streamlit Cloud:**
        1. Click on ⚙️ **Settings** (hamburger menu top-right)
        2. Go to **Secrets**
        3. Add:
        ```toml
        EODHD_API_KEY = "your_api_key_here"
        ```
        4. Click **Save**
        5. App will restart automatically
        
        **Get your API key:** https://eodhistoricaldata.com
        """)
        st.info("💡 **Tip:** Free tier provides 20 API calls/day. For this system, a paid plan ($9.99/month) is recommended.")
        st.stop()
    
    # Load data on first run
    if st.session_state.analysis_result is None:
        with st.spinner("🚀 Loading market data... This may take a few minutes..."):
            try:
                result = load_market_data()
                st.session_state.analysis_result = result
                st.session_state.last_update = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                st.success("✅ Data loaded successfully!")
                
            except Exception as e:
                st.error("❌ Failed to load market data")
                st.error(str(e))
                
                # Check if it's an API key error
                if "401" in str(e) or "Unauthorized" in str(e):
                    st.warning("🔑 **API Key Error:** Your EODHD API key may be invalid or expired.")
                    st.info("Please verify your API key in Settings → Secrets")
                
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
                
                st.stop()
    
    # Render content
    result = st.session_state.analysis_result
    
    if result:
        # Market Regime
        market_regime = result.get('market_regime', {})
        render_market_regime(market_regime)
        
        st.divider()
        
        # Rankings
        rankings = result.get('rankings', {})
        render_rankings(rankings)
        
        st.divider()
        
        # Detailed Analysis
        instruments = result.get('instruments', {})
        processed_data = result.get('processed_data', {})
        render_detailed_analysis(instruments, processed_data)
        
        # Footer
        st.divider()
        st.caption("© 2024 Kriterion Quant. All rights reserved.")
        st.caption("This system provides educational information only. Not financial advice.")
    
    else:
        st.warning("No data available. Click 'Refresh Data' in the sidebar.")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("❌ Critical Error")
        st.error(str(e))
        
        with st.expander("Stack Trace"):
            st.code(traceback.format_exc())
        
        logger.error(f"Critical error: {str(e)}")
        logger.error(traceback.format_exc())
