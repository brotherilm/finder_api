import requests
import sys

# Ganti dengan token bot Anda
TOKEN = "8186303125:AAEU3cKzbllqtiot55iRbDf0Q5yK44EelGA"

# Ganti dengan URL Vercel deployment Anda
WEBHOOK_URL = "https://your-vercel-domain.vercel.app/api/webhook"

def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    data = {
        "url": WEBHOOK_URL,
        "allowed_updates": ["message"]
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def delete_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
    response = requests.post(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def get_webhook_info():
    url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "set":
            set_webhook()
        elif sys.argv[1] == "delete":
            delete_webhook()
        elif sys.argv[1] == "info":
            get_webhook_info()
        else:
            print("Usage: python setup_webhook.py [set|delete|info]")
    else:
        get_webhook_info()
