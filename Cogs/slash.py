import asyncio
import json
import os
import random
import re
import time
import uuid
import datetime

import pytz

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# 権限チェック（ダミー）
# =========================================================

def is_allowed():
    async def predicate(interaction: discord.Interaction) -> bool:
        return True
    return app_commands.check(predicate)


# =========================================================
# 定数
# =========================================================

MEMBER_LOG_DATA_FILE = "member_log_data.json"
ROLE_PANEL_DATA_FILE = "role_panel_data.json"
ANTIRAID_DATA_FILE = "antiraid_data.json"
FIXED_MESSAGE_DATA_FILE = "fixed_message_data.json"
AUTO_REACTION_DATA_FILE = "auto_reaction_data.json"
TICKET_PANEL_DATA_FILE = "ticket_panel_data.json"
STATUS_STAFF_DATA_FILE = "status_staff_data.json"
STATUS_PANEL_DATA_FILE = "status_panel_data.json"
INVITE_CAMPAIGN_DATA_FILE = "invite_campaign_data.json"
PERIODIC_MESSAGE_DATA_FILE = "periodic_message_data.json"
MEDIATION_DATA_FILE = "mediation_data.json"
TICKET_SETTINGS_DRAFT_FILE = "ticket_settings_draft.json"


# =========================================================
# 共通
# =========================================================

def parse_duration(value: str) -> int:
    match = re.fullmatch(
        r"\s*(\d+)\s*(m|h|d|w|minute|minutes|hour|hours|day|days|week|weeks)\s*",
        value.lower()
    )
    if not match:
        raise ValueError("例: 30m、2h、1d、1week")
    amount = int(match.group(1))
    unit = match.group(2)
    multipliers = {
        "m": 60, "minute": 60, "minutes": 60,
        "h": 3600, "hour": 3600, "hours": 3600,
        "d": 86400, "day": 86400, "days": 86400,
        "w": 604800, "week": 604800, "weeks": 604800
    }
    seconds = amount * multipliers[unit]
    if amount < 1 or seconds > 365 * 86400:
        raise ValueError("時間は1以上、1年以内にしてください。")
    return seconds


def parse_color(value: str):
    if not value:
        return None
    value = value.strip().lstrip("#")
    try:
        return discord.Color(int(value, 16))
    except ValueError:
        return None


async def respond_error(interaction, message):
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_member_log_data(): return load_json(MEMBER_LOG_DATA_FILE)
def save_member_log_data(data): save_json(MEMBER_LOG_DATA_FILE, data)
def load_role_panel_data(): return load_json(ROLE_PANEL_DATA_FILE)
def save_role_panel_data(data): save_json(ROLE_PANEL_DATA_FILE, data)
def load_antiraid_data(): return load_json(ANTIRAID_DATA_FILE)
def save_antiraid_data(data): save_json(ANTIRAID_DATA_FILE, data)
def load_fixed_message_data(): return load_json(FIXED_MESSAGE_DATA_FILE)
def save_fixed_message_data(data): save_json(FIXED_MESSAGE_DATA_FILE, data)
def load_auto_reaction_data(): return load_json(AUTO_REACTION_DATA_FILE)
def save_auto_reaction_data(data): save_json(AUTO_REACTION_DATA_FILE, data)
def load_ticket_panel_data(): return load_json(TICKET_PANEL_DATA_FILE)
def save_ticket_panel_data(data): save_json(TICKET_PANEL_DATA_FILE, data)
def load_status_staff_data(): return load_json(STATUS_STAFF_DATA_FILE)
def save_status_staff_data(data): save_json(STATUS_STAFF_DATA_FILE, data)
def load_status_panel_data(): return load_json(STATUS_PANEL_DATA_FILE)
def save_status_panel_data(data): save_json(STATUS_PANEL_DATA_FILE, data)
def load_invite_campaign_data(): return load_json(INVITE_CAMPAIGN_DATA_FILE)
def save_invite_campaign_data(data): save_json(INVITE_CAMPAIGN_DATA_FILE, data)
def load_periodic_message_data(): return load_json(PERIODIC_MESSAGE_DATA_FILE)
def save_periodic_message_data(data): save_json(PERIODIC_MESSAGE_DATA_FILE, data)
def load_mediation_data(): return load_json(MEDIATION_DATA_FILE)
def save_mediation_data(data): save_json(MEDIATION_DATA_FILE, data)
def load_ticket_settings_draft(): return load_json(TICKET_SETTINGS_DRAFT_FILE)
def save_ticket_settings_draft(data): save_json(TICKET_SETTINGS_DRAFT_FILE, data)


def default_ticket_settings():
    return {
        "panel_title": "購入・お問い合わせ",
        "panel_description": "チケットを開きましたらスタッフが対応するまでお待ちください。",
        "mention_role_id": None,
        "embed_title": None,
        "embed_description": None,
        "category_id": None,
        "archive_channel_id": None,
        "requirements": [],
        "max_tickets": 1,
        "delete_permission": "admin",
        "welcome_message": None,
        "mode": "multi",
        "button_label": "🎫 チケットを作成",
    }


def get_guild_draft(guild_id: int) -> dict:
    """ギルドごとの設定下書きを取得（なければデフォルト）"""
    data = load_ticket_settings_draft()
    gid = str(guild_id)
    if gid not in data:
        data[gid] = default_ticket_settings()
        save_ticket_settings_draft(data)
    # 欠損キーを補完
    merged = default_ticket_settings()
    merged.update(data[gid])
    return merged


def update_guild_draft(guild_id: int, settings: dict):
    """ギルドごとの設定下書きを保存"""
    data = load_ticket_settings_draft()
    data[str(guild_id)] = settings
    save_ticket_settings_draft(data)


def format_account_age(created_at: datetime.datetime):
    jst = pytz.timezone("Asia/Tokyo")
    created_jst = created_at.astimezone(jst)
    now = datetime.datetime.now(jst)
    delta = now - created_jst
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    created_str = created_jst.strftime("%Y-%m-%d %H:%M:%S JST")
    elapsed_str = f"{days}日 {hours:02d}時間 {minutes:02d}分"
    return created_str, elapsed_str


# =========================================================
# チケット設定 表示ヘルパー
# =========================================================

def build_ticket_settings_embed(panel: dict) -> discord.Embed:
    reqs = panel.get("requirements") or []

    if reqs:
        req_lines = []
        for i, r in enumerate(reqs, start=1):
            name = r.get("name", "無題")
            emoji = r.get("emoji", "📝")
            desc = r.get("description", "") or "説明なし"
            req_lines.append(f"{i}.{name}\n　{emoji}\n　{desc}")
        req_value = "\n".join(req_lines)
    else:
        req_value = "なし"

    if len(req_value) > 1024:
        req_value = req_value[:1021] + "..."

    title = panel.get("panel_title") or "未設定"
    desc = panel.get("panel_description") or "未設定"
    mention_role_id = panel.get("mention_role_id")
    role_text = f"<@&{mention_role_id}>" if mention_role_id else "未設定"
    embed_title = panel.get("embed_title") or "未設定"
    embed_desc = panel.get("embed_description") or "未設定"

    embed = discord.Embed(
        title="チケット設定",
        description=(
            f"**タイトル**\n{title}\n\n"
            f"**説明**\n{desc}\n\n"
            f"**スタッフロール**\n{role_text}\n\n"
            f"**チケット作成後の埋め込みメッセージタイトル**\n{embed_title}\n\n"
            f"**埋め込み説明**\n{embed_desc}\n\n"
            f"**要件一覧**\n{req_value}\n\n"
            f"下のドロップダウン（検索可）からチケット作成するカテゴリーを設定できます。\n"
            f"下のドロップダウン（検索可）からチケットを削除したときのスクリプトなどを送信されるチャンネルを設定できます。"
        ),
        color=discord.Color.blurple()
    )

    category_id = panel.get("category_id")
    embed.add_field(
        name="チケット作成するカテゴリー",
        value=f"<#{category_id}>" if category_id else "設定なし",
        inline=False
    )
    archive_id = panel.get("archive_channel_id")
    embed.add_field(
        name="チケットを削除したときのスクリプトなどを送信されるチャンネル",
        value=f"<#{archive_id}>" if archive_id else "設定なし",
        inline=False
    )
    panel_message_id = panel.get("panel_message_id")
    panel_channel_id = panel.get("panel_channel_id")
    if panel_message_id and panel_channel_id:
        embed.add_field(
            name="作成済みパネル",
            value=f"<#{panel_channel_id}> (message: {panel_message_id})",
            inline=False
        )
    return embed


# =========================================================
# NUKE
# =========================================================

class ConfirmNukeView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="チャンネルを再作成", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("チャンネル管理権限が必要です。", ephemeral=True)
            return
        if interaction.channel_id != self.channel.id:
            await interaction.response.send_message("実行対象のチャンネルが異なります。", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        old_channel = self.channel
        try:
            new_channel = await old_channel.clone(reason=f"Nuke requested by {interaction.user}")
            await new_channel.edit(category=old_channel.category, position=old_channel.position)
            await old_channel.delete(reason=f"Nuke requested by {interaction.user}")
            await new_channel.send("**nukeが完了しました。**")
        except discord.Forbidden:
            await interaction.followup.send("Botにチャンネル管理権限がありません。", ephemeral=True)
        except discord.HTTPException as error:
            await interaction.followup.send(f"再作成に失敗しました: {error}", ephemeral=True)
        self.stop()

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content="キャンセルしました。", view=None)
        self.stop()


# =========================================================
# GIVEAWAY
# =========================================================

class GiveawayView(discord.ui.View):
    def __init__(self, cog, giveaway_id, prize, winner_count, end_time):
        super().__init__(timeout=None)
        self.cog = cog
        self.giveaway_id = giveaway_id
        self.prize = prize
        self.winner_count = winner_count
        self.end_time = end_time
        self.participants = set()
        self.started = True
        self.ended = False
        self.cancelled = False
        self.message = None
        self.winners = []
        self.join_button.custom_id = f"gw_join_{giveaway_id}"
        self.list_button.custom_id = f"gw_list_{giveaway_id}"

    def make_embed(self):
        if self.cancelled:
            color = discord.Color.red(); state = "中止"
        elif self.ended:
            color = discord.Color.dark_grey(); state = "終了"
        else:
            color = discord.Color.gold(); state = "開催中"
        end_text = f"<t:{self.end_time}:R>" if self.end_time else "未設定"
        return discord.Embed(
            title="🎉 Giveaway",
            description=(
                f"**景品:** {self.prize}\n"
                f"**当選人数:** {self.winner_count}人\n"
                f"**参加人数:** {len(self.participants)}人\n"
                f"**終了:** {end_text}\n"
                f"**状態:** {state}\n\n"
                "参加するには下のボタンを押してください！"
            ),
            color=color
        )

    async def refresh(self):
        if self.message:
            try:
                await self.message.edit(embed=self.make_embed(), view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="🎉 参加する", style=discord.ButtonStyle.success, custom_id="gw_join_default")
    async def join_button(self, interaction, button):
        if self.ended or self.cancelled:
            await interaction.response.send_message("この抽選は終了しています。", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            self.participants.remove(interaction.user.id)
            text = "抽選への参加を取り消しました。"
        else:
            self.participants.add(interaction.user.id)
            text = "抽選に参加しました！"
        await interaction.response.send_message(text, ephemeral=True)
        await self.refresh()

    @discord.ui.button(label="👥 参加者リスト", style=discord.ButtonStyle.primary, custom_id="gw_list_default")
    async def list_button(self, interaction, button):
        ids = sorted(self.participants)
        embed = discord.Embed(
            title="👥 参加者リスト",
            description=("\n".join(f"• <@{uid}>" for uid in ids[:100]) if ids else "参加者はいません。"),
            color=discord.Color.blurple()
        )
        embed.add_field(name="参加人数", value=f"{len(ids)}人", inline=False)
        if len(ids) > 100:
            embed.set_footer(text="最初の100人のみ表示しています。")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class StopGiveawayView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=60)
        self.cog = cog
        self.select.options = options

    @discord.ui.select(placeholder="終了する配布を選択", custom_id="giveaway_stop_select")
    async def select(self, interaction, select):
        message_id = int(select.values[0])
        view = self.cog.active_giveaways.get(message_id)
        if not view:
            await interaction.response.edit_message(content="配布が見つかりません。既に終了している可能性があります。", view=None)
            return
        if interaction.guild_id != view.message.guild.id:
            await interaction.response.edit_message(content="このサーバーの配布ではありません。", view=None)
            return
        view.ended = True
        view.stop()
        await view.refresh()
        ids = list(view.participants)
        if ids:
            chosen = random.sample(ids, min(view.winner_count, len(ids)))
            view.winners = chosen
            result = f"🎉 **{view.prize}** の配布が終了しました！\n当選者: {' '.join(f'<@{uid}>' for uid in chosen)}"
        else:
            view.winners = []
            result = f"**{view.prize}** の配布が終了しました。参加者はいませんでした。"
        try:
            await view.message.channel.send(result)
        except discord.HTTPException:
            pass
        self.cog.active_giveaways.pop(message_id, None)
        self.cog.ended_giveaways[message_id] = view
        await interaction.response.edit_message(content=f"配布「{view.prize}」を終了しました。", view=None)


class RedrawGiveawayView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=60)
        self.cog = cog
        self.select.options = options

    @discord.ui.select(placeholder="再抽選する配布を選択", custom_id="giveaway_redraw_select")
    async def select(self, interaction, select):
        message_id = int(select.values[0])
        view = self.cog.ended_giveaways.get(message_id)
        if not view:
            await interaction.response.edit_message(content="配布が見つかりません。", view=None)
            return
        if interaction.guild_id != view.message.guild.id:
            await interaction.response.edit_message(content="このサーバーの配布ではありません。", view=None)
            return
        ids = list(view.participants)
        if not ids:
            await interaction.response.edit_message(content="参加者がいないため、再抽選できません。", view=None)
            return
        chosen = random.sample(ids, min(view.winner_count, len(ids)))
        view.winners = chosen
        result = f"🎉 **{view.prize}** の再抽選が行われました！\n当選者: {' '.join(f'<@{uid}>' for uid in chosen)}"
        try:
            await view.message.channel.send(result)
        except discord.HTTPException:
            pass
        await interaction.response.edit_message(content=f"配布「{view.prize}」の再抽選を実行しました。", view=None)


# =========================================================
# VERIFY
# =========================================================

def build_verify_embed(title: str, description: str, role: discord.Role, guild_id: int):
    return discord.Embed(
        title=title,
        description=(
            f"{description}\n\n"
            f"認証後 {role.mention} が付与されます\n"
            f"**{guild_id} | Dev.@anzy1m**"
        ),
        color=discord.Color.blurple()
    )


class VerifyMathModal(discord.ui.Modal):
    def __init__(self, cog, role, answer):
        super().__init__(title="計算認証")
        self.cog = cog
        self.role = role
        self.answer = answer
        self.answer_input = discord.ui.TextInput(label="答えを入力してください", placeholder="半角数字で入力", max_length=10, required=True)
        self.add_item(self.answer_input)

    async def on_submit(self, interaction):
        if self.answer_input.value.strip() != str(self.answer):
            await interaction.response.send_message("❌ 答えが違います。もう一度お試しください。", ephemeral=True)
            return
        try:
            await interaction.user.add_roles(self.role, reason="Verify (math)")
        except discord.Forbidden:
            await interaction.response.send_message("ロールを付与できません。Botの権限を確認してください。", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("ロールの付与に失敗しました。", ephemeral=True)
            return
        await interaction.response.send_message("✅ 認証が完了しました！", ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self, cog, role, verify_type):
        super().__init__(timeout=None)
        self.cog = cog
        self.role = role
        self.verify_type = verify_type
        self.verify_button.custom_id = f"verify_{role.id}_{verify_type}"
        self.verify_button.label = "認証 ✅"

    @discord.ui.button(label="認証 ✅", style=discord.ButtonStyle.success, custom_id="verify_default")
    async def verify_button(self, interaction, button):
        if self.verify_type == "button":
            try:
                await interaction.user.add_roles(self.role, reason="Verify (button)")
            except discord.Forbidden:
                await interaction.response.send_message("ロールを付与できません。Botの権限を確認してください。", ephemeral=True)
                return
            except discord.HTTPException:
                await interaction.response.send_message("ロールの付与に失敗しました。", ephemeral=True)
                return
            await interaction.response.send_message("✅ 認証が完了しました！", ephemeral=True)
        elif self.verify_type == "math":
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            answer = a + b
            modal = VerifyMathModal(self.cog, self.role, answer)
            modal.title = f"計算認証: {a} + {b} = ?"
            await interaction.response.send_modal(modal)


class VerifyRoleSelectView(discord.ui.View):
    def __init__(self, cog, verify_type, title, description):
        super().__init__(timeout=120)
        self.cog = cog
        self.verify_type = verify_type
        self.title = title
        self.description = description
        self.role_select.options = []

    @discord.ui.select(placeholder="認証後に付与するロールを選択", custom_id="verify_role_select")
    async def role_select(self, interaction, select):
        role = interaction.guild.get_role(int(select.values[0]))
        if not role:
            await interaction.response.edit_message(content="ロールが見つかりません。", view=None)
            return
        view = VerifyView(self.cog, role, self.verify_type)
        embed = build_verify_embed(self.title, self.description, role, interaction.guild_id)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.edit_message(content=f"✅ 認証パネルを作成しました（ロール: {role.mention}）", view=None)


# =========================================================
# TICKET (旧・対話式セットアップ / 互換維持)
# =========================================================

class TicketSetupModeView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このセットアップは実行者本人のみ操作できます。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="1ボタン式（シンプル）", style=discord.ButtonStyle.primary, emoji="🎫")
    async def simple_mode(self, interaction, button):
        view = TicketSetupSimpleView(self.cog, self.user_id)
        await interaction.response.edit_message(
            content=(
                "**1ボタン式**を選択しました。\n"
                "以下の項目を設定してください。\n"
                "（ボタン名・カテゴリー・メンションロールは必須です）"
            ),
            view=view
        )

    @discord.ui.button(label="複数項目から選ぶ式", style=discord.ButtonStyle.success, emoji="📋")
    async def multi_mode(self, interaction, button):
        view = TicketSetupMultiView(self.cog, self.user_id)
        await interaction.response.edit_message(
            content=(
                "**複数項目から選ぶ式**を選択しました。\n"
                "チケットパネルの下に要件を表示し、ユーザーが選択できるようにします。\n"
                "まずは基本設定を行います。"
            ),
            view=view
        )


class TicketSetupSimpleView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.settings = {
            "mode": "simple",
            "button_label": "🎫 チケットを作成",
            "max_tickets": 1,
            "mention_role_id": None,
            "category_id": None,
            "delete_permission": "admin",
            "panel_title": "購入・お問い合わせ",
            "panel_description": "チケットを開きましたらスタッフが対応するまでお待ちください。",
            "embed_title": None,
            "embed_description": None,
            "welcome_message": None,
            "archive_channel_id": None,
            "requirements": [{"name": "その他", "description": "", "emoji": "📝", "placeholder": "チケットの種類を選択してください"}],
        }

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このセットアップは実行者本人のみ操作できます。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="ボタン名を設定", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def set_button_label(self, interaction, button):
        await interaction.response.send_modal(TicketSetupTextModal(self, "button_label", "ボタン名", "チケット作成ボタンの名前"))

    @discord.ui.button(label="カテゴリーを設定", style=discord.ButtonStyle.secondary, emoji="📁")
    async def set_category(self, interaction, button):
        categories = interaction.guild.categories[:25]
        if not categories:
            await interaction.response.send_message("カテゴリーがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in categories]
        await interaction.response.edit_message(content="チケットを作成するカテゴリーを選択してください。", view=TicketSetupObjectSelectView(self, "category_id", options))

    @discord.ui.button(label="メンションロールを設定", style=discord.ButtonStyle.secondary, emoji="🔔")
    async def set_mention_role(self, interaction, button):
        roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed][:25]
        if not roles:
            await interaction.response.send_message("ロールがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        await interaction.response.edit_message(content="チケット作成時にメンションするロールを選択してください。", view=TicketSetupObjectSelectView(self, "mention_role_id", options))

    @discord.ui.button(label="最大チケット数を設定", style=discord.ButtonStyle.secondary, emoji="🔢")
    async def set_max_tickets(self, interaction, button):
        await interaction.response.send_modal(TicketSetupTextModal(self, "max_tickets", "最大チケット数", "1〜10の数字"))

    @discord.ui.button(label="削除権限を設定", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def set_delete_permission(self, interaction, button):
        options = [discord.SelectOption(label="管理者のみ", value="admin"), discord.SelectOption(label="全員", value="everyone")]
        await interaction.response.edit_message(content="チケット削除権限を選択してください。", view=TicketSetupObjectSelectView(self, "delete_permission", options))

    @discord.ui.button(label="パネルタイトル/説明を設定", style=discord.ButtonStyle.secondary, emoji="📝")
    async def set_panel_text(self, interaction, button):
        await interaction.response.send_modal(TicketSetupPanelTextModal(self))

    @discord.ui.button(label="埋め込み設定", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def set_embed(self, interaction, button):
        await interaction.response.send_modal(TicketSetupEmbedModal(self))

    @discord.ui.button(label="ウェルカムメッセージ", style=discord.ButtonStyle.secondary, emoji="👋")
    async def set_welcome(self, interaction, button):
        await interaction.response.send_modal(TicketSetupTextModal(self, "welcome_message", "ウェルカムメッセージ", "チケット作成後のメッセージ"))

    @discord.ui.button(label="アーカイブチャンネル", style=discord.ButtonStyle.secondary, emoji="📦")
    async def set_archive(self, interaction, button):
        channels = interaction.guild.text_channels[:25]
        if not channels:
            await interaction.response.send_message("テキストチャンネルがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in channels]
        await interaction.response.edit_message(content="アーカイブ（削除ログ）チャンネルを選択してください。", view=TicketSetupObjectSelectView(self, "archive_channel_id", options))

    @discord.ui.button(label="✅ パネルを作成", style=discord.ButtonStyle.success, emoji="✅")
    async def create_panel(self, interaction, button):
        s = self.settings
        if not s["category_id"]:
            await interaction.response.send_message("カテゴリーを設定してください。", ephemeral=True)
            return
        if not s["mention_role_id"]:
            await interaction.response.send_message("メンションロールを設定してください。", ephemeral=True)
            return

        panel_id = uuid.uuid4().hex[:10]
        self.cog.ticket_panels[panel_id] = {
            "id": panel_id,
            "creator_id": interaction.user.id,
            "mode": "simple",
            "button_label": s["button_label"],
            "max_tickets": s["max_tickets"],
            "mention_role_id": s["mention_role_id"],
            "embed_title": s["embed_title"],
            "embed_description": s["embed_description"],
            "welcome_message": s["welcome_message"],
            "delete_permission": s["delete_permission"],
            "category_id": s["category_id"],
            "archive_channel_id": s["archive_channel_id"],
            "channel_id": interaction.channel.id,
            "message_id": None,
            "panel_title": s["panel_title"],
            "panel_description": s["panel_description"],
            "requirements": s["requirements"],
            "access_role_ids": [],
            "access_user_ids": [],
        }

        embed = discord.Embed(
            title=s["panel_title"] or "🎫 チケット",
            description=s["panel_description"] or "下のドロップダウンからチケットを作成できます。",
            color=discord.Color.blurple()
        )
        req_lines = []
        for i, r in enumerate(s["requirements"], start=1):
            name = r.get("name", "無題")
            emoji = r.get("emoji", "📝")
            desc = r.get("description", "") or "説明なし"
            req_lines.append(f"{i}.{name}\n　{emoji}\n　{desc}")
        if req_lines:
            embed.add_field(name="要件一覧", value="\n".join(req_lines)[:1024], inline=False)
        embed.set_footer(text=f"1人につき最大 {s['max_tickets']} 件まで")

        view = TicketPanelView(self.cog, panel_id)
        await interaction.response.send_message("チケットパネルを作成しました。", ephemeral=True)
        message = await interaction.channel.send(embed=embed, view=view)
        self.cog.ticket_panels[panel_id]["message_id"] = message.id

        data = load_ticket_panel_data()
        data[panel_id] = self.cog.ticket_panels[panel_id]
        save_ticket_panel_data(data)
        self.stop()


class TicketSetupMultiView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=900)
        self.cog = cog
        self.user_id = user_id
        self.settings = {
            "mode": "multi",
            "button_label": "🎫 チケットを作成",
            "max_tickets": 1,
            "mention_role_id": None,
            "category_id": None,
            "delete_permission": "admin",
            "panel_title": "購入・お問い合わせ",
            "panel_description": "チケットを開きましたらスタッフが対応するまでお待ちください。",
            "embed_title": None,
            "embed_description": None,
            "welcome_message": None,
            "archive_channel_id": None,
            "requirements": [],
        }

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このセットアップは実行者本人のみ操作できます。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="基本設定", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def basic_settings(self, interaction, button):
        await interaction.response.send_message("基本設定を行います。各項目を設定してください。", view=TicketSetupMultiBasicView(self), ephemeral=True)

    @discord.ui.button(label="要件を追加", style=discord.ButtonStyle.success, emoji="➕")
    async def add_requirement(self, interaction, button):
        if len(self.settings["requirements"]) >= 25:
            await interaction.response.send_message("要件は最大25個までです。", ephemeral=True)
            return
        await interaction.response.send_modal(TicketRequirementModal(self))

    @discord.ui.button(label="要件を確認", style=discord.ButtonStyle.secondary, emoji="📋")
    async def view_requirements(self, interaction, button):
        reqs = self.settings["requirements"]
        if not reqs:
            await interaction.response.send_message("要件がまだありません。", ephemeral=True)
            return
        lines = [f"{r.get('emoji', '📝')} **{r['name']}** - {r.get('description', '')}" for r in reqs]
        embed = discord.Embed(title="登録済みの要件", description="\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="要件を削除", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_requirement(self, interaction, button):
        reqs = self.settings["requirements"]
        if not reqs:
            await interaction.response.send_message("要件がまだありません。", ephemeral=True)
            return
        options = [
            discord.SelectOption(
                label=r["name"][:100],
                value=str(i),
                emoji=r.get("emoji", "📝")[:1] if r.get("emoji") else None
            )
            for i, r in enumerate(reqs[:25])
        ]
        await interaction.response.edit_message(content="削除する要件を選択してください。", view=TicketRequirementRemoveView(self, options))

    @discord.ui.button(label="✅ パネルを作成", style=discord.ButtonStyle.success, emoji="✅")
    async def create_panel(self, interaction, button):
        s = self.settings
        if not s["category_id"]:
            await interaction.response.send_message("カテゴリーを設定してください。", ephemeral=True)
            return
        if not s["mention_role_id"]:
            await interaction.response.send_message("メンションロールを設定してください。", ephemeral=True)
            return
        if not s["requirements"]:
            await interaction.response.send_message("要件を1つ以上追加してください。", ephemeral=True)
            return

        panel_id = uuid.uuid4().hex[:10]
        self.cog.ticket_panels[panel_id] = {
            "id": panel_id,
            "creator_id": interaction.user.id,
            "mode": "multi",
            "button_label": s["button_label"],
            "max_tickets": s["max_tickets"],
            "mention_role_id": s["mention_role_id"],
            "embed_title": s["embed_title"],
            "embed_description": s["embed_description"],
            "welcome_message": s["welcome_message"],
            "delete_permission": s["delete_permission"],
            "category_id": s["category_id"],
            "archive_channel_id": s["archive_channel_id"],
            "channel_id": interaction.channel.id,
            "message_id": None,
            "panel_title": s["panel_title"],
            "panel_description": s["panel_description"],
            "requirements": s["requirements"],
            "access_role_ids": [],
            "access_user_ids": [],
        }

        embed = discord.Embed(
            title=s["panel_title"] or "🎫 チケット",
            description=s["panel_description"] or "下のドロップダウンからチケットを作成できます。",
            color=discord.Color.blurple()
        )

        req_lines = []
        for i, r in enumerate(s["requirements"], start=1):
            name = r.get("name", "無題")
            emoji = r.get("emoji", "📝")
            desc = r.get("description", "") or "説明なし"
            req_lines.append(f"{i}.{name}\n　{emoji}\n　{desc}")
        if req_lines:
            embed.add_field(name="要件一覧", value="\n".join(req_lines)[:1024], inline=False)
        embed.set_footer(text=f"1人につき最大 {s['max_tickets']} 件まで")

        view = TicketPanelView(self.cog, panel_id)
        await interaction.response.send_message("チケットパネルを作成しました。", ephemeral=True)
        message = await interaction.channel.send(embed=embed, view=view)
        self.cog.ticket_panels[panel_id]["message_id"] = message.id

        data = load_ticket_panel_data()
        data[panel_id] = self.cog.ticket_panels[panel_id]
        save_ticket_panel_data(data)
        self.stop()


class TicketSetupMultiBasicView(discord.ui.View):
    def __init__(self, parent: TicketSetupMultiView):
        super().__init__(timeout=600)
        self.parent = parent

    async def interaction_check(self, interaction):
        if interaction.user.id != self.parent.user_id:
            await interaction.response.send_message("このセットアップは実行者本人のみ操作できます。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="ボタン名", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def set_button_label(self, interaction, button):
        await interaction.response.send_modal(TicketSetupTextModal(self.parent, "button_label", "ボタン名", "チケット作成ボタンの名前"))

    @discord.ui.button(label="カテゴリー", style=discord.ButtonStyle.secondary, emoji="📁")
    async def set_category(self, interaction, button):
        categories = interaction.guild.categories[:25]
        if not categories:
            await interaction.response.send_message("カテゴリーがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in categories]
        await interaction.response.edit_message(content="カテゴリーを選択してください。", view=TicketSetupObjectSelectView(self.parent, "category_id", options, back_view=self))

    @discord.ui.button(label="メンションロール", style=discord.ButtonStyle.secondary, emoji="🔔")
    async def set_mention_role(self, interaction, button):
        roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed][:25]
        if not roles:
            await interaction.response.send_message("ロールがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        await interaction.response.edit_message(content="メンションロールを選択してください。", view=TicketSetupObjectSelectView(self.parent, "mention_role_id", options, back_view=self))

    @discord.ui.button(label="最大チケット数", style=discord.ButtonStyle.secondary, emoji="🔢")
    async def set_max_tickets(self, interaction, button):
        await interaction.response.send_modal(TicketSetupTextModal(self.parent, "max_tickets", "最大チケット数", "1〜10の数字"))

    @discord.ui.button(label="削除権限", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def set_delete_permission(self, interaction, button):
        options = [discord.SelectOption(label="管理者のみ", value="admin"), discord.SelectOption(label="全員", value="everyone")]
        await interaction.response.edit_message(content="削除権限を選択してください。", view=TicketSetupObjectSelectView(self.parent, "delete_permission", options, back_view=self))

    @discord.ui.button(label="パネルタイトル/説明", style=discord.ButtonStyle.secondary, emoji="📝")
    async def set_panel_text(self, interaction, button):
        await interaction.response.send_modal(TicketSetupPanelTextModal(self.parent))

    @discord.ui.button(label="埋め込み設定", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def set_embed(self, interaction, button):
        await interaction.response.send_modal(TicketSetupEmbedModal(self.parent))

    @discord.ui.button(label="ウェルカムメッセージ", style=discord.ButtonStyle.secondary, emoji="👋")
    async def set_welcome(self, interaction, button):
        await interaction.response.send_modal(TicketSetupTextModal(self.parent, "welcome_message", "ウェルカムメッセージ", "チケット作成後のメッセージ"))

    @discord.ui.button(label="アーカイブチャンネル", style=discord.ButtonStyle.secondary, emoji="📦")
    async def set_archive(self, interaction, button):
        channels = interaction.guild.text_channels[:25]
        if not channels:
            await interaction.response.send_message("テキストチャンネルがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in channels]
        await interaction.response.edit_message(content="アーカイブチャンネルを選択してください。", view=TicketSetupObjectSelectView(self.parent, "archive_channel_id", options, back_view=self))

    @discord.ui.button(label="戻る", style=discord.ButtonStyle.primary, emoji="↩️")
    async def back(self, interaction, button):
        await interaction.response.edit_message(
            content=("**複数項目から選ぶ式**の設定画面です。\n「基本設定」で詳細を、「要件を追加」で項目を追加してください。"),
            view=self.parent
        )


class TicketSetupTextModal(discord.ui.Modal):
    def __init__(self, setup_view, field, label, placeholder):
        super().__init__(title=f"設定: {label}")
        self.setup_view = setup_view
        self.field = field
        self.input = discord.ui.TextInput(label=label, placeholder=placeholder, max_length=1000, required=False)
        self.add_item(self.input)

    async def on_submit(self, interaction):
        value = self.input.value.strip()
        if self.field == "max_tickets":
            try:
                value = int(value)
                if value < 1 or value > 10:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("1〜10の数字で入力してください。", ephemeral=True)
                return
        self.setup_view.settings[self.field] = value if value else self.setup_view.settings.get(self.field)
        await interaction.response.send_message(f"`{self.field}` を更新しました。", ephemeral=True)


class TicketSetupPanelTextModal(discord.ui.Modal):
    def __init__(self, setup_view):
        super().__init__(title="パネルタイトル/説明")
        self.setup_view = setup_view
        self.title_input = discord.ui.TextInput(label="パネルタイトル", required=False, max_length=200)
        self.desc_input = discord.ui.TextInput(label="パネル説明", style=discord.TextStyle.paragraph, required=False, max_length=1000)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        if self.title_input.value.strip():
            self.setup_view.settings["panel_title"] = self.title_input.value.strip()
        if self.desc_input.value.strip():
            self.setup_view.settings["panel_description"] = self.desc_input.value.strip()
        await interaction.response.send_message("パネルタイトル/説明を更新しました。", ephemeral=True)


class TicketSetupEmbedModal(discord.ui.Modal):
    def __init__(self, setup_view):
        super().__init__(title="チケット埋め込み設定")
        self.setup_view = setup_view
        self.title_input = discord.ui.TextInput(label="埋め込みタイトル", required=False, max_length=200)
        self.desc_input = discord.ui.TextInput(label="埋め込み説明", style=discord.TextStyle.paragraph, required=False, max_length=1000)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        if self.title_input.value.strip():
            self.setup_view.settings["embed_title"] = self.title_input.value.strip()
        if self.desc_input.value.strip():
            self.setup_view.settings["embed_description"] = self.desc_input.value.strip()
        await interaction.response.send_message("埋め込み設定を更新しました。", ephemeral=True)


class TicketRequirementModal(discord.ui.Modal):
    def __init__(self, multi_view):
        super().__init__(title="要件を追加")
        self.multi_view = multi_view
        self.name_input = discord.ui.TextInput(label="要件名", placeholder="例: 購入希望", max_length=100, required=True)
        self.desc_input = discord.ui.TextInput(label="説明", placeholder="例: 商品の購入について", max_length=200, required=False)
        self.emoji_input = discord.ui.TextInput(label="絵文字", placeholder="例: 🛒", max_length=10, required=False)
        self.placeholder_input = discord.ui.TextInput(
            label="セレクトのプレースホルダー文言",
            placeholder="例: Please choose your payment method.",
            max_length=150, required=False
        )
        self.add_item(self.name_input)
        self.add_item(self.desc_input)
        self.add_item(self.emoji_input)
        self.add_item(self.placeholder_input)

    async def on_submit(self, interaction):
        self.multi_view.settings["requirements"].append({
            "name": self.name_input.value.strip(),
            "description": self.desc_input.value.strip() or "",
            "emoji": self.emoji_input.value.strip() or "📝",
            "placeholder": self.placeholder_input.value.strip() or "Please choose an option."
        })
        await interaction.response.send_message(f"要件「{self.name_input.value.strip()}」を追加しました。", ephemeral=True)


class TicketRequirementRemoveView(discord.ui.View):
    def __init__(self, multi_view, options):
        super().__init__(timeout=120)
        self.multi_view = multi_view
        self.select.options = options

    @discord.ui.select(placeholder="削除する要件を選択", custom_id="ticket_req_remove")
    async def select(self, interaction, select):
        idx = int(select.values[0])
        reqs = self.multi_view.settings["requirements"]
        if 0 <= idx < len(reqs):
            removed = reqs.pop(idx)
            await interaction.response.edit_message(content=f"要件「{removed['name']}」を削除しました。", view=None)
        else:
            await interaction.response.edit_message(content="削除に失敗しました。", view=None)


class TicketSetupObjectSelectView(discord.ui.View):
    def __init__(self, setup_view, field, options, back_view=None):
        super().__init__(timeout=120)
        self.setup_view = setup_view
        self.field = field
        self.back_view = back_view
        self.select.options = options

    @discord.ui.select(placeholder="選択してください", custom_id="ticket_setup_object_select")
    async def select(self, interaction, select):
        value = select.values[0]
        if self.field in ("max_tickets",):
            value = int(value)
        self.setup_view.settings[self.field] = value
        await interaction.response.edit_message(content=f"`{self.field}` を更新しました。", view=self.back_view or self.setup_view)


# =========================================================
# TICKET PANEL (セレクトメニュー方式)
# =========================================================

class TicketSelectMenu(discord.ui.Select):
    def __init__(self, cog, panel_id, panel):
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel

        requirements = panel.get("requirements") or [
            {"name": "その他", "description": "", "emoji": "📝", "placeholder": "チケットの種類を選択してください"}
        ]

        options = []
        for req in requirements[:25]:
            name = req.get("name", "無題")
            desc = req.get("description", "") or ""
            emoji = req.get("emoji", "📝")
            options.append(discord.SelectOption(
                label=name[:100], value=name,
                description=desc[:100] if desc else None,
                emoji=emoji[:1] if emoji else None
            ))

        placeholder = requirements[0].get("placeholder", "チケットの種類を選択してください")
        super().__init__(placeholder=placeholder[:150], options=options, custom_id=f"ticket_select_{panel_id}")

    async def callback(self, interaction: discord.Interaction):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel or not interaction.guild:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return

        user_tickets = [
            ch for ch in interaction.guild.channels
            if isinstance(ch, discord.TextChannel)
            and ch.topic == f"ticket_owner:{interaction.user.id}:panel:{self.panel_id}"
        ]
        if len(user_tickets) >= panel.get("max_tickets", 1):
            await interaction.response.send_message(
                f"あなたは既に {panel.get('max_tickets', 1)} 件のチケットを作成しています。", ephemeral=True
            )
            return

        requirement_name = self.values[0]
        requirement_desc = ""
        for req in panel.get("requirements", []):
            if req.get("name") == requirement_name:
                requirement_desc = req.get("description", "") or ""
                break

        modal = TicketDetailModal(self.cog, self.panel_id, panel, requirement_name, requirement_desc)
        await interaction.response.send_modal(modal)


class TicketPanelView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        panel = cog.ticket_panels.get(panel_id)
        if panel:
            self.add_item(TicketSelectMenu(cog, panel_id, panel))


class TicketDetailModal(discord.ui.Modal):
    def __init__(self, cog, panel_id, panel, requirement_name, requirement_desc):
        super().__init__(title="チケット詳細")
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel
        self.requirement_name = requirement_name
        self.requirement_desc = requirement_desc
        self.detail_input = discord.ui.TextInput(
            label="詳細（任意）", placeholder="要件の詳細を入力してください",
            style=discord.TextStyle.paragraph, required=False, max_length=500
        )
        self.add_item(self.detail_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel or not interaction.guild:
            return await interaction.followup.send("パネルが見つかりません。", ephemeral=True)
        detail = self.detail_input.value.strip() if self.detail_input.value else ""
        category = interaction.guild.get_channel(panel["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.followup.send("カテゴリーが見つかりません。", ephemeral=True)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True)
        }
        mention_role_id = panel.get("mention_role_id")
        if mention_role_id:
            role = interaction.guild.get_role(mention_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        for rid in panel.get("access_role_ids", []):
            role = interaction.guild.get_role(rid)
            if role:
                ow = overwrites.get(role) or discord.PermissionOverwrite()
                ow.view_channel = True; ow.send_messages = True; ow.read_message_history = True
                overwrites[role] = ow
        for uid in panel.get("access_user_ids", []):
            member = interaction.guild.get_member(uid)
            if member:
                ow = overwrites.get(member) or discord.PermissionOverwrite()
                ow.view_channel = True; ow.send_messages = True; ow.read_message_history = True
                overwrites[member] = ow

        channel_name = f"ticket-{interaction.user.name}"[:100]
        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name, category=category, overwrites=overwrites,
                topic=f"ticket_owner:{interaction.user.id}:panel:{self.panel_id}"
            )
        except discord.HTTPException as error:
            return await interaction.followup.send(f"チケットの作成に失敗しました: {error}", ephemeral=True)

        embed = discord.Embed(
            title=panel.get("embed_title") or "チケット",
            description=panel.get("embed_description") or "サポートします。",
            color=discord.Color.blurple()
        )
        req_value = self.requirement_name
        if self.requirement_desc:
            req_value += f"\n{self.requirement_desc}"
        embed.add_field(name="要件", value=f"```{req_value}```", inline=False)
        if detail:
            embed.add_field(name="詳細", value=f"```{detail}```", inline=False)
        embed.add_field(name="作成者", value=interaction.user.mention, inline=False)

        mention_text = interaction.user.mention
        panel_creator_id = panel.get("creator_id")
        if panel_creator_id:
            mention_text += f" <@{panel_creator_id}>"
        if mention_role_id:
            role = interaction.guild.get_role(mention_role_id)
            if role:
                mention_text += f" {role.mention}"

        await channel.send(content=mention_text, embed=embed, view=TicketControlView(self.cog, self.panel_id))
        await interaction.followup.send(f"チケットを作成しました: {channel.mention}", ephemeral=True)


# =========================================================
# TICKET CONTROL
# =========================================================

class TicketControlRoleSelect(discord.ui.Select):
    def __init__(self, cog, panel_id, options):
        super().__init__(placeholder="スタッフロールを選択", options=options)
        self.cog = cog
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.edit_message(content="パネルが見つかりません。", view=None)
            return
        panel["mention_role_id"] = int(self.values[0])
        data = load_ticket_panel_data()
        data[self.panel_id] = panel
        save_ticket_panel_data(data)
        role = interaction.guild.get_role(int(self.values[0]))
        await interaction.response.edit_message(content=f"スタッフロールを {role.mention if role else self.values[0]} に設定しました。", view=None)


class TicketControlPanelModal(discord.ui.Modal):
    def __init__(self, cog, panel_id):
        super().__init__(title="パネル設定")
        self.cog = cog
        self.panel_id = panel_id
        panel = cog.ticket_panels.get(panel_id, {})
        self.title_input = discord.ui.TextInput(label="パネルタイトル", default=panel.get("panel_title", ""), required=False, max_length=200)
        self.desc_input = discord.ui.TextInput(label="パネル説明", default=panel.get("panel_description", ""), style=discord.TextStyle.paragraph, required=False, max_length=1000)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return
        if self.title_input.value.strip():
            panel["panel_title"] = self.title_input.value.strip()
        if self.desc_input.value.strip():
            panel["panel_description"] = self.desc_input.value.strip()
        data = load_ticket_panel_data()
        data[self.panel_id] = panel
        save_ticket_panel_data(data)
        try:
            ch = interaction.guild.get_channel(panel["channel_id"])
            if isinstance(ch, discord.TextChannel):
                msg = await ch.fetch_message(panel["message_id"])
                embed = msg.embeds[0] if msg.embeds else discord.Embed()
                embed.title = panel.get("panel_title") or "🎫 チケット"
                embed.description = panel.get("panel_description") or "下のドロップダウンからチケットを作成できます。"
                await msg.edit(embed=embed)
        except (discord.HTTPException, AttributeError):
            pass
        await interaction.response.send_message("パネル設定を更新しました。", ephemeral=True)


class TicketControlEmbedModal(discord.ui.Modal):
    def __init__(self, cog, panel_id):
        super().__init__(title="埋め込み設定")
        self.cog = cog
        self.panel_id = panel_id
        panel = cog.ticket_panels.get(panel_id, {})
        self.title_input = discord.ui.TextInput(label="埋め込みタイトル", default=panel.get("embed_title") or "", required=False, max_length=200)
        self.desc_input = discord.ui.TextInput(label="埋め込み説明", default=panel.get("embed_description") or "", style=discord.TextStyle.paragraph, required=False, max_length=1000)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return
        panel["embed_title"] = self.title_input.value.strip() or None
        panel["embed_description"] = self.desc_input.value.strip() or None
        data = load_ticket_panel_data()
        data[self.panel_id] = panel
        save_ticket_panel_data(data)
        await interaction.response.send_message("埋め込み設定を更新しました。", ephemeral=True)


class TicketControlRequirementModal(discord.ui.Modal):
    def __init__(self, cog, panel_id):
        super().__init__(title="要件追加")
        self.cog = cog
        self.panel_id = panel_id
        self.name_input = discord.ui.TextInput(label="要件タイトル", max_length=100, required=True)
        self.emoji_input = discord.ui.TextInput(label="絵文字", max_length=10, required=False)
        self.desc_input = discord.ui.TextInput(label="説明", style=discord.TextStyle.paragraph, max_length=200, required=False)
        self.add_item(self.name_input)
        self.add_item(self.emoji_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return
        panel.setdefault("requirements", []).append({
            "name": self.name_input.value.strip(),
            "description": self.desc_input.value.strip() or "",
            "emoji": self.emoji_input.value.strip() or "📝",
            "placeholder": "チケットの種類を選択してください"
        })
        data = load_ticket_panel_data()
        data[self.panel_id] = panel
        save_ticket_panel_data(data)
        await interaction.response.send_message(f"要件「{self.name_input.value.strip()}」を追加しました。", ephemeral=True)


class TicketControlView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.panel_button.custom_id = f"ticket_cfg_panel_{panel_id}"
        self.role_button.custom_id = f"ticket_cfg_role_{panel_id}"
        self.embed_button.custom_id = f"ticket_cfg_embed_{panel_id}"
        self.req_button.custom_id = f"ticket_cfg_req_{panel_id}"
        self.close_button.custom_id = f"ticket_cfg_close_{panel_id}"

    @discord.ui.button(label="パネル設定", style=discord.ButtonStyle.secondary, emoji="📝")
    async def panel_button(self, interaction, button):
        await interaction.response.send_modal(TicketControlPanelModal(self.cog, self.panel_id))

    @discord.ui.button(label="ロール設定", style=discord.ButtonStyle.secondary, emoji="🔔")
    async def role_button(self, interaction, button):
        roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed][:25]
        if not roles:
            await interaction.response.send_message("ロールがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        view = discord.ui.View(timeout=120)
        view.add_item(TicketControlRoleSelect(self.cog, self.panel_id, options))
        await interaction.response.send_message("スタッフロールを選択してください。", view=view, ephemeral=True)

    @discord.ui.button(label="埋め込み設定", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def embed_button(self, interaction, button):
        await interaction.response.send_modal(TicketControlEmbedModal(self.cog, self.panel_id))

    @discord.ui.button(label="要件追加", style=discord.ButtonStyle.success, emoji="➕")
    async def req_button(self, interaction, button):
        await interaction.response.send_modal(TicketControlRequirementModal(self.cog, self.panel_id))

    @discord.ui.button(label="🔒 チケットを閉じる", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction, button):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return
        if panel.get("delete_permission") == "admin" and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("削除にはチャンネル管理権限が必要です。", ephemeral=True)
            return
        await interaction.response.send_message("チケットを削除します...", ephemeral=True)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.HTTPException:
            pass


# =========================================================
# TICKET SETTINGS (即時パネル表示 / _parent 衝突回避 / 下書き永続化)
# =========================================================

class TicketSettingsCategorySelect(discord.ui.ChannelSelect):
    def __init__(self, settings_view: "TicketSettingsView", row: int = 0):
        self.settings_view = settings_view
        super().__init__(
            placeholder="🔎 チケット作成するカテゴリーを選択（検索可）",
            channel_types=[discord.ChannelType.category],
            min_values=1, max_values=1,
            custom_id="ticket_settings_category",
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        if self.settings_view is None:
            await interaction.response.send_message(
                "設定画面の有効期限が切れました。もう一度 `/チケット` を実行してください。",
                ephemeral=True
            )
            return
        self.settings_view.settings["category_id"] = self.values[0].id
        self.settings_view.save_draft()
        embed = build_ticket_settings_embed(self.settings_view.settings)
        await interaction.response.edit_message(embed=embed, view=self.settings_view)


class TicketSettingsArchiveSelect(discord.ui.ChannelSelect):
    def __init__(self, settings_view: "TicketSettingsView", row: int = 1):
        self.settings_view = settings_view
        super().__init__(
            placeholder="🔎 チケット削除時のログ送信チャンネルを選択（検索可）",
            channel_types=[discord.ChannelType.text],
            min_values=1, max_values=1,
            custom_id="ticket_settings_archive",
            row=row
        )

    async def callback(self, interaction: discord.Interaction):
        if self.settings_view is None:
            await interaction.response.send_message(
                "設定画面の有効期限が切れました。もう一度 `/チケット` を実行してください。",
                ephemeral=True
            )
            return
        self.settings_view.settings["archive_channel_id"] = self.values[0].id
        self.settings_view.save_draft()
        embed = build_ticket_settings_embed(self.settings_view.settings)
        await interaction.response.edit_message(embed=embed, view=self.settings_view)


class TicketSettingsPanelModal(discord.ui.Modal):
    def __init__(self, parent: "TicketSettingsView"):
        super().__init__(title="パネル設定")
        self.parent = parent
        self.title_input = discord.ui.TextInput(label="タイトル", default=parent.settings.get("panel_title") or "", required=False, max_length=200)
        self.desc_input = discord.ui.TextInput(label="説明", default=parent.settings.get("panel_description") or "", style=discord.TextStyle.paragraph, required=False, max_length=1000)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        if self.title_input.value.strip():
            self.parent.settings["panel_title"] = self.title_input.value.strip()
        if self.desc_input.value.strip():
            self.parent.settings["panel_description"] = self.desc_input.value.strip()
        self.parent.save_draft()
        embed = build_ticket_settings_embed(self.parent.settings)
        try:
            await interaction.message.edit(embed=embed, view=self.parent)
        except (discord.HTTPException, AttributeError):
            pass
        await interaction.response.send_message("パネル設定を更新しました。", ephemeral=True)


class TicketSettingsRoleSelect(discord.ui.Select):
    def __init__(self, settings_view: "TicketSettingsView", options):
        self.settings_view = settings_view
        super().__init__(
            placeholder="スタッフロールを選択",
            options=options,
            custom_id="ticket_settings_role"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.settings_view is None:
            await interaction.response.send_message(
                "設定画面の有効期限が切れました。もう一度 `/チケット` を実行してください。",
                ephemeral=True
            )
            return
        self.settings_view.settings["mention_role_id"] = int(self.values[0])
        self.settings_view.save_draft()
        embed = build_ticket_settings_embed(self.settings_view.settings)
        try:
            await interaction.message.edit(embed=embed, view=self.settings_view)
        except (discord.HTTPException, AttributeError):
            pass
        role = interaction.guild.get_role(int(self.values[0]))
        await interaction.response.send_message(
            f"スタッフロールを {role.mention if role else self.values[0]} に設定しました。",
            ephemeral=True
        )


class TicketSettingsRoleView(discord.ui.View):
    def __init__(self, parent: "TicketSettingsView", options):
        super().__init__(timeout=120)
        self.add_item(TicketSettingsRoleSelect(parent, options))


class TicketSettingsEmbedModal(discord.ui.Modal):
    def __init__(self, parent: "TicketSettingsView"):
        super().__init__(title="埋め込み設定")
        self.parent = parent
        self.title_input = discord.ui.TextInput(label="チケット作成後の埋め込みタイトル", default=parent.settings.get("embed_title") or "", required=False, max_length=200)
        self.desc_input = discord.ui.TextInput(label="埋め込み説明", default=parent.settings.get("embed_description") or "", style=discord.TextStyle.paragraph, required=False, max_length=1000)
        self.add_item(self.title_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        self.parent.settings["embed_title"] = self.title_input.value.strip() or None
        self.parent.settings["embed_description"] = self.desc_input.value.strip() or None
        self.parent.save_draft()
        embed = build_ticket_settings_embed(self.parent.settings)
        try:
            await interaction.message.edit(embed=embed, view=self.parent)
        except (discord.HTTPException, AttributeError):
            pass
        await interaction.response.send_message("埋め込み設定を更新しました。", ephemeral=True)


class TicketSettingsRequirementModal(discord.ui.Modal):
    def __init__(self, parent: "TicketSettingsView"):
        super().__init__(title="要件追加")
        self.parent = parent
        self.name_input = discord.ui.TextInput(label="タイトル", max_length=100, required=True)
        self.emoji_input = discord.ui.TextInput(label="絵文字", max_length=10, required=False)
        self.desc_input = discord.ui.TextInput(label="説明", style=discord.TextStyle.paragraph, max_length=200, required=False)
        self.add_item(self.name_input)
        self.add_item(self.emoji_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction):
        reqs = self.parent.settings.setdefault("requirements", [])
        if len(reqs) >= 25:
            await interaction.response.send_message("要件は最大25個までです。", ephemeral=True)
            return
        reqs.append({
            "name": self.name_input.value.strip(),
            "description": self.desc_input.value.strip() or "",
            "emoji": self.emoji_input.value.strip() or "📝",
            "placeholder": "チケットの種類を選択してください"
        })
        self.parent.save_draft()
        embed = build_ticket_settings_embed(self.parent.settings)
        try:
            await interaction.message.edit(embed=embed, view=self.parent)
        except (discord.HTTPException, AttributeError):
            pass
        await interaction.response.send_message(f"要件「{self.name_input.value.strip()}」を追加しました。", ephemeral=True)


class TicketSettingsRequirementsRemoveSelect(discord.ui.Select):
    def __init__(self, parent: "TicketSettingsView", options):
        self.parent = parent
        super().__init__(placeholder="削除する要件を選択", options=options, custom_id="ticket_settings_req_remove")

    async def callback(self, interaction: discord.Interaction):
        try:
            idx = int(self.values[0])
        except (ValueError, TypeError):
            await interaction.response.send_message("削除に失敗しました。", ephemeral=True)
            return
        reqs = self.parent.settings.get("requirements", [])
        if 0 <= idx < len(reqs):
            removed = reqs.pop(idx)
            self.parent.save_draft()
            embed = build_ticket_settings_embed(self.parent.settings)
            try:
                await interaction.message.edit(embed=embed, view=self.parent)
            except (discord.HTTPException, AttributeError):
                pass
            await interaction.response.send_message(f"要件「{removed.get('name', '')}」を削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message("削除に失敗しました。", ephemeral=True)


class TicketSettingsRequirementsRemoveView(discord.ui.View):
    def __init__(self, parent: "TicketSettingsView", options):
        super().__init__(timeout=120)
        self.add_item(TicketSettingsRequirementsRemoveSelect(parent, options))


class TicketSettingsView(discord.ui.View):
    def __init__(self, cog, user_id, guild_id, settings=None):
        super().__init__(timeout=1800)
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id
        if settings is None:
            settings = get_guild_draft(guild_id)
        self.settings = settings
        self.add_item(TicketSettingsCategorySelect(self, row=0))
        self.add_item(TicketSettingsArchiveSelect(self, row=1))

    def save_draft(self):
        update_guild_draft(self.guild_id, self.settings)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この設定は実行者本人のみ操作できます。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="パネル設定", style=discord.ButtonStyle.secondary, emoji="📝", row=2)
    async def panel_button(self, interaction, button):
        await interaction.response.send_modal(TicketSettingsPanelModal(self))

    @discord.ui.button(label="ロール設定", style=discord.ButtonStyle.secondary, emoji="🔔", row=2)
    async def role_button(self, interaction, button):
        roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed][:25]
        if not roles:
            await interaction.response.send_message("ロールがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        view = TicketSettingsRoleView(self, options)
        await interaction.response.send_message("スタッフロールを選択してください。", view=view, ephemeral=True)

    @discord.ui.button(label="埋め込み設定", style=discord.ButtonStyle.secondary, emoji="🖼️", row=2)
    async def embed_button(self, interaction, button):
        await interaction.response.send_modal(TicketSettingsEmbedModal(self))

    @discord.ui.button(label="要件追加", style=discord.ButtonStyle.success, emoji="➕", row=2)
    async def req_button(self, interaction, button):
        await interaction.response.send_modal(TicketSettingsRequirementModal(self))

    @discord.ui.button(label="要件削除", style=discord.ButtonStyle.danger, emoji="🗑️", row=3)
    async def req_remove_button(self, interaction, button):
        reqs = self.settings.get("requirements", [])
        if not reqs:
            await interaction.response.send_message("削除できる要件がありません。", ephemeral=True)
            return
        options = []
        for i, r in enumerate(reqs[:25]):
            label = r.get("name", "無題")[:100]
            options.append(discord.SelectOption(
                label=f"{i+1}. {label}",
                value=str(i),
                emoji=r.get("emoji", "📝")[:1] if r.get("emoji") else None
            ))
        view = TicketSettingsRequirementsRemoveView(self, options)
        await interaction.response.send_message("削除する要件を選択してください。", view=view, ephemeral=True)

    @discord.ui.button(label="✅ パネルを作成", style=discord.ButtonStyle.success, emoji="✅", row=4)
    async def create_button(self, interaction, button):
        s = self.settings
        if not s.get("category_id"):
            await interaction.response.send_message("カテゴリーを設定してください。", ephemeral=True)
            return
        if not s.get("mention_role_id"):
            await interaction.response.send_message("スタッフロールを設定してください。", ephemeral=True)
            return

        category = interaction.guild.get_channel(s["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "設定されたカテゴリーが見つかりません。選び直してください。",
                ephemeral=True
            )
            return

        # 既存パネルがあれば再利用（編集）、無ければ新規作成
        panel_id = s.get("panel_id")
        existing_panel = None
        if panel_id and panel_id in self.cog.ticket_panels:
            existing_panel = self.cog.ticket_panels[panel_id]

        if existing_panel is None:
            panel_id = uuid.uuid4().hex[:10]
            existing_panel = {"id": panel_id}

        panel_data = {
            "id": panel_id,
            "creator_id": interaction.user.id,
            "mode": s.get("mode", "multi"),
            "button_label": s.get("button_label", "🎫 チケットを作成"),
            "max_tickets": s.get("max_tickets", 1),
            "mention_role_id": s["mention_role_id"],
            "embed_title": s.get("embed_title"),
            "embed_description": s.get("embed_description"),
            "welcome_message": s.get("welcome_message"),
            "delete_permission": s.get("delete_permission", "admin"),
            "category_id": s["category_id"],
            "archive_channel_id": s.get("archive_channel_id"),
            "channel_id": s.get("panel_channel_id") or interaction.channel.id,
            "message_id": s.get("panel_message_id"),
            "panel_title": s.get("panel_title"),
            "panel_description": s.get("panel_description"),
            "requirements": s.get("requirements") or [],
            "access_role_ids": [],
            "access_user_ids": [],
        }
        self.cog.ticket_panels[panel_id] = panel_data

        embed = discord.Embed(
            title=s.get("panel_title") or "🎫 チケット",
            description=s.get("panel_description") or "下のドロップダウンからチケットを作成できます。",
            color=discord.Color.blurple()
        )
        req_lines = []
        for i, r in enumerate(s.get("requirements") or [], start=1):
            name = r.get("name", "無題")
            emoji = r.get("emoji", "📝")
            desc = r.get("description", "") or "説明なし"
            req_lines.append(f"{i}.{name}\n　{emoji}\n　{desc}")
        if req_lines:
            embed.add_field(name="要件一覧", value="\n".join(req_lines)[:1024], inline=False)
        embed.set_footer(text=f"1人につき最大 {s.get('max_tickets', 1)} 件まで")

        view = TicketPanelView(self.cog, panel_id)

        # 既存メッセージが生きていれば編集、無ければ新規送信
        target_channel_id = panel_data.get("channel_id")
        target_message_id = panel_data.get("message_id")
        edited = False
        if target_channel_id and target_message_id:
            ch = interaction.guild.get_channel(target_channel_id)
            if isinstance(ch, discord.TextChannel):
                try:
                    msg = await ch.fetch_message(target_message_id)
                    await msg.edit(embed=embed, view=view)
                    edited = True
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    edited = False

        if not edited:
            try:
                message = await interaction.channel.send(embed=embed, view=view)
            except discord.HTTPException as e:
                await interaction.response.send_message(f"パネル作成に失敗しました: {e}", ephemeral=True)
                return
            panel_data["channel_id"] = interaction.channel.id
            panel_data["message_id"] = message.id

        self.cog.ticket_panels[panel_id] = panel_data

        # 下書きにも保存（次回 /チケット 実行時に引き継ぐ）
        self.settings["panel_id"] = panel_id
        self.settings["panel_channel_id"] = panel_data["channel_id"]
        self.settings["panel_message_id"] = panel_data["message_id"]
        self.save_draft()

        data = load_ticket_panel_data()
        data[panel_id] = panel_data
        save_ticket_panel_data(data)

        if edited:
            await interaction.response.send_message(
                "✅ 既存パネルを更新しました。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "✅ チケットパネルを作成しました。\n"
                "（削除されても、同じ画面から「✅ パネルを作成」を再度押せば再作成できます）",
                ephemeral=True
            )
        # ★ self.stop() を呼ばない：何度でも押せるようにする


# =========================================================
# VOUCH PANEL
# =========================================================

class VouchRatingView(discord.ui.View):
    def __init__(self, cog, panel_id, user_id, product_name, quantity, impression):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.user_id = user_id
        self.product_name = product_name
        self.quantity = quantity
        self.impression = impression

    async def send_review(self, interaction, stars):
        panel = self.cog.vouch_panels.get(self.panel_id)
        if not panel or not interaction.guild:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return
        destination = interaction.guild.get_channel(panel["destination_id"])
        if not isinstance(destination, discord.TextChannel):
            await interaction.response.send_message("実績送信先チャンネルが見つかりません。", ephemeral=True)
            return
        embed = discord.Embed(title="🛒 実績レビュー", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="購入者", value=interaction.user.mention, inline=True)
        embed.add_field(name="商品", value=self.product_name, inline=True)
        embed.add_field(name="個数", value=str(self.quantity), inline=True)
        embed.add_field(name="評価", value=f"{'⭐' * stars} `{stars}/5`", inline=False)
        embed.add_field(name="感想", value=self.impression, inline=False)
        embed.set_footer(text=f"Review by {interaction.user.display_name} / ID: {interaction.user.id}")
        try:
            await destination.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("Botに送信先への閲覧・送信権限がありません。", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("実績を送信できませんでした。", ephemeral=True)
            return
        panel["count"] += 1
        counter_id = panel.get("counter_id")
        if counter_id:
            counter = interaction.guild.get_channel(counter_id)
            if isinstance(counter, discord.TextChannel):
                name = f"{panel['counter_base_name']} -{panel['count']}"[:100]
                try:
                    await counter.edit(name=name, reason="実績カウント更新")
                except discord.HTTPException:
                    pass
        await interaction.response.edit_message(content="✅ 実績を送信しました。", view=None)

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary)
    async def star1(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True); return
        await self.send_review(interaction, 1)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary)
    async def star2(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True); return
        await self.send_review(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def star3(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True); return
        await self.send_review(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def star4(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True); return
        await self.send_review(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def star5(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True); return
        await self.send_review(interaction, 5)


class VouchModal(discord.ui.Modal):
    def __init__(self, cog, panel_id):
        super().__init__(title="実績を送信")
        self.cog = cog
        self.panel_id = panel_id
        self.product_name = discord.ui.TextInput(label="商品名", placeholder="購入した商品名", max_length=100, required=True)
        self.quantity = discord.ui.TextInput(label="個数", placeholder="数字のみ", max_length=10, required=True)
        self.impression = discord.ui.TextInput(label="感想", placeholder="感想を入力", style=discord.TextStyle.paragraph, max_length=1000, required=True)
        self.add_item(self.product_name)
        self.add_item(self.quantity)
        self.add_item(self.impression)

    async def on_submit(self, interaction):
        panel = self.cog.vouch_panels.get(self.panel_id)
        if not panel or not interaction.guild:
            await interaction.response.send_message("パネルが見つからないか、サーバー外で使用されています。", ephemeral=True)
            return
        if not self.quantity.value.isdigit():
            await interaction.response.send_message("個数は数字のみで入力してください。", ephemeral=True)
            return
        view = VouchRatingView(self.cog, self.panel_id, interaction.user.id, self.product_name.value, int(self.quantity.value), self.impression.value)
        await interaction.response.send_message(
            "レビュー内容を受け取りました。\n"
            f"**{self.product_name.value}** の評価を選んでください。",
            view=view, ephemeral=True
        )


class VouchView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.submit_button.custom_id = f"vouch_submit_{panel_id}"

    @discord.ui.button(label="📋 実績を送信", style=discord.ButtonStyle.success, custom_id="vouch_submit_default")
    async def submit_button(self, interaction, button):
        await interaction.response.send_modal(VouchModal(self.cog, self.panel_id))


# =========================================================
# STATUS PANEL
# =========================================================

def status_embed(guild, staff_list):
    colors = {"対応不可": discord.Color.red(), "対応遅延": discord.Color.orange(), "対応可能": discord.Color.green()}
    priority = {"対応不可": 0, "対応遅延": 1, "対応可能": 2}
    if staff_list:
        worst = min(staff_list, key=lambda s: priority.get(s["status"], 3))
        color = colors.get(worst["status"], discord.Color.blurple())
    else:
        color = discord.Color.blurple()
    embed = discord.Embed(title="対応状況", color=color)
    if not staff_list:
        embed.description = "登録されているスタッフがいません。"
        return embed
    lines = []
    for staff in staff_list:
        member = guild.get_member(staff["user_id"])
        mention = member.mention if member else f"<@{staff['user_id']}>"
        lines.append(
            f"# {mention}\n"
            f"現在の状態\n"
            f"**{staff['emoji']} {staff['status']}**\n"
            f"一言\n"
            f"{staff['message'] or '設定なし'}"
        )
    embed.description = "\n\n".join(lines)
    return embed


class StatusMessageModal(discord.ui.Modal):
    def __init__(self, cog, panel_id, user_id):
        super().__init__(title="一言を変更")
        self.cog = cog
        self.panel_id = panel_id
        self.user_id = user_id
        self.message_input = discord.ui.TextInput(label="一言", placeholder="現在の状況など", required=False, max_length=200)
        self.add_item(self.message_input)

    async def on_submit(self, interaction):
        panel = self.cog.status_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True); return
        target = None
        for s in panel.get("staff", []):
            if s["user_id"] == self.user_id:
                target = s; break
        if not target:
            await interaction.response.send_message("あなたはこのパネルのスタッフではありません。", ephemeral=True); return
        target["message"] = self.message_input.value.strip()
        await self.cog.refresh_status(panel)
        await interaction.response.send_message("一言を更新しました。", ephemeral=True)


class StatusSelectView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.select.custom_id = f"status_select_{panel_id}"
        self.message_button.custom_id = f"status_message_{panel_id}"

    @discord.ui.select(
        placeholder="対応状況を変更",
        options=[
            discord.SelectOption(label="対応不可", value="対応不可", emoji="🔴"),
            discord.SelectOption(label="対応遅延", value="対応遅延", emoji="🟠"),
            discord.SelectOption(label="対応可能", value="対応可能", emoji="🟢"),
        ],
        custom_id="status_select_default"
    )
    async def select(self, interaction, select):
        panel = self.cog.status_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True); return
        target = None
        for s in panel.get("staff", []):
            if s["user_id"] == interaction.user.id:
                target = s; break
        if not target:
            await interaction.response.send_message(
                "あなたはこのパネルのスタッフではありません。\n"
                "管理者に `/対応状況スタッフ追加` を依頼してください。",
                ephemeral=True
            ); return
        status = select.values[0]
        emojis = {"対応不可": "🔴", "対応遅延": "🟠", "対応可能": "🟢"}
        target["status"] = status
        target["emoji"] = emojis[status]
        await self.cog.refresh_status(panel)
        await interaction.response.send_message(f"あなたの状態を「{status}」に変更しました。", ephemeral=True)

    @discord.ui.button(label="✏️ 一言変更", style=discord.ButtonStyle.primary, custom_id="status_message_default")
    async def message_button(self, interaction, button):
        panel = self.cog.status_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True); return
        staff_ids = [s["user_id"] for s in panel.get("staff", [])]
        if interaction.user.id not in staff_ids:
            await interaction.response.send_message("あなたはこのパネルのスタッフではありません。", ephemeral=True); return
        await interaction.response.send_modal(StatusMessageModal(self.cog, self.panel_id, interaction.user.id))


# =========================================================
# TICKET EDIT (パネル編集メニュー)
# =========================================================

class TicketEditSelectView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=120)
        self.cog = cog
        self.select.options = options

    @discord.ui.select(placeholder="編集するチケットパネルを選択", custom_id="ticket_edit_select")
    async def select(self, interaction, select):
        panel_id = select.values[0]
        panel = self.cog.ticket_panels.get(panel_id)
        if not panel:
            await interaction.response.edit_message(content="パネルが見つかりません。", view=None)
            return
        view = TicketEditMenuView(self.cog, panel_id)
        await interaction.response.edit_message(content=f"パネル `{panel_id}` の編集メニューです。", view=view)


class TicketEditMenuView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=180)
        self.cog = cog
        self.panel_id = panel_id
        self.field_select.options = [
            discord.SelectOption(label="ボタン名", value="button_label"),
            discord.SelectOption(label="最大チケット数", value="max_tickets"),
            discord.SelectOption(label="メンションロール", value="mention_role"),
            discord.SelectOption(label="埋め込みタイトル", value="embed_title"),
            discord.SelectOption(label="埋め込み説明", value="embed_description"),
            discord.SelectOption(label="ウェルカムメッセージ", value="welcome_message"),
            discord.SelectOption(label="削除権限", value="delete_permission"),
            discord.SelectOption(label="カテゴリー", value="category"),
            discord.SelectOption(label="アーカイブチャンネル", value="archive_channel"),
        ]

    @discord.ui.select(placeholder="編集する項目を選択", options=[], custom_id="ticket_edit_field")
    async def field_select(self, interaction, select):
        field = select.values[0]

        if field == "category":
            categories = interaction.guild.categories[:25]
            if not categories:
                await interaction.response.send_message("カテゴリーがありません。", ephemeral=True); return
            options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in categories]
            view = TicketEditObjectSelectView(self.cog, self.panel_id, field, options)
            await interaction.response.edit_message(content="新しいカテゴリーを選択してください。", view=view)
        elif field == "mention_role":
            roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed][:25]
            if not roles:
                await interaction.response.send_message("ロールがありません。", ephemeral=True); return
            options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
            view = TicketEditObjectSelectView(self.cog, self.panel_id, field, options)
            await interaction.response.edit_message(content="新しいメンションロールを選択してください。", view=view)
        elif field == "archive_channel":
            channels = [c for c in interaction.guild.text_channels][:25]
            if not channels:
                await interaction.response.send_message("テキストチャンネルがありません。", ephemeral=True); return
            options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in channels]
            view = TicketEditObjectSelectView(self.cog, self.panel_id, field, options)
            await interaction.response.edit_message(content="新しいアーカイブチャンネルを選択してください。", view=view)
        else:
            await interaction.response.send_modal(TicketEditModal(self.cog, self.panel_id, field))


class TicketEditObjectSelectView(discord.ui.View):
    def __init__(self, cog, panel_id, field, options):
        super().__init__(timeout=120)
        self.cog = cog
        self.panel_id = panel_id
        self.field = field
        self.select.options = options

    @discord.ui.select(placeholder="選択してください", custom_id="ticket_edit_object_select")
    async def select(self, interaction, select):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.edit_message(content="パネルが見つかりません。", view=None)
            return
        value = int(select.values[0])
        if self.field == "category":
            panel["category_id"] = value
        elif self.field == "mention_role":
            panel["mention_role_id"] = value
        elif self.field == "archive_channel":
            panel["archive_channel_id"] = value
        data = load_ticket_panel_data()
        data[self.panel_id] = panel
        save_ticket_panel_data(data)
        await interaction.response.edit_message(content=f"`{self.field}` を更新しました。", view=None)


class TicketEditModal(discord.ui.Modal):
    def __init__(self, cog, panel_id, field):
        super().__init__(title=f"編集: {field}")
        self.cog = cog
        self.panel_id = panel_id
        self.field = field
        self.value_input = discord.ui.TextInput(label="新しい値", placeholder="新しい値を入力してください", required=False, max_length=1000)
        self.add_item(self.value_input)

    async def on_submit(self, interaction):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True); return
        value = self.value_input.value.strip()
        field = self.field
        try:
            if field == "button_label":
                panel["button_label"] = value or panel["button_label"]
            elif field == "max_tickets":
                panel["max_tickets"] = int(value) if value else panel["max_tickets"]
            elif field == "embed_title":
                panel["embed_title"] = value
            elif field == "embed_description":
                panel["embed_description"] = value
            elif field == "welcome_message":
                panel["welcome_message"] = value
            elif field == "delete_permission":
                if value in ("admin", "everyone"):
                    panel["delete_permission"] = value
                else:
                    raise ValueError("admin または everyone を指定してください。")
        except ValueError as error:
            await interaction.response.send_message(f"値が不正です: {error}", ephemeral=True); return
        data = load_ticket_panel_data()
        data[self.panel_id] = panel
        save_ticket_panel_data(data)
        await interaction.response.send_message(f"`{field}` を更新しました。", ephemeral=True)


# =========================================================
# MEMBER LOG SETTING
# =========================================================

def build_member_log_embed(guild_id: int, join_channel_id, leave_channel_id):
    join_text = f"<#{join_channel_id}>" if join_channel_id else "設定なし"
    leave_text = f"<#{leave_channel_id}>" if leave_channel_id else "設定なし"
    embed = discord.Embed(
        title="メンバーログ設定",
        description=(
            f"サーバー名: {guild_id}\n"
            f"下のドロップダウン（検索可）から入室/退室通知チャンネルを設定できます。\n"
            f"解除はボタンで行えます。"
        ),
        color=discord.Color.blurple()
    )
    embed.add_field(name="入室通知チャンネル", value=join_text, inline=False)
    embed.add_field(name="退室通知チャンネル", value=leave_text, inline=False)
    return embed


class MemberLogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, cog, log_type: str):
        self.cog = cog
        self.log_type = log_type
        placeholder = "入室通知チャンネルを選択（検索できます）" if log_type == "join" else "退室通知チャンネルを選択（検索できます）"
        super().__init__(
            placeholder=placeholder,
            channel_types=[discord.ChannelType.text],
            min_values=1, max_values=1,
            custom_id=f"member_log_select_{log_type}"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        channel = self.values[0]
        data = load_member_log_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"join_channel_id": None, "leave_channel_id": None}
        if self.log_type == "join":
            data[gid]["join_channel_id"] = channel.id
        else:
            data[gid]["leave_channel_id"] = channel.id
        save_member_log_data(data)
        embed = build_member_log_embed(interaction.guild.id, data[gid].get("join_channel_id"), data[gid].get("leave_channel_id"))
        await interaction.response.edit_message(embed=embed, view=self.view)


class MemberLogRemoveButton(discord.ui.Button):
    def __init__(self, cog, log_type: str):
        self.cog = cog
        self.log_type = log_type
        label = "入室通知 解除" if log_type == "join" else "退室通知 解除"
        super().__init__(label=label, style=discord.ButtonStyle.danger, custom_id=f"member_log_remove_{log_type}")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_member_log_data()
        gid = str(interaction.guild.id)
        if gid in data:
            if self.log_type == "join":
                data[gid]["join_channel_id"] = None
            else:
                data[gid]["leave_channel_id"] = None
            save_member_log_data(data)
        embed = build_member_log_embed(interaction.guild.id, data.get(gid, {}).get("join_channel_id"), data.get(gid, {}).get("leave_channel_id"))
        await interaction.response.edit_message(embed=embed, view=self.view)


class MemberLogSettingView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(MemberLogChannelSelect(cog, "join"))
        self.add_item(MemberLogChannelSelect(cog, "leave"))
        self.add_item(MemberLogRemoveButton(cog, "join"))
        self.add_item(MemberLogRemoveButton(cog, "leave"))


# =========================================================
# ANTIRAID
# =========================================================

def build_antiraid_embed(guild, data):
    embed = discord.Embed(
        title="荒らし対策設定",
        description=(f"サーバー名: {guild.name} ({guild.id})\n下のドロップダウン（検索可）から各種設定を変更できます。"),
        color=discord.Color.red()
    )
    embed.add_field(name="連投スパム", value="オン" if data.get("spam_enabled") else "オフ", inline=False)
    embed.add_field(name="リンク検知", value="オン" if data.get("link_enabled") else "オフ", inline=False)
    ignore_users = data.get("ignore_user_ids", [])
    embed.add_field(name="荒らし対策を検知しないメンバー", value="\n".join(f"<@{uid}>" for uid in ignore_users) if ignore_users else "なし", inline=False)
    ignore_roles = data.get("ignore_role_ids", [])
    embed.add_field(name="荒らし対策を検知しないロール", value="\n".join(f"<@&{rid}>" for rid in ignore_roles) if ignore_roles else "なし", inline=False)
    return embed


class AntiraidIgnoreUserSelect(discord.ui.UserSelect):
    def __init__(self, cog):
        super().__init__(placeholder="🔍 荒らし対策を検知しないメンバー（検索できます）", min_values=0, max_values=25, custom_id="antiraid_ignore_users")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False, "ignore_user_ids": [], "ignore_role_ids": []}
        data[gid]["ignore_user_ids"] = [u.id for u in self.values]
        save_antiraid_data(data)
        embed = build_antiraid_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class AntiraidIgnoreRoleSelect(discord.ui.RoleSelect):
    def __init__(self, cog):
        super().__init__(placeholder="🔍 荒らし対策を検知しないロール（検索できます）", min_values=0, max_values=25, custom_id="antiraid_ignore_roles")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False, "ignore_user_ids": [], "ignore_role_ids": []}
        data[gid]["ignore_role_ids"] = [r.id for r in self.values]
        save_antiraid_data(data)
        embed = build_antiraid_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class AntiraidToggleButton(discord.ui.Button):
    def __init__(self, cog, toggle_type):
        self.cog = cog
        self.toggle_type = toggle_type
        label = "連投スパム 切替" if toggle_type == "spam" else "リンク検知 切替"
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"antiraid_toggle_{toggle_type}")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False, "ignore_user_ids": [], "ignore_role_ids": []}
        if self.toggle_type == "spam":
            data[gid]["spam_enabled"] = not data[gid].get("spam_enabled", False)
        else:
            data[gid]["link_enabled"] = not data[gid].get("link_enabled", False)
        save_antiraid_data(data)
        embed = build_antiraid_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class AntiraidSettingView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(AntiraidToggleButton(cog, "spam"))
        self.add_item(AntiraidToggleButton(cog, "link"))
        self.add_item(AntiraidIgnoreUserSelect(cog))
        self.add_item(AntiraidIgnoreRoleSelect(cog))


class AntiraidPunishView(discord.ui.View):
    def __init__(self, member, reason):
        super().__init__(timeout=300)
        self.member = member
        self.reason = reason

    async def interaction_check(self, interaction):
        if not interaction.user.guild_permissions.kick_members and \
           not interaction.user.guild_permissions.ban_members and \
           not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("この操作にはモデレーション権限が必要です。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="BAN", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction, button):
        try:
            await self.member.ban(reason=f"Anti-raid: {self.reason} / by {interaction.user}")
            await interaction.response.send_message(f"{self.member.mention} をBANしました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("BANできません。権限を確認してください。", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"BANに失敗しました: {e}", ephemeral=True)

    @discord.ui.button(label="KICK", style=discord.ButtonStyle.danger, emoji="👢")
    async def kick_button(self, interaction, button):
        try:
            await self.member.kick(reason=f"Anti-raid: {self.reason} / by {interaction.user}")
            await interaction.response.send_message(f"{self.member.mention} をKICKしました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("KICKできません。権限を確認してください。", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"KICKに失敗しました: {e}", ephemeral=True)

    @discord.ui.button(label="TIMEOUT", style=discord.ButtonStyle.primary, emoji="⏳")
    async def timeout_button(self, interaction, button):
        view = TimeoutDurationView(self.member, self.reason)
        await interaction.response.send_message("TIMEOUT期間を選択してください。", view=view, ephemeral=True)


class TimeoutDurationView(discord.ui.View):
    def __init__(self, member, reason):
        super().__init__(timeout=120)
        self.member = member
        self.reason = reason

    async def apply_timeout(self, interaction, seconds):
        try:
            until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
            await self.member.timeout(until, reason=f"Anti-raid: {self.reason} / by {interaction.user}")
            await interaction.response.send_message(f"{self.member.mention} を {seconds}秒間 TIMEOUT にしました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("TIMEOUTできません。権限を確認してください。", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"TIMEOUTに失敗しました: {e}", ephemeral=True)

    @discord.ui.button(label="5分", style=discord.ButtonStyle.secondary)
    async def t5m(self, interaction, button): await self.apply_timeout(interaction, 5 * 60)

    @discord.ui.button(label="10分", style=discord.ButtonStyle.secondary)
    async def t10m(self, interaction, button): await self.apply_timeout(interaction, 10 * 60)

    @discord.ui.button(label="1時間", style=discord.ButtonStyle.secondary)
    async def t1h(self, interaction, button): await self.apply_timeout(interaction, 60 * 60)

    @discord.ui.button(label="1週間", style=discord.ButtonStyle.secondary)
    async def t1w(self, interaction, button): await self.apply_timeout(interaction, 7 * 24 * 60 * 60)


# =========================================================
# FIXED MESSAGE
# =========================================================

class FixedMessageRemoveSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="解除する固定メッセージを選択", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_fixed_message_data()
        gid = str(interaction.guild.id)
        cid = self.values[0]
        if gid in data and cid in data[gid]:
            info = data[gid].pop(cid)
            save_fixed_message_data(data)
            channel = interaction.guild.get_channel(info["channel_id"])
            if isinstance(channel, discord.TextChannel):
                if info.get("message_id"):
                    try:
                        msg = await channel.fetch_message(info["message_id"])
                        await msg.delete()
                    except discord.HTTPException:
                        pass
            await interaction.response.edit_message(content="固定メッセージを解除しました。", view=None)
        else:
            await interaction.response.edit_message(content="設定が見つかりません。", view=None)


class FixedMessageRemoveView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120)
        self.add_item(FixedMessageRemoveSelect(options))


# =========================================================
# AUTO REACTION
# =========================================================

def build_auto_reaction_embed(guild, data):
    embed = discord.Embed(
        title="自動リアクション設定",
        description=(f"サーバー名: {guild.name} ({guild.id})\n下のドロップダウン（検索可）から各種設定を変更できます。"),
        color=discord.Color.blurple()
    )
    embed.add_field(name="自動リアクション", value="オン" if data else "オフ", inline=False)
    if data:
        lines = []
        for cid, emojis in data.items():
            channel = guild.get_channel(int(cid))
            ch_name = channel.mention if channel else f"<#{cid}>"
            lines.append(f"{ch_name} → {' '.join(emojis)}")
        embed.add_field(name="リアクションするチャンネル", value="\n".join(lines)[:1024] if lines else "なし", inline=False)
    else:
        embed.add_field(name="リアクションするチャンネル", value="なし", inline=False)
    return embed


class AutoReactionChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, cog, index):
        self.cog = cog
        self.index = index
        super().__init__(
            placeholder="🔍 リアクションチャンネル（検索できます）" if index == 0 else f"🔍 リアクションチャンネル{index + 1}",
            channel_types=[discord.ChannelType.text],
            min_values=1, max_values=1,
            custom_id=f"auto_reaction_channel_{index}"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        modal = AutoReactionEmojiModal(self.cog, self.values[0].id)
        await interaction.response.send_modal(modal)


class AutoReactionEmojiModal(discord.ui.Modal):
    def __init__(self, cog, channel_id):
        super().__init__(title="絵文字を設定")
        self.cog = cog
        self.channel_id = channel_id
        self.emoji_input = discord.ui.TextInput(label="絵文字（カンマ区切りで最大4つ）", placeholder="例: 👍,🎉,😊,🔥", required=True, max_length=200)
        self.add_item(self.emoji_input)

    async def on_submit(self, interaction):
        emojis = [e.strip() for e in self.emoji_input.value.split(",") if e.strip()]
        if not emojis:
            await interaction.response.send_message("絵文字を1つ以上指定してください。", ephemeral=True); return
        data = load_auto_reaction_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid][str(self.channel_id)] = emojis
        save_auto_reaction_data(data)
        embed = build_auto_reaction_embed(interaction.guild, data[gid])
        view = AutoReactionSettingView(self.cog)
        await interaction.response.edit_message(embed=embed, view=view)


class AutoReactionSettingView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        for i in range(3):
            self.add_item(AutoReactionChannelSelect(cog, i))


class AutoReactionRemoveSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="解除するチャンネルの絵文字を選択（複数可）", min_values=1, max_values=25, options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_auto_reaction_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            await interaction.response.edit_message(content="設定がありません。", view=None); return
        removed = []
        for val in self.values:
            cid, emoji = val.split(":", 1)
            if cid in data[gid] and emoji in data[gid][cid]:
                data[gid][cid].remove(emoji)
                removed.append(emoji)
                if not data[gid][cid]:
                    del data[gid][cid]
        save_auto_reaction_data(data)
        await interaction.response.edit_message(content=f"以下の自動リアクションを解除しました: {' '.join(removed)}", view=None)


class AutoReactionRemoveView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120)
        self.add_item(AutoReactionRemoveSelect(options))


# =========================================================
# INVITE CAMPAIGN
# =========================================================

class InviteCampaignView(discord.ui.View):
    def __init__(self, cog, campaign_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.campaign_id = campaign_id
        self.create_link.custom_id = f"invite_create_{campaign_id}"
        self.participants.custom_id = f"invite_participants_{campaign_id}"
        self.ranking.custom_id = f"invite_ranking_{campaign_id}"

    @discord.ui.button(label="🔗 招待リンク作成", style=discord.ButtonStyle.primary)
    async def create_link(self, interaction, button):
        data = load_invite_campaign_data()
        campaign = data.get(self.campaign_id)
        if not campaign or not campaign.get("active"):
            await interaction.response.send_message("このキャンペーンは終了しています。", ephemeral=True); return
        user_links = campaign.setdefault("user_links", {})
        uid = str(interaction.user.id)
        if uid in user_links:
            invite_url = user_links[uid]
        else:
            try:
                target_channel = interaction.guild.get_channel(campaign["channel_id"])
                if not isinstance(target_channel, discord.TextChannel):
                    target_channel = interaction.channel
                invite = await target_channel.create_invite(max_age=0, max_uses=0, unique=True, reason=f"Invite campaign {self.campaign_id} by {interaction.user}")
                invite_url = invite.url
                user_links[uid] = invite_url
                campaign.setdefault("invite_map", {})[invite.code] = uid
                save_invite_campaign_data(data)
            except discord.HTTPException as e:
                await interaction.response.send_message(f"招待リンクの作成に失敗しました: {e}", ephemeral=True); return
        await interaction.response.send_message(f"あなた専用の招待リンクです。\n\n{invite_url}", ephemeral=True)

    @discord.ui.button(label="👤 現在の参加人数", style=discord.ButtonStyle.secondary)
    async def participants(self, interaction, button):
        data = load_invite_campaign_data()
        campaign = data.get(self.campaign_id)
        if not campaign:
            await interaction.response.send_message("キャンペーンが見つかりません。", ephemeral=True); return
        uid = str(interaction.user.id)
        counts = campaign.get("counts", {})
        my_count = counts.get(uid, 0)
        total_joins = campaign.get("total_joins", 0)
        max_count = max(counts.values()) if counts else 0
        needed = max(0, max_count - my_count + 1) if max_count > 0 else 0
        embed = discord.Embed(title="あなたの招待状況", color=discord.Color.blurple())
        embed.add_field(name="招待した人数", value=f"{my_count}人", inline=False)
        embed.add_field(name="現在の参加人数", value=f"{total_joins}人", inline=False)
        embed.add_field(name="1位になるまでの招待数", value=f"{needed}回", inline=False)
        embed.set_footer(text="有効条件: 招待された人がサーバーに現在も在籍していること")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🏆 ランキング", style=discord.ButtonStyle.success)
    async def ranking(self, interaction, button):
        data = load_invite_campaign_data()
        campaign = data.get(self.campaign_id)
        if not campaign:
            await interaction.response.send_message("キャンペーンが見つかりません。", ephemeral=True); return
        counts = campaign.get("counts", {})
        if not counts:
            await interaction.response.send_message("まだ招待実績がありません。", ephemeral=True); return
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        lines = []
        for i, (uid, cnt) in enumerate(sorted_counts[:10], start=1):
            member = interaction.guild.get_member(int(uid))
            name = member.mention if member else f"<@{uid}>"
            lines.append(f"{i}位 - {name} {cnt}回")
        embed = discord.Embed(title="🏆 招待ランキング", description="\n".join(lines), color=discord.Color.gold())
        uid = str(interaction.user.id)
        my_count = counts.get(uid, 0)
        my_rank = 0
        for i, (u, c) in enumerate(sorted_counts, start=1):
            if u == uid:
                my_rank = i; break
        if my_rank > 0:
            member = interaction.guild.get_member(int(uid))
            name = member.mention if member else f"<@{uid}>"
            embed.add_field(name="自分の成績", value=f"{my_rank}位 - {name} {my_count}回", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class InviteCampaignStopSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="停止するキャンペーンを選択", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_invite_campaign_data()
        cid = self.values[0]
        campaign = data.get(cid)
        if not campaign:
            await interaction.response.edit_message(content="キャンペーンが見つかりません。", view=None); return
        campaign["active"] = False
        save_invite_campaign_data(data)
        await interaction.response.edit_message(content=f"キャンペーン「{campaign.get('title', cid)}」を停止しました。", view=None)


class InviteCampaignStopView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120)
        self.add_item(InviteCampaignStopSelect(options))


# =========================================================
# PERIODIC MESSAGE
# =========================================================

class PeriodicMessageModal(discord.ui.Modal):
    def __init__(self, cog, channel: discord.TextChannel):
        super().__init__(title="定期メッセージ設定")
        self.cog = cog
        self.channel = channel
        self.text_input = discord.ui.TextInput(label="送信するテキスト", style=discord.TextStyle.paragraph, required=True, max_length=2000)
        self.interval_input = discord.ui.TextInput(label="送信間隔（例: 1m, 1h, 1d, 1w）", placeholder="1m / 1h / 1d / 1w", required=True, max_length=20)
        self.image_input = discord.ui.TextInput(label="画像URL（任意）", required=False, max_length=500)
        self.add_item(self.text_input)
        self.add_item(self.interval_input)
        self.add_item(self.image_input)

    async def on_submit(self, interaction):
        try:
            seconds = parse_duration(self.interval_input.value.strip())
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True); return
        pm_id = uuid.uuid4().hex[:10]
        data = load_periodic_message_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid][pm_id] = {
            "id": pm_id, "channel_id": self.channel.id,
            "text": self.text_input.value, "interval": seconds,
            "image_url": self.image_input.value.strip() or None,
            "last_sent": 0, "active": True
        }
        save_periodic_message_data(data)
        await interaction.response.send_message(
            f"定期メッセージを設定しました。\nチャンネル: {self.channel.mention}\n間隔: {self.interval_input.value.strip()}",
            ephemeral=True
        )


class PeriodicMessageRemoveSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="解除する定期メッセージを選択", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_periodic_message_data()
        gid = str(interaction.guild.id)
        pid = self.values[0]
        if gid in data and pid in data[gid]:
            data[gid][pid]["active"] = False
            save_periodic_message_data(data)
            await interaction.response.edit_message(content="定期メッセージを解除しました。", view=None)
        else:
            await interaction.response.edit_message(content="設定が見つかりません。", view=None)


class PeriodicMessageRemoveView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120)
        self.add_item(PeriodicMessageRemoveSelect(options))


# =========================================================
# MEDIATION
# =========================================================

def build_mediation_settings_embed(guild, data):
    role_ids = data.get("role_ids", [])
    member_ids = data.get("member_ids", [])
    roles_text = "\n".join(f"<@&{rid}>" for rid in role_ids) if role_ids else "設定なし"
    members_text = "\n".join(f"<@{uid}>" for uid in member_ids) if member_ids else "設定なし"
    return discord.Embed(
        title="仲介設定",
        description=f"サーバー名: {guild.name} ({guild.id})\n仲介ロール・仲介メンバーを設定できます。",
        color=discord.Color.blurple()
    ).add_field(name="仲介ロール", value=roles_text, inline=False).add_field(name="仲介メンバー", value=members_text, inline=False)


def build_mediation_channel_embed(guild, data):
    request_category_id = data.get("request_category_id")
    counter_id = data.get("counter_channel_id")
    counter_enabled = data.get("counter_enabled", False)
    counter_count = data.get("counter_count", 0)
    category_text = f"<#{request_category_id}>" if request_category_id else "設定なし"
    counter_text = f"<#{counter_id}>" if counter_id else "設定なし"
    embed = discord.Embed(
        title="仲介詳細設定",
        description=(f"サーバー名: {guild.name} ({guild.id})\n下のドロップダウン（検索可）から仲介依頼のチケット作成カテゴリーを設定できます。"),
        color=discord.Color.blurple()
    )
    embed.add_field(name="仲介依頼のチケット作成カテゴリー", value=category_text, inline=False)
    embed.add_field(name="実績カウントチャンネル", value=counter_text, inline=False)
    embed.add_field(name="カウント", value=f"する（現在: -{counter_count}）" if counter_enabled else "しない", inline=False)
    return embed


class MediationRoleSelect(discord.ui.RoleSelect):
    def __init__(self, cog):
        super().__init__(placeholder="🔍 仲介ロールを選択（検索・複数選択可能）", min_values=0, max_values=25, custom_id="mediation_role_select")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid]["role_ids"] = [r.id for r in self.values]
        save_mediation_data(data)
        embed = build_mediation_settings_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class MediationMemberSelect(discord.ui.UserSelect):
    def __init__(self, cog):
        super().__init__(placeholder="🔍 仲介メンバーを選択（検索・複数選択可能）", min_values=0, max_values=25, custom_id="mediation_member_select")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid]["member_ids"] = [u.id for u in self.values]
        save_mediation_data(data)
        embed = build_mediation_settings_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class MediationSettingsView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(MediationRoleSelect(cog))
        self.add_item(MediationMemberSelect(cog))


class MediationRequestCategorySelect(discord.ui.ChannelSelect):
    def __init__(self, cog):
        super().__init__(placeholder="🔎 仲介依頼のチケット作成カテゴリーを選択（検索できます）", channel_types=[discord.ChannelType.category], min_values=1, max_values=1, custom_id="mediation_request_category_select")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid]["request_category_id"] = self.values[0].id
        save_mediation_data(data)
        embed = build_mediation_channel_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class MediationCounterChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, cog):
        super().__init__(placeholder="🔎 実績カウントチャンネルを選択（検索できます）", channel_types=[discord.ChannelType.text], min_values=1, max_values=1, custom_id="mediation_counter_channel_select")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid]["counter_channel_id"] = self.values[0].id
        save_mediation_data(data)
        embed = build_mediation_channel_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class MediationCounterToggleButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="カウントする/しない 切替", style=discord.ButtonStyle.primary, custom_id="mediation_counter_toggle")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid]["counter_enabled"] = not data[gid].get("counter_enabled", False)
        if "counter_count" not in data[gid]:
            data[gid]["counter_count"] = 0
        save_mediation_data(data)
        embed = build_mediation_channel_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class MediationChannelSettingView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(MediationRequestCategorySelect(cog))
        self.add_item(MediationCounterChannelSelect(cog))
        self.add_item(MediationCounterToggleButton(cog))


class MediationRequestPanelView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.request_button.custom_id = f"mediation_request_{panel_id}"
        self.reserve_check_button.custom_id = f"mediation_reserve_check_{panel_id}"
        self.reserve_cancel_button.custom_id = f"mediation_reserve_cancel_{panel_id}"

    @discord.ui.button(label="仲介依頼", style=discord.ButtonStyle.success, emoji="🤝", custom_id="mediation_request_default")
    async def request_button(self, interaction, button):
        view = MediationStartMethodView(self.cog, self.panel_id)
        await interaction.response.send_message("開始方法を選択してください", view=view, ephemeral=True)

    @discord.ui.button(label="予約確認", style=discord.ButtonStyle.primary, emoji="📅", custom_id="mediation_reserve_check_default")
    async def reserve_check_button(self, interaction, button):
        await self.cog.show_mediation_reservations(interaction)

    @discord.ui.button(label="予約キャンセル", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="mediation_reserve_cancel_default")
    async def reserve_cancel_button(self, interaction, button):
        await self.cog.cancel_mediation_reservation(interaction)


class MediationStartMethodSelect(discord.ui.Select):
    def __init__(self, cog, panel_id):
        options = [
            discord.SelectOption(label="⚡今すぐ始める", value="now", description="すぐに仲介依頼を開始します"),
            discord.SelectOption(label="⏰時間指定（予約）", value="reserve", description="日時を指定して予約します"),
        ]
        super().__init__(placeholder="開始方法を選択してください", options=options, custom_id="mediation_start_method_select")
        self.cog = cog
        self.panel_id = panel_id

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "now":
            view = MediationPartnerSelectView(self.cog, self.panel_id, None)
            await interaction.response.edit_message(content="取引相手を選択してください（検索可能）", view=view)
        else:
            view = MediationPartnerSelectView(self.cog, self.panel_id, None, reserve=True)
            await interaction.response.edit_message(content="取引相手を選択してください（検索可能）", view=view)


class MediationStartMethodView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.add_item(MediationStartMethodSelect(cog, panel_id))


class MediationPartnerSelect(discord.ui.UserSelect):
    def __init__(self, cog, panel_id, reserve):
        super().__init__(placeholder="🔍 取引相手を選択（検索可能）", min_values=1, max_values=1, custom_id="mediation_partner_select")
        self.cog = cog
        self.panel_id = panel_id
        self.reserve = reserve

    async def callback(self, interaction: discord.Interaction):
        partner = self.values[0]
        view = MediationTradeTypeView(self.cog, self.panel_id, partner.id, self.reserve)
        await interaction.response.edit_message(content=f"取引相手: {partner.mention}\n取引内容を選択してください。", view=view)


class MediationPartnerSelectView(discord.ui.View):
    def __init__(self, cog, panel_id, partner_id, reserve=False):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.reserve = reserve
        self.add_item(MediationPartnerSelect(cog, panel_id, reserve))


class MediationTradeTypeView(discord.ui.View):
    def __init__(self, cog, panel_id, partner_id, reserve):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.reserve = reserve

    @discord.ui.button(label="💰売買", style=discord.ButtonStyle.success, custom_id="mediation_trade_buy")
    async def trade_buy(self, interaction, button):
        modal = MediationTradeDetailModal(self.cog, self.panel_id, self.partner_id, "売買", self.reserve)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔄️交換", style=discord.ButtonStyle.primary, custom_id="mediation_trade_exchange")
    async def trade_exchange(self, interaction, button):
        modal = MediationTradeDetailModal(self.cog, self.panel_id, self.partner_id, "交換", self.reserve)
        await interaction.response.send_modal(modal)


class MediationTradeDetailModal(discord.ui.Modal):
    def __init__(self, cog, panel_id, partner_id, trade_type, reserve):
        super().__init__(title=f"取引内容（{trade_type}）")
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.trade_type = trade_type
        self.reserve = reserve
        self.content_input = discord.ui.TextInput(label="取引内容", placeholder="取引の内容を入力してください", style=discord.TextStyle.paragraph, required=True, max_length=500)
        self.my_item_input = discord.ui.TextInput(label="自分の出す内容", required=True, max_length=300)
        self.partner_item_input = discord.ui.TextInput(label="相手を出す内容", required=True, max_length=300)
        self.add_item(self.content_input)
        self.add_item(self.my_item_input)
        self.add_item(self.partner_item_input)

    async def on_submit(self, interaction):
        view = MediationMediatorChoiceView(
            self.cog, self.panel_id, self.partner_id, self.trade_type,
            self.content_input.value, self.my_item_input.value, self.partner_item_input.value, self.reserve
        )
        await interaction.response.send_message("仲介人を指定しますか？", view=view, ephemeral=True)


class MediationMediatorChoiceView(discord.ui.View):
    def __init__(self, cog, panel_id, partner_id, trade_type, content, my_item, partner_item, reserve):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.trade_type = trade_type
        self.content = content
        self.my_item = my_item
        self.partner_item = partner_item
        self.reserve = reserve

    @discord.ui.button(label="指定する", style=discord.ButtonStyle.success, custom_id="mediation_mediator_yes")
    async def yes(self, interaction, button):
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        role_ids = g.get("role_ids", [])
        member_ids = g.get("member_ids", [])
        options = []
        seen = set()
        for rid in role_ids:
            role = interaction.guild.get_role(rid)
            if not role:
                continue
            for m in role.members:
                if m.id in seen:
                    continue
                seen.add(m.id)
                options.append(discord.SelectOption(label=m.display_name[:100], value=str(m.id)))
        for uid in member_ids:
            if uid in seen:
                continue
            m = interaction.guild.get_member(uid)
            if not m:
                continue
            seen.add(m.id)
            options.append(discord.SelectOption(label=m.display_name[:100], value=str(m.id)))
        if not options:
            await interaction.response.send_message("仲介できるメンバーが見つかりません。", ephemeral=True); return
        view = MediationMediatorSelectView(
            self.cog, self.panel_id, self.partner_id, self.trade_type,
            self.content, self.my_item, self.partner_item, self.reserve, options[:25]
        )
        await interaction.response.edit_message(content="仲介人を選択してください。", view=view)

    @discord.ui.button(label="指定しない", style=discord.ButtonStyle.secondary, custom_id="mediation_mediator_no")
    async def no(self, interaction, button):
        await self._create_ticket(interaction, None)

    async def _create_ticket(self, interaction, mediator_id):
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        request_category_id = g.get("request_category_id")
        if not request_category_id:
            await interaction.response.send_message("仲介依頼のチケット作成カテゴリーが設定されていません。", ephemeral=True); return
        category = interaction.guild.get_channel(request_category_id)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("チケット作成カテゴリーが見つかりません。", ephemeral=True); return
        if self.reserve:
            modal = MediationReserveTimeModal(
                self.cog, self.panel_id, self.partner_id, self.trade_type,
                self.content, self.my_item, self.partner_item, mediator_id
            )
            await interaction.response.send_modal(modal); return
        await self.cog.create_mediation_ticket(
            interaction.guild, interaction.user, self.partner_id, mediator_id,
            self.trade_type, self.content, self.my_item, self.partner_item, category
        )
        await interaction.response.send_message("仲介依頼チケットを作成しました。", ephemeral=True)


class MediationMediatorSelect(discord.ui.Select):
    def __init__(self, cog, panel_id, partner_id, trade_type, content, my_item, partner_item, reserve, options):
        super().__init__(placeholder="🔍 仲介人を選択（検索可能）", options=options, custom_id="mediation_mediator_select")
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.trade_type = trade_type
        self.content = content
        self.my_item = my_item
        self.partner_item = partner_item
        self.reserve = reserve

    async def callback(self, interaction: discord.Interaction):
        mediator_id = int(self.values[0])
        view = MediationMediatorConfirmView(
            self.cog, self.panel_id, self.partner_id, self.trade_type,
            self.content, self.my_item, self.partner_item, self.reserve, mediator_id
        )
        await interaction.response.edit_message(content=f"仲介人: <@{mediator_id}>\nこの内容でチケットを作成しますか？", view=view)


class MediationMediatorSelectView(discord.ui.View):
    def __init__(self, cog, panel_id, partner_id, trade_type, content, my_item, partner_item, reserve, options):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.trade_type = trade_type
        self.content = content
        self.my_item = my_item
        self.partner_item = partner_item
        self.reserve = reserve
        self.add_item(MediationMediatorSelect(cog, panel_id, partner_id, trade_type, content, my_item, partner_item, reserve, options))


class MediationMediatorConfirmView(discord.ui.View):
    def __init__(self, cog, panel_id, partner_id, trade_type, content, my_item, partner_item, reserve, mediator_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.trade_type = trade_type
        self.content = content
        self.my_item = my_item
        self.partner_item = partner_item
        self.reserve = reserve
        self.mediator_id = mediator_id

    @discord.ui.button(label="作成", style=discord.ButtonStyle.success, custom_id="mediation_confirm_create")
    async def create(self, interaction, button): await self._create(interaction)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary, custom_id="mediation_confirm_cancel")
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content="キャンセルしました。", view=None)

    async def _create(self, interaction):
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        request_category_id = g.get("request_category_id")
        if not request_category_id:
            await interaction.response.send_message("仲介依頼のチケット作成カテゴリーが設定されていません。", ephemeral=True); return
        category = interaction.guild.get_channel(request_category_id)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("チケット作成カテゴリーが見つかりません。", ephemeral=True); return
        if self.reserve:
            modal = MediationReserveTimeModal(
                self.cog, self.panel_id, self.partner_id, self.trade_type,
                self.content, self.my_item, self.partner_item, self.mediator_id
            )
            await interaction.response.send_modal(modal); return
        await self.cog.create_mediation_ticket(
            interaction.guild, interaction.user, self.partner_id, self.mediator_id,
            self.trade_type, self.content, self.my_item, self.partner_item, category
        )
        await interaction.response.send_message("仲介依頼チケットを作成しました。", ephemeral=True)


class MediationReserveTimeModal(discord.ui.Modal):
    def __init__(self, cog, panel_id, partner_id, trade_type, content, my_item, partner_item, mediator_id):
        super().__init__(title="予約時間の指定")
        self.cog = cog
        self.panel_id = panel_id
        self.partner_id = partner_id
        self.trade_type = trade_type
        self.content = content
        self.my_item = my_item
        self.partner_item = partner_item
        self.mediator_id = mediator_id
        self.time_input = discord.ui.TextInput(label="予約時間（例: 2026-10-15 21:00）", placeholder="YYYY-MM-DD HH:MM (JST)", required=True, max_length=30)
        self.add_item(self.time_input)

    async def on_submit(self, interaction):
        try:
            jst = pytz.timezone("Asia/Tokyo")
            dt = datetime.datetime.strptime(self.time_input.value.strip(), "%Y-%m-%d %H:%M")
            dt = jst.localize(dt)
            timestamp = int(dt.timestamp())
        except Exception:
            await interaction.response.send_message("時間の形式が正しくありません。例: 2026-10-15 21:00", ephemeral=True); return
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        reservations = data[gid].setdefault("reservations", [])
        res_id = uuid.uuid4().hex[:10]
        reservations.append({
            "id": res_id, "guild_id": interaction.guild.id,
            "requester_id": interaction.user.id, "partner_id": self.partner_id,
            "mediator_id": self.mediator_id, "trade_type": self.trade_type,
            "content": self.content, "my_item": self.my_item, "partner_item": self.partner_item,
            "timestamp": timestamp, "channel_id": data[gid].get("request_category_id"),
        })
        save_mediation_data(data)
        self.cog.schedule_mediation_reservation(res_id, timestamp)
        await interaction.response.send_message(
            f"予約を受け付けました。\n指定時刻: <t:{timestamp}:F> (<t:{timestamp}:R>)", ephemeral=True
        )


def build_mediation_ticket_embed(guild, requester_id, partner_id, mediator_id, trade_type, content, my_item, partner_item, embed_title, embed_description, status="進行中"):
    embed = discord.Embed(
        title=embed_title or "🤝 仲介依頼",
        description=embed_description or "仲介依頼が作成されました。",
        color=discord.Color.blurple()
    )
    embed.add_field(name="仲介依頼者", value=f"<@{requester_id}>", inline=True)
    embed.add_field(name="取引相手", value=f"<@{partner_id}>", inline=True)
    if mediator_id:
        embed.add_field(name="仲介者", value=f"<@{mediator_id}>", inline=True)
    else:
        embed.add_field(name="仲介者", value="未指定（仲介ロールをメンション）", inline=True)
    embed.add_field(name="取引内容", value=trade_type, inline=True)
    embed.add_field(name="内容", value=content or "なし", inline=False)
    embed.add_field(name="自分の出す内容", value=my_item or "なし", inline=False)
    embed.add_field(name="相手を出す内容", value=partner_item or "なし", inline=False)
    embed.add_field(name="ステータス", value=status, inline=False)
    return embed


class MediationTicketControlView(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.ticket_id = ticket_id
        self.abort_button.custom_id = f"med_abort_{ticket_id}"
        self.support_button.custom_id = f"med_support_{ticket_id}"
        self.complete_button.custom_id = f"med_complete_{ticket_id}"

    @discord.ui.button(label="仲介依頼中断", style=discord.ButtonStyle.danger, emoji="⛔", custom_id="med_abort_default")
    async def abort_button(self, interaction, button):
        ticket = self.cog.mediation_tickets.get(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True); return
        if interaction.user.id not in self.cog.get_mediation_staff_ids(interaction.guild, ticket):
            await interaction.response.send_message("仲介人のみ実行できます。", ephemeral=True); return
        await interaction.response.send_message("中断処理を開始します。", ephemeral=True)
        requester = ticket["requester_id"]
        partner = ticket["partner_id"]
        await interaction.channel.send(
            f"<@{requester}> <@{partner}>\n5分後にこの仲介依頼は中断されます。",
            view=MediationResumeView(self.cog, self.ticket_id)
        )

        async def abort_after():
            await asyncio.sleep(300)
            t = self.cog.mediation_tickets.get(self.ticket_id)
            if not t or t.get("resumed"):
                return
            try:
                await interaction.channel.delete(reason="仲介依頼中断")
            except discord.HTTPException:
                pass
            self.cog.mediation_tickets.pop(self.ticket_id, None)

        asyncio.create_task(abort_after())

    @discord.ui.button(label="仲介対応", style=discord.ButtonStyle.primary, emoji="🤝", custom_id="med_support_default")
    async def support_button(self, interaction, button):
        ticket = self.cog.mediation_tickets.get(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True); return
        if interaction.user.id not in self.cog.get_mediation_staff_ids(interaction.guild, ticket):
            await interaction.response.send_message("仲介人のみ実行できます。", ephemeral=True); return
        await interaction.response.send_message("対応を開始しました。", ephemeral=True)
        ticket["supported_by"] = interaction.user.id
        guild = interaction.guild
        channel = interaction.channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
        }
        requester = guild.get_member(ticket["requester_id"])
        if requester:
            overwrites[requester] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        partner = guild.get_member(ticket["partner_id"])
        if partner:
            overwrites[partner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        try:
            await channel.edit(overwrites=overwrites)
        except discord.HTTPException:
            pass
        await interaction.channel.send(f"{interaction.user.mention} が対応を開始します🤝🥳")

    @discord.ui.button(label="対応完了", style=discord.ButtonStyle.success, emoji="✅", custom_id="med_complete_default")
    async def complete_button(self, interaction, button):
        ticket = self.cog.mediation_tickets.get(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True); return
        if interaction.user.id not in self.cog.get_mediation_staff_ids(interaction.guild, ticket):
            await interaction.response.send_message("仲介人のみ実行できます。", ephemeral=True); return
        requester = ticket["requester_id"]
        partner = ticket["partner_id"]
        mediator = ticket.get("supported_by") or ticket.get("mediator_id")
        embed = discord.Embed(
            title="仲介が完了しました。",
            description=(f"仲介者 <@{mediator}>" if mediator else "仲介者 未指定"),
            color=discord.Color.green()
        )
        embed.add_field(
            name="",
            value=("ご利用ありがとうございました、\n↓下の**評価する**から仲介人の評価をお願い致します。"),
            inline=False
        )
        await interaction.response.send_message("完了処理を実行しました。", ephemeral=True)
        await interaction.channel.send(
            content=f"<@{requester}> <@{partner}>",
            embed=embed,
            view=MediationReviewStartView(self.cog, self.ticket_id)
        )
        ticket["status"] = "完了"


class MediationResumeView(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.ticket_id = ticket_id
        self.resume_button.custom_id = f"med_resume_{ticket_id}"

    @discord.ui.button(label="依頼を再開する", style=discord.ButtonStyle.success, custom_id="med_resume_default")
    async def resume_button(self, interaction, button):
        ticket = self.cog.mediation_tickets.get(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True); return
        ticket["resumed"] = True
        await interaction.response.send_message("依頼を再開しました。", ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass


class MediationReviewStartView(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.ticket_id = ticket_id
        self.review_button.custom_id = f"med_review_{ticket_id}"
        self.end_button.custom_id = f"med_end_{ticket_id}"

    @discord.ui.button(label="評価する", style=discord.ButtonStyle.primary, emoji="⭐", custom_id="med_review_default")
    async def review_button(self, interaction, button):
        ticket = self.cog.mediation_tickets.get(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True); return
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        role_ids = g.get("role_ids", [])
        member_ids = g.get("member_ids", [])
        options = []
        seen = set()
        for rid in role_ids:
            role = interaction.guild.get_role(rid)
            if not role:
                continue
            for m in role.members:
                if m.id in seen:
                    continue
                seen.add(m.id)
                options.append(discord.SelectOption(label=m.display_name[:100], value=str(m.id)))
        for uid in member_ids:
            if uid in seen:
                continue
            m = interaction.guild.get_member(uid)
            if not m:
                continue
            seen.add(m.id)
            options.append(discord.SelectOption(label=m.display_name[:100], value=str(m.id)))
        if not options:
            await interaction.response.send_message("評価できる仲介者が見つかりません。", ephemeral=True); return
        view = MediationReviewMediatorSelectView(self.cog, self.ticket_id, options[:25])
        await interaction.response.send_message("仲介者を選んでください。", view=view, ephemeral=True)

    @discord.ui.button(label="仲介依頼を終了する", style=discord.ButtonStyle.danger, emoji="🔚", custom_id="med_end_default")
    async def end_button(self, interaction, button):
        ticket = self.cog.mediation_tickets.get(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True); return
        supported_by = ticket.get("supported_by")
        if not supported_by or interaction.user.id != supported_by:
            await interaction.response.send_message("仲介対応した人のみ実行できます。", ephemeral=True); return
        await interaction.response.send_message("5秒以内に削除します。", ephemeral=True)

        async def delete_later():
            await asyncio.sleep(5)
            try:
                await interaction.channel.delete(reason="仲介依頼終了")
            except discord.HTTPException:
                pass
            self.cog.mediation_tickets.pop(self.ticket_id, None)

        asyncio.create_task(delete_later())


class MediationReviewMediatorSelect(discord.ui.Select):
    def __init__(self, cog, ticket_id, options):
        super().__init__(placeholder="仲介者を選択", options=options, custom_id="med_review_mediator_select")
        self.cog = cog
        self.ticket_id = ticket_id

    async def callback(self, interaction: discord.Interaction):
        mediator_id = int(self.values[0])
        modal = MediationReviewModal(self.cog, self.ticket_id, mediator_id)
        await interaction.response.send_modal(modal)


class MediationReviewMediatorSelectView(discord.ui.View):
    def __init__(self, cog, ticket_id, options):
        super().__init__(timeout=300)
        self.cog = cog
        self.ticket_id = ticket_id
        self.add_item(MediationReviewMediatorSelect(cog, ticket_id, options))


class MediationReviewModal(discord.ui.Modal):
    def __init__(self, cog, ticket_id, mediator_id):
        super().__init__(title="仲介実績レビュー")
        self.cog = cog
        self.ticket_id = ticket_id
        self.mediator_id = mediator_id
        self.rating_input = discord.ui.TextInput(label="評価（1〜5）", placeholder="5", required=True, max_length=1)
        self.review_input = discord.ui.TextInput(label="レビュー", style=discord.TextStyle.paragraph, required=True, max_length=1000)
        self.add_item(self.rating_input)
        self.add_item(self.review_input)

    async def on_submit(self, interaction):
        try:
            rating = int(self.rating_input.value.strip())
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("評価は1〜5の数字で入力してください。", ephemeral=True); return
        ticket = self.cog.mediation_tickets.get(self.ticket_id)
        if not ticket:
            await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True); return
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        counter_id = g.get("counter_channel_id")
        embed = discord.Embed(title="🤝 仲介実績レビュー", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="仲介依頼者", value=f"<@{ticket['requester_id']}>", inline=True)
        embed.add_field(name="仲介者", value=f"<@{self.mediator_id}>", inline=True)
        embed.add_field(name="評価", value=f"{'⭐' * rating} {rating}/5", inline=False)
        embed.add_field(name="レビュー", value=self.review_input.value, inline=False)
        embed.set_footer(text=f"Review by {interaction.user.display_name} / ID: {interaction.user.id}")
        if counter_id:
            counter = interaction.guild.get_channel(counter_id)
            if isinstance(counter, discord.TextChannel):
                try:
                    await counter.send(embed=embed)
                except discord.HTTPException:
                    pass
                if g.get("counter_enabled"):
                    count = g.get("counter_count", 0) + 1
                    g["counter_count"] = count
                    save_mediation_data(data)
                    try:
                        await counter.edit(name=f"{counter.name.split(' -')[0]} -{count}")
                    except discord.HTTPException:
                        pass
        await interaction.response.send_message("レビューを送信しました。", ephemeral=True)


class MediationReservationCancelSelect(discord.ui.Select):
    def __init__(self, cog, options):
        super().__init__(placeholder="キャンセルする予約を選択", options=options, custom_id="mediation_reservation_cancel_select")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        res_id = self.values[0]
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        reservations = g.get("reservations", [])
        target = None
        for r in reservations:
            if r.get("id") == res_id:
                target = r; break
        if not target:
            await interaction.response.edit_message(content="予約が見つかりません。", view=None); return
        is_staff = interaction.user.id in self.cog.get_mediation_staff_ids(interaction.guild, {})
        if not is_staff and target.get("requester_id") != interaction.user.id:
            await interaction.response.edit_message(content="この予約をキャンセルする権限がありません。", view=None); return
        g["reservations"] = [r for r in reservations if r.get("id") != res_id]
        save_mediation_data(data)
        self.cog.mediation_reservation_tasks.pop(res_id, None)
        await interaction.response.edit_message(content=f"予約ID `{res_id}` をキャンセルしました。", view=None)


class MediationReservationCancelView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=120)
        self.cog = cog
        self.add_item(MediationReservationCancelSelect(cog, options))


# =========================================================
# MAIN COG
# =========================================================

class SlashCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        self.ended_giveaways = {}
        self.vouch_panels = {}
        self.status_panels = load_status_panel_data()
        self.ticket_panels = load_ticket_panel_data()
        self.periodic_tasks = {}
        self.invite_cache = {}
        self.mediation_tickets = {}
        self.mediation_reservation_tasks = {}

    async def cog_load(self):
        data = load_periodic_message_data()
        for gid, items in data.items():
            for pid, info in items.items():
                if info.get("active"):
                    self._start_periodic_task(gid, pid, info)
        med = load_mediation_data()
        for gid, g in med.items():
            for r in g.get("reservations", []):
                self.schedule_mediation_reservation(r["id"], r["timestamp"])

    async def refresh_status(self, panel):
        channel = self.bot.get_channel(panel["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            message = await channel.fetch_message(panel["message_id"])
            await message.edit(embed=status_embed(channel.guild, panel["staff"]))
        except discord.HTTPException:
            pass

    def _start_periodic_task(self, gid, pid, info):
        key = f"{gid}:{pid}"
        if key in self.periodic_tasks:
            return

        async def runner():
            while True:
                data = load_periodic_message_data()
                cur = data.get(gid, {}).get(pid)
                if not cur or not cur.get("active"):
                    break
                interval = cur["interval"]
                now = time.time()
                last = cur.get("last_sent", 0)
                wait = max(1, interval - (now - last))
                await asyncio.sleep(wait)
                data = load_periodic_message_data()
                cur = data.get(gid, {}).get(pid)
                if not cur or not cur.get("active"):
                    break
                channel = self.bot.get_channel(int(cur["channel_id"]))
                if isinstance(channel, discord.TextChannel):
                    try:
                        if cur.get("image_url"):
                            embed = discord.Embed(description=cur["text"])
                            embed.set_image(url=cur["image_url"])
                            await channel.send(embed=embed)
                        else:
                            await channel.send(cur["text"])
                    except discord.HTTPException:
                        pass
                cur["last_sent"] = time.time()
                data[gid][pid] = cur
                save_periodic_message_data(data)
            self.periodic_tasks.pop(key, None)

        task = asyncio.create_task(runner())
        self.periodic_tasks[key] = task

    def get_mediation_staff_ids(self, guild, ticket):
        if ticket.get("mediator_id"):
            return {ticket["mediator_id"]}
        data = load_mediation_data()
        g = data.get(str(guild.id), {})
        ids = set(g.get("member_ids", []))
        for rid in g.get("role_ids", []):
            role = guild.get_role(rid)
            if role:
                for m in role.members:
                    ids.add(m.id)
        return ids

    async def create_mediation_ticket(self, guild, requester, partner_id, mediator_id, trade_type, content, my_item, partner_item, category):
        ticket_id = uuid.uuid4().hex[:10]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            requester: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
        }
        partner = guild.get_member(partner_id)
        if partner:
            overwrites[partner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        if mediator_id:
            mediator = guild.get_member(mediator_id)
            if mediator:
                overwrites[mediator] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        else:
            data = load_mediation_data()
            g = data.get(str(guild.id), {})
            for rid in g.get("role_ids", []):
                role = guild.get_role(rid)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        try:
            ticket_channel = await guild.create_text_channel(
                name=f"mediation-{requester.name}"[:100], category=category,
                overwrites=overwrites, topic=f"mediation_ticket:{ticket_id}"
            )
        except discord.HTTPException:
            return None
        data = load_mediation_data()
        g = data.get(str(guild.id), {})
        embed = build_mediation_ticket_embed(
            guild, requester.id, partner_id, mediator_id,
            trade_type, content, my_item, partner_item,
            g.get("ticket_embed_title"), g.get("ticket_embed_description")
        )
        mention_text = f"{requester.mention} <@{partner_id}>"
        if mediator_id:
            mention_text += f" <@{mediator_id}>"
        else:
            for rid in g.get("role_ids", []):
                role = guild.get_role(rid)
                if role:
                    mention_text += f" {role.mention}"
        view = MediationTicketControlView(self, ticket_id)
        message = await ticket_channel.send(content=mention_text, embed=embed, view=view)
        self.mediation_tickets[ticket_id] = {
            "id": ticket_id, "guild_id": guild.id,
            "channel_id": ticket_channel.id, "message_id": message.id,
            "requester_id": requester.id, "partner_id": partner_id,
            "mediator_id": mediator_id, "trade_type": trade_type,
            "content": content, "my_item": my_item, "partner_item": partner_item,
            "status": "進行中", "resumed": False, "supported_by": None,
        }
        return ticket_channel

    def schedule_mediation_reservation(self, res_id, timestamp):
        if res_id in self.mediation_reservation_tasks:
            return

        async def runner():
            wait = max(1, timestamp - time.time())
            await asyncio.sleep(wait)
            data = load_mediation_data()
            target = None
            for g, gdata in data.items():
                for r in gdata.get("reservations", []):
                    if r["id"] == res_id:
                        target = r; break
                if target:
                    break
            if not target:
                self.mediation_reservation_tasks.pop(res_id, None); return
            guild = self.bot.get_guild(target["guild_id"])
            if not guild:
                self.mediation_reservation_tasks.pop(res_id, None); return
            category_id = target.get("channel_id")
            category = guild.get_channel(category_id) if category_id else None
            if not isinstance(category, discord.CategoryChannel):
                self.mediation_reservation_tasks.pop(res_id, None); return
            requester = guild.get_member(target["requester_id"])
            if not requester:
                self.mediation_reservation_tasks.pop(res_id, None); return
            await self.create_mediation_ticket(
                guild, requester, target["partner_id"], target.get("mediator_id"),
                target["trade_type"], target["content"], target["my_item"], target["partner_item"], category
            )
            data = load_mediation_data()
            for g, gdata in data.items():
                gdata["reservations"] = [r for r in gdata.get("reservations", []) if r["id"] != res_id]
            save_mediation_data(data)
            self.mediation_reservation_tasks.pop(res_id, None)

        task = asyncio.create_task(runner())
        self.mediation_reservation_tasks[res_id] = task

    async def show_mediation_reservations(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        reservations = g.get("reservations", [])
        if not reservations:
            return await interaction.response.send_message("予約はありません。", ephemeral=True)
        is_staff = interaction.user.id in self.get_mediation_staff_ids(interaction.guild, {})
        targets = reservations if is_staff else [r for r in reservations if r.get("requester_id") == interaction.user.id]
        if not targets:
            return await interaction.response.send_message("あなたの予約はありません。", ephemeral=True)
        embed = discord.Embed(title="📅 仲介予約一覧", color=discord.Color.blurple())
        for r in targets[:25]:
            ts = r.get("timestamp", 0)
            partner = f"<@{r.get('partner_id')}>" if r.get("partner_id") else "未設定"
            mediator = f"<@{r.get('mediator_id')}>" if r.get("mediator_id") else "未指定"
            embed.add_field(
                name=f"予約ID: {r.get('id', '不明')}",
                value=(
                    f"依頼者: <@{r.get('requester_id')}>\n"
                    f"取引相手: {partner}\n"
                    f"仲介者: {mediator}\n"
                    f"取引内容: {r.get('trade_type', '不明')}\n"
                    f"予定時刻: <t:{ts}:F> (<t:{ts}:R>)\n"
                    f"内容: {r.get('content', '')[:100]}"
                ),
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cancel_mediation_reservation(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        g = data.get(gid, {})
        reservations = g.get("reservations", [])
        if not reservations:
            return await interaction.response.send_message("予約はありません。", ephemeral=True)
        is_staff = interaction.user.id in self.get_mediation_staff_ids(interaction.guild, {})
        targets = reservations if is_staff else [r for r in reservations if r.get("requester_id") == interaction.user.id]
        if not targets:
            return await interaction.response.send_message("キャンセルできる予約がありません。", ephemeral=True)
        options = []
        for r in targets[:25]:
            ts = r.get("timestamp", 0)
            options.append(discord.SelectOption(
                label=f"予約ID: {r.get('id', '不明')}"[:100],
                description=f"<t:{ts}:F> / 相手: <@{r.get('partner_id')}>"[:100],
                value=r.get("id")
            ))
        view = MediationReservationCancelView(self, options)
        await interaction.response.send_message("キャンセルする予約を選択してください。", view=view, ephemeral=True)

    # -----------------------------------------------------
    # /nuke
    # -----------------------------------------------------

    @app_commands.command(name="nuke", description="現在のテキストチャンネルを再作成します")
    async def nuke(self, interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルで使用してください。", ephemeral=True); return
        await interaction.response.send_message("本当にこのチャンネルを再作成しますか？", view=ConfirmNukeView(interaction.channel), ephemeral=True)

    # -----------------------------------------------------
    # /ロック
    # -----------------------------------------------------

    @app_commands.command(name="ロック", description="チャンネルをロックします")
    @app_commands.describe(role="任意：@everyone以外に送信を禁止するロール（省略時は@everyoneのみ）")
    async def lock(self, interaction: discord.Interaction, role: discord.Role = None):
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルで使用してください。", ephemeral=True); return
        channel = interaction.channel
        overwrites = channel.overwrites
        everyone_ow = overwrites.get(interaction.guild.default_role) or discord.PermissionOverwrite()
        everyone_ow.send_messages = False
        everyone_ow.create_public_threads = False
        everyone_ow.create_private_threads = False
        overwrites[interaction.guild.default_role] = everyone_ow
        if role is not None and not role.is_default():
            role_ow = overwrites.get(role) or discord.PermissionOverwrite()
            role_ow.send_messages = False
            role_ow.create_public_threads = False
            role_ow.create_private_threads = False
            overwrites[role] = role_ow
        try:
            await channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            await interaction.response.send_message("Botにチャンネル管理権限がありません。", ephemeral=True); return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"ロックに失敗しました: {e}", ephemeral=True); return
        embed = discord.Embed(
            description=(f"⚠️ {interaction.user.mention} : {channel.mention} をロックしました。\n`/アンロック` でチャンネルをアンロックできます"),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    # -----------------------------------------------------
    # /アンロック
    # -----------------------------------------------------

    @app_commands.command(name="アンロック", description="チャンネルのロックを解除します")
    @app_commands.describe(role="任意：@everyone以外に解除するロール（省略時は@everyoneのみ）")
    async def unlock(self, interaction: discord.Interaction, role: discord.Role = None):
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルで使用してください。", ephemeral=True); return
        channel = interaction.channel
        overwrites = channel.overwrites
        everyone_ow = overwrites.get(interaction.guild.default_role) or discord.PermissionOverwrite()
        everyone_ow.send_messages = None
        everyone_ow.create_public_threads = None
        everyone_ow.create_private_threads = None
        overwrites[interaction.guild.default_role] = everyone_ow
        if role is not None and not role.is_default():
            role_ow = overwrites.get(role) or discord.PermissionOverwrite()
            role_ow.send_messages = None
            role_ow.create_public_threads = None
            role_ow.create_private_threads = None
            overwrites[role] = role_ow
        try:
            await channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            await interaction.response.send_message("Botにチャンネル管理権限がありません。", ephemeral=True); return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"アンロックに失敗しました: {e}", ephemeral=True); return
        embed = discord.Embed(
            description=(f"✅ {interaction.user.mention} : {channel.mention} をアンロックしました。\n再び `/ロック` でチャンネルをロックできます"),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    # -----------------------------------------------------
    # /ロール付与
    # -----------------------------------------------------

    @app_commands.command(name="ロール付与", description="指定したユーザーまたは全員にロールを付与します")
    @app_commands.describe(role="付与するロール", target="付与対象（省略時は全員）")
    async def role_grant(self, interaction: discord.Interaction, role: discord.Role, target: discord.Member = None):
        if not interaction.guild:
            await interaction.response.send_message("サーバー内で使用してください。", ephemeral=True); return
        if role.is_default() or role.managed:
            await interaction.response.send_message("このロールは付与できません。", ephemeral=True); return
        await interaction.response.defer(ephemeral=True)
        if target is not None:
            targets = [target]
        else:
            targets = [m for m in interaction.guild.members if not m.bot and role not in m.roles]
        success = 0
        failed = 0
        for member in targets:
            try:
                await member.add_roles(role, reason=f"/ロール付与 by {interaction.user}")
                success += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1
        if target is not None:
            msg = f"{target.mention} に {role.mention} を付与しました。"
        else:
            msg = f"{role.mention} を {success}人 に付与しました。"
            if failed:
                msg += f"（失敗: {failed}人）"
        await interaction.followup.send(msg, ephemeral=True)

    # -----------------------------------------------------
    # /配布作成
    # -----------------------------------------------------

    @app_commands.command(name="配布作成", description="景品の配布を作成し、同時に開始します")
    @app_commands.describe(prize="景品名", duration="配布期間（例: 30m、1h、1d、1week）", winners="当選人数")
    async def giveaway_create(self, interaction, prize: str, duration: str, winners: app_commands.Range[int, 1, 20] = 1):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルで使用してください。", ephemeral=True); return
        try:
            seconds = parse_duration(duration)
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True); return
        giveaway_id = uuid.uuid4().hex[:12]
        end_time = int(time.time() + seconds)
        view = GiveawayView(self, giveaway_id, prize, winners, end_time)
        await interaction.response.send_message(f"配布「{prize}」を開始しました。期間: {duration}", ephemeral=True)
        message = await interaction.channel.send(embed=view.make_embed(), view=view)
        view.message = message
        self.active_giveaways[message.id] = view

        async def finish():
            try:
                await asyncio.sleep(seconds)
                if view.ended:
                    return
                view.ended = True
                await view.refresh()
                ids = list(view.participants)
                if ids:
                    chosen = random.sample(ids, min(view.winner_count, len(ids)))
                    view.winners = chosen
                    result = f"🎉 **{view.prize}** の配布が終了しました！\n当選者: {' '.join(f'<@{uid}>' for uid in chosen)}"
                else:
                    view.winners = []
                    result = f"**{view.prize}** の配布が終了しました。参加者はいませんでした。"
                try:
                    await view.message.channel.send(result)
                except discord.HTTPException:
                    pass
            except asyncio.CancelledError:
                pass
            except discord.HTTPException:
                pass
            finally:
                self.active_giveaways.pop(message.id, None)
                self.ended_giveaways[message.id] = view

        asyncio.create_task(finish())

    @app_commands.command(name="配布終了", description="開催中の配布を選択して即座に終了し、当選者を発表します")
    async def giveaway_stop(self, interaction):
        guild_giveaways = {}
        for mid, view in self.active_giveaways.items():
            if view.message and view.message.guild and view.message.guild.id == interaction.guild_id and not view.ended and not view.cancelled:
                guild_giveaways[mid] = view
        if not guild_giveaways:
            await interaction.response.send_message("開催中の配布が見つかりません。", ephemeral=True); return
        options = []
        for mid, view in list(guild_giveaways.items())[:25]:
            options.append(discord.SelectOption(
                label=f"{view.prize[:50]}",
                description=f"ID: {mid} / 参加者: {len(view.participants)}人",
                value=str(mid)
            ))
        view = StopGiveawayView(self, options)
        await interaction.response.send_message("終了する配布を選択してください。", view=view, ephemeral=True)

    @app_commands.command(name="配布再抽選", description="終了した配布を選択して当選者を再抽選します")
    async def giveaway_redraw(self, interaction):
        guild_giveaways = {}
        for mid, view in self.ended_giveaways.items():
            if view.message and view.message.guild and view.message.guild.id == interaction.guild_id and not view.cancelled:
                guild_giveaways[mid] = view
        if not guild_giveaways:
            await interaction.response.send_message("再抽選できる配布が見つかりません。", ephemeral=True); return
        options = []
        for mid, view in list(guild_giveaways.items())[:25]:
            options.append(discord.SelectOption(
                label=f"{view.prize[:50]}",
                description=f"ID: {mid} / 参加者: {len(view.participants)}人",
                value=str(mid)
            ))
        view = RedrawGiveawayView(self, options)
        await interaction.response.send_message("再抽選する配布を選択してください。", view=view, ephemeral=True)

    @app_commands.command(name="埋め込み送信", description="埋め込みメッセージを送信します（画像はファイル選択）")
    @app_commands.describe(title="埋め込みのタイトル", description="埋め込みの説明", color="色（例: ff0000、00ff00）", footer="フッター", image="画像ファイル（自分のPCから選択）")
    async def embed(self, interaction, title: str, description: str, color: str = None, footer: str = None, image: discord.Attachment = None):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルで使用してください。", ephemeral=True); return
        embed = discord.Embed(title=title, description=description, color=parse_color(color) or discord.Color.blurple())
        if footer:
            embed.set_footer(text=footer)
        file = None
        if image:
            file = await image.to_file()
            embed.set_image(url=f"attachment://{image.filename}")
        await interaction.response.send_message("埋め込みを送信しました。", ephemeral=True)
        if file:
            await interaction.channel.send(embed=embed, file=file)
        else:
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="dm送信", description="指定したユーザーにDMを送信します")
    @app_commands.describe(user="送信先のユーザー", message="送信するメッセージ")
    async def dm_anc(self, interaction, user: discord.User, message: str):
        try:
            await user.send(message)
        except discord.Forbidden:
            await interaction.response.send_message("このユーザーにはDMを送信できません（DMを拒否している可能性があります）。", ephemeral=True); return
        except discord.HTTPException:
            await interaction.response.send_message("DMの送信に失敗しました。", ephemeral=True); return
        await interaction.response.send_message(f"{user.mention} にDMを送信しました。", ephemeral=True)

    @app_commands.command(name="認証パネル", description="認証パネルを作成します")
    @app_commands.describe(type="認証方法（計算認証 or ボタン認証）", title="パネルのタイトル（任意）", description="パネルの説明（任意）", role="認証後に付与するロール（省略時は選択メニュー）")
    @app_commands.choices(type=[
        app_commands.Choice(name="計算認証", value="math"),
        app_commands.Choice(name="ボタン認証", value="button")
    ])
    async def verify(self, interaction, type: app_commands.Choice[str] = None, title: str = "認証", description: str = "下のボタンから認証してください。", role: discord.Role = None):
        if not interaction.guild:
            await interaction.response.send_message("サーバー内で使用してください。", ephemeral=True); return
        verify_type = type.value if type else "button"
        if role is not None:
            if role.is_default() or role.managed:
                await interaction.response.send_message("このロールは設定できません。", ephemeral=True); return
            view = VerifyView(self, role, verify_type)
            embed = build_verify_embed(title, description, role, interaction.guild_id)
            await interaction.response.send_message("認証パネルを作成しました。", ephemeral=True)
            await interaction.channel.send(embed=embed, view=view)
            return
        roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed and not r.is_premium_subscriber()]
        if not roles:
            await interaction.response.send_message("設定できるロールがありません。", ephemeral=True); return
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]
        view = VerifyRoleSelectView(self, verify_type, title, description)
        view.role_select.options = options
        await interaction.response.send_message("認証後に付与するロールを選択してください。", view=view, ephemeral=True)

    @app_commands.command(name="実績パネル", description="実績送信パネルを作成します")
    @app_commands.describe(destination="実績を送信するチャンネル", title="パネルタイトル", description="パネル説明", counter_channel="任意：実績数を表示するチャンネル")
    async def vouch_panel(self, interaction, destination: discord.TextChannel, title: str, description: str, counter_channel: discord.TextChannel = None):
        panel_id = uuid.uuid4().hex[:10]
        self.vouch_panels[panel_id] = {
            "destination_id": destination.id, "title": title, "description": description,
            "count": 0, "counter_id": counter_channel.id if counter_channel else None,
            "counter_base_name": (counter_channel.name if counter_channel else None)
        }
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        embed.set_footer(text=f"Vouch Panel: {panel_id}")
        view = VouchView(self, panel_id)
        await interaction.response.send_message("実績パネルを作成しました。", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="対応状況", description="対応状況パネルを表示します")
    @app_commands.describe(description="パネルの説明（任意）")
    async def status(self, interaction: discord.Interaction, description: str = "現在の対応状況です。"):
        if not interaction.guild:
            await interaction.response.send_message("サーバー内で使用してください。", ephemeral=True); return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルで使用してください。", ephemeral=True); return
        panel_id = uuid.uuid4().hex[:10]
        staff_data = load_status_staff_data()
        gid = str(interaction.guild.id)
        staff_ids = staff_data.get(gid, [])
        staff_list = []
        for uid in staff_ids:
            member = interaction.guild.get_member(uid)
            if not member:
                continue
            staff_list.append({"user_id": uid, "status": "対応可能", "emoji": "🟢", "message": ""})
        panel = {
            "id": panel_id, "creator_id": interaction.user.id,
            "description": description, "channel_id": interaction.channel.id,
            "message_id": None, "staff": staff_list,
        }
        view = StatusSelectView(self, panel_id)
        panel_message = await interaction.channel.send(embed=status_embed(interaction.guild, staff_list), view=view)
        panel["message_id"] = panel_message.id
        self.status_panels[panel_id] = panel
        data = load_status_panel_data()
        data[panel_id] = panel
        save_status_panel_data(data)
        await interaction.response.send_message("ステータスパネルを作成しました。", ephemeral=True)

    @app_commands.command(name="対応状況スタッフ追加", description="対応状況パネルに表示するスタッフを追加します")
    @app_commands.describe(user="追加するスタッフ")
    async def status_staff_add(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.guild:
            await interaction.response.send_message("サーバー内で使用してください。", ephemeral=True); return
        data = load_status_staff_data()
        gid = str(interaction.guild.id)
        staff_ids = data.get(gid, [])
        if user.id in staff_ids:
            await interaction.response.send_message(f"{user.mention} は既にスタッフとして登録されています。", ephemeral=True); return
        staff_ids.append(user.id)
        data[gid] = staff_ids
        save_status_staff_data(data)
        for panel in self.status_panels.values():
            if panel.get("channel_id") and interaction.guild.get_channel(panel["channel_id"]):
                if not any(s["user_id"] == user.id for s in panel["staff"]):
                    panel["staff"].append({"user_id": user.id, "status": "対応可能", "emoji": "🟢", "message": ""})
                    await self.refresh_status(panel)
        await interaction.response.send_message(f"{user.mention} を対応状況スタッフに追加しました。", ephemeral=True)

    @app_commands.command(name="対応状況スタッフ削除", description="対応状況パネルからスタッフを削除します")
    @app_commands.describe(user="削除するスタッフ")
    async def status_staff_remove(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.guild:
            await interaction.response.send_message("サーバー内で使用してください。", ephemeral=True); return
        data = load_status_staff_data()
        gid = str(interaction.guild.id)
        staff_ids = data.get(gid, [])
        if user.id not in staff_ids:
            await interaction.response.send_message(f"{user.mention} はスタッフとして登録されていません。", ephemeral=True); return
        staff_ids.remove(user.id)
        data[gid] = staff_ids
        save_status_staff_data(data)
        for panel in self.status_panels.values():
            panel["staff"] = [s for s in panel["staff"] if s["user_id"] != user.id]
            await self.refresh_status(panel)
        await interaction.response.send_message(f"{user.mention} を対応状況スタッフから削除しました。", ephemeral=True)

    # -----------------------------------------------------
    # /チケット（即時パネル表示 / 下書き永続化）
    # -----------------------------------------------------

    @app_commands.command(name="チケット", description="チケット設定パネルを表示します（前回の設定を引き継ぎます）")
    async def ticket(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("サーバー内で使用してください。", ephemeral=True); return

        settings = get_guild_draft(interaction.guild.id)
        view = TicketSettingsView(self, interaction.user.id, interaction.guild.id, settings)
        embed = build_ticket_settings_embed(view.settings)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="チケットパネル編集", description="既存のチケットパネルを編集します")
    async def ticket_edit(self, interaction):
        guild_panels = {pid: panel for pid, panel in self.ticket_panels.items() if panel.get("channel_id")}
        if not guild_panels:
            await interaction.response.send_message("編集できるチケットパネルがありません。", ephemeral=True); return
        options = []
        for pid, panel in list(guild_panels.items())[:25]:
            options.append(discord.SelectOption(
                label=f"{panel.get('panel_title', panel.get('button_label', 'パネル'))[:50]}",
                description=f"ID: {pid}",
                value=pid
            ))
        view = TicketEditSelectView(self, options)
        await interaction.response.send_message("編集するチケットパネルを選択してください。", view=view, ephemeral=True)

    @app_commands.command(name="入室退出通知", description="メンバーの入室・退室通知を設定します")
    async def member_log(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_member_log_data()
        gid = str(interaction.guild.id)
        entry = data.get(gid, {})
        embed = build_member_log_embed(interaction.guild.id, entry.get("join_channel_id"), entry.get("leave_channel_id"))
        view = MemberLogSettingView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="荒らし対策", description="荒らし対策の設定を行います")
    async def antiraid(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False, "ignore_user_ids": [], "ignore_role_ids": []}
            save_antiraid_data(data)
        embed = build_antiraid_embed(interaction.guild, data[gid])
        view = AntiraidSettingView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="固定メッセージ", description="固定メッセージを設定します")
    @app_commands.describe(channel="対象チャンネル", text="固定メッセージ本文")
    async def fixed_message(self, interaction: discord.Interaction, channel: discord.TextChannel, text: str):
        await interaction.response.defer(ephemeral=True)
        formatted = f"__**Stickied Message:**__\n\n{text}"
        data = load_fixed_message_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        old = data[gid].get(str(channel.id))
        if old and old.get("message_id"):
            old_channel = interaction.guild.get_channel(old["channel_id"])
            if isinstance(old_channel, discord.TextChannel):
                try:
                    old_msg = await old_channel.fetch_message(old["message_id"])
                    await old_msg.delete()
                except discord.HTTPException:
                    pass
        data[gid][str(channel.id)] = {"channel_id": channel.id, "text": formatted, "message_id": None, "last_trigger_user_id": None}
        save_fixed_message_data(data)
        try:
            msg = await channel.send(formatted)
            data[gid][str(channel.id)]["message_id"] = msg.id
            save_fixed_message_data(data)
        except discord.HTTPException as e:
            await interaction.followup.send(f"送信に失敗しました: {e}", ephemeral=True); return
        await interaction.followup.send(
            "固定メッセージを設定しました。\nこのチャンネルにメッセージが送信されると、Botが自動で固定メッセージを投稿します。",
            ephemeral=True
        )

    @app_commands.command(name="固定メッセージ解除", description="固定メッセージを解除します")
    async def fixed_message_remove(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_fixed_message_data()
        gid = str(interaction.guild.id)
        if gid not in data or not data[gid]:
            return await interaction.response.send_message("固定メッセージが設定されていません。", ephemeral=True)
        options = []
        for cid, info in list(data[gid].items())[:25]:
            channel = interaction.guild.get_channel(int(cid))
            ch_name = channel.name if channel else cid
            preview = info["text"][:50] + ("..." if len(info["text"]) > 50 else "")
            options.append(discord.SelectOption(label=f"#{ch_name}: {preview}", value=cid))
        view = FixedMessageRemoveView(options)
        await interaction.response.send_message("解除する固定メッセージを選択してください。", view=view, ephemeral=True)

    @app_commands.command(name="自動リアクション", description="指定チャンネルのメッセージに自動でリアクションします")
    async def auto_reaction(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_auto_reaction_data()
        gid = str(interaction.guild.id)
        guild_data = data.get(gid, {})
        embed = build_auto_reaction_embed(interaction.guild, guild_data)
        view = AutoReactionSettingView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="自動リアクション解除", description="自動リアクションを解除します")
    async def auto_reaction_remove(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_auto_reaction_data()
        gid = str(interaction.guild.id)
        if gid not in data or not data[gid]:
            return await interaction.response.send_message("自動リアクションが設定されていません。", ephemeral=True)
        options = []
        for cid, emojis in data[gid].items():
            channel = interaction.guild.get_channel(int(cid))
            ch_name = channel.name if channel else cid
            for e in emojis:
                options.append(discord.SelectOption(label=f"#{ch_name} : {e}", value=f"{cid}:{e}"))
        if not options:
            return await interaction.response.send_message("解除できるリアクションがありません。", ephemeral=True)
        view = AutoReactionRemoveView(options)
        await interaction.response.send_message("解除する絵文字を選択してください（複数可）。", view=view, ephemeral=True)

    @app_commands.command(name="ロール付与パネル", description="リアクションでロールを付与するパネルを作成します")
    @app_commands.describe(
        role1="1つ目のロール", emoji1="1つ目のロールの絵文字",
        role2="2つ目のロール（任意）", emoji2="2つ目のロールの絵文字（任意）",
        role3="3つ目のロール（任意）", emoji3="3つ目のロールの絵文字（任意）",
        role4="4つ目のロール（任意）", emoji4="4つ目のロールの絵文字（任意）",
        role5="5つ目のロール（任意）", emoji5="5つ目のロールの絵文字（任意）",
        role6="6つ目のロール（任意）", emoji6="6つ目のロールの絵文字（任意）",
        title="パネルのタイトル（任意）", description="パネルの説明（任意）",
    )
    async def role_panel(
        self, interaction: discord.Interaction,
        role1: discord.Role, emoji1: str,
        role2: discord.Role = None, emoji2: str = None,
        role3: discord.Role = None, emoji3: str = None,
        role4: discord.Role = None, emoji4: str = None,
        role5: discord.Role = None, emoji5: str = None,
        role6: discord.Role = None, emoji6: str = None,
        title: str = "ロール付与パネル",
        description: str = "以下のリアクションからロールを受け取ってください",
    ):
        if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("テキストチャンネルで使用してください。", ephemeral=True)
        pairs = []
        for role, emoji in [(role1, emoji1), (role2, emoji2), (role3, emoji3), (role4, emoji4), (role5, emoji5), (role6, emoji6)]:
            if role and emoji:
                if role.is_default() or role.managed:
                    continue
                pairs.append({"role_id": role.id, "emoji": emoji})
        if not pairs:
            return await interaction.response.send_message("有効なロールと絵文字の組み合わせがありません。", ephemeral=True)
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        lines = []
        for p in pairs:
            role = interaction.guild.get_role(p["role_id"])
            if role:
                lines.append(f"{p['emoji']} → {role.mention}")
        embed.add_field(name="リアクション一覧", value="\n".join(lines) if lines else "設定なし", inline=False)
        embed.set_footer(text="もう一度押すとロールが外れます / Developer @anzy1m")
        await interaction.response.send_message("パネルを作成しました。", ephemeral=True)
        message = await interaction.channel.send(embed=embed)
        for p in pairs:
            try:
                await message.add_reaction(p["emoji"])
            except Exception as e:
                print(f"リアクション付与失敗: {e}")
        data = load_role_panel_data()
        data[str(message.id)] = {"guild_id": interaction.guild.id, "pairs": pairs}
        save_role_panel_data(data)

    @app_commands.command(name="招待キャンペーン", description="招待キャンペーンを作成します")
    @app_commands.describe(duration="キャンペーン期間（例: 1d, 1w）", title="キャンペーンタイトル", description="キャンペーン説明")
    async def invite_campaign(self, interaction: discord.Interaction, duration: str, title: str, description: str):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        try:
            seconds = parse_duration(duration)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
        campaign_id = uuid.uuid4().hex[:10]
        end_time = int(time.time() + seconds)
        data = load_invite_campaign_data()
        data[campaign_id] = {
            "id": campaign_id, "guild_id": interaction.guild.id, "channel_id": interaction.channel.id,
            "title": title, "description": description, "end_time": end_time, "active": True,
            "user_links": {}, "invite_map": {}, "counts": {}, "total_joins": 0, "join_members": []
        }
        save_invite_campaign_data(data)
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        embed.add_field(name="期間", value=f"<t:{end_time}:R>", inline=False)
        view = InviteCampaignView(self, campaign_id)
        await interaction.response.send_message("キャンペーンを作成しました。", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

        async def finish():
            await asyncio.sleep(seconds)
            d = load_invite_campaign_data()
            c = d.get(campaign_id)
            if not c or not c.get("active"):
                return
            c["active"] = False
            save_invite_campaign_data(d)

        asyncio.create_task(finish())

    @app_commands.command(name="招待キャンペーン停止", description="招待キャンペーンを停止します")
    async def invite_campaign_stop(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_invite_campaign_data()
        options = []
        for cid, c in data.items():
            if c.get("guild_id") == interaction.guild.id and c.get("active"):
                options.append(discord.SelectOption(label=c.get("title", cid)[:100], value=cid))
        if not options:
            return await interaction.response.send_message("停止できるキャンペーンがありません。", ephemeral=True)
        view = InviteCampaignStopView(options)
        await interaction.response.send_message("停止するキャンペーンを選択してください。", view=view, ephemeral=True)

    @app_commands.command(name="定期メッセージ送信", description="指定したチャンネルに定期的にメッセージを送信します")
    @app_commands.describe(channel="送信先チャンネル", text="送信するテキスト", interval="送信間隔（例: 1m, 1h, 1d, 1w）", image_url="画像URL（任意）")
    async def periodic_message(self, interaction: discord.Interaction, channel: discord.TextChannel, text: str, interval: str, image_url: str = None):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        try:
            seconds = parse_duration(interval)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
        pm_id = uuid.uuid4().hex[:10]
        data = load_periodic_message_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid][pm_id] = {
            "id": pm_id, "channel_id": channel.id, "text": text, "interval": seconds,
            "image_url": image_url, "last_sent": 0, "active": True
        }
        save_periodic_message_data(data)
        self._start_periodic_task(gid, pm_id, data[gid][pm_id])
        await interaction.response.send_message(
            f"定期メッセージを設定しました。\nチャンネル: {channel.mention}\n間隔: {interval}", ephemeral=True
        )

    @app_commands.command(name="定期メッセージ送信解除", description="定期メッセージを解除します")
    async def periodic_message_remove(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_periodic_message_data()
        gid = str(interaction.guild.id)
        if gid not in data or not data[gid]:
            return await interaction.response.send_message("定期メッセージが設定されていません。", ephemeral=True)
        options = []
        for pid, info in data[gid].items():
            if info.get("active"):
                channel = interaction.guild.get_channel(info["channel_id"])
                ch_name = channel.name if channel else str(info["channel_id"])
                options.append(discord.SelectOption(label=f"#{ch_name}: {info['text'][:50]}", value=pid))
        if not options:
            return await interaction.response.send_message("解除できる定期メッセージがありません。", ephemeral=True)
        view = PeriodicMessageRemoveView(options)
        await interaction.response.send_message("解除する定期メッセージを選択してください。", view=view, ephemeral=True)

    @app_commands.command(name="定期メッセージ送信確認", description="設定済みの定期メッセージを確認します")
    async def periodic_message_check(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_periodic_message_data()
        gid = str(interaction.guild.id)
        items = data.get(gid, {})
        active_items = {k: v for k, v in items.items() if v.get("active")}
        if not active_items:
            return await interaction.response.send_message("設定済みの定期メッセージはありません。", ephemeral=True)
        embed = discord.Embed(title="定期メッセージ一覧", color=discord.Color.blurple())
        for pid, info in active_items.items():
            channel = interaction.guild.get_channel(info["channel_id"])
            ch_name = channel.mention if channel else f"<#{info['channel_id']}>"
            embed.add_field(
                name=f"ID: {pid} / {ch_name}",
                value=(f"間隔: {info['interval']}秒\nテキスト: {info['text'][:100]}\n画像: {info.get('image_url') or 'なし'}"),
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="仲介依頼パネル作成", description="仲介依頼パネルを作成します")
    @app_commands.describe(title="パネルのタイトル", description="パネルの説明")
    async def mediation_request_panel(self, interaction: discord.Interaction, title: str, description: str):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        panel_id = uuid.uuid4().hex[:10]
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        embed.add_field(name="使い方", value="下の 仲介依頼 ボタンから、今すぐ依頼または時間指定予約を選べます。", inline=False)
        embed.set_footer(text="仲介依頼ボタンから依頼できます")
        view = MediationRequestPanelView(self, panel_id)
        await interaction.response.send_message("仲介依頼パネルを作成しました。", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="仲介設定", description="仲介ロール・仲介メンバーを設定します")
    async def mediation_settings(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
            save_mediation_data(data)
        embed = build_mediation_settings_embed(interaction.guild, data[gid])
        view = MediationSettingsView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="仲介実績チャンネル", description="仲介実績の送信チャンネル・カウント設定を行います")
    async def mediation_channel(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
            save_mediation_data(data)
        embed = build_mediation_channel_embed(interaction.guild, data[gid])
        view = MediationChannelSettingView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="仲介チケット管理", description="仲介依頼のチケット作成カテゴリーを設定します")
    async def mediation_ticket_manage(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
            save_mediation_data(data)
        embed = build_mediation_channel_embed(interaction.guild, data[gid])
        view = MediationChannelSettingView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="仲介チケット詳細", description="仲介チケットの埋め込みタイトル・説明を設定します")
    @app_commands.describe(title="埋め込みタイトル", description="埋め込み説明")
    async def mediation_ticket_detail(self, interaction: discord.Interaction, title: str, description: str):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        data = load_mediation_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}
        data[gid]["ticket_embed_title"] = title
        data[gid]["ticket_embed_description"] = description
        save_mediation_data(data)
        await interaction.response.send_message("仲介チケットの埋め込みタイトル・説明を保存しました。", ephemeral=True)

    @app_commands.command(name="仲介人追加", description="現在の仲介チケットに仲介人を追加します")
    @app_commands.describe(user="追加する仲介人")
    async def mediation_add_mediator(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("テキストチャンネルで実行してください。", ephemeral=True)
        topic = channel.topic or ""
        if not topic.startswith("mediation_ticket:"):
            return await interaction.response.send_message("このチャンネルは仲介チケットではありません。", ephemeral=True)
        ticket_id = topic.split(":", 1)[1]
        ticket = self.mediation_tickets.get(ticket_id)
        if not ticket:
            return await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True)
        try:
            await channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        except discord.HTTPException:
            return await interaction.response.send_message("権限の付与に失敗しました。", ephemeral=True)
        ticket.setdefault("extra_mediators", [])
        if user.id not in ticket["extra_mediators"]:
            ticket["extra_mediators"].append(user.id)
        await interaction.response.send_message(f"{user.mention} を仲介人として追加しました。", ephemeral=True)

    @app_commands.command(name="仲介人削除", description="現在の仲介チケットから仲介人を削除します")
    @app_commands.describe(user="削除する仲介人")
    async def mediation_remove_mediator(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("テキストチャンネルで実行してください。", ephemeral=True)
        topic = channel.topic or ""
        if not topic.startswith("mediation_ticket:"):
            return await interaction.response.send_message("このチャンネルは仲介チケットではありません。", ephemeral=True)
        ticket_id = topic.split(":", 1)[1]
        ticket = self.mediation_tickets.get(ticket_id)
        if not ticket:
            return await interaction.response.send_message("チケット情報が見つかりません。", ephemeral=True)
        try:
            await channel.set_permissions(user, overwrite=None)
        except discord.HTTPException:
            return await interaction.response.send_message("権限の削除に失敗しました。", ephemeral=True)
        extras = ticket.get("extra_mediators", [])
        if user.id in extras:
            extras.remove(user.id)
        await interaction.response.send_message(f"{user.mention} を仲介人から削除しました。", ephemeral=True)

    # -----------------------------------------------------
    # リアクションイベント
    # -----------------------------------------------------

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        data = load_role_panel_data()
        panel = data.get(str(payload.message_id))
        if not panel:
            return
        if payload.guild_id != panel.get("guild_id"):
            return
        emoji_str = str(payload.emoji)
        target = None
        for p in panel.get("pairs", []):
            if p["emoji"] == emoji_str:
                target = p; break
        if not target:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return
        role = guild.get_role(target["role_id"])
        if not role:
            return
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="ロール付与パネル（解除）")
            else:
                await member.add_roles(role, reason="ロール付与パネル（付与）")
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        data = load_role_panel_data()
        panel = data.get(str(payload.message_id))
        if not panel:
            return
        if payload.guild_id != panel.get("guild_id"):
            return
        emoji_str = str(payload.emoji)
        target = None
        for p in panel.get("pairs", []):
            if p["emoji"] == emoji_str:
                target = p; break
        if not target:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return
        role = guild.get_role(target["role_id"])
        if not role:
            return
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="ロール付与パネル（リアクション解除）")
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    # -----------------------------------------------------
    # 自動リアクション & 荒らし対策 & 固定メッセージ イベント
    # -----------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        data_ar = load_auto_reaction_data()
        gid = str(message.guild.id)
        if gid in data_ar and str(message.channel.id) in data_ar[gid]:
            for emoji in data_ar[gid][str(message.channel.id)]:
                try:
                    await message.add_reaction(emoji)
                except discord.HTTPException:
                    pass
        fixed_data = load_fixed_message_data()
        if gid in fixed_data and str(message.channel.id) in fixed_data[gid]:
            info = fixed_data[gid][str(message.channel.id)]
            if info.get("message_id"):
                try:
                    old_msg = await message.channel.fetch_message(info["message_id"])
                    await old_msg.delete()
                except discord.HTTPException:
                    pass
            try:
                new_msg = await message.channel.send(info["text"])
                info["message_id"] = new_msg.id
                info["last_trigger_user_id"] = message.author.id
                fixed_data[gid][str(message.channel.id)] = info
                save_fixed_message_data(fixed_data)
            except discord.HTTPException:
                pass
        antiraid = load_antiraid_data()
        if gid not in antiraid:
            return
        settings = antiraid[gid]
        if message.author.id in settings.get("ignore_user_ids", []):
            return
        for role in message.author.roles:
            if role.id in settings.get("ignore_role_ids", []):
                return
        if settings.get("link_enabled"):
            if re.search(r"https?://\S+", message.content):
                await self._handle_antiraid_detection(message, "リンク検知しました。", "リンクの送信は禁止されています。")
                return
        if settings.get("spam_enabled"):
            try:
                recent = []
                async for msg in message.channel.history(limit=10, before=message):
                    if msg.author.id == message.author.id:
                        recent.append(msg)
                if len(recent) >= 2:
                    now = message.created_at.timestamp()
                    if now - recent[0].created_at.timestamp() < 3:
                        await self._handle_antiraid_detection(message, "連投スパムを検知しました。", "連投は禁止されています。")
            except discord.HTTPException:
                pass

    async def _handle_antiraid_detection(self, message, title, description):
        try:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            embed = discord.Embed(
                title=f"🚨 {title}",
                description=(
                    f"{message.author.mention}\n\n{description}\n\n"
                    f"**メッセージ内容:**\n```{message.content[:1000]}```"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"User ID: {message.author.id}")
            view = AntiraidPunishView(message.author, f"{title} / メッセージID: {message.id}")
            await message.channel.send(content=message.author.mention, embed=embed, view=view)
        except Exception as e:
            print(f"_handle_antiraid_detection error: {e}")

    # -----------------------------------------------------
    # 入室・退室イベント
    # -----------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            data = load_invite_campaign_data()
            for cid, campaign in data.items():
                if campaign.get("guild_id") != member.guild.id:
                    continue
                if not campaign.get("active"):
                    continue
                try:
                    invites = await member.guild.invites()
                except discord.HTTPException:
                    invites = []
                used_code = None
                for inv in invites:
                    if inv.uses and inv.uses > 0:
                        key = f"{member.guild.id}:{inv.code}"
                        old_uses = self.invite_cache.get(key, 0)
                        if inv.uses > old_uses:
                            used_code = inv.code
                            self.invite_cache[key] = inv.uses
                            break
                if used_code and used_code in campaign.get("invite_map", {}):
                    inviter_id = campaign["invite_map"][used_code]
                    campaign.setdefault("counts", {})
                    campaign["counts"][inviter_id] = campaign["counts"].get(inviter_id, 0) + 1
                    campaign["total_joins"] = campaign.get("total_joins", 0) + 1
                    campaign.setdefault("join_members", []).append(member.id)
                    save_invite_campaign_data(data)
            log_data = load_member_log_data()
            guild_id_str = str(member.guild.id)
            entry = log_data.get(guild_id_str, {})
            channel_id = entry.get("join_channel_id")
            if not channel_id:
                return
            channel = member.guild.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.TextChannel):
                return
            created_str, elapsed_str = format_account_age(member.created_at)
            embed = discord.Embed(
                title="",
                description=(
                    f"{member.mention} がサーバーに参加しました\n\n"
                    f"🕰️ **アカウント作成からの経過:**\n{created_str}\n経過: {elapsed_str}\n\n"
                    f"👥 現在のサーバー人数: {member.guild.member_count}"
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            try:
                embed.set_thumbnail(url=member.display_avatar.url)
            except Exception:
                pass
            embed.set_author(name=f"{member.display_name}", icon_url=member.display_avatar.url if member.display_avatar else None)
            await channel.send(embed=embed)
        except Exception as e:
            print(f"on_member_join error: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            data = load_member_log_data()
            guild_id_str = str(member.guild.id)
            entry = data.get(guild_id_str, {})
            channel_id = entry.get("leave_channel_id")
            if not channel_id:
                return
            channel = member.guild.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.TextChannel):
                return
            created_str, elapsed_str = format_account_age(member.created_at)
            embed = discord.Embed(
                title="",
                description=(
                    f"{member.mention} がサーバーから退出しました\n\n"
                    f"🕰️ **アカウント作成からの経過:**\n{created_str}\n経過: {elapsed_str}\n\n"
                    f"👥 現在のサーバー人数: {member.guild.member_count}"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            try:
                embed.set_thumbnail(url=member.display_avatar.url)
            except Exception:
                pass
            embed.set_author(name=f"{member.display_name}", icon_url=member.display_avatar.url if member.display_avatar else None)
            await channel.send(embed=embed)
        except Exception as e:
            print(f"on_member_remove error: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                for inv in invites:
                    self.invite_cache[f"{guild.id}:{inv.code}"] = inv.uses or 0
            except discord.HTTPException:
                pass


# =========================================================
# EXTENSION SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCog(bot))
