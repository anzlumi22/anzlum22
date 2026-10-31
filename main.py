import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import traceback
from flask import Flask
from threading import Thread

from utils import is_authorized


# =========================
# Discord Bot
# =========================

# 環境変数 "TOKEN" を読み込んで変数に代入する
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("環境変数 TOKEN が設定されていません")

intents = discord.Intents.all()


class MyBot(commands.Bot):

    async def setup_hook(self):
        # ===== グローバルチェックを登録 =====
        self.tree.interaction_check = is_authorized

        base_dir = os.path.dirname(os.path.abspath(__file__))
        cogs_dir = os.path.join(base_dir, "Cogs")

        if os.path.exists(cogs_dir):
            for filename in os.listdir(cogs_dir):
                if filename.endswith(".py") and not filename.startswith("_"):
                    extension = f"Cogs.{filename[:-3]}"

                    try:
                        await self.load_extension(extension)
                        print(f"Loaded: {extension}")
                    except Exception:
                        print(f"Failed to load: {extension}")
                        traceback.print_exc()

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands")
        except Exception:
            traceback.print_exc()


bot = MyBot(
    command_prefix="$",
    intents=intents,
    help_command=None
)


# =========================
# Webサーバー（RenderやBotkeepのヘルスチェック用）
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)


# =========================
# ステータス更新（視聴中）
# =========================

@tasks.loop(minutes=5)
async def update_status():
    guild_count = len(bot.guilds)
    member_count = sum(guild.member_count for guild in bot.guilds)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{guild_count}台の自販機 | {member_count}members"
        )
    )


# =========================
# イベント
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")

    if not update_status.is_running():
        update_status.start()


# =========================
# 起動
# =========================

if __name__ == "__main__":
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()

    bot.run(TOKEN)
