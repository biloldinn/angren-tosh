import time
from apscheduler.schedulers.background import BackgroundScheduler
from bot_instance import bot
from config import config, save_config
from logger import logger

scheduler = BackgroundScheduler()

def send_ad(force=False):
    cfg = config # Uses shared config object
    target_id = cfg.get('ad_target_group') or cfg.get('destination_group')
    
    if not target_id:
        return

    if not force and not cfg.get('is_ad_active'):
        return

    try:
        if cfg.get('ad_photo'):
            bot.send_photo(target_id, cfg['ad_photo'], caption=cfg.get('ad_text'))
        elif cfg.get('ad_text'):
            bot.send_message(target_id, cfg['ad_text'])
        logger.info(f"Ad sent to {target_id}")
    except Exception as e:
        logger.error(f"Failed to send ad: {e}")

def reschedule_ads():
    scheduler.remove_all_jobs()
    if config.get('is_ad_active') and config.get('ad_interval_minutes', 0) > 0:
        scheduler.add_job(send_ad, 'interval', minutes=config['ad_interval_minutes'], id='ad_job')
        logger.info(f"Ad job scheduled every {config['ad_interval_minutes']} minutes")

def start_ads():
    if not scheduler.running:
        scheduler.start()
    reschedule_ads()
