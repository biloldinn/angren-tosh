from flask import Flask
import threading
import time
import requests
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def ping_self():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        print("[KEP ALIVE] RENDER_EXTERNAL_URL not set. Self-ping disabled.")
        return
    
    print(f"[KEEP ALIVE] Starting self-ping for {url}")
    while True:
        try:
            requests.get(url)
            print(f"[KEEP ALIVE] Pinged {url} successfully")
        except Exception as e:
            print(f"[KEEP ALIVE] Self-ping failed: {e}")
        time.sleep(600) # Ping every 10 minutes

# Start self-ping in a separate thread
threading.Thread(target=ping_self, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
