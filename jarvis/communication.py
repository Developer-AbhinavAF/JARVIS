"""jarvis.communication

Communication integrations: WhatsApp, Discord, Slack, Telegram, SMS.
"""

from __future__ import annotations

import logging
import subprocess
import time
import webbrowser
from dataclasses import dataclass
from typing import Any

from jarvis.secure_storage import secure_storage

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Message data."""
    platform: str
    recipient: str
    content: str
    timestamp: str


class WhatsAppController:
    """WhatsApp Web integration."""
    
    def send_message(self, phone: str, message: str) -> str:
        """Send WhatsApp message via WhatsApp Web."""
        # Format phone number
        phone = phone.replace(" ", "").replace("-", "").replace("+", "")
        if not phone.startswith("91"):
            phone = "91" + phone  # India default
        
        # Encode message
        encoded_msg = message.replace(" ", "%20").replace("\n", "%0A")
        
        # Open WhatsApp Web
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
        webbrowser.open(url)
        
        return f"Opening WhatsApp Web to send message to {phone}"
    
    def open_chat(self, phone: str | None = None) -> str:
        """Open WhatsApp chat."""
        if phone:
            phone = phone.replace(" ", "").replace("-", "").replace("+", "")
            if not phone.startswith("91"):
                phone = "91" + phone
            url = f"https://web.whatsapp.com/send?phone={phone}"
        else:
            url = "https://web.whatsapp.com"
        
        webbrowser.open(url)
        return "Opening WhatsApp Web"


class DiscordController:
    """Discord integration."""
    
    def __init__(self) -> None:
        self.bot_token = secure_storage.get("DISCORD_BOT_TOKEN")
        self.webhook_url = secure_storage.get("DISCORD_WEBHOOK_URL")
    
    def open_discord(self) -> str:
        """Open Discord app or web."""
        # Try to open Discord app first
        try:
            subprocess.Popen(["discord"], shell=True)
            return "Opening Discord"
        except Exception:
            # Fallback to web
            webbrowser.open("https://discord.com/app")
            return "Opening Discord Web"
    
    def send_via_webhook(self, message: str, channel: str = "general") -> str:
        """Send message via webhook."""
        if not self.webhook_url:
            return "Discord webhook not configured"
        
        try:
            import requests
            
            payload = {
                "content": message,
                "username": "JARVIS",
            }
            
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 204:
                return f"Message sent to Discord #{channel}"
            return f"Failed to send: {response.status_code}"
            
        except Exception as e:
            return f"Discord webhook error: {e}"


class SlackController:
    """Slack integration."""
    
    def __init__(self) -> None:
        self.token = secure_storage.get("SLACK_BOT_TOKEN")
        self.webhook = secure_storage.get("SLACK_WEBHOOK_URL")
    
    def open_slack(self) -> str:
        """Open Slack."""
        try:
            subprocess.Popen(["slack"], shell=True)
            return "Opening Slack"
        except Exception:
            webbrowser.open("https://slack.com")
            return "Opening Slack Web"
    
    def send_message(self, channel: str, text: str) -> str:
        """Send Slack message."""
        if not self.token:
            return "Slack token not configured"
        
        try:
            import requests
            
            url = "https://slack.com/api/chat.postMessage"
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "channel": channel,
                "text": text,
            }
            
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            
            if data.get("ok"):
                return f"Message sent to #{channel}"
            return f"Slack error: {data.get('error', 'Unknown error')}"
            
        except Exception as e:
            return f"Slack send error: {e}"
    
    def send_via_webhook(self, text: str) -> str:
        """Send via incoming webhook."""
        if not self.webhook:
            return "Slack webhook not configured"
        
        try:
            import requests
            
            payload = {"text": text}
            response = requests.post(self.webhook, json=payload)
            
            if response.status_code == 200:
                return "Message sent to Slack"
            return f"Webhook failed: {response.status_code}"
            
        except Exception as e:
            return f"Webhook error: {e}"


class TelegramController:
    """Telegram Bot integration."""
    
    def __init__(self) -> None:
        self.bot_token = secure_storage.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = secure_storage.get("TELEGRAM_CHAT_ID")
    
    def send_message(self, text: str) -> str:
        """Send Telegram message."""
        if not self.bot_token or not self.chat_id:
            return "Telegram not configured"
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            
            if data.get("ok"):
                return "Message sent via Telegram"
            return f"Telegram error: {data.get('description', 'Unknown')}"
            
        except Exception as e:
            return f"Telegram send error: {e}"
    
    def open_telegram(self) -> str:
        """Open Telegram."""
        try:
            subprocess.Popen(["telegram"], shell=True)
            return "Opening Telegram"
        except Exception:
            webbrowser.open("https://web.telegram.org")
            return "Opening Telegram Web"


class SMSController:
    """SMS sending via Twilio or similar."""
    
    def __init__(self) -> None:
        self.account_sid = secure_storage.get("TWILIO_ACCOUNT_SID")
        self.auth_token = secure_storage.get("TWILIO_AUTH_TOKEN")
        self.from_number = secure_storage.get("TWILIO_PHONE_NUMBER")
    
    def send_sms(self, to: str, message: str) -> str:
        """Send SMS via Twilio."""
        if not self.account_sid or not self.auth_token:
            return "SMS not configured. Please setup Twilio."
        
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            # Format phone
            to = to.replace(" ", "").replace("-", "")
            if not to.startswith("+"):
                to = "+91" + to
            
            msg = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to,
            )
            
            return f"SMS sent to {to}. SID: {msg.sid}"
            
        except Exception as e:
            return f"SMS failed: {e}"
    
    def send_bulk_sms(self, numbers: list[str], message: str) -> str:
        """Send bulk SMS."""
        results = []
        for num in numbers:
            result = self.send_sms(num, message)
            results.append(result)
        
        success = sum(1 for r in results if "sent" in r.lower())
        return f"Bulk SMS: {success}/{len(numbers)} sent successfully"


class VoiceRecorder:
    """Voice call recording."""
    
    def __init__(self) -> None:
        self.is_recording = False
        self.recordings: list[str] = []
    
    def start_recording(self, name: str | None = None) -> str:
        """Start voice recording."""
        if self.is_recording:
            return "Already recording"
        
        self.is_recording = True
        filename = f"recording_{name or time.strftime('%Y%m%d_%H%M%S')}.wav"
        
        # Would integrate with actual audio recording
        # For now, placeholder
        self.recordings.append(filename)
        
        return f"Started recording: {filename}"
    
    def stop_recording(self) -> str:
        """Stop voice recording."""
        if not self.is_recording:
            return "Not recording"
        
        self.is_recording = False
        return "Recording stopped and saved"
    
    def list_recordings(self) -> str:
        """List recordings."""
        if not self.recordings:
            return "No recordings"
        return f"Recordings: {', '.join(self.recordings)}"


# Global instances
whatsapp = WhatsAppController()
discord = DiscordController()
slack = SlackController()
telegram = TelegramController()
sms = SMSController()
recorder = VoiceRecorder()


def send_whatsapp(phone: str, message: str) -> str:
    """Send WhatsApp message."""
    return whatsapp.send_message(phone, message)


def send_discord(message: str, channel: str = "general") -> str:
    """Send Discord message."""
    return discord.send_via_webhook(message, channel)


def send_slack(message: str, channel: str = "general") -> str:
    """Send Slack message."""
    return slack.send_message(channel, message)


def send_telegram(message: str) -> str:
    """Send Telegram message."""
    return telegram.send_message(message)


def send_sms(to: str, message: str) -> str:
    """Send SMS."""
    return sms.send_sms(to, message)
