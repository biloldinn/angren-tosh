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

    if str(message.chat.id) == str(source) or (message.chat.username and message.chat.username == str(source).replace('@', '')):
        try:
            user = message.from_user
            if not user:
                profile_link = "Noma'lum"
            else:
                name = user.first_name + (f" {user.last_name}" if user.last_name else "")
                if user.username:
                    profile_link = f"<a href='https://t.me/{user.username}'>{name} (@{user.username})</a>"
                else:
                    profile_link = f"<a href='tg://user?id={user.id}'>{name} (Profil)</a>"

            footer = f"\n\n👉 <b>Mijoz:</b> {profile_link}"
            
            # Forward based on content type
            if message.text:
                new_text = message.text + footer
                bot.send_message(target, new_text, parse_mode="HTML")
            elif message.photo:
                caption = (message.caption or "") + footer
                bot.send_photo(target, message.photo[-1].file_id, caption=caption, parse_mode="HTML")
            elif message.video:
                caption = (message.caption or "") + footer
                bot.send_video(target, message.video.file_id, caption=caption, parse_mode="HTML")
            else:
                # For other types, just copy but add a notification message
                bot.copy_message(target, message.chat.id, message.message_id)
                bot.send_message(target, f"☝️ Yuqodagi xabar egasi: {profile_link}", parse_mode="HTML")

            logger.info(f"Message {message.message_id} forwarded with profile link to {target}")
            
            # Delete from source
            bot.delete_message(message.chat.id, message.message_id)
            logger.info(f"Message {message.message_id} deleted from source {message.chat.id}")
        except Exception as e:
            logger.error(f"Forwarding error: {e}")

# Separate handler for channel posts if needed
def handle_channel_forwarding(message):
    handle_forwarding(message)
