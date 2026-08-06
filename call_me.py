import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TO_NUMBER = os.getenv("MY_PHONE_NUMBER")
WEBHOOK = os.getenv("TWILIO_WEBHOOK")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

print("📞 Calling...")

call = client.calls.create(
    to=TO_NUMBER,
    from_=FROM_NUMBER,
    url=WEBHOOK,
)

print("\n✅ Call Created Successfully!")
print("SID:", call.sid)
print("Status:", call.status)