import asyncio
import time
from bot_instance import bot
from config import config
from logger import logger
import html

def handle_forwarding(message):
    cfg = config
    source = cfg.get('source_group')
    target = cfg.get('destination_group')

    if not cfg.get('is_forwarding_active') or not source or not target:
        return

    if str(message.chat.id) == str(source) or (message.chat.username and message.chat.username == str(source).replace('@', '')):
        try:
            sender = message.from_user
            is_anonymous_bot = sender and sender.id in [1087968824, 777000, 136817688]
            
            if sender and not is_anonymous_bot:
                name = html.escape(sender.first_name + (f" {sender.last_name}" if sender.last_name else ""))
                if sender.username:
                    profile_link = f"<a href='https://t.me/{sender.username}'>{name} (@{sender.username})</a>"
                else:
                    profile_link = f"<a href='tg://user?id={sender.id}'>{name} (Profil)</a>"
            elif message.sender_chat:
                chat = message.sender_chat
                name = html.escape(chat.title or "Mijoz")
                profile_link = f"<a href='https://t.me/{chat.username}'>{name}</a>" if chat.username else f"<b>{name}</b>"
            else:
                profile_link = "<i>Yashirin profil</i>"

            footer = f"\n\n👤 <b>Mijoz:</b> {profile_link}"
            
            # Create inline button for easy profile access
            mk = types.InlineKeyboardMarkup()
            if sender and not is_anonymous_bot:
                if sender.username:
                    mk.add(types.InlineKeyboardButton("✉️ Mijozga yozish", url=f"https://t.me/{sender.username}"))
                else:
                    mk.add(types.InlineKeyboardButton("👤 Profil (Faqat haydovchiga)", url=f"tg://user?id={sender.id}"))
            elif message.sender_chat and message.sender_chat.username:
                mk.add(types.InlineKeyboardButton("👤 Profil (Kanal)", url=f"https://t.me/{message.sender_chat.username}"))

            # Forward based on content type
            if message.text:
                new_text = html.escape(message.text) + footer
                bot.send_message(target, new_text, parse_mode="HTML", reply_markup=mk if mk.keyboard else None)
            elif message.photo:
                caption = html.escape(message.caption or "") + footer
                bot.send_photo(target, message.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=mk if mk.keyboard else None)
            elif message.video:
                caption = html.escape(message.caption or "") + footer
                bot.send_video(target, message.video.file_id, caption=caption, parse_mode="HTML", reply_markup=mk if mk.keyboard else None)
            else:
                # For other types
                copied = bot.copy_message(target, message.chat.id, message.message_id, reply_markup=mk if mk.keyboard else None)
                bot.send_message(target, f"☝️ Yuqoridagi xabar egasi: {profile_link}", parse_mode="HTML", reply_to_message_id=copied.message_id)

            logger.info(f"Message {message.message_id} forwarded with profile link to {target}")
            
            # Delete from source
            bot.delete_message(message.chat.id, message.message_id)
            logger.info(f"Message {message.message_id} deleted from source {message.chat.id}")
        except Exception as e:
            logger.error(f"Forwarding error: {e}")

# Separate handler for channel posts if needed
def handle_channel_forwarding(message):
    handle_forwarding(message)
