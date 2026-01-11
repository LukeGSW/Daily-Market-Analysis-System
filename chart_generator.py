# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Chart Generator Module (Enhanced Visuals)
============================================================================
Generazione grafici Plotly professionali con:
- Candlestick charts
- Overlay tecnici (SMA 50/200, Bollinger Bands)
- Volume bars
- LIVELLI CHIAVE (PWH, PWL, Pivot) visualizzati sul grafico
- Stile branding Kriterion Quant
============================================================================
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, Dict
import logging

from config import CONFIG

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# CHART GENERATION
# ============================================================================

def create_candlestick_chart(
    df: pd.DataFrame,
    ticker: str,
    lookback_days: int = None,
    show_volume: bool = True,
    show_sma: bool = True,
    show_bb: bool = True,
    key_levels: Dict[str, float] = None  # NUOVO ARGOMENTO PER LIVELLI
) -> go.Figure:
    """
    Crea grafico candlestick interattivo con overlay tecnici e livelli chiave.
    
    Args:
        df: DataFrame con OHLCV e indicatori
        ticker: Symbol ticker (per titolo)
        lookback_days: Giorni da visualizzare (default: da CONFIG)
        show_volume: Mostra volume subplot
        show_sma: Mostra SMA 50/200
        show_bb: Mostra Bollinger Bands
        key_levels: Dict con livelli prezzo (PWH, PWL, Pivot, etc.)
    
    Returns:
        Plotly Figure object
    """
    if df.empty:
        logger.warning(f"DataFrame vuoto per {ticker}")
        return go.Figure()
    
    # Lookback period
    if lookback_days is None:
        lookback_days = CONFIG['CHART_LOOKBACK_DAYS']
    
    # Limita DataFrame agli ultimi N giorni
    df_plot = df.tail(lookback_days).copy()
    
    if df_plot.empty:
        return go.Figure()
    
    # Colors
    colors = CONFIG['COLORS']
    candle_up = colors['CANDLE_UP']
    candle_down = colors['CANDLE_DOWN']
    sma50_color = colors['SMA_50']
    sma200_color = colors['SMA_200']
    
    # Create subplots (price + volume se richiesto)
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{ticker}", "Volume")
        )
    else:
        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=(f"{ticker}",)
        )
    
    # --- CANDLESTICK ---
    candlestick = go.Candlestick(
        x=df_plot['Date'],
        open=df_plot['Open'],
        high=df_plot['High'],
        low=df_plot['Low'],
        close=df_plot['Close'],
        name='Price',
        increasing_line_color=candle_up,
        decreasing_line_color=candle_down,
        increasing_fillcolor=candle_up,
        decreasing_fillcolor=candle_down
    )
    
    fig.add_trace(candlestick, row=1, col=1)
    
    # --- SMA OVERLAY ---
    if show_sma:
        # SMA 50
        if 'SMA_50' in df_plot.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_plot['Date'],
                    y=df_plot['SMA_50'],
                    mode='lines',
                    name='SMA 50',
                    line=dict(color=sma50_color, width=1.5),
                    opacity=0.8
                ),
                row=1, col=1
            )
        
        # SMA 200
        if 'SMA_200' in df_plot.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_plot['Date'],
                    y=df_plot['SMA_200'],
                    mode='lines',
                    name='SMA 200',
                    line=dict(color=sma200_color, width=2),
                    opacity=0.8
                ),
                row=1, col=1
            )
    
    # --- BOLLINGER BANDS ---
    if show_bb and all(col in df_plot.columns for col in ['BB_upper', 'BB_lower']):
        # Upper band
        fig.add_trace(
            go.Scatter(
                x=df_plot['Date'],
                y=df_plot['BB_upper'],
                mode='lines',
                name='BB Upper',
                line=dict(color='rgba(128, 128, 128, 0.3)', width=1, dash='dash'),
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Lower band
        fig.add_trace(
            go.Scatter(
                x=df_plot['Date'],
                y=df_plot['BB_lower'],
                mode='lines',
                name='BB Lower',
                line=dict(color='rgba(128, 128, 128, 0.3)', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(128, 128, 128, 0.05)',
                showlegend=True
            ),
            row=1, col=1
        )

    # --- KEY LEVELS OVERLAY (Insight Visuali) ---
    if key_levels:
        # Prev Week High (Green Dot)
        if 'prev_week_high' in key_levels and key_levels['prev_week_high'] > 0:
            fig.add_hline(
                y=key_levels['prev_week_high'], 
                line_dash="dot", 
                line_color="green", 
                line_width=1, 
                annotation_text="PWH", 
                annotation_position="top right", 
                row=1, col=1
            )
        
        # Prev Week Low (Red Dot)
        if 'prev_week_low' in key_levels and key_levels['prev_week_low'] > 0:
            fig.add_hline(
                y=key_levels['prev_week_low'], 
                line_dash="dot", 
                line_color="red", 
                line_width=1, 
                annotation_text="PWL", 
                annotation_position="bottom right", 
                row=1, col=1
            )
            
        # Pivot Point (Blue Dash)
        if 'pivot_point' in key_levels and key_levels['pivot_point'] > 0:
            fig.add_hline(
                y=key_levels['pivot_point'], 
                line_dash="dash", 
                line_color="blue", 
                line_width=1, 
                annotation_text="Pivot", 
                annotation_position="right", 
                row=1, col=1
            )
            
        # Prev Day High (Light Green Dash)
        if 'prev_day_high' in key_levels and key_levels['prev_day_high'] > 0:
            fig.add_hline(
                y=key_levels['prev_day_high'],
                line_dash="dash",
                line_color="rgba(0, 128, 0, 0.4)",
                line_width=1,
                annotation_text="PDH",
                annotation_position="top left",
                row=1, col=1
            )

        # Prev Day Low (Light Red Dash)
        if 'prev_day_low' in key_levels and key_levels['prev_day_low'] > 0:
            fig.add_hline(
                y=key_levels['prev_day_low'],
                line_dash="dash",
                line_color="rgba(255, 0, 0, 0.4)",
                line_width=1,
                annotation_text="PDL",
                annotation_position="bottom left",
                row=1, col=1
            )
    
    # --- VOLUME BARS ---
    if show_volume and 'Volume' in df_plot.columns:
        # Color volume bars based on price movement
        colors_volume = []
        for i in range(len(df_plot)):
            if i == 0:
                colors_volume.append(candle_up)
            else:
                if df_plot['Close'].iloc[i] >= df_plot['Close'].iloc[i-1]:
                    colors_volume.append(candle_up)
                else:
                    colors_volume.append(candle_down)
        
        fig.add_trace(
            go.Bar(
                x=df_plot['Date'],
                y=df_plot['Volume'],
                name='Volume',
                marker_color=colors_volume,
                showlegend=False
            ),
            row=2, col=1
        )
    
    # --- LAYOUT STYLING ---
    fig.update_layout(
        title={
            'text': f"{ticker} - Technical Analysis",
            'font': {'size': 20, 'color': colors['PRIMARY'][0]},
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='Date',
        yaxis_title='Price',
        template='plotly_white',
        hovermode='x unified',
        height=450 if show_volume else 400,
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(250, 250, 250, 0.5)',
        paper_bgcolor='white'
    )
    
    # Update axes
    fig.update_xaxes(
        rangeslider_visible=False,
        gridcolor='rgba(200, 200, 200, 0.3)',
        showgrid=True
    )
    
    fig.update_yaxes(
        gridcolor='rgba(200, 200, 200, 0.3)',
        showgrid=True
    )
    
    # Volume y-axis label
    if show_volume:
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig

def create_chart_with_indicators(
    df: pd.DataFrame,
    ticker: str,
    ticker_info: Dict = None
) -> go.Figure:
    """
    Crea grafico completo con tutti gli indicatori rilevanti.
    """
    if df.empty:
        return go.Figure()
    
    # Estrai livelli dall'ultima riga se presenti
    last = df.iloc[-1]
    k_levels = {
        'prev_week_high': last.get('prev_week_high'),
        'prev_week_low': last.get('prev_week_low'),
        'prev_day_high': last.get('prev_day_high'),
        'prev_day_low': last.get('prev_day_low'),
        'pivot_point': last.get('pivot_point')
    }
    
    # Usa candlestick base come foundation
    fig = create_candlestick_chart(
        df, 
        ticker,
        show_volume=True,
        show_sma=True,
        show_bb=True,
        key_levels=k_levels
    )
    
    # Aggiungi info ticker al titolo se disponibile
    if ticker_info:
        name = ticker_info.get('name', ticker)
        category = ticker_info.get('category', '')
        title_text = f"{ticker} - {name}"
        if category:
            title_text += f" ({category})"
        
        fig.update_layout(
            title={'text': title_text}
        )
    
    return fig

# ============================================================================
# BATCH CHART GENERATION
# ============================================================================

def generate_all_charts(
    processed_data: Dict[str, pd.DataFrame],
    progress_callback=None
) -> Dict[str, go.Figure]:
    """
    Genera grafici per tutti i ticker.
    Passa i Key Levels estratti dai dati per visualizzazione.
    """
    logger.info(f"📊 Generazione grafici per {len(processed_data)} ticker...")
    
    charts = {}
    total = len(processed_data)
    
    for i, (ticker, df) in enumerate(processed_data.items(), 1):
        try:
            if progress_callback:
                progress_callback(i, total, ticker)
            
            # Estrai Key Levels dall'ultima riga
            last = df.iloc[-1]
            k_levels = {
                'prev_week_high': last.get('prev_week_high'),
                'prev_week_low': last.get('prev_week_low'),
                'prev_day_high': last.get('prev_day_high'),
                'prev_day_low': last.get('prev_day_low'),
                'pivot_point': last.get('pivot_point')
            }
            
            fig = create_candlestick_chart(df, ticker, key_levels=k_levels)
            charts[ticker] = fig
            
            if i % 10 == 0:
                logger.info(f"   ... {i}/{total} grafici generati")
                
        except Exception as e:
            logger.error(f"❌ Errore grafico {ticker}: {str(e)}")
            charts[ticker] = go.Figure()
    
    logger.info(f"✅ {len(charts)} grafici generati con successo")
    
    return charts

def generate_charts_html(charts: Dict[str, go.Figure]) -> Dict[str, str]:
    """
    Converte grafici Plotly in HTML strings per embedding.
    """
    logger.info(f"🔄 Conversione {len(charts)} grafici in HTML...")
    
    charts_html = {}
    
    for ticker, fig in charts.items():
        try:
            # Convert to HTML (no full_html, no plotlyjs - will be loaded once)
            html = fig.to_html(
                full_html=False,
                include_plotlyjs=False,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                }
            )
            charts_html[ticker] = html
            
        except Exception as e:
            logger.error(f"❌ Errore conversione HTML {ticker}: {str(e)}")
            charts_html[ticker] = "<div>Chart Error</div>"
    
    logger.info(f"✅ Conversione HTML completata")
    
    return charts_html

# ============================================================================
# SPECIALIZED CHARTS
# ============================================================================

def create_comparison_chart(
    data_dict: Dict[str, pd.DataFrame],
    tickers: list,
    normalize: bool = True
) -> go.Figure:
    """
    Crea grafico comparativo tra multipli ticker.
    """
    fig = go.Figure()
    
    colors_palette = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]
    
    for i, ticker in enumerate(tickers):
        if ticker not in data_dict:
            continue
        
        df = data_dict[ticker]
        if df.empty:
            continue
        
        # Limita a ultimi 252 giorni
        df_plot = df.tail(CONFIG['CHART_LOOKBACK_DAYS'])
        
        if normalize:
            # Normalizza a 100 (primo valore = 100)
            values = (df_plot['Close'] / df_plot['Close'].iloc[0]) * 100
            y_title = 'Normalized Price (Base 100)'
        else:
            values = df_plot['Close']
            y_title = 'Price'
        
        fig.add_trace(
            go.Scatter(
                x=df_plot['Date'],
                y=values,
                mode='lines',
                name=ticker,
                line=dict(
                    color=colors_palette[i % len(colors_palette)],
                    width=2
                )
            )
        )
    
    fig.update_layout(
        title='Ticker Comparison',
        xaxis_title='Date',
        yaxis_title=y_title,
        template='plotly_white',
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig

def create_performance_heatmap(scores_dict: Dict[str, Dict[str, float]]) -> go.Figure:
    """
    Crea heatmap performance scores.
    """
    # Prepara dati per heatmap
    tickers = list(scores_dict.keys())
    score_types = ['composite', 'trend', 'momentum', 'volatility', 'relative_strength']
    
    z_data = []
    for score_type in score_types:
        row = [scores_dict[t].get(score_type, 0) for t in tickers]
        z_data.append(row)
    
    fig = go.Figure(
        data=go.Heatmap(
            z=z_data,
            x=tickers,
            y=['Composite', 'Trend', 'Momentum', 'Volatility', 'Rel. Strength'],
            colorscale='RdYlGn',
            zmid=50,
            text=[[f"{val:.0f}" for val in row] for row in z_data],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Score")
        )
    )
    
    fig.update_layout(
        title='Scores Heatmap',
        xaxis_title='Ticker',
        yaxis_title='Score Type',
        height=400
    )
    
    return fig

# ============================================================================
# CHART EXPORT UTILITIES
# ============================================================================

def save_chart_as_image(
    fig: go.Figure,
    filepath: str,
    width: int = 1200,
    height: int = 600
):
    """
    Salva grafico Plotly come immagine PNG.
    """
    try:
        fig.write_image(filepath, width=width, height=height)
        logger.info(f"✅ Chart salvato: {filepath}")
    except Exception as e:
        logger.warning(f"⚠️ Impossibile salvare immagine: {str(e)}")
        logger.warning("   Installa kaleido: pip install kaleido")

def export_chart_html(
    fig: go.Figure,
    filepath: str,
    include_plotlyjs: bool = True
):
    """
    Esporta grafico come file HTML standalone.
    """
    try:
        fig.write_html(
            filepath,
            include_plotlyjs=include_plotlyjs,
            config={'displayModeBar': True, 'displaylogo': False}
        )
        logger.info(f"✅ HTML salvato: {filepath}")
    except Exception as e:
        logger.error(f"❌ Errore export HTML: {str(e)}")

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Chart Generator Test")
    print("="*70)
    
    # 1. Genera dati sample
    print("\n1. Generazione dati sample...")
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    n = len(dates)
    
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(n) * 2)
    
    df_sample = pd.DataFrame({
        'Date': dates,
        'Open': prices + np.random.randn(n) * 0.5,
        'High': prices + np.abs(np.random.randn(n) * 1.5),
        'Low': prices - np.abs(np.random.randn(n) * 1.5),
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, n),
        'SMA_50': pd.Series(prices).rolling(50).mean(),
        'SMA_200': pd.Series(prices).rolling(200).mean(),
        'BB_upper': pd.Series(prices).rolling(20).mean() + 2 * pd.Series(prices).rolling(20).std(),
        'BB_middle': pd.Series(prices).rolling(20).mean(),
        'BB_lower': pd.Series(prices).rolling(20).mean() - 2 * pd.Series(prices).rolling(20).std(),
    })
    
    print(f"   ✅ Sample data: {len(df_sample)} righe")
    
    # 2. Test candlestick chart con LIVELLI
    print("\n2. Creazione candlestick chart con LIVELLI...")
    
    # Mock levels
    mock_levels = {
        'prev_week_high': prices[-1] * 1.05,
        'prev_week_low': prices[-1] * 0.95,
        'pivot_point': prices[-1],
        'prev_day_high': prices[-1] * 1.02,
        'prev_day_low': prices[-1] * 0.98
    }
    
    fig = create_candlestick_chart(
        df_sample,
        'TEST',
        show_volume=True,
        show_sma=True,
        show_bb=True,
        key_levels=mock_levels  # Passaggio livelli
    )
    print(f"   ✅ Chart creato con successo")
    
    # 3. Test export HTML
    print("\n3. Export HTML...")
    try:
        export_chart_html(fig, 'test_chart_levels.html')
        print("   ✅ File salvato: test_chart_levels.html")
    except Exception as e:
        print(f"   ⚠️ Export fallito: {str(e)}")
    
    print("\n" + "="*70)
    print("✅ Test completato con successo!")
    print("\nPer visualizzare il chart generato:")
    print("   Apri: test_chart_levels.html nel browser")
