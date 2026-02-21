import os
import sys
import json
import time
import threading
import requests
import random
import base64
from websocket import WebSocket
from keep_alive import keep_alive

# --- CONFIGURATION ---
TARGET_GUILD_ID = "1474464326051172418" # The only server where commands will work
TARGET_CHANNEL_ID = "1474495027223855104" # The VC to join
OWNER_ID = "1407866476949536848"

should_be_in_vc = False 
current_status = "online" 

usertoken = os.getenv("TOKEN")

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
    time.sleep(random.uniform(3.0, 5.5))
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    try: requests.delete(url, headers=headers)
    except: pass

def heartbeat_loop(ws, interval):
    while True:
        time.sleep(interval + random.uniform(0.1, 0.7))
        try: ws.send(json.dumps({"op": 1, "d": None}))
        except: break

def joiner(token):
    global should_be_in_vc, current_status
    ws = WebSocket()
    ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
    hello = json.loads(ws.recv())
    heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

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

    while True:
        response = ws.recv()
        if not response: break
        try:
            event = json.loads(response)
            if event.get("t") == "MESSAGE_CREATE":
                data = event.get("d", {})
                
                # --- ADDED SECURITY CHECKS ---
                msg_guild_id = data.get("guild_id")
                author_id = data.get("author", {}).get("id")
                content = data.get("content")

                # Only triggers if: 
                # 1. It's from YOU
                # 2. It's in the RIGHT SERVER
                if author_id == OWNER_ID and msg_guild_id == TARGET_GUILD_ID:
                    
                    if content == ",j":
                        should_be_in_vc = True
                        current_status = "dnd"
                        ws.send(json.dumps({"op": 4, "d": {"guild_id": TARGET_GUILD_ID, "channel_id": TARGET_CHANNEL_ID, "self_mute": False, "self_deaf": False}}))
                        time.sleep(1)
                        ws.send(json.dumps({"op": 3, "d": {"status": "dnd", "since": 0, "activities": [], "afk": False}}))
                        threading.Thread(target=stealth_delete, args=(data.get("channel_id"), data.get("id"))).start()

                    elif content == ",l":
                        should_be_in_vc = False
                        current_status = "online"
                        ws.send(json.dumps({"op": 4, "d": {"guild_id": TARGET_GUILD_ID, "channel_id": None, "self_mute": False, "self_deaf": False}}))
                        time.sleep(1)
                        ws.send(json.dumps({"op": 3, "d": {"status": "online", "since": 0, "activities": [], "afk": False}}))
                        threading.Thread(target=stealth_delete, args=(data.get("channel_id"), data.get("id"))).start()
        except: break

def run_joiner():
    while True:
        try: joiner(usertoken)
        except: time.sleep(10)

keep_alive()
run_joiner()
