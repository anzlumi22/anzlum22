import discord
from discord.ext import commands
from discord import app_commands
import os
import time

from Cogs.vending import VENDING_DATA_FILE, load_json, save_json
from utils import (
    load_license_entries,
    save_license_entries,
    find_entry,
    format_expires,
    set_entry,
    remove_entry,
    extend_entry,
    make_permanent,
    WEEK_SECONDS,
    MONTH_SECONDS,
)


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
    async def set_log_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        # グローバルチェックで守られているのでここでは何もしなくてOK
        config = load_json(VENDING_DATA_FILE)
        config["log_channel_id"] = channel.id
        save_json(VENDING_DATA_FILE, config)

        await interaction.response.send_message(
            f"✅ ログチャンネルを {channel.mention} に設定しました。",
            ephemeral=True
        )

    # ==============================
    # 利用権限管理（Botオーナー限定）
    # ==============================
    @app_commands.command(
        name="利用権限管理",
        description="利用権限の一覧・付与・剥奪・延長・永久化を行います"
    )
    @app_commands.describe(
        operation="実行する操作",
        user_id="対象ユーザーのID（一覧以外では必須）",
        guild_id="対象サーバーID（任意・未入力なら全サーバー）"
    )
    @app_commands.choices(operation=[
        app_commands.Choice(name="一覧", value="list"),
        app_commands.Choice(name="剥奪", value="revoke"),
        app_commands.Choice(name="永久付与", value="grant_perm"),
        app_commands.Choice(name="1週間付与", value="grant_1w"),
        app_commands.Choice(name="1ヶ月付与", value="grant_1m"),
        app_commands.Choice(name="1週間延長", value="extend_1w"),
        app_commands.Choice(name="2週間延長", value="extend_2w"),
        app_commands.Choice(name="1ヶ月延長", value="extend_1m"),
        app_commands.Choice(name="永久に変更", value="make_perm"),
    ])
    async def license_manage(
        self,
        interaction: discord.Interaction,
        operation: app_commands.Choice[str],
        user_id: str = None,
        guild_id: str = None
    ):
        # グローバルチェックでBotオーナー限定は保証済み
        try:
            op = operation.value

            # ---------- 一覧 ----------
            if op == "list":
                entries = load_license_entries()
                if not entries:
                    embed = discord.Embed(
                        title="利用権限一覧",
                        description="利用権限を持つユーザーはいません。",
                        color=discord.Color.orange()
                    )
                    embed.set_footer(text="Developer @anzy1m")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                embed = discord.Embed(
                    title="利用権限一覧",
                    color=discord.Color.blurple(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text="Developer @anzy1m")

                for e in entries[:25]:
                    gid_text = "全サーバー" if e["guild_id"] is None else str(e["guild_id"])
                    expires_text = format_expires(e["expires_at"])
                    embed.add_field(
                        name=f"<@{e['user_id']}> (`{e['user_id']}`)",
                        value=(
                            f"```権限時間: {expires_text}\n"
                            f"サーバーID: {gid_text}```"
                        ),
                        inline=False
                    )

                if len(entries) > 25:
                    embed.set_footer(text="最初の25件のみ表示しています。 / Developer @anzy1m")

                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # ---------- 一覧以外は user_id 必須 ----------
            if user_id is None:
                await interaction.response.send_message(
                    "❌ ユーザーIDを指定してください。",
                    ephemeral=True
                )
                return

            try:
                target_user_id = int(user_id.strip())
            except ValueError:
                await interaction.response.send_message(
                    "❌ ユーザーIDは数字で指定してください。",
                    ephemeral=True
                )
                return

            # ---------- サーバーID（任意） ----------
            target_guild_id = None
            if guild_id is not None and guild_id.strip() != "":
                try:
                    target_guild_id = int(guild_id.strip())
                except ValueError:
                    await interaction.response.send_message(
                        "❌ サーバーIDは数字で指定してください。",
                        ephemeral=True
                    )
                    return

            entries = load_license_entries()
            now = int(time.time())

            # ---------- 剥奪 ----------
            if op == "revoke":
                if target_guild_id is None:
                    before = len(entries)
                    entries[:] = [e for e in entries if e["user_id"] != target_user_id]
                    removed = before - len(entries)
                    save_license_entries(entries)
                    await interaction.response.send_message(
                        f"✅ <@{target_user_id}> の利用権限を全サーバーから剥奪しました。（{removed}件）",
                        ephemeral=True
                    )
                else:
                    ok = remove_entry(entries, target_user_id, target_guild_id)
                    save_license_entries(entries)
                    if ok:
                        await interaction.response.send_message(
                            f"✅ <@{target_user_id}> の利用権限をサーバー `{target_guild_id}` から剥奪しました。",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            f"ℹ️ <@{target_user_id}> はサーバー `{target_guild_id}` の利用権限を持っていません。",
                            ephemeral=True
                        )
                return

            # ---------- 付与系 ----------
            if op == "grant_perm":
                expires_at = None
            elif op == "grant_1w":
                expires_at = now + WEEK_SECONDS
            elif op == "grant_1m":
                expires_at = now + MONTH_SECONDS
            else:
                expires_at = None

            if op in ("grant_perm", "grant_1w", "grant_1m"):
                if target_guild_id is None:
                    set_entry(entries, target_user_id, None, expires_at)
                    save_license_entries(entries)
                    await interaction.response.send_message(
                        f"✅ <@{target_user_id}> に全サーバーの利用権限を付与しました。\n"
                        f"権限時間: `{format_expires(expires_at)}`",
                        ephemeral=True
                    )
                else:
                    set_entry(entries, target_user_id, target_guild_id, expires_at)
                    save_license_entries(entries)
                    await interaction.response.send_message(
                        f"✅ <@{target_user_id}> にサーバー `{target_guild_id}` の利用権限を付与しました。\n"
                        f"権限時間: `{format_expires(expires_at)}`",
                        ephemeral=True
                    )
                return

            # ---------- 延長系 ----------
            if op in ("extend_1w", "extend_2w", "extend_1m"):
                if op == "extend_1w":
                    seconds = WEEK_SECONDS
                elif op == "extend_2w":
                    seconds = 2 * WEEK_SECONDS
                else:
                    seconds = MONTH_SECONDS

                if target_guild_id is None:
                    targets = [e for e in entries if e["user_id"] == target_user_id]
                    if not targets:
                        await interaction.response.send_message(
                            f"ℹ️ <@{target_user_id}> は利用権限を持っていません。",
                            ephemeral=True
                        )
                        return
                    for e in targets:
                        if e["expires_at"] is not None:
                            e["expires_at"] += seconds
                    save_license_entries(entries)
                    await interaction.response.send_message(
                        f"✅ <@{target_user_id}> の全サーバー利用権限を延長しました。\n"
                        f"延長時間: `+{seconds // 86400}日`",
                        ephemeral=True
                    )
                else:
                    ok = extend_entry(entries, target_user_id, target_guild_id, seconds)
                    save_license_entries(entries)
                    if ok:
                        await interaction.response.send_message(
                            f"✅ <@{target_user_id}> のサーバー `{target_guild_id}` の利用権限を延長しました。\n"
                            f"延長時間: `+{seconds // 86400}日`",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            f"ℹ️ <@{target_user_id}> はサーバー `{target_guild_id}` の利用権限を持っていません。",
                            ephemeral=True
                        )
                return

            # ---------- 永久に変更 ----------
            if op == "make_perm":
                if target_guild_id is None:
                    targets = [e for e in entries if e["user_id"] == target_user_id]
                    if not targets:
                        await interaction.response.send_message(
                            f"ℹ️ <@{target_user_id}> は利用権限を持っていません。",
                            ephemeral=True
                        )
                        return
                    for e in targets:
                        e["expires_at"] = None
                    save_license_entries(entries)
                    await interaction.response.send_message(
                        f"✅ <@{target_user_id}> の全サーバー利用権限を永久に変更しました。",
                        ephemeral=True
                    )
                else:
                    ok = make_permanent(entries, target_user_id, target_guild_id)
                    save_license_entries(entries)
                    if ok:
                        await interaction.response.send_message(
                            f"✅ <@{target_user_id}> のサーバー `{target_guild_id}` の利用権限を永久に変更しました。",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            f"ℹ️ <@{target_user_id}> はサーバー `{target_guild_id}` の利用権限を持っていません。",
                            ephemeral=True
                        )
                return

        except Exception as e:
            try:
                embed = discord.Embed(
                    title="エラーが発生しました",
                    description=f"```{str(e)}```",
                    color=discord.Color.red()
                )
                embed.set_footer(text="Developer @anzy1m")
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(SettingCog(bot))
