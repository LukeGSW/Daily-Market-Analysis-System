# -*- coding: utf-8 -*-
"""
============================================================================
KRITERION QUANT - Daily Market Analysis System
Scheduler Script
============================================================================
Script standalone per esecuzione via GitHub Actions.

Workflow:
1. Esegue analisi completa
2. Genera report JSON + HTML
3. Invia notifica Telegram
4. (Opzionale) Commit risultati su GitHub

Designed per cron job giornaliero ore 08:00 IT (07:00 UTC).
============================================================================
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path
import traceback

# Setup logging PRIMA di importare altri moduli
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dma_scheduler.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Import moduli DMA System
try:
    from market_analysis import run_full_analysis, get_analysis_summary
    from report_generator import generate_complete_reports
    from telegram_notifier import send_daily_summary, send_error_alert, validate_telegram_config
    
    logger.info("✅ Moduli DMA System importati con successo")
    
except ImportError as e:
    logger.error(f"❌ Errore import moduli: {str(e)}")
    logger.error("Assicurati che tutti i file siano presenti nella directory")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Directory per output files
OUTPUT_DIR = Path("./data")
OUTPUT_DIR.mkdir(exist_ok=True)

# Flags operativi (configurabili via environment variables)
SAVE_REPORTS = os.getenv('SAVE_REPORTS', 'true').lower() == 'true'
SEND_TELEGRAM = os.getenv('SEND_TELEGRAM', 'true').lower() == 'true'
COMMIT_RESULTS = os.getenv('COMMIT_RESULTS', 'false').lower() == 'true'

# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def run_daily_analysis():
    """
    Esegue analisi giornaliera completa.
    
    Steps:
    1. Run full market analysis
    2. Generate reports (JSON + HTML)
    3. Send Telegram notification
    4. (Optional) Commit to GitHub
    
    Returns:
        Dict con risultati esecuzione
    """
    execution_start = datetime.now()
    
    logger.info("="*70)
    logger.info("🚀 AVVIO DAILY ANALYSIS - KRITERION QUANT DMA SYSTEM")
    logger.info("="*70)
    logger.info(f"⏰ Execution time: {execution_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📁 Output directory: {OUTPUT_DIR.absolute()}")
    logger.info(f"💾 Save reports: {SAVE_REPORTS}")
    logger.info(f"📱 Send Telegram: {SEND_TELEGRAM}")
    logger.info(f"📤 Commit results: {COMMIT_RESULTS}")
    logger.info("="*70)
    
    execution_result = {
        'success': False,
        'execution_time': None,
        'analysis_completed': False,
        'reports_generated': False,
        'telegram_sent': False,
        'error': None
    }
    
    try:
        # --- STEP 1: RUN ANALYSIS ---
        logger.info("\n" + "="*70)
        logger.info("📊 STEP 1: RUNNING MARKET ANALYSIS")
        logger.info("="*70)
        
        analysis_result = run_full_analysis()
        execution_result['analysis_completed'] = True
        
        # Summary
        summary = get_analysis_summary(analysis_result)
        logger.info("\n📈 Analysis Summary:")
        logger.info(f"   Market Condition: {summary['market_regime']}")
        logger.info(f"   VIX Level: {summary['vix_level']:.2f}")
        logger.info(f"   Instruments: {summary['instruments_count']}")
        logger.info(f"   Signals: {summary['total_signals']}")
        logger.info(f"   Top 3: {', '.join(summary['top_5_tickers'][:3])}")
        
        # --- STEP 2: GENERATE REPORTS ---
        if SAVE_REPORTS:
            logger.info("\n" + "="*70)
            logger.info("📄 STEP 2: GENERATING REPORTS")
            logger.info("="*70)
            
            reports = generate_complete_reports(
                analysis_result,
                output_dir=str(OUTPUT_DIR),
                save_files=True
            )
            
            execution_result['reports_generated'] = True
            
            logger.info("\n✅ Reports saved:")
            logger.info(f"   JSON: {reports['json_path']}")
            logger.info(f"   HTML: {reports['html_path']}")
        else:
            logger.info("\n⏭️  STEP 2: Skipping report generation (SAVE_REPORTS=false)")
        
        # --- STEP 3: SEND TELEGRAM NOTIFICATION ---
        if SEND_TELEGRAM:
            logger.info("\n" + "="*70)
            logger.info("📱 STEP 3: SENDING TELEGRAM NOTIFICATION")
            logger.info("="*70)
            
            # Validate config first
            telegram_validation = validate_telegram_config()
            
            if telegram_validation['ready']:
                success = send_daily_summary(analysis_result)
                execution_result['telegram_sent'] = success
                
                if success:
                    logger.info("✅ Telegram notification sent successfully")
                else:
                    logger.warning("⚠️ Telegram notification failed")
            else:
                logger.warning("⚠️ Telegram not configured - skipping notification")
                logger.warning(f"   Issues: {[k for k, v in telegram_validation.items() if not v and k != 'ready']}")
        else:
            logger.info("\n⏭️  STEP 3: Skipping Telegram (SEND_TELEGRAM=false)")
        
        # --- STEP 4: COMMIT TO GITHUB (OPTIONAL) ---
        if COMMIT_RESULTS:
            logger.info("\n" + "="*70)
            logger.info("📤 STEP 4: COMMITTING RESULTS TO GITHUB")
            logger.info("="*70)
            
            try:
                commit_success = commit_to_github(OUTPUT_DIR)
                if commit_success:
                    logger.info("✅ Results committed to GitHub")
                else:
                    logger.warning("⚠️ Git commit skipped (no changes or git not configured)")
            except Exception as e:
                logger.error(f"❌ Git commit failed: {str(e)}")
        else:
            logger.info("\n⏭️  STEP 4: Skipping Git commit (COMMIT_RESULTS=false)")
        
        # --- EXECUTION COMPLETE ---
        execution_end = datetime.now()
        execution_time = (execution_end - execution_start).total_seconds()
        execution_result['execution_time'] = execution_time
        execution_result['success'] = True
        
        logger.info("\n" + "="*70)
        logger.info("✅ DAILY ANALYSIS COMPLETED SUCCESSFULLY")
        logger.info("="*70)
        logger.info(f"⏱️  Total execution time: {execution_time:.2f} seconds")
        logger.info(f"✅ Analysis: {'OK' if execution_result['analysis_completed'] else 'FAILED'}")
        logger.info(f"✅ Reports: {'OK' if execution_result['reports_generated'] else 'SKIPPED'}")
        logger.info(f"✅ Telegram: {'OK' if execution_result['telegram_sent'] else 'SKIPPED/FAILED'}")
        logger.info("="*70)
        
        return execution_result
        
    except Exception as e:
        # --- ERROR HANDLING ---
        logger.error("\n" + "="*70)
        logger.error("❌ CRITICAL ERROR IN DAILY ANALYSIS")
        logger.error("="*70)
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Error Message: {str(e)}")
        logger.error("\nStack Trace:")
        logger.error(traceback.format_exc())
        logger.error("="*70)
        
        execution_result['error'] = str(e)
        
        # Try to send error alert via Telegram
        if SEND_TELEGRAM:
            try:
                logger.info("\n📱 Attempting to send error alert via Telegram...")
                send_error_alert(e, context="Daily Analysis Scheduler")
            except Exception as telegram_error:
                logger.error(f"⚠️ Failed to send Telegram error alert: {str(telegram_error)}")
        
        return execution_result

# ============================================================================
# GIT OPERATIONS (OPTIONAL)
# ============================================================================

def commit_to_github(output_dir: Path) -> bool:
    """
    Commit report files to GitHub repository.
    
    Useful per storicizzare analisi giornaliere.
    
    Args:
        output_dir: Directory con file da committare
    
    Returns:
        True se commit riuscito
    """
    import subprocess
    
    try:
        logger.info("📤 Preparing git commit...")
        
        # Check if git is configured
        result = subprocess.run(
            ['git', 'config', 'user.name'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning("Git user not configured - skipping commit")
            return False
        
        # Add files
        logger.info(f"   Adding files from {output_dir}...")
        subprocess.run(
            ['git', 'add', str(output_dir)],
            check=True
        )
        
        # Check if there are changes
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            capture_output=True
        )
        
        if result.returncode == 0:
            logger.info("   No changes to commit")
            return False
        
        # Commit
        commit_message = f"Daily Market Analysis - {datetime.now().strftime('%Y-%m-%d')}"
        logger.info(f"   Committing: {commit_message}")
        
        subprocess.run(
            ['git', 'commit', '-m', commit_message],
            check=True
        )
        
        # Push
        logger.info("   Pushing to remote...")
        subprocess.run(
            ['git', 'push'],
            check=True
        )
        
        logger.info("✅ Git commit completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Git operation failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in git operations: {str(e)}")
        return False

# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_usage():
    """Print usage instructions."""
    print("""
KRITERION QUANT - Daily Market Analysis Scheduler

Usage:
    python scheduler.py [options]

Options:
    --no-reports     Skip report generation
    --no-telegram    Skip Telegram notification
    --commit         Commit results to GitHub
    --help           Show this help message

Environment Variables:
    SAVE_REPORTS     Save JSON/HTML reports (default: true)
    SEND_TELEGRAM    Send Telegram notification (default: true)
    COMMIT_RESULTS   Commit to GitHub (default: false)

Examples:
    # Standard execution (GitHub Actions default)
    python scheduler.py

    # Local test without Telegram
    python scheduler.py --no-telegram

    # Full execution with git commit
    python scheduler.py --commit

Notes:
    - Requires EODHD_API_KEY configured
    - Telegram requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
    - Git commit requires repository with write access
    """)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for scheduler."""
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        print_usage()
        sys.exit(0)
    
    # Override config from CLI args
    global SAVE_REPORTS, SEND_TELEGRAM, COMMIT_RESULTS
    
    if '--no-reports' in args:
        SAVE_REPORTS = False
        logger.info("CLI: Report generation disabled")
    
    if '--no-telegram' in args:
        SEND_TELEGRAM = False
        logger.info("CLI: Telegram notification disabled")
    
    if '--commit' in args:
        COMMIT_RESULTS = True
        logger.info("CLI: Git commit enabled")
    
    # Run daily analysis
    try:
        result = run_daily_analysis()
        
        # Exit code based on success
        if result['success']:
            logger.info("\n🎉 Scheduler execution completed successfully")
            sys.exit(0)
        else:
            logger.error("\n❌ Scheduler execution failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

if __name__ == "__main__":
    main()
