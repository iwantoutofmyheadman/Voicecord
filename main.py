import os
import sys
import json
import time
import threading
import requests
import random
import base64
from websocket import WebSocket
from flask import Flask

# --- CONFIGURATION ---
TARGET_GUILD_ID = "1474464326051172418" 
TARGET_CHANNEL_ID = "1474495027223855104" 
OWNER_ID = "1407866476949536848"

# Global state - set default to invisible if you prefer
should_be_in_vc = False 
current_status = "invisible" 

usertoken = os.getenv("TOKEN")
if not usertoken:
    print("[ERROR] TOKEN environment variable is missing!")
else:
    print(f"[INFO] Token detected (starts with: {usertoken[:10]}...)")

# --- WEB SERVER (FOR RAILWAY HEALTH CHECKS) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running and listening.", 200

# --- UTILS ---
def get_super_properties():
    props = {
        "os": "Windows", "browser": "Chrome", "device": "",
        "system_locale": "en-US", "browser_version": "120.0.0.0",
        "os_version": "10", "release_channel": "stable",
    }
    return base64.b64encode(json.dumps(props).encode()).decode()

headers = {
    "Authorization": usertoken,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Super-Properties": get_super_properties()
}

def stealth_delete(channel_id, message_id):
    time.sleep(random.uniform(2.5, 4.5))
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    try: 
        requests.delete(url, headers=headers)
    except: 
        pass

def heartbeat_loop(ws, interval):
    while True:
        time.sleep(interval + random.uniform(0.1, 0.5))
        try: 
            ws.send(json.dumps({"op": 1, "d": None}))
        except: 
            break

# --- MAIN GATEWAY LOGIC ---
def joiner(token):
    global should_be_in_vc, current_status
    
    print("[DEBUG] Connecting to Discord Gateway...")
    ws = WebSocket()
    try:
        ws.connect("wss://gateway.discord.gg/?v=9&encoding=json", timeout=10)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    try:
        hello = json.loads(ws.recv())
        heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000
    except:
        return

    # IDENTIFY
    auth = {
        "op": 2,
        "d": {
            "token": token,
            "capabilities": 16381,
            "properties": {"$os": "Windows", "$browser": "Chrome", "$device": ""},
            "presence": {"status": current_status, "since": 0, "activities": [], "afk": False},
            "compress": False
        }
    }
    ws.send(json.dumps(auth))

    if should_be_in_vc:
        time.sleep(2)
        ws.send(json.dumps({
            "op": 4, "d": {"guild_id": TARGET_GUILD_ID, "channel_id": TARGET_CHANNEL_ID, "self_mute": False, "self_deaf": False}
        }))

    threading.Thread(target=heartbeat_loop, args=(ws, heartbeat_interval), daemon=True).start()
    print("[SUCCESS] Bot is connected and ready.")

    while True:
        try:
            response = ws.recv()
            if not response: break
            event = json.loads(response)
            
            if event.get("t") == "MESSAGE_CREATE":
                data = event.get("d", {})
                if data.get("author", {}).get("id") == OWNER_ID and data.get("guild_id") == TARGET_GUILD_ID:
                    content = data.get("content")

                    if content == ",j":
                        should_be_in_vc = True
                        current_status = "dnd"
                        # Set status to DnD
                        ws.send(json.dumps({"op": 3, "d": {"status": "dnd", "since": 0, "activities": [], "afk": False}}))
                        time.sleep(1.2)
                        # Join VC
                        ws.send(json.dumps({"op": 4, "d": {"guild_id": TARGET_GUILD_ID, "channel_id": TARGET_CHANNEL_ID, "self_mute": False, "self_deaf": False}}))
                        print("✓ Action: Join VC / Status: DnD")
                        threading.Thread(target=stealth_delete, args=(data.get("channel_id"), data.get("id"))).start()

                    elif content == ",l":
                        should_be_in_vc = False
                        current_status = "invisible"
                        # Set status to Invisible
                        ws.send(json.dumps({"op": 3, "d": {"status": "invisible", "since": 0, "activities": [], "afk": False}}))
                        time.sleep(1.2)
                        # Leave VC
                        ws.send(json.dumps({"op": 4, "d": {"guild_id": TARGET_GUILD_ID, "channel_id": None, "self_mute": False, "self_deaf": False}}))
                        print("✓ Action: Leave VC / Status: Invisible")
                        threading.Thread(target=stealth_delete, args=(data.get("channel_id"), data.get("id"))).start()
        except: 
            break

def run_bot():
    while True:
        try:
            joiner(usertoken)
        except Exception as e:
            print(f"Gateway Error: {e}. Reconnecting in 10s...")
            time.sleep(10)

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Start bot in background thread
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Run Flask on the main thread for Railway
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Web Server on port {port}")
    app.run(host="0.0.0.0", port=port)
