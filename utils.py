import os
import json
import time

import discord
from discord import app_commands


# =========================================================
# 利用権限データ操作
# =========================================================

VENDING_DATA_FILE = "vending_data.json"

WEEK_SECONDS = 7 * 24 * 60 * 60
MONTH_SECONDS = 30 * 24 * 60 * 60


def _load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def _save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_license_entries():
    config = _load_json(VENDING_DATA_FILE)
    entries = config.get("license_entries", [])
    if not isinstance(entries, list):
        return []
    normalized = []
    for e in entries:
        try:
            normalized.append({
                "user_id": int(e["user_id"]),
                "guild_id": int(e["guild_id"]) if e.get("guild_id") is not None else None,
                "expires_at": int(e["expires_at"]) if e.get("expires_at") is not None else None,
            })
        except (KeyError, TypeError, ValueError):
            continue
    return normalized


def save_license_entries(entries):
    config = _load_json(VENDING_DATA_FILE)
    config["license_entries"] = entries
    _save_json(VENDING_DATA_FILE, config)


def find_entry(entries, user_id, guild_id):
    for e in entries:
        if e["user_id"] == user_id and e["guild_id"] == guild_id:
            return e
    return None


def format_expires(expires_at):
    if expires_at is None:
        return "永久"
    remaining = expires_at - int(time.time())
    if remaining <= 0:
        return "期限切れ"
    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    minutes = (remaining % 3600) // 60
    if days > 0:
        return f"{days}日 {hours}時間後"
    if hours > 0:
        return f"{hours}時間 {minutes}分後"
    return f"{minutes}分後"


def set_entry(entries, user_id, guild_id, expires_at):
    e = find_entry(entries, user_id, guild_id)
    if e:
        e["expires_at"] = expires_at
    else:
        entries.append({
            "user_id": user_id,
            "guild_id": guild_id,
            "expires_at": expires_at,
        })


def remove_entry(entries, user_id, guild_id):
    before = len(entries)
    entries[:] = [
        e for e in entries
        if not (e["user_id"] == user_id and e["guild_id"] == guild_id)
    ]
    return len(entries) != before


def extend_entry(entries, user_id, guild_id, seconds):
    e = find_entry(entries, user_id, guild_id)
    if not e:
        return False
    if e["expires_at"] is None:
        return True
    e["expires_at"] += seconds
    return True


def make_permanent(entries, user_id, guild_id):
    e = find_entry(entries, user_id, guild_id)
    if not e:
        return False
    e["expires_at"] = None
    return True


# =========================================================
# 利用権限チェック
# =========================================================

async def check_license(interaction: discord.Interaction) -> bool:
    """利用権限チェック（Botオーナー or license_entries に登録済み）"""
    try:
        if await interaction.client.is_owner(interaction.user):
            return True
    except Exception:
        pass

    user_id = interaction.user.id
    guild_id = interaction.guild_id
    now = int(time.time())

    entries = load_license_entries()

    for e in entries:
        if e["user_id"] != user_id:
            continue
        if e["guild_id"] is not None and e["guild_id"] != guild_id:
            continue
        if e["expires_at"] is None:
            return True
        if e["expires_at"] > now:
            return True

    try:
        embed = discord.Embed(
            title="🚫 利用権限がありません",
            description=(
                "このコマンドを実行するには利用権限が必要です。\n"
                "管理者に `/利用権限管理` での付与を依頼してください。"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="Developer @anzy1m")

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass

    return False


async def check_owner(interaction: discord.Interaction) -> bool:
    """Botオーナー限定チェック"""
    try:
        if await interaction.client.is_owner(interaction.user):
            return True
    except Exception:
        pass

    try:
        embed = discord.Embed(
            title="🚫 権限がありません",
            description="このコマンドはBotオーナーのみ使用できます。",
            color=discord.Color.red()
        )
        embed.set_footer(text="Developer @anzy1m")

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass

    return False


# =========================================================
# 後方互換（既存コードが is_allowed を呼んでいる場合）
# =========================================================

def is_allowed():
    async def predicate(interaction: discord.Interaction) -> bool:
        return True
    return app_commands.check(predicate)
