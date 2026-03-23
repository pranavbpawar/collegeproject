import requests
import datetime

BASE_URL = "https://takes-entrepreneurs-gifts-hosted.trycloudflare.com/api/v1/agent"

print(f"Testing against: {BASE_URL}")

# 1. Register
reg_data = {
    "hostname": "test-remote-pc",
    "username": "remote_employee",
    "os": "Windows",
    "os_version": "11",
    "ip_address": "203.0.113.45",
    "mac_address": "00:1B:44:11:3A:B7"
}
print("Registering agent...")
r = requests.post(f"{BASE_URL}/register", json=reg_data)
r.raise_for_status()
creds = r.json()
agent_id = creds["agent_id"]
api_key = creds["api_key"]
print(f"Registered! ID: {agent_id}, API_KEY: {api_key}")

headers = {
    "x-agent-id": agent_id,
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

# 2. Heartbeat
print("Sending heartbeat...")
hb_data = {
    "agent_id": agent_id,
    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
}
r2 = requests.post(f"{BASE_URL}/heartbeat", headers=headers, json=hb_data)
r2.raise_for_status()
print(f"Heartbeat OK: {r2.json()}")

# 3. Events
print("Sending telemetry events...")
events_data = {
    "agent_id": agent_id,
    "sent_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "events": [
        {
            "type": "website_visit",
            "url": "https://github.com/company/project",
            "title": "GitHub - internal project",
            "browser": "Chrome",
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "type": "app_usage",
            "app_name": "vscode.exe",
            "window_title": "main.py - Visual Studio Code",
            "duration_seconds": 300,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    ]
}
r3 = requests.post(f"{BASE_URL}/events", headers=headers, json=events_data)
r3.raise_for_status()
print(f"Events sent OK. Server received {r3.json().get('received')} events.")
