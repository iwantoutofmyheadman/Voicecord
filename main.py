import os
import sys
import json
import time
import threading
import requests
import random
from websocket import WebSocket
from keep_alive import keep_alive

# Initial default settings
GUILD_ID = "1474464326051172418"
CHANNEL_ID = "1474495027223855104"
OWNER_ID = "1407866476949536848"

SELF_MUTE = False
SELF_DEAF = False

should_be_in_vc = False 
current_status = "online" # Track status globally

usertoken = os.getenv("TOKEN")
if not usertoken:
    print("[ERROR] TOKEN not found in environment variables.")
    sys.exit()

headers = {
    "Authorization": usertoken,
    "Content-Type": "application/json"
}

def stealth_delete(channel_id, message_id):
    delay = random.uniform(1.2, 3.5)
    time.sleep(delay)
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    try:
        requests.delete(url, headers=headers)
    except Exception:
        pass

def heartbeat_loop(ws, interval):
    while True:
        time.sleep(interval)
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

    # Identification & Presence Payload
    auth = {
        "op": 2,
        "d": {
            "token": token,
            "properties": {"$os": "windows", "$browser": "chrome", "$device": "pc"},
            "presence": {"status": current_status, "afk": False}
        }
    }

    # Voice Channel Payload
    vc_payload = {
        "op": 4,
        "d": {
            "guild_id": GUILD_ID,
            "channel_id": CHANNEL_ID,
            "self_mute": SELF_MUTE,
            "self_deaf": SELF_DEAF
        }
    }

    ws.send(json.dumps(auth))
    
    # Rejoin VC if state was already active before a disconnect
    if should_be_in_vc:
        ws.send(json.dumps(vc_payload))

    threading.Thread(target=heartbeat_loop, args=(ws, heartbeat_interval), daemon=True).start()

    while True:
        response = ws.recv()
        if not response: break
            
        try:
            event = json.loads(response)
            if event.get("t") == "MESSAGE_CREATE":
                msg_data = event.get("d", {})
                author_id = msg_data.get("author", {}).get("id")
                content = msg_data.get("content")
                msg_id = msg_data.get("id")
                msg_chan_id = msg_data.get("channel_id")
                
                if author_id == OWNER_ID:
                    # --- LEAVE CALL / ONLINE ---
                    if content == ",l":
                        should_be_in_vc = False
                        current_status = "online"
                        
                        # Update VC (Leave)
                        leave_vc = vc_payload.copy()
                        leave_vc["d"]["channel_id"] = None
                        ws.send(json.dumps(leave_vc))
                        
                        # Update Status (Online)
                        ws.send(json.dumps({"op": 3, "d": {"status": "online", "afk": False, "since": 0, "activities": []}}))
                        
                        print("Left VC and set status to Online.")
                        threading.Thread(target=stealth_delete, args=(msg_chan_id, msg_id)).start()
                        
                    # --- JOIN CALL / DND ---
                    elif content == ",j":
                        should_be_in_vc = True
                        current_status = "dnd"
                        
                        # Update VC (Join)
                        ws.send(json.dumps(vc_payload))
                        
                        # Update Status (DnD)
                        ws.send(json.dumps({"op": 3, "d": {"status": "dnd", "afk": False, "since": 0, "activities": []}}))
                        
                        print("Joined VC and set status to DnD.")
                        threading.Thread(target=stealth_delete, args=(msg_chan_id, msg_id)).start()
                        
        except Exception:
            pass

def run_joiner():
    print("Ready. Commands: ,j (Join/DnD) | ,l (Leave/Online)")
    while True:
        try:
            joiner(usertoken)
        except Exception:
            time.sleep(5)

keep_alive()
run_joiner()
