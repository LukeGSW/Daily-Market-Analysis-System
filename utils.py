# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Utilities Module
============================================================================
Funzioni helper comuni utilizzate in tutto il sistema:
- Number formatting
- Date/time utilities
- Type conversion
- Color mapping
- Logger setup
- File operations
============================================================================
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Union
import numpy as np
import pandas as pd

from config import CONFIG

# ============================================================================
# NUMBER FORMATTING
# ============================================================================

def format_number(
    value: Union[int, float, np.number],
    decimals: int = 2,
    use_separator: bool = True
) -> str:
    """
    Formatta numero con decimali e separatore migliaia.
    
    Args:
        value: Numero da formattare
        decimals: Numero decimali (default: 2)
        use_separator: Usa separatore migliaia (default: True)
    
    Returns:
        Stringa formattata
    
    Examples:
        >>> format_number(1234.567, 2)
        '1,234.57'
        >>> format_number(1234.567, 0)
        '1,235'
    """
    if pd.isna(value) or value is None:
        return "N/A"
    
    try:
        value = float(value)
        
        if use_separator:
            return f"{value:,.{decimals}f}"
        else:
            return f"{value:.{decimals}f}"
            
    except (ValueError, TypeError):
        return "N/A"

def format_percentage(
    value: Union[float, np.number],
    decimals: int = 2,
    include_sign: bool = True
) -> str:
    """
    Formatta numero come percentuale.
    
    Args:
        value: Valore percentuale (es. 5.5 per 5.5%)
        decimals: Numero decimali
        include_sign: Include + per valori positivi
    
    Returns:
        Stringa formattata con %
    
    Examples:
        >>> format_percentage(5.5, 2)
        '+5.50%'
        >>> format_percentage(-2.3, 1)
        '-2.3%'
    """
    if pd.isna(value) or value is None:
        return "N/A"
    
    try:
        value = float(value)
        
        if include_sign:
            return f"{value:+.{decimals}f}%"
        else:
            return f"{value:.{decimals}f}%"
            
    except (ValueError, TypeError):
        return "N/A"

def format_currency(
    value: Union[float, np.number],
    currency: str = "$",
    decimals: int = 2
) -> str:
    """
    Formatta numero come valuta.
    
    Args:
        value: Importo
        currency: Simbolo valuta (default: $)
        decimals: Numero decimali
    
    Returns:
        Stringa formattata con valuta
    
    Examples:
        >>> format_currency(1234.56)
        '$1,234.56'
        >>> format_currency(1234.56, '€', 2)
        '€1,234.56'
    """
    if pd.isna(value) or value is None:
        return "N/A"
    
    try:
        value = float(value)
        formatted = f"{abs(value):,.{decimals}f}"
        
        if value < 0:
            return f"-{currency}{formatted}"
        else:
            return f"{currency}{formatted}"
            
    except (ValueError, TypeError):
        return "N/A"

def format_large_number(value: Union[int, float, np.number]) -> str:
    """
    Formatta numeri grandi con suffissi (K, M, B).
    
    Args:
        value: Numero da formattare
    
    Returns:
        Stringa con suffisso
    
    Examples:
        >>> format_large_number(1234)
        '1.23K'
        >>> format_large_number(1234567)
        '1.23M'
        >>> format_large_number(1234567890)
        '1.23B'
    """
    if pd.isna(value) or value is None:
        return "N/A"
    
    try:
        value = float(value)
        abs_value = abs(value)
        sign = "-" if value < 0 else ""
        
        if abs_value >= 1e9:
            return f"{sign}{abs_value/1e9:.2f}B"
        elif abs_value >= 1e6:
            return f"{sign}{abs_value/1e6:.2f}M"
        elif abs_value >= 1e3:
            return f"{sign}{abs_value/1e3:.2f}K"
        else:
            return f"{sign}{abs_value:.2f}"
            
    except (ValueError, TypeError):
        return "N/A"

# ============================================================================
# DATE/TIME UTILITIES
# ============================================================================

def format_date(
    date: Union[datetime, pd.Timestamp, str],
    format_string: str = '%Y-%m-%d'
) -> str:
    """
    Formatta data in stringa.
    
    Args:
        date: Data da formattare
        format_string: Formato output (default: YYYY-MM-DD)
    
    Returns:
        Stringa data formattata
    
    Examples:
        >>> format_date(datetime(2024, 12, 31))
        '2024-12-31'
        >>> format_date('2024-12-31', '%d/%m/%Y')
        '31/12/2024'
    """
    if pd.isna(date) or date is None:
        return "N/A"
    
    try:
        if isinstance(date, str):
            date = pd.to_datetime(date)
        elif isinstance(date, pd.Timestamp):
            date = date.to_pydatetime()
        
        return date.strftime(format_string)
        
    except Exception:
        return "N/A"

def get_business_days_between(
    start_date: Union[datetime, str],
    end_date: Union[datetime, str]
) -> int:
    """
    Calcola giorni lavorativi tra due date.
    
    Args:
        start_date: Data inizio
        end_date: Data fine
    
    Returns:
        Numero giorni lavorativi
    """
    try:
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        return len(pd.bdate_range(start_date, end_date))
        
    except Exception:
        return 0

def get_date_n_days_ago(n: int, from_date: datetime = None) -> datetime:
    """
    Ritorna data N giorni fa.
    
    Args:
        n: Numero giorni indietro
        from_date: Data di partenza (default: oggi)
    
    Returns:
        Data n giorni fa
    """
    if from_date is None:
        from_date = datetime.now()
    
    return from_date - timedelta(days=n)

def is_market_open(date: datetime = None) -> bool:
    """
    Check se mercato USA è aperto (approssimativo).
    
    Args:
        date: Data da controllare (default: oggi)
    
    Returns:
        True se giorno lavorativo
    
    Note:
        Controllo semplificato (solo weekend).
        Non considera festività USA.
    """
    if date is None:
        date = datetime.now()
    
    # Weekend
    if date.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    return True

# ============================================================================
# TYPE CONVERSION
# ============================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Conversione sicura a float.
    
    Args:
        value: Valore da convertire
        default: Valore default se conversione fallisce
    
    Returns:
        Float o default
    """
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """
    Conversione sicura a int.
    
    Args:
        value: Valore da convertire
        default: Valore default se conversione fallisce
    
    Returns:
        Int o default
    """
    try:
        if pd.isna(value):
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_str(value: Any, default: str = "") -> str:
    """
    Conversione sicura a stringa.
    
    Args:
        value: Valore da convertire
        default: Valore default se None o NaN
    
    Returns:
        Stringa o default
    """
    try:
        if pd.isna(value) or value is None:
            return default
        return str(value)
    except Exception:
        return default

def clean_numeric_string(value: str) -> float:
    """
    Pulisce stringa numerica (rimuove simboli) e converte a float.
    
    Args:
        value: Stringa come "$1,234.56" o "1.234,56 €"
    
    Returns:
        Float pulito
    
    Examples:
        >>> clean_numeric_string("$1,234.56")
        1234.56
        >>> clean_numeric_string("1.234,56 €")
        1234.56
    """
    try:
        # Rimuovi simboli comuni
        cleaned = value.replace('$', '').replace('€', '').replace('£', '')
        cleaned = cleaned.replace(',', '').replace(' ', '').strip()
        
        return float(cleaned)
        
    except (ValueError, AttributeError):
        return 0.0

# ============================================================================
# COLOR MAPPING
# ============================================================================

def get_score_color(score: float) -> str:
    """
    Mappa score (0-100) a colore hex.
    
    Utilizza configurazione da CONFIG['COLORS'].
    
    Args:
        score: Score 0-100
    
    Returns:
        Hex color code
    
    Examples:
        >>> get_score_color(85)
        '#38a169'  # Verde eccellente
        >>> get_score_color(30)
        '#e53e3e'  # Rosso poor
    """
    colors = CONFIG.get('COLORS', {})
    
    if score >= 70:
        return colors.get('SCORE_EXCELLENT', '#38a169')
    elif score >= 55:
        return colors.get('SCORE_GOOD', '#48bb78')
    elif score >= 40:
        return colors.get('SCORE_NEUTRAL', '#d69e2e')
    elif score >= 25:
        return colors.get('SCORE_POOR', '#ed8936')
    else:
        return colors.get('SCORE_BAD', '#e53e3e')

def get_change_color(change: float, use_green_red: bool = True) -> str:
    """
    Colore per variazione percentuale.
    
    Args:
        change: Variazione % (positiva o negativa)
        use_green_red: Verde/rosso se True, blu/rosso se False
    
    Returns:
        Hex color code
    """
    colors = CONFIG.get('COLORS', {})
    
    if change > 0:
        return colors.get('ACCENT_GREEN', '#38a169') if use_green_red else '#3182ce'
    elif change < 0:
        return colors.get('ACCENT_RED', '#e53e3e')
    else:
        return '#718096'  # Grigio per zero

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Converte RGB a hex.
    
    Args:
        r, g, b: Valori 0-255
    
    Returns:
        Hex color string
    
    Examples:
        >>> rgb_to_hex(255, 0, 0)
        '#ff0000'
    """
    return f"#{r:02x}{g:02x}{b:02x}"

def hex_to_rgb(hex_color: str) -> tuple:
    """
    Converte hex a RGB tuple.
    
    Args:
        hex_color: Hex string come '#ff0000' o 'ff0000'
    
    Returns:
        Tuple (r, g, b)
    
    Examples:
        >>> hex_to_rgb('#ff0000')
        (255, 0, 0)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Setup logger personalizzato.
    
    Args:
        name: Nome logger
        level: Livello logging (default: INFO)
        log_file: Path file log (opzionale)
        use_colors: Usa colorlog se disponibile
    
    Returns:
        Logger configurato
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Rimuovi handler esistenti
    logger.handlers = []
    
    # Format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Try colorlog for colored output
    if use_colors:
        try:
            from colorlog import ColoredFormatter
            
            formatter = ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
                datefmt=date_format,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(formatter)
        except ImportError:
            # Fallback to standard formatter
            formatter = logging.Formatter(log_format, datefmt=date_format)
            console_handler.setFormatter(formatter)
    else:
        formatter = logging.Formatter(log_format, datefmt=date_format)
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # File handler (opzionale)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

# ============================================================================
# FILE OPERATIONS
# ============================================================================

def ensure_dir_exists(path: str) -> None:
    """
    Crea directory se non esiste.
    
    Args:
        path: Path directory
    """
    os.makedirs(path, exist_ok=True)

def get_file_size(filepath: str) -> str:
    """
    Ritorna dimensione file in formato leggibile.
    
    Args:
        filepath: Path file
    
    Returns:
        Stringa come "1.23 MB"
    """
    try:
        size_bytes = os.path.getsize(filepath)
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.2f} PB"
        
    except OSError:
        return "N/A"

def safe_read_file(filepath: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    Legge file con gestione errori.
    
    Args:
        filepath: Path file
        encoding: Encoding (default: utf-8)
    
    Returns:
        Contenuto file o None
    """
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logging.error(f"Errore lettura file {filepath}: {str(e)}")
        return None

def safe_write_file(
    filepath: str,
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True
) -> bool:
    """
    Scrive file con gestione errori.
    
    Args:
        filepath: Path file
        content: Contenuto da scrivere
        encoding: Encoding (default: utf-8)
        create_dirs: Crea directory se non esistono
    
    Returns:
        True se scrittura riuscita
    """
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        logging.error(f"Errore scrittura file {filepath}: {str(e)}")
        return False

# ============================================================================
# DATA VALIDATION
# ============================================================================

def is_valid_ticker(ticker: str) -> bool:
    """
    Valida ticker symbol.
    
    Args:
        ticker: Symbol ticker
    
    Returns:
        True se valido
    """
    if not ticker or not isinstance(ticker, str):
        return False
    
    # Rimuovi spazi
    ticker = ticker.strip().upper()
    
    # Lunghezza ragionevole (1-10 chars)
    if len(ticker) < 1 or len(ticker) > 10:
        return False
    
    # Solo lettere, numeri, ^, -, .
    import re
    pattern = r'^[A-Z0-9\^.\-]+$'
    
    return bool(re.match(pattern, ticker))

def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Limita valore tra min e max.
    
    Args:
        value: Valore da limitare
        min_val: Minimo
        max_val: Massimo
    
    Returns:
        Valore clampato
    
    Examples:
        >>> clamp(150, 0, 100)
        100
        >>> clamp(-10, 0, 100)
        0
    """
    return max(min_val, min(max_val, value))

def normalize_score(
    value: float,
    min_val: float = 0.0,
    max_val: float = 100.0
) -> float:
    """
    Normalizza valore in range 0-100.
    
    Args:
        value: Valore da normalizzare
        min_val: Valore minimo originale
        max_val: Valore massimo originale
    
    Returns:
        Score normalizzato 0-100
    """
    if max_val == min_val:
        return 50.0
    
    normalized = ((value - min_val) / (max_val - min_val)) * 100
    return clamp(normalized, 0.0, 100.0)

# ============================================================================
# MISCELLANEOUS
# ============================================================================

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Tronca stringa a lunghezza massima.
    
    Args:
        text: Testo da troncare
        max_length: Lunghezza massima
        suffix: Suffisso per testo troncato
    
    Returns:
        Testo troncato
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_environment() -> str:
    """
    Rileva ambiente di esecuzione.
    
    Returns:
        'streamlit', 'github_actions', 'colab', 'local'
    """
    # Check Streamlit
    try:
        import streamlit
        return 'streamlit'
    except ImportError:
        pass
    
    # Check GitHub Actions
    if os.getenv('GITHUB_ACTIONS') == 'true':
        return 'github_actions'
    
    # Check Google Colab
    try:
        import google.colab
        return 'colab'
    except ImportError:
        pass
    
    return 'local'

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Utilities Test")
    print("="*70)
    
    # 1. Number formatting
    print("\n1. Number Formatting:")
    print(f"   format_number(1234.567): {format_number(1234.567)}")
    print(f"   format_percentage(5.5): {format_percentage(5.5)}")
    print(f"   format_currency(1234.56): {format_currency(1234.56)}")
    print(f"   format_large_number(1234567): {format_large_number(1234567)}")
    
    # 2. Date utilities
    print("\n2. Date Utilities:")
    print(f"   format_date(today): {format_date(datetime.now())}")
    print(f"   is_market_open(): {is_market_open()}")
    print(f"   business_days_between(today, +30d): {get_business_days_between(datetime.now(), datetime.now() + timedelta(days=30))}")
    
    # 3. Type conversion
    print("\n3. Type Conversion:")
    print(f"   safe_float('123.45'): {safe_float('123.45')}")
    print(f"   safe_int('123'): {safe_int('123')}")
    print(f"   clean_numeric_string('$1,234.56'): {clean_numeric_string('$1,234.56')}")
    
    # 4. Color mapping
    print("\n4. Color Mapping:")
    print(f"   get_score_color(85): {get_score_color(85)}")
    print(f"   get_score_color(30): {get_score_color(30)}")
    print(f"   get_change_color(5.5): {get_change_color(5.5)}")
    
    # 5. Data validation
    print("\n5. Data Validation:")
    print(f"   is_valid_ticker('SPY'): {is_valid_ticker('SPY')}")
    print(f"   is_valid_ticker('INVALID@'): {is_valid_ticker('INVALID@')}")
    print(f"   clamp(150, 0, 100): {clamp(150, 0, 100)}")
    
    # 6. Environment detection
    print("\n6. Environment Detection:")
    print(f"   Current environment: {get_environment()}")
    
    # 7. Logger setup
    print("\n7. Logger Setup:")
    test_logger = setup_logger('test_logger', level=logging.INFO)
    test_logger.info("This is a test log message")
    
    print("\n" + "="*70)
    print("✅ Test completato con successo!")
