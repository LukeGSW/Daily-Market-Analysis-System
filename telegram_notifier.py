# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Telegram Notifier Module
============================================================================
Gestisce invio notifiche giornaliere via Telegram Bot:
- Summary market regime
- Top/Bottom performers
- Segnali critici
- Statistiche analisi

Formato messaggio: Markdown con emoji per readability.
============================================================================
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    from telegram import Bot
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("⚠️ python-telegram-bot non installato. Funzionalità Telegram disabilitate.")

from config import CONFIG, SECRETS

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# TELEGRAM NOTIFIER CLASS
# ============================================================================

class TelegramNotifier:
    """
    Gestisce notifiche Telegram per DMA System.
    """
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Inizializza Telegram Notifier.
        
        Args:
            bot_token: Telegram Bot Token (default: da SECRETS)
            chat_id: Telegram Chat ID (default: da SECRETS)
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError(
                "python-telegram-bot non installato. "
                "Installa con: pip install python-telegram-bot"
            )
        
        self.bot_token = bot_token or SECRETS.get('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = chat_id or SECRETS.get('TELEGRAM_CHAT_ID', '')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN non configurato")
        
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID non configurato")
        
        self.bot = Bot(token=self.bot_token)
        self.max_message_length = CONFIG.get('TELEGRAM_MAX_MESSAGE_LENGTH', 4096)
        
        logger.info("✅ Telegram Notifier inizializzato")
    
    async def send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.MARKDOWN,
        disable_preview: bool = True
    ) -> bool:
        """
        Invia messaggio Telegram.
        
        Args:
            text: Testo messaggio
            parse_mode: Markdown o HTML
            disable_preview: Disabilita link preview
        
        Returns:
            True se invio riuscito
        """
        try:
            # Truncate se troppo lungo
            if len(text) > self.max_message_length:
                logger.warning(f"⚠️ Messaggio troncato: {len(text)} → {self.max_message_length} chars")
                text = text[:self.max_message_length - 50] + "\n\n... [Messaggio troncato]"
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
            
            logger.info("✅ Messaggio Telegram inviato con successo")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore invio Telegram: {str(e)}")
            return False
    
    def send_message_sync(
        self,
        text: str,
        parse_mode: str = ParseMode.MARKDOWN,
        disable_preview: bool = True
    ) -> bool:
        """
        Versione sincrona di send_message.
        
        Utile per chiamate da script non-async.
        """
        return asyncio.run(
            self.send_message(text, parse_mode, disable_preview)
        )

# ============================================================================
# MESSAGE FORMATTING
# ============================================================================

def format_daily_summary(analysis_result: Dict) -> str:
    """
    Formatta messaggio giornaliero per Telegram.
    
    Args:
        analysis_result: Output da market_analysis.run_full_analysis()
    
    Returns:
        Messaggio formattato in Markdown
    """
    metadata = analysis_result.get('metadata', {})
    market_regime = analysis_result.get('market_regime', {})
    instruments = analysis_result.get('instruments', {})
    rankings = analysis_result.get('rankings', {})
    
    # Extract data
    date = metadata.get('analysis_date', datetime.now().strftime('%Y-%m-%d'))
    instruments_count = len(instruments)
    
    vix_level = market_regime.get('vix_level', 0)
    vix_regime = market_regime.get('vix_regime', 'unknown')
    spy_trend = market_regime.get('spy_trend', 'unknown')
    spy_above_sma200 = market_regime.get('spy_above_sma200', False)
    market_condition = market_regime.get('market_condition', 'unknown')
    
    # Top/Bottom performers
    by_composite = rankings.get('by_composite_score', [])
    top_5 = by_composite[:5] if by_composite else []
    bottom_5 = by_composite[-5:] if by_composite else []
    bottom_5.reverse()
    
    # Count total signals
    total_signals = sum(
        len(inst.get('signals', []))
        for inst in instruments.values()
    )
    
    # Critical signals (ticker con più segnali)
    ticker_signals = [
        (ticker, len(data.get('signals', [])))
        for ticker, data in instruments.items()
        if data.get('signals', [])
    ]
    ticker_signals.sort(key=lambda x: x[1], reverse=True)
    critical_tickers = ticker_signals[:3]
    
    # --- BUILD MESSAGE ---
    
    message = f"""📊 *KRITERION QUANT - Daily Market Analysis*
📅 {date}

"""
    
    # Market Regime
    vix_emoji = "🟢" if vix_regime == "low" else "🟡" if vix_regime == "medium" else "🔴"
    spy_emoji = "📈" if spy_trend == "uptrend" else "📉"
    
    message += f"""*🌍 MARKET REGIME*
{vix_emoji} *VIX:* {vix_level:.2f} ({vix_regime.upper()})
{spy_emoji} *SPY:* {spy_trend.upper()} ({'Above' if spy_above_sma200 else 'Below'} SMA200)
💼 *Condition:* {market_condition.replace('_', ' ').title()}

"""
    
    # Analysis Stats
    message += f"""*📈 ANALYSIS STATS*
🎯 Instruments: {instruments_count}
⚠️ Total Signals: {total_signals}

"""
    
    # Top 5 Performers
    message += "*🏆 TOP 5 PERFORMERS*\n"
    for i, item in enumerate(top_5, 1):
        ticker = item.get('ticker', 'N/A')
        score = item.get('composite', 0)
        trend = item.get('trend', 0)
        
        # Emoji based on score
        if score >= 70:
            emoji = "🟢"
        elif score >= 55:
            emoji = "🟡"
        else:
            emoji = "🟠"
        
        message += f"{emoji} `{ticker:6s}` Score: *{score:.1f}* (Trend: {trend:.0f})\n"
    
    message += "\n"
    
    # Bottom 5 Performers
    message += "*⚠️ BOTTOM 5 PERFORMERS*\n"
    for i, item in enumerate(bottom_5, 1):
        ticker = item.get('ticker', 'N/A')
        score = item.get('composite', 0)
        trend = item.get('trend', 0)
        
        # Emoji based on score
        if score >= 40:
            emoji = "🟠"
        elif score >= 25:
            emoji = "🔴"
        else:
            emoji = "⛔"
        
        message += f"{emoji} `{ticker:6s}` Score: *{score:.1f}* (Trend: {trend:.0f})\n"
    
    message += "\n"
    
    # Critical Signals
    if critical_tickers:
        message += "*🔔 CRITICAL SIGNALS*\n"
        for ticker, signal_count in critical_tickers:
            ticker_data = instruments.get(ticker, {})
            signals = ticker_data.get('signals', [])
            
            # Show first 2 signals
            signals_preview = signals[:2]
            message += f"• *{ticker}* ({signal_count} signals):\n"
            for sig in signals_preview:
                message += f"  → {sig}\n"
        
        message += "\n"
    
    # Footer
    message += """━━━━━━━━━━━━━━━━━━
🤖 Kriterion Quant DMA System v1.0
🌐 [KriterionQuant.com](https://kriterionquant.com)
"""
    
    return message

def format_error_message(error: Exception, context: str = "") -> str:
    """
    Formatta messaggio errore per Telegram.
    
    Args:
        error: Exception
        context: Contesto errore
    
    Returns:
        Messaggio formattato
    """
    message = f"""❌ *KRITERION QUANT - ERROR ALERT*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    if context:
        message += f"*Context:* {context}\n"
    
    message += f"""*Error Type:* {type(error).__name__}
*Message:* {str(error)}

⚠️ Daily analysis failed. Please check logs.
"""
    
    return message

def format_test_message() -> str:
    """
    Genera messaggio test per verificare Telegram bot.
    
    Returns:
        Messaggio test formattato
    """
    message = f"""🧪 *KRITERION QUANT - TEST MESSAGE*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Telegram Bot connection successful!

*Configuration:*
• Bot Token: Configured ✓
• Chat ID: Configured ✓
• Max Message Length: 4096 chars

This is a test message to verify that the Telegram notification system is working correctly.

━━━━━━━━━━━━━━━━━━
🤖 Kriterion Quant DMA System v1.0
"""
    
    return message

# ============================================================================
# HIGH-LEVEL NOTIFICATION FUNCTIONS
# ============================================================================

def send_daily_summary(analysis_result: Dict) -> bool:
    """
    Invia summary giornaliero via Telegram.
    
    Args:
        analysis_result: Output da market_analysis.run_full_analysis()
    
    Returns:
        True se invio riuscito
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("⚠️ Telegram non disponibile - skip notification")
        return False
    
    try:
        logger.info("📱 Preparazione notifica Telegram...")
        
        # Format message
        message = format_daily_summary(analysis_result)
        
        # Send
        notifier = TelegramNotifier()
        success = notifier.send_message_sync(message)
        
        if success:
            logger.info("✅ Notifica giornaliera inviata con successo")
        else:
            logger.error("❌ Invio notifica fallito")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Errore send_daily_summary: {str(e)}")
        return False

def send_error_alert(error: Exception, context: str = "") -> bool:
    """
    Invia alert errore via Telegram.
    
    Args:
        error: Exception
        context: Contesto errore
    
    Returns:
        True se invio riuscito
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("⚠️ Telegram non disponibile - skip error alert")
        return False
    
    try:
        logger.info("🚨 Invio error alert...")
        
        # Format message
        message = format_error_message(error, context)
        
        # Send
        notifier = TelegramNotifier()
        success = notifier.send_message_sync(message)
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Errore send_error_alert: {str(e)}")
        return False

def send_test_message() -> bool:
    """
    Invia messaggio test per verificare bot.
    
    Returns:
        True se invio riuscito
    """
    if not TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot non installato")
        return False
    
    try:
        print("🧪 Invio messaggio test...")
        
        # Format message
        message = format_test_message()
        
        # Send
        notifier = TelegramNotifier()
        success = notifier.send_message_sync(message)
        
        if success:
            print("✅ Test message inviato con successo!")
        else:
            print("❌ Invio test message fallito")
        
        return success
        
    except ValueError as e:
        print(f"❌ Configurazione mancante: {str(e)}")
        print("\nConfigura TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID in:")
        print("  - .streamlit/secrets.toml (locale/Streamlit Cloud)")
        print("  - Environment variables (GitHub Actions)")
        return False
        
    except Exception as e:
        print(f"❌ Errore: {str(e)}")
        return False

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_telegram_config() -> Dict[str, bool]:
    """
    Valida configurazione Telegram.
    
    Returns:
        Dict con status validazione
    """
    validation = {
        'telegram_lib_installed': TELEGRAM_AVAILABLE,
        'bot_token_configured': bool(SECRETS.get('TELEGRAM_BOT_TOKEN')),
        'chat_id_configured': bool(SECRETS.get('TELEGRAM_CHAT_ID')),
        'ready': False
    }
    
    validation['ready'] = all([
        validation['telegram_lib_installed'],
        validation['bot_token_configured'],
        validation['chat_id_configured']
    ])
    
    return validation

def get_telegram_status() -> str:
    """
    Ritorna status Telegram come stringa descrittiva.
    
    Returns:
        Status message
    """
    validation = validate_telegram_config()
    
    if validation['ready']:
        return "✅ Telegram fully configured and ready"
    
    issues = []
    if not validation['telegram_lib_installed']:
        issues.append("python-telegram-bot not installed")
    if not validation['bot_token_configured']:
        issues.append("TELEGRAM_BOT_TOKEN missing")
    if not validation['chat_id_configured']:
        issues.append("TELEGRAM_CHAT_ID missing")
    
    return f"⚠️ Telegram not ready: {', '.join(issues)}"

# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KRITERION QUANT - Telegram Notifier Test")
    print("="*70)
    
    # 1. Check configuration
    print("\n1. Configuration Check:")
    validation = validate_telegram_config()
    
    print(f"   Telegram Library: {'✅' if validation['telegram_lib_installed'] else '❌'}")
    print(f"   Bot Token: {'✅ Configured' if validation['bot_token_configured'] else '❌ Missing'}")
    print(f"   Chat ID: {'✅ Configured' if validation['chat_id_configured'] else '❌ Missing'}")
    print(f"\n   Status: {get_telegram_status()}")
    
    if not validation['ready']:
        print("\n⚠️ Telegram non configurato correttamente.")
        print("\nPer configurare:")
        print("1. Crea bot con @BotFather su Telegram")
        print("2. Ottieni Bot Token")
        print("3. Aggiungi bot a chat/gruppo")
        print("4. Ottieni Chat ID da getUpdates")
        print("5. Configura in .streamlit/secrets.toml:")
        print('   TELEGRAM_BOT_TOKEN = "your_token"')
        print('   TELEGRAM_CHAT_ID = "your_chat_id"')
        exit(1)
    
    # 2. Test message sending
    print("\n2. Invio Test Message...")
    success = send_test_message()
    
    if not success:
        print("\n❌ Test fallito")
        exit(1)
    
    # 3. Test formatted summary (con mock data)
    print("\n3. Test Formatted Summary (mock data)...")
    
    mock_analysis = {
        'metadata': {
            'analysis_date': '2024-12-31',
            'instruments_analyzed': 28
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
                'scores': {'composite': 65},
                'signals': ['Breaking weekly high']
            },
            'QQQ': {
                'scores': {'composite': 75},
                'signals': ['MACD Bullish Crossover', 'Volume Surge']
            }
        },
        'rankings': {
            'by_composite_score': [
                {'ticker': 'QQQ', 'composite': 75, 'trend': 80},
                {'ticker': 'SPY', 'composite': 65, 'trend': 70},
                {'ticker': 'IWM', 'composite': 60, 'trend': 65},
                {'ticker': 'DIA', 'composite': 58, 'trend': 62},
                {'ticker': 'GLD', 'composite': 55, 'trend': 60},
                {'ticker': 'TLT', 'composite': 45, 'trend': 40},
                {'ticker': 'UNG', 'composite': 20, 'trend': 25}
            ]
        }
    }
    
    formatted = format_daily_summary(mock_analysis)
    print("\n   Preview formatted message:")
    print("   " + "-"*66)
    print("   " + formatted.replace("\n", "\n   ")[:500])
    print("   ...")
    print("   " + "-"*66)
    
    # 4. Ask to send mock summary
    response = input("\n4. Vuoi inviare il mock summary a Telegram? (y/n): ")
    
    if response.lower() == 'y':
        print("\n   Invio mock summary...")
        notifier = TelegramNotifier()
        success = notifier.send_message_sync(formatted)
        
        if success:
            print("   ✅ Mock summary inviato!")
        else:
            print("   ❌ Invio fallito")
    else:
        print("   ⏭️  Skipped")
    
    # 5. Test error alert
    response = input("\n5. Vuoi testare error alert? (y/n): ")
    
    if response.lower() == 'y':
        print("\n   Invio error alert...")
        test_error = Exception("Test error for notification system")
        success = send_error_alert(test_error, "Test Context")
        
        if success:
            print("   ✅ Error alert inviato!")
        else:
            print("   ❌ Invio fallito")
    else:
        print("   ⏭️  Skipped")
    
    print("\n" + "="*70)
    print("✅ Test completato!")
    print("\nNote:")
    print("  - Controlla Telegram per vedere i messaggi ricevuti")
    print("  - Se non ricevi messaggi, verifica Bot Token e Chat ID")
    print("  - Verifica che il bot sia stato aggiunto alla chat")
