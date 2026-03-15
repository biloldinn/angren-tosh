from flask import Flask
import threading
from bot_instance import bot
import handlers # Ensure handlers are registered
import ads
from logger import logger

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running with unified structure!"

def run_bot():
    logger.info("Bot starting in polling mode...")
    ads.start_ads()
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        logger.error(f"Bot polling crashed: {e}")

if __name__ == "__main__":
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask app
    app.run(host="0.0.0.0", port=8080)
