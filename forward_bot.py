from app import app, run_bot
import threading
import os
from logger import logger

if __name__ == "__main__":
    logger.info("Starting bot via forward_bot.py shim...")
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask app
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)
