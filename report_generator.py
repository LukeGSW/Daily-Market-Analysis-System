# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Report Generator Module
============================================================================
Genera report giornalieri in formato:
- JSON strutturato (per LLM analysis)
- HTML professionale (dashboard completa)

Include template Jinja2 per rendering HTML con stile Kriterion Quant.
============================================================================
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging
from pathlib import Path

from config import CONFIG
from chart_generator import generate_charts_html

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# JSON SERIALIZATION HELPERS
# ============================================================================

def convert_types(obj):
    """
    Converte tipi numpy/pandas in tipi nativi Python per JSON serialization.
    
    Args:
        obj: Oggetto da convertire
    
    Returns:
        Oggetto convertito
    """
    # Gestione Interi NumPy
    if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
        np.int16, np.int32, np.int64, np.uint8,
        np.uint16, np.uint32, np.uint64, np.integer)):
        return int(obj)
    
    # Gestione Float NumPy
    elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64, np.floating)):
        return float(obj)
    
    # Gestione Booleani NumPy (IL FIX CHE MANCAVA)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    
    # Gestione Array NumPy
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    
    # Gestione Date (Pandas Timestamp, datetime, date)
    elif isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    
    # Gestione Pandas Series/DataFrame
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    
    # Gestione NaN/None
    elif pd.isna(obj):
        return None
        
    return obj

def clean_dict_for_json(data: Any) -> Any:
    """
    Pulisce ricorsivamente strutture dati per JSON serialization.
    
    Args:
        data: Dict, List o valore da pulire
    
    Returns:
        Struttura pulita con tipi nativi
    """
    if isinstance(data, dict):
        return {k: clean_dict_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_dict_for_json(item) for item in data]
    else:
        return convert_types(data)

# ============================================================================
# JSON REPORT GENERATION
# ============================================================================

def generate_json_report(analysis_result: Dict) -> str:
    """
    Genera report JSON strutturato dall'analysis result.
    
    Il JSON è ottimizzato per:
    - Analisi LLM esterna
    - Data persistence
    - API consumption
    
    Args:
        analysis_result: Output da market_analysis.run_full_analysis()
    
    Returns:
        JSON string formattato
    """
    logger.info("📄 Generazione JSON report...")
    
    # Seleziona le sezioni rilevanti (escludendo DataFrame pesanti se presenti in processed_data)
    # processed_data solitamente contiene DF che non vogliamo nel JSON di sintesi, 
    # ma se servissero per l'LLM, andrebbero convertiti. Per ora manteniamo la struttura snella.
    report_data = {
        'metadata': analysis_result.get('metadata', {}),
        'market_regime': analysis_result.get('market_regime', {}),
        'instruments': analysis_result.get('instruments', {}),
        'rankings': analysis_result.get('rankings', {}),
        'notable_events': analysis_result.get('notable_events', []) # Aggiunto se presente
    }
    
    try:
        # Clean per JSON serialization (con gestione errori)
        report_data_clean = clean_dict_for_json(report_data)
        
        # Serialize con indentazione
        json_string = json.dumps(
            report_data_clean,
            indent=CONFIG.get('JSON_INDENT', 2),
            ensure_ascii=False
        )
        
        logger.info(f"✅ JSON report generato: {len(json_string)} caratteri")
        return json_string
        
    except Exception as e:
        logger.error(f"❌ Errore critico generazione JSON: {str(e)}")
        # Ritorna un JSON di errore valido per non rompere la UI
        return json.dumps({"error": f"JSON generation failed: {str(e)}"})

def save_json_report(json_string: str, filepath: str = None) -> str:
    """
    Salva JSON report su file.
    
    Args:
        json_string: JSON da salvare
        filepath: Path file (default: dma_data_YYYY-MM-DD.json)
    
    Returns:
        Path file salvato
    """
    if filepath is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
        filepath = f"dma_data_{date_str}.json"
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_string)
        
        logger.info(f"💾 JSON salvato: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"❌ Errore salvataggio JSON: {str(e)}")
        raise

# ============================================================================
# HTML TEMPLATE
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DMA System | {{ date }}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1a365d;
            --secondary: #2d3748;
            --accent: #38a169;
            --danger: #e53e3e;
            --warning: #d69e2e;
            --bg: #f7fafc;
            --card-bg: #ffffff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--secondary); line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); color: white; padding: 30px 0; margin-bottom: 30px; }
        header .container { display: flex; justify-content: space-between; align-items: center; }
        h1 { font-size: 2rem; font-weight: 800; }
        h2 { color: var(--primary); font-size: 1.5rem; margin-bottom: 20px; border-bottom: 3px solid var(--accent); padding-bottom: 10px; }
        .meta { font-size: 0.85rem; opacity: 0.8; }
        section { background: var(--card-bg); border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .regime-panel { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .metric-card { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 8px; text-align: center; }
        .metric-label { font-size: 0.9rem; color: var(--secondary); margin-bottom: 8px; font-weight: 600; }
        .metric-val { font-size: 2rem; font-weight: 800; color: var(--primary); }
        .rankings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .ranking-card { background: #f8f9fa; padding: 20px; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { background: var(--primary); color: white; padding: 10px; text-align: left; font-size: 0.85rem; }
        td { padding: 10px; border-bottom: 1px solid #e9ecef; }
        tr:hover { background: #f8f9fa; }
        .score-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; color: white; font-weight: 600; font-size: 0.9rem; }
        .instrument-card { background: var(--card-bg); border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 2px solid #e9ecef; }
        .ticker-title { font-size: 1.5rem; font-weight: 800; color: var(--primary); margin-right: 10px; }
        .ticker-name { font-size: 1rem; color: var(--secondary); opacity: 0.7; }
        .scores-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .score-box { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 6px; }
        .score-box .label { font-size: 0.8rem; color: var(--secondary); margin-bottom: 5px; }
        .score-box .value { font-size: 1.8rem; font-weight: 700; }
        .signals-area { background: #fff3cd; border-left: 4px solid var(--warning); padding: 12px; margin-bottom: 15px; border-radius: 4px; }
        .signal-tag { display: inline-block; background: var(--warning); color: white; padding: 4px 10px; border-radius: 4px; margin-right: 8px; margin-bottom: 5px; font-size: 0.8rem; }
        .text-green { color: var(--accent); }
        .text-red { color: var(--danger); }
    </style>
</head>
<body>
<header>
    <div class="container">
        <div>
            <h1>KRITERION QUANT</h1>
            <div class="meta">Daily Market Analysis System v1.0</div>
        </div>
        <div style="text-align: right;">
            <div>{{ date }}</div>
            <div class="meta">Generated: {{ timestamp }}</div>
        </div>
    </div>
</header>
<div class="container">
    <section>
        <h2 style="margin-bottom: 15px; color: var(--primary);">Market Regime</h2>
        <div class="regime-panel">
            <div class="metric-card">
                <div class="metric-label">VIX Level</div>
                <div class="metric-val" style="color: {% if regime.vix_regime == 'low' %}var(--accent){% elif regime.vix_regime == 'medium' %}var(--warning){% else %}var(--danger){% endif %}">
                    {{ "%.2f"|format(regime.vix_level) }}
                </div>
                <div class="meta">{{ regime.vix_regime|upper }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">SPY Trend</div>
                <div class="metric-val" style="color: {% if regime.spy_trend == 'uptrend' %}var(--accent){% else %}var(--danger){% endif %}">
                    {{ regime.spy_trend|upper }}
                </div>
                <div class="meta">{{ 'Above SMA200' if regime.spy_above_sma200 else 'Below SMA200' }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Top Sector</div>
                <div class="metric-val">{{ top_sector }}</div>
            </div>
        </div>
    </section>

    <section>
        <div class="rankings-grid">
            <div class="ranking-card">
                <h3 style="margin-top:0">Top 5 Composite Score</h3>
                <table>
                    <tr><th>Ticker</th><th>Score</th><th>Trend</th></tr>
                    {% for item in rankings.by_composite_score[:5] %}
                    <tr>
                        <td><b>{{ item.ticker }}</b></td>
                        <td><span class="score-badge" style="background-color: {{ get_color(item.composite) }}">{{ "%.1f"|format(item.composite) }}</span></td>
                        <td>{{ "%.0f"|format(item.trend) }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <div class="ranking-card">
                <h3 style="margin-top:0">Bottom 5 Composite Score</h3>
                <table>
                    <tr><th>Ticker</th><th>Score</th><th>Trend</th></tr>
                    {% for item in rankings.by_composite_score[-5:]|reverse %}
                    <tr>
                        <td><b>{{ item.ticker }}</b></td>
                        <td><span class="score-badge" style="background-color: {{ get_color(item.composite) }}">{{ "%.1f"|format(item.composite) }}</span></td>
                        <td>{{ "%.0f"|format(item.trend) }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </section>

    <section>
        <h2 style="margin-bottom: 20px; color: var(--primary);">Detailed Analysis</h2>
        {% for ticker, data in instruments.items() %}
        <div class="instrument-card">
            <div class="card-header">
                <div>
                    <span class="ticker-title">{{ ticker }}</span>
                    <span class="ticker-name">{{ data.info.name }}</span>
                    <span style="font-size: 0.8rem; background: #e2e8f0; padding: 2px 6px; border-radius: 4px; margin-left: 10px;">{{ data.info.category }}</span>
                </div>
                <div style="font-weight: bold; font-size: 1.1rem;">
                    ${{ "%.2f"|format(data.current.price) }}
                    <span class="{{ 'text-green' if data.current.change_1d_pct >= 0 else 'text-red' }}" style="font-size: 0.9rem;">
                        ({{ "%+.2f"|format(data.current.change_1d_pct) }}%)
                    </span>
                </div>
            </div>
            <div class="scores-grid">
                <div class="score-box">
                    <div class="label">Composite</div>
                    <div class="value" style="color: {{ get_color(data.scores.composite) }}">{{ "%.0f"|format(data.scores.composite) }}</div>
                </div>
                <div class="score-box">
                    <div class="label">Trend</div>
                    <div class="value" style="color: {{ get_color(data.scores.trend) }}">{{ "%.0f"|format(data.scores.trend) }}</div>
                </div>
                <div class="score-box">
                    <div class="label">Momentum</div>
                    <div class="value" style="color: {{ get_color(data.scores.momentum) }}">{{ "%.0f"|format(data.scores.momentum) }}</div>
                </div>
                <div class="score-box">
                    <div class="label">Volatility</div>
                    <div class="value" style="color: {{ get_color(data.scores.volatility) }}">{{ "%.0f"|format(data.scores.volatility) }}</div>
                </div>
                <div class="score-box">
                    <div class="label">Rel. Strength</div>
                    <div class="value" style="color: {{ get_color(data.scores.relative_strength) }}">{{ "%.0f"|format(data.scores.relative_strength) }}</div>
                </div>
            </div>
            {% if data.signals %}
            <div class="signals-area">
                <b>⚠️ Active Signals: </b>
                {% for sig in data.signals %}
                <span class="signal-tag">{{ sig }}</span>
                {% endfor %}
            </div>
            {% endif %}
            <div style="height: 450px;">{{ charts[ticker] | safe }}</div>
        </div>
        {% endfor %}
    </section>
    
    <footer style="text-align: center; padding: 40px; color: #a0aec0; font-size: 0.8rem;">
        <p>Generated by Kriterion Quant DMA System v1.0</p>
        <p>© {{ date[:4] }} Kriterion Quant. All rights reserved.</p>
    </footer>
</div>
</body>
</html>
"""

# ============================================================================
# HTML REPORT GENERATION
# ============================================================================

def generate_html_report(
    analysis_result: Dict,
    charts_html: Dict[str, str] = None
) -> str:
    """
    Genera report HTML completo usando template Jinja2.
    
    Args:
        analysis_result: Output da market_analysis.run_full_analysis()
        charts_html: Dict {ticker: HTML string} da chart_generator
    
    Returns:
        HTML string completo
    """
    logger.info("📄 Generazione HTML report...")
    
    from jinja2 import Template
    
    # Helper functions per template
    def get_color(score: float) -> str:
        """Mappa score a colore."""
        if score >= 70:
            return CONFIG['COLORS']['SCORE_EXCELLENT']
        elif score >= 55:
            return CONFIG['COLORS']['SCORE_GOOD']
        elif score >= 40:
            return CONFIG['COLORS']['SCORE_NEUTRAL']
        elif score >= 25:
            return CONFIG['COLORS']['SCORE_POOR']
        else:
            return CONFIG['COLORS']['SCORE_BAD']
    
    # Genera charts se non forniti
    if charts_html is None:
        logger.info("   Generazione grafici per HTML...")
        from chart_generator import generate_all_charts
        processed_data = analysis_result.get('processed_data', {})
        charts = generate_all_charts(processed_data)
        charts_html = generate_charts_html(charts)
    
    # Determina top sector
    instruments = analysis_result.get('instruments', {})
    top_sector = "N/A"
    best_score = -1
    
    for ticker, data in instruments.items():
        if data['info']['category'] == 'Sector':
            score = data['scores']['composite']
            if score > best_score:
                best_score = score
                top_sector = ticker
    
    # Render template
    template = Template(HTML_TEMPLATE)
    
    html_output = template.render(
        date=datetime.now().strftime('%Y-%m-%d'),
        timestamp=datetime.now().strftime('%H:%M:%S UTC'),
        regime=analysis_result.get('market_regime', {}),
        instruments=instruments,
        rankings=analysis_result.get('rankings', {}),
        charts=charts_html,
        top_sector=top_sector,
        get_color=get_color
    )
    
    logger.info(f"✅ HTML report generato: {len(html_output)} caratteri")
    
    return html_output

def save_html_report(html_string: str, filepath: str = None) -> str:
    """
    Salva HTML report su file.
    
    Args:
        html_string: HTML da salvare
        filepath: Path file (default: dma_report_YYYY-MM-DD.html)
    
    Returns:
        Path file salvato
    """
    if filepath is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
        filepath = f"dma_report_{date_str}.html"
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_string)
        
        logger.info(f"💾 HTML salvato: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"❌ Errore salvataggio HTML: {str(e)}")
        raise

# ============================================================================
# COMPLETE REPORT GENERATION
# ============================================================================

def generate_complete_reports(
    analysis_result: Dict,
    output_dir: str = ".",
    save_files: bool = True
) -> Dict[str, str]:
    """
    Genera entrambi i report (JSON + HTML) e li salva.
    
    Args:
        analysis_result: Output da market_analysis.run_full_analysis()
        output_dir: Directory output files
        save_files: Se True, salva su disco
    
    Returns:
        Dict con paths e contenuti:
        {
            'json_content': str,
            'json_path': str,
            'html_content': str,
            'html_path': str
        }
    """
    logger.info("="*70)
    logger.info("📊 GENERAZIONE REPORT COMPLETI")
    logger.info("="*70)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 1. JSON Report
    logger.info("\n1. Generazione JSON Report...")
    json_content = generate_json_report(analysis_result)
    json_path = None
    
    if save_files:
        json_path = str(output_dir / f"dma_data_{datetime.now().strftime('%Y-%m-%d')}.json")
        save_json_report(json_content, json_path)
    
    # 2. HTML Report
    logger.info("\n2. Generazione HTML Report...")
    
    # Genera charts HTML
    processed_data = analysis_result.get('processed_data', {})
    from chart_generator import generate_all_charts
    charts = generate_all_charts(processed_data)
    charts_html = generate_charts_html(charts)
    
    html_content = generate_html_report(analysis_result, charts_html)
    html_path = None
    
    if save_files:
        html_path = str(output_dir / f"dma_report_{datetime.now().strftime('%Y-%m-%d')}.html")
        save_html_report(html_content, html_path)
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("✅ REPORT GENERATI CON SUCCESSO")
    logger.info("="*70)
    
    if save_files:
        logger.info(f"📄 JSON: {json_path}")
        logger.info(f"📄 HTML: {html_path}")
    
    logger.info(f"📊 JSON Size: {len(json_content):,} bytes")
    logger.info(f"📊 HTML Size: {len(html_content):,} bytes")
    
    return {
        'json_content': json_content,
        'json_path': json_path,
        'html_content': html_content,
        'html_path': html_path
    }

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_json_report(filepath: str) -> Dict:
    """
    Carica JSON report da file.
    
    Args:
        filepath: Path file JSON
    
    Returns:
        Dict con dati report
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"✅ JSON caricato: {filepath}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Errore caricamento JSON: {str(e)}")
        raise

def get_report_summary(json_data: Dict) -> Dict:
    """
    Estrae summary da JSON report.
    
    Args:
        json_data: Dict da load_json_report()
    
    Returns:
        Dict summary
    """
    metadata = json_data.get('metadata', {})
    market_regime = json_data.get('market_regime', {})
    instruments = json_data.get('instruments', {})
    rankings = json_data.get('rankings', {})
    
    summary = {
        'date': metadata.get('analysis_date', 'N/A'),
        'instruments_count': len(instruments),
        'market_condition': market_regime.get('market_condition', 'unknown'),
        'vix_level': market_regime.get('vix_level', 0),
        'top_3': [item['ticker'] for item in rankings.get('by_composite_score', [])[:3]],
        'bottom_3': [item['ticker'] for item in rankings.get('by_composite_score', [])[-3:]]
    }
    
    return summary

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Report Generator Test")
    print("="*70)
    
    # Mock analysis result per test
    print("\n1. Creazione mock analysis result...")
    
    mock_result = {
        'metadata': {
            'analysis_date': '2024-12-31',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'generated_by': 'Test',
            'instruments_analyzed': 3
        },
        'market_regime': {
            'vix_level': 14.5,
            'vix_regime': 'low',
            'spy_trend': 'uptrend',
            'spy_above_sma200': True,
            'market_condition': 'bullish'
        },
        'instruments': {
            'SPY': {
                'info': {'name': 'S&P 500 ETF', 'category': 'Equity Index', 'benchmark': 'SPY'},
                'current': {'price': 500.0, 'change_1d_pct': 0.5, 'volume': 100000000},
                'scores': {'composite': 65, 'trend': 70, 'momentum': 60, 'volatility': 70, 'relative_strength': 0},
                'signals': ['Breaking above weekly high']
            },
            'QQQ': {
                'info': {'name': 'Nasdaq 100 ETF', 'category': 'Equity Index', 'benchmark': 'SPY'},
                'current': {'price': 400.0, 'change_1d_pct': 1.0, 'volume': 50000000},
                'scores': {'composite': 75, 'trend': 80, 'momentum': 70, 'volatility': 75, 'relative_strength': 80},
                'signals': []
            },
            'XLK': {
                'info': {'name': 'Technology Select', 'category': 'Sector', 'benchmark': 'SPY'},
                'current': {'price': 200.0, 'change_1d_pct': 0.8, 'volume': 20000000},
                'scores': {'composite': 72, 'trend': 75, 'momentum': 68, 'volatility': 72, 'relative_strength': 75},
                'signals': ['MACD Bullish Crossover']
            }
        },
        'rankings': {
            'by_composite_score': [
                {'ticker': 'QQQ', 'composite': 75, 'trend': 80},
                {'ticker': 'XLK', 'composite': 72, 'trend': 75},
                {'ticker': 'SPY', 'composite': 65, 'trend': 70}
            ]
        },
        'processed_data': {}
    }
    
    print("   ✅ Mock data creato")
    
    # 2. Test JSON generation
    print("\n2. Test JSON Generation...")
    json_content = generate_json_report(mock_result)
    print(f"   ✅ JSON generato: {len(json_content)} chars")
    print(f"\n   Preview (prime 200 chars):")
    print(f"   {json_content[:200]}...")
    
    # 3. Test JSON save
    print("\n3. Test JSON Save...")
    json_path = save_json_report(json_content, 'test_report.json')
    print(f"   ✅ Salvato in: {json_path}")
    
    # 4. Test HTML generation (senza charts)
    print("\n4. Test HTML Generation (mock charts)...")
    mock_charts = {
        'SPY': '<div>SPY Chart Placeholder</div>',
        'QQQ': '<div>QQQ Chart Placeholder</div>',
        'XLK': '<div>XLK Chart Placeholder</div>'
    }
    
    html_content = generate_html_report(mock_result, mock_charts)
    print(f"   ✅ HTML generato: {len(html_content)} chars")
    
    # 5. Test HTML save
    print("\n5. Test HTML Save...")
    html_path = save_html_report(html_content, 'test_report.html')
    print(f"   ✅ Salvato in: {html_path}")
    
    # 6. Test load JSON
    print("\n6. Test Load JSON...")
    loaded_data = load_json_report(json_path)
    print(f"   ✅ JSON caricato: {len(loaded_data)} keys")
    
    # 7. Test summary extraction
    print("\n7. Test Summary Extraction...")
    summary = get_report_summary(loaded_data)
    print("   Summary:")
    for key, value in summary.items():
        print(f"      {key}: {value}")
    
    print("\n" + "="*70)
    print("✅ Test completato con successo!")
    print("\nFile generati:")
    print(f"   - {json_path}")
    print(f"   - {html_path}")
    print("\nApri test_report.html nel browser per vedere il report.")
