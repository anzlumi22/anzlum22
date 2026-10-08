import discord
from discord import app_commands
import json
import os

VENDING_DATA_FILE = "vending_data.json"

def load_allowed_users():
    if os.path.exists(VENDING_DATA_FILE):
        with open(VENDING_DATA_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data.get("allowed_user_ids", [])
            except json.JSONDecodeError:
                return []
    return []

def is_allowed():
    async def predicate(interaction: discord.Interaction) -> bool:
        if await interaction.client.is_owner(interaction.user):
            return True
        
        allowed_ids = load_allowed_users()
        if interaction.user.id not in allowed_ids:
            await interaction.response.send_message("🚫 あなたはこのBotの機能を利用する権限がありません。", ephemeral=True)
            return False
        
        return True
    return app_commands.check(predicate)
