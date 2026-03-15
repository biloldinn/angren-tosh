import telebot
from config import TOKEN
from logger import logger

if not TOKEN:
    logger.error("BOT_TOKEN is missing!")
    raise ValueError("BOT_TOKEN is missing!")

bot = telebot.TeleBot(TOKEN, parse_mode=None)

# Set bot commands
bot.set_my_commands([
    telebot.types.BotCommand("start", "Botni ishga tushirish"),
    telebot.types.BotCommand("admin", "Admin panel"),
    telebot.types.BotCommand("status", "Bot holatini ko'rish"),
    telebot.types.BotCommand("setgroups", "Guruhlarni sozlash")
])

logger.info("Bot instance initialized.")
