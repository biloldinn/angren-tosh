import os
import json
from dotenv import load_dotenv
from logger import logger

load_dotenv()

TOKEN = os.environ.get('BOT_TOKEN')
# Admin IDs - supports multiple
admin_id_env = os.environ.get('ADMIN_ID', '7985206085')
ADMIN_IDS = [int(i.strip()) for i in admin_id_env.split(',') if i.strip().isdigit()]
# Add the second admin ID if not already present
if 1506545257 not in ADMIN_IDS:
    ADMIN_IDS.append(1506545257)

CONFIG_FILE = 'bot_config.json'

DEFAULT_CONFIG = {
    "ad_text": "Sizning reklamangiz shu yerda bo'lishi mumkin!",
    "ad_photo": None,
    "ad_interval_minutes": 5,
    "is_ad_active": False,
    "is_forwarding_active": True,
    "source_group": None,
    "destination_group": None,
    "ad_target_group": None
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

config = load_config()
