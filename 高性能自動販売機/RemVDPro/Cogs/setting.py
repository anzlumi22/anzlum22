```python
import discord
from discord.ext import commands
from discord import app_commands
import os

from Cogs.vending import VENDING_DATA_FILE, load_json, save_json
from utils import is_allowed


class SettingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==============================
    # ログチャンネル設定
    # ==============================
    @app_commands.command(
        name="ログチャンネル設定",
        description="購入ログを送信するチャンネルを設定します"
    )
    @app_commands.describe(channel="ログチャンネル")
    @is_allowed()
    async def set_log_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        config = load_json(VENDING_DATA_FILE)

        config["log_channel_id"] = channel.id

        save_json(VENDING_DATA_FILE, config)

        await interaction.response.send_message(
            f"✅ ログチャンネルを {channel.mention} に設定しました。",
            ephemeral=True
        )

    # ==============================
    # 許可ユーザー追加
    # ==============================
    @app_commands.command(
        name="許可ユーザー追加",
        description="管理コマンドを使えるユーザーを追加します"
    )
    @app_commands.describe(user="追加するユーザー")
    @is_allowed()
    async def add_allowed_user(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        # このDiscord IDの人だけ許可ユーザーを追加可能
        if interaction.user.id != 1522560755856183298:
            await interaction.response.send_message(
                "🚫 このコマンドを使用する権限がありません。",
                ephemeral=True
            )
            return

        config = load_json(VENDING_DATA_FILE)

        allowed_user_ids = config.get("allowed_user_ids", [])

        if user.id not in allowed_user_ids:
            allowed_user_ids.append(user.id)

            config["allowed_user_ids"] = allowed_user_ids

            save_json(VENDING_DATA_FILE, config)

            await interaction.response.send_message(
                f"✅ {user.mention} を許可ユーザーリストに追加しました。\n"
                f"これですべての管理コマンドが使用可能です。",
                ephemeral=True
            )

        else:
            await interaction.response.send_message(
                f"🚫 {user.mention} は既に許可ユーザーリストに含まれています。",
                ephemeral=True
            )

    # ==============================
    # 許可ユーザー削除
    # ==============================
    @app_commands.command(
        name="許可ユーザー削除",
        description="許可ユーザーリストからユーザーを削除します"
    )
    @app_commands.describe(user="削除するユーザー")
    @is_allowed()
    async def remove_allowed_user(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        config = load_json(VENDING_DATA_FILE)

        allowed_user_ids = config.get("allowed_user_ids", [])

        if user.id in allowed_user_ids:
            allowed_user_ids.remove(user.id)

            config["allowed_user_ids"] = allowed_user_ids

            save_json(VENDING_DATA_FILE, config)

            await interaction.response.send_message(
                f"✅ {user.mention} を許可ユーザーリストから削除しました。",
                ephemeral=True
            )

        else:
            await interaction.response.send_message(
                f"🚫 {user.mention} は許可ユーザーリストに含まれていません。",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(SettingCog(bot))
