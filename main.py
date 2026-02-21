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
GUILD_ID = "1474464326051172418"
CHANNEL_ID = "1474495027223855104"
OWNER_ID = "1407866476949536848"

should_be_in_vc = False 
current_status = "online" 

usertoken = os.getenv("TOKEN")

# Generate X-Super-Properties to mimic a real Chrome browser
def get_super_properties():
    props = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "browser_version": "120.0.0.0",
        "os_version": "10",
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": 256523,
        "client_event_source": None
    }
    return base64.b64encode(json.dumps(props).encode()).decode()

headers = {
    "Authorization": usertoken,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Super-Properties": get_super_properties()
}

def stealth_delete(channel_id, message_id):
    # Human-like delay: mimics someone clicking 'delete'
    time.sleep(random.uniform(2.5, 5.0))
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    try: 
        requests.delete(url, headers=headers)
    except: 
        pass

def heartbeat_loop(ws, interval):
    while True:
        # Randomized heartbeat interval to avoid perfect periodicity
        jitter = random.uniform(0.1, 0.9)
        time.sleep(interval + jitter)
        try: 
            ws.send(json.dumps({"op": 1, "d": None}))
        except: 
            break

def joiner(token):
    global should_be_in_vc, current_status
    
    ws = WebSocket()
    ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")

    hello = json.loads(ws.recv())
    heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

    # 1. Identify (Mimicking a real browser login)
    auth = {
        "op": 2,
        "d": {
            "token": token,
            "capabilities": 16381, # Real client capability flag
            "properties": {
                "$os": "Windows",
                "$browser": "Chrome",
                "$device": "",
                "$system_locale": "en-US",
                "$browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "$browser_version": "120.0.0.0",
                "$os_version": "10",
            },
            "presence": {"status": current_status, "afk": False},
            "compress": False
        }
    }
    ws.send(json.dumps(auth))

    # Initial rejoin logic if applicable
    if should_be_in_vc:
        time.sleep(random.uniform(2.0, 4.0))
        ws.send(json.dumps({
            "op": 4,
            "d": {"guild_id": GUILD_ID, "channel_id": CHANNEL_ID, "self_mute": False, "self_deaf": False}
        }))

    threading.Thread(target=heartbeat_loop, args=(ws, heartbeat_interval), daemon=True).start()

    while True:
        response = ws.recv()
        if not response: break
        
        try:
            event = json.loads(response)
            if event.get("t") == "MESSAGE_CREATE":
                data = event.get("d", {})
                if data.get("author", {}).get("id") == OWNER_ID:
                    content = data.get("content")
                    
                    # --- JOIN COMMAND ---
                    if content == ",j":
                        should_be_in_vc = True
                        current_status = "dnd"
                        
                        # Random delay to look like human reaction time
                        time.sleep(random.uniform(0.5, 1.2))
                        
                        ws.send(json.dumps({
                            "op": 4,
                            "d": {"guild_id": GUILD_ID, "channel_id": CHANNEL_ID, "self_mute": False, "self_deaf": False}
                        }))
                        
                        time.sleep(random.uniform(0.8, 1.5))
                        
                        ws.send(json.dumps({
                            "op": 3, 
                            "d": {"status": "dnd", "afk": False, "since": 0, "activities": []}
                        }))
                        threading.Thread(target=stealth_delete, args=(data.get("channel_id"), data.get("id"))).start()

                    # --- LEAVE COMMAND ---
                    elif content == ",l":
                        should_be_in_vc = False
                        current_status = "online"
                        
                        time.sleep(random.uniform(0.5, 1.2))
                        
                        ws.send(json.dumps({
                            "op": 4,
                            "d": {"guild_id": GUILD_ID, "channel_id": None, "self_mute": False, "self_deaf": False}
                        }))
                        
                        time.sleep(random.uniform(0.8, 1.5))
                        
                        ws.send(json.dumps({
                            "op": 3, 
                            "d": {"status": "online", "afk": False, "since": 0, "activities": []}
                        }))
                        threading.Thread(target=stealth_delete, args=(data.get("channel_id"), data.get("id"))).start()
                        
        except:
            break

def run_joiner():
    while True:
        try:
            joiner(usertoken)
        except:
            # Exponential backoff on disconnect
            time.sleep(random.uniform(5, 15))

keep_alive()
run_joiner()
