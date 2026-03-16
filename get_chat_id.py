import telebot
import os

TOKEN = "8580639697:AAFPv5TYWiWFXFxaMYQWPN7JzCwMUMYkVIQ"
bot = telebot.TeleBot(TOKEN)

try:
    chat = bot.get_chat("@TOSHKENTANGRENTAKSI")
    print(f"CHAT_ID: {chat.id}")
except Exception as e:
    print(f"ERROR: {e}")
