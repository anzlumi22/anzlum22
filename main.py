import discord
from discord.ext import commands
from discord import app_commands
import os
import traceback

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("環境変数 TOKEN が設定されていません")


class MyBot(commands.Bot):
    async def setup_hook(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cogs_dir = os.path.join(base_dir, "Cogs")

        print(f"[INFO] Cogs dir: {cogs_dir}")

        if not os.path.exists(cogs_dir):
            print("[ERROR] Cogsフォルダが存在しません")
            return

        for file in os.listdir(cogs_dir):
            if file.endswith(".py") and not file.startswith("_"):
                ext = f"Cogs.{file[:-3]}"

                try:
                    await self.load_extension(ext)
                    print(f"[OK] Loaded Cog: {ext}")

                except Exception as e:
                    print(f"[NG] Failed Cog: {ext}")
                    print(e)
                    traceback.print_exc()

        try:
            synced = await self.tree.sync()
            print(f"[INFO] Slash commands synced: {len(synced)}")

        except Exception as e:
            print("[ERROR] Slash commands sync failed")
            print(e)
            traceback.print_exc()


intents = discord.Intents.all()

bot = MyBot(
    command_prefix="$",
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    print("===================================")
    print(f"Bot logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("===================================")


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    print("[ERROR] Slash command error:")
    print(error)
    traceback.print_exc()


if __name__ == "__main__":
    bot.run(TOKEN)
