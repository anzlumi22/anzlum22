import discord 
from discord.ext import commands 
from discord import app_commands 
import os 
import traceback 
from flask import Flask 
from threading import Thread 
 
# ========================= 
# Render用Webサーバー 
# ========================= 
 
app = Flask(__name__) 
 
@app.route("/") 
def home(): 
    return "Bot is online!" 
 
def run_web(): 
    port = int(os.environ.get("PORT", 10000)) 
    app.run(host="0.0.0.0", port=port) 
 
# ========================= 
# Discord Bot 
# ========================= 
 
TOKEN = os.getenv("TOKEN") 
 
if not TOKEN: 
    raise RuntimeError("環境変数 TOKEN が設定されていません") 
 
intents = discord.Intents.all() 
 
bot = commands.Bot( 
    command_prefix="$", 
    intents=intents, 
    help_command=None 
) 
 
 
class MyBot(commands.Bot): 
 
    async def setup_hook(self): 
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
 
 
@bot.event 
async def on_ready(): 
    print(f"Logged in as {bot.user}") 
    print(f"Bot ID: {bot.user.id}") 
    print(f"Servers: {len(bot.guilds)}") 
 
 
# ========================= 
# 起動 
# ========================= 
 
if __name__ == "__main__": 
    web_thread = Thread(target=run_web, daemon=True) 
    web_thread.start() 
 
    bot.run(TOKEN) 
