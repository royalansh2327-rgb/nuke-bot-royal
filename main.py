import os
import time
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Get secrets/settings from Render Environment Variables
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "1410458084874260592")
AUTH_SECRET = os.getenv("AUTH_SECRET", "")

if not BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set in Render Environment Variables.")


def send_discord_embed(embed):
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"

    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        headers=headers,
        json={"embeds": [embed]},
        timeout=15
    )

    if response.status_code == 429:
        data = response.json()
        time.sleep(float(data.get("retry_after", 1)))

        response = requests.post(
            url,
            headers=headers,
            json={"embeds": [embed]},
            timeout=15
        )

    response.raise_for_status()


@app.route("/")
def home():
    return "Command Logger is online!"


@app.route("/notify", methods=["POST"])
def notify():
    if AUTH_SECRET:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {AUTH_SECRET}":
            return jsonify({"error": "Unauthorized"}), 401

    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400

    data = request.get_json()

    command = str(data.get("command", "Unknown"))
    username = str(data.get("username", "Unknown User"))
    user_id = str(data.get("user_id", "Unknown"))
    bot_name = str(data.get("bot_name", "Unknown Bot"))
    description = str(
        data.get("description", "No description provided.")
    )

    embed = {
        "title": "Command Triggered",
        "description": "A command or trigger was used.",
        "color": 3092798,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [
            {
                "name": "Command / Trigger",
                "value": f"`{command}`",
                "inline": True
            },
            {
                "name": "Who triggered it",
                "value": f"{username} (`{user_id}`)",
                "inline": True
            },
            {
                "name": "Bot Used",
                "value": bot_name,
                "inline": True
            },
            {
                "name": "What it did",
                "value": description[:1024],
                "inline": False
            }
        ],
        "footer": {
            "text": "Command Logger"
        }
    }

    try:
        send_discord_embed(embed)
        return jsonify({"ok": True}), 200

    except requests.HTTPError as error:
        return jsonify({
            "error": "Discord API error",
            "details": error.response.text if error.response else str(error)
        }), 500

    except Exception as error:
        return jsonify({
            "error": "Server error",
            "details": str(error)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
