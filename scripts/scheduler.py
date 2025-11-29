import schedule
import time
import subprocess
import logging
import os
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_script(script_name):
    """Runs a python script and logs the output."""
    logger.info(f"🚀 Starting {script_name}...")
    try:
        # Resolve script path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, script_name)
        
        # Use the venv python if available, else system python
        # Check relative to script_dir (which is scripts/) -> ../venv
        venv_python = os.path.join(script_dir, '..', 'venv', 'bin', 'python')
        python_executable = venv_python if os.path.exists(venv_python) else "python3"
            
        result = subprocess.run(
            [python_executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"✅ {script_name} completed successfully.")
        logger.info(f"Output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {script_name} failed with error:")
        logger.error(e.stderr)
    except Exception as e:
        logger.error(f"❌ Unexpected error running {script_name}: {e}")

def job_daily_update():
    logger.info("⏰ Triggering Daily Update...")
    # 1. Fetch Matches (API)
    run_script("scripts/etl_pipeline.py")
    # 2. Scrape Tactical Data
    run_script("scripts/scraper_pipeline.py")
    # 3. Scrape Players
    run_script("scripts/scraper_players.py")
    logger.info("💤 Update Job Finished. Sleeping...")

# Schedule the job
# Run every day at 02:00 AM
schedule.every().day.at("02:00").do(run_script, "scripts/scraper_players.py") # Update players
schedule.every().day.at("02:30").do(job_daily_update) # Full pipeline

logger.info("⏳ Scheduler Started. Waiting for jobs...")
logger.info("   - Daily Player Sync at 02:00")
logger.info("   - Full Data Pipeline at 02:30")

while True:
    schedule.run_pending()
    time.sleep(60)
