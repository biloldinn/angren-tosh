import asyncio
import time
from bot_instance import bot
from config import config
from logger import logger

def handle_forwarding(message):
    cfg = config
    source = cfg.get('source_group')
    target = cfg.get('destination_group')

    if not cfg.get('is_forwarding_active') or not source or not target:
        return

    if str(message.chat.id) == str(source) or message.chat.username == str(source).replace('@', ''):
        try:
            # Copy message to target
            bot.copy_message(target, message.chat.id, message.message_id)
            logger.info(f"Message {message.message_id} forwarded from {source} to {target}")
            
            # Delete from source
            bot.delete_message(message.chat.id, message.message_id)
            logger.info(f"Message {message.message_id} deleted from source {message.chat.id}")
        except Exception as e:
            logger.error(f"Forwarding error: {e}")

# Separate handler for channel posts if needed
def handle_channel_forwarding(message):
    handle_forwarding(message)
