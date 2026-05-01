import os
import re
import tempfile
import requests
import discord
from PIL import Image
import pytesseract

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

IGNORE_STATUS_WORDS = [
    "won", "winner", "winning", "lost", "losing", "loss",
    "settled", "cashed", "cash out", "cashout",
    "void", "push", "in progress", "live", "pending",
    "open bet", "graded", "resulted"
]

BET365_WORDS = ["bet365", "bet 365"]

SLIP_WORDS = [
    "parlay", "betslip", "bet slip", "odds", "stake",
    "to win", "wager", "risk", "draftkings", "fanduel",
    "betmgm", "caesars", "fanatics", "espn bet", "bet365", "bet 365"
]

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()

async def ocr_attachment(attachment: discord.Attachment) -> str:
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        return ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        response = requests.get(attachment.url, timeout=20)
        response.raise_for_status()
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        image = Image.open(tmp_path)
        text = pytesseract.image_to_string(image)
        return clean_text(text)
    except Exception as e:
        print(f"OCR failed: {e}")
        return ""

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    message_text = clean_text(message.content)

    image_texts = []
    for attachment in message.attachments:
        image_text = await ocr_attachment(attachment)
        if image_text:
            image_texts.append(image_text)

    combined_text = clean_text(message_text + " " + " ".join(image_texts))

    has_image = any(
        a.content_type and a.content_type.startswith("image/")
        for a in message.attachments
    )

    print("---- MESSAGE CHECK ----")
    print(combined_text[:500])

    # Ignore finished/live slips
    if any(word in combined_text for word in IGNORE_STATUS_WORDS):
        return

    looks_like_slip = has_image or any(word in combined_text for word in SLIP_WORDS)

    if not looks_like_slip:
        return

    # Bet365 → 📘
    if any(word in combined_text for word in BET365_WORDS):
        await message.add_reaction("📘")
        return

    # Everything else → 🔥
    await message.add_reaction("🔥")

client.run(DISCORD_TOKEN)
