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


def load_member_log_data():
    return load_json(MEMBER_LOG_DATA_FILE)


def save_member_log_data(data):
    save_json(MEMBER_LOG_DATA_FILE, data)


def load_role_panel_data():
    return load_json(ROLE_PANEL_DATA_FILE)


def save_role_panel_data(data):
    save_json(ROLE_PANEL_DATA_FILE, data)


def load_antiraid_data():
    return load_json(ANTIRAID_DATA_FILE)


def save_antiraid_data(data):
    save_json(ANTIRAID_DATA_FILE, data)


def load_fixed_message_data():
    return load_json(FIXED_MESSAGE_DATA_FILE)


def save_fixed_message_data(data):
    save_json(FIXED_MESSAGE_DATA_FILE, data)


def load_auto_reaction_data():
    return load_json(AUTO_REACTION_DATA_FILE)


def save_auto_reaction_data(data):
    save_json(AUTO_REACTION_DATA_FILE, data)


def load_ticket_panel_data():
    return load_json(TICKET_PANEL_DATA_FILE)


def save_ticket_panel_data(data):
    save_json(TICKET_PANEL_DATA_FILE, data)


def load_status_staff_data():
    return load_json(STATUS_STAFF_DATA_FILE)


def save_status_staff_data(data):
    save_json(STATUS_STAFF_DATA_FILE, data)


def load_status_panel_data():
    return load_json(STATUS_PANEL_DATA_FILE)


def save_status_panel_data(data):
    save_json(STATUS_PANEL_DATA_FILE, data)


def load_invite_campaign_data():
    return load_json(INVITE_CAMPAIGN_DATA_FILE)


def save_invite_campaign_data(data):
    save_json(INVITE_CAMPAIGN_DATA_FILE, data)


def load_periodic_message_data():
    return load_json(PERIODIC_MESSAGE_DATA_FILE)


def save_periodic_message_data(data):
    save_json(PERIODIC_MESSAGE_DATA_FILE, data)


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
# NUKE
# =========================================================

class ConfirmNukeView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(
        label="チャンネルを再作成",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction, button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "チャンネル管理権限が必要です。",
                ephemeral=True
            )
            return

        if interaction.channel_id != self.channel.id:
            await interaction.response.send_message(
                "実行対象のチャンネルが異なります。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        old_channel = self.channel

        try:
            new_channel = await old_channel.clone(
                reason=f"Nuke requested by {interaction.user}"
            )

            await new_channel.edit(
                category=old_channel.category,
                position=old_channel.position
            )

            await old_channel.delete(
                reason=f"Nuke requested by {interaction.user}"
            )

            await new_channel.send("**nukeが完了しました。**")

        except discord.Forbidden:
            await interaction.followup.send(
                "Botにチャンネル管理権限がありません。",
                ephemeral=True
            )
        except discord.HTTPException as error:
            await interaction.followup.send(
                f"再作成に失敗しました: {error}",
                ephemeral=True
            )

        self.stop()

    @discord.ui.button(
        label="キャンセル",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(
            content="キャンセルしました。",
            view=None
        )
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
            color = discord.Color.red()
            state = "中止"
        elif self.ended:
            color = discord.Color.dark_grey()
            state = "終了"
        else:
            color = discord.Color.gold()
            state = "開催中"

        end_text = (
            f"<t:{self.end_time}:R>" if self.end_time else "未設定"
        )

        embed = discord.Embed(
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
        return embed

    async def refresh(self):
        if self.message:
            try:
                await self.message.edit(embed=self.make_embed(), view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(
        label="🎉 参加する",
        style=discord.ButtonStyle.success,
        custom_id="gw_join_default"
    )
    async def join_button(self, interaction, button):
        if self.ended or self.cancelled:
            await interaction.response.send_message(
                "この抽選は終了しています。",
                ephemeral=True
            )
            return

        if interaction.user.id in self.participants:
            self.participants.remove(interaction.user.id)
            text = "抽選への参加を取り消しました。"
        else:
            self.participants.add(interaction.user.id)
            text = "抽選に参加しました！"

        await interaction.response.send_message(text, ephemeral=True)
        await self.refresh()

    @discord.ui.button(
        label="👥 参加者リスト",
        style=discord.ButtonStyle.primary,
        custom_id="gw_list_default"
    )
    async def list_button(self, interaction, button):
        ids = sorted(self.participants)

        embed = discord.Embed(
            title="👥 参加者リスト",
            description=(
                "\n".join(f"• <@{uid}>" for uid in ids[:100])
                if ids else "参加者はいません。"
            ),
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="参加人数",
            value=f"{len(ids)}人",
            inline=False
        )

        if len(ids) > 100:
            embed.set_footer(text="最初の100人のみ表示しています。")

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# =========================================================
# GIVEAWAY STOP (配布終了)
# =========================================================

class StopGiveawayView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=60)
        self.cog = cog
        self.select.options = options

    @discord.ui.select(
        placeholder="終了する配布を選択",
        custom_id="giveaway_stop_select"
    )
    async def select(self, interaction, select):
        message_id = int(select.values[0])
        view = self.cog.active_giveaways.get(message_id)

        if not view:
            await interaction.response.edit_message(
                content="配布が見つかりません。既に終了している可能性があります。",
                view=None
            )
            return

        if interaction.guild_id != view.message.guild.id:
            await interaction.response.edit_message(
                content="このサーバーの配布ではありません。",
                view=None
            )
            return

        view.ended = True
        view.stop()
        await view.refresh()

        ids = list(view.participants)
        if ids:
            chosen = random.sample(ids, min(view.winner_count, len(ids)))
            view.winners = chosen
            result = (
                f"🎉 **{view.prize}** の配布が終了しました！\n"
                f"当選者: {' '.join(f'<@{uid}>' for uid in chosen)}"
            )
        else:
            view.winners = []
            result = f"**{view.prize}** の配布が終了しました。参加者はいませんでした。"

        try:
            await view.message.channel.send(result)
        except discord.HTTPException:
            pass

        self.cog.active_giveaways.pop(message_id, None)
        self.cog.ended_giveaways[message_id] = view

        await interaction.response.edit_message(
            content=f"配布「{view.prize}」を終了しました。",
            view=None
        )


# =========================================================
# GIVEAWAY REDRAW (配布再抽選)
# =========================================================

class RedrawGiveawayView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=60)
        self.cog = cog
        self.select.options = options

    @discord.ui.select(
        placeholder="再抽選する配布を選択",
        custom_id="giveaway_redraw_select"
    )
    async def select(self, interaction, select):
        message_id = int(select.values[0])
        view = self.cog.ended_giveaways.get(message_id)

        if not view:
            await interaction.response.edit_message(
                content="配布が見つかりません。",
                view=None
            )
            return

        if interaction.guild_id != view.message.guild.id:
            await interaction.response.edit_message(
                content="このサーバーの配布ではありません。",
                view=None
            )
            return

        ids = list(view.participants)
        if not ids:
            await interaction.response.edit_message(
                content="参加者がいないため、再抽選できません。",
                view=None
            )
            return

        chosen = random.sample(ids, min(view.winner_count, len(ids)))
        view.winners = chosen

        result = (
            f"🎉 **{view.prize}** の再抽選が行われました！\n"
            f"当選者: {' '.join(f'<@{uid}>' for uid in chosen)}"
        )

        try:
            await view.message.channel.send(result)
        except discord.HTTPException:
            pass

        await interaction.response.edit_message(
            content=f"配布「{view.prize}」の再抽選を実行しました。",
            view=None
        )


# =========================================================
# VERIFY
# =========================================================

def build_verify_embed(title: str, description: str, role: discord.Role, guild_id: int):
    embed = discord.Embed(
        title=title,
        description=(
            f"{description}\n\n"
            f"認証後 {role.mention} が付与されます\n"
            f"**{guild_id} | Dev.@anzy1m**"
        ),
        color=discord.Color.blurple()
    )
    return embed


class VerifyMathModal(discord.ui.Modal):
    def __init__(self, cog, role, answer):
        super().__init__(title="計算認証")
        self.cog = cog
        self.role = role
        self.answer = answer

        self.answer_input = discord.ui.TextInput(
            label="答えを入力してください",
            placeholder="半角数字で入力",
            max_length=10,
            required=True
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction):
        if self.answer_input.value.strip() != str(self.answer):
            await interaction.response.send_message(
                "❌ 答えが違います。もう一度お試しください。",
                ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(
                self.role,
                reason="Verify (math)"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "ロールを付与できません。Botの権限を確認してください。",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "ロールの付与に失敗しました。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "✅ 認証が完了しました！",
            ephemeral=True
        )


class VerifyView(discord.ui.View):
    def __init__(self, cog, role, verify_type):
        super().__init__(timeout=None)
        self.cog = cog
        self.role = role
        self.verify_type = verify_type

        self.verify_button.custom_id = f"verify_{role.id}_{verify_type}"
        self.verify_button.label = "認証 ✅"

    @discord.ui.button(
        label="認証 ✅",
        style=discord.ButtonStyle.success,
        custom_id="verify_default"
    )
    async def verify_button(self, interaction, button):
        if self.verify_type == "button":
            try:
                await interaction.user.add_roles(
                    self.role,
                    reason="Verify (button)"
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "ロールを付与できません。Botの権限を確認してください。",
                    ephemeral=True
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "ロールの付与に失敗しました。",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                "✅ 認証が完了しました！",
                ephemeral=True
            )

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

    @discord.ui.select(
        placeholder="認証後に付与するロールを選択",
        custom_id="verify_role_select"
    )
    async def role_select(self, interaction, select):
        role = interaction.guild.get_role(int(select.values[0]))
        if not role:
            await interaction.response.edit_message(
                content="ロールが見つかりません。",
                view=None
            )
            return

        view = VerifyView(self.cog, role, self.verify_type)
        embed = build_verify_embed(
            self.title, self.description, role, interaction.guild_id
        )

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.edit_message(
            content=f"✅ 認証パネルを作成しました（ロール: {role.mention}）",
            view=None
        )


# =========================================================
# TICKET (対話式セットアップ)
# =========================================================

class TicketSetupModeView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "このセットアップは実行者本人のみ操作できます。",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="1ボタン式（シンプル）",
        style=discord.ButtonStyle.primary,
        emoji="🎫"
    )
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

    @discord.ui.button(
        label="複数項目から選ぶ式",
        style=discord.ButtonStyle.success,
        emoji="📋"
    )
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
            "requirements": [{"name": "その他", "description": "", "emoji": "📝"}],
        }

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "このセットアップは実行者本人のみ操作できます。",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="ボタン名を設定", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def set_button_label(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupTextModal(self, "button_label", "ボタン名", "チケット作成ボタンの名前")
        )

    @discord.ui.button(label="カテゴリーを設定", style=discord.ButtonStyle.secondary, emoji="📁")
    async def set_category(self, interaction, button):
        categories = interaction.guild.categories[:25]
        if not categories:
            await interaction.response.send_message("カテゴリーがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in categories]
        await interaction.response.edit_message(
            content="チケットを作成するカテゴリーを選択してください。",
            view=TicketSetupObjectSelectView(self, "category_id", options)
        )

    @discord.ui.button(label="メンションロールを設定", style=discord.ButtonStyle.secondary, emoji="🔔")
    async def set_mention_role(self, interaction, button):
        roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed][:25]
        if not roles:
            await interaction.response.send_message("ロールがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        await interaction.response.edit_message(
            content="チケット作成時にメンションするロールを選択してください。",
            view=TicketSetupObjectSelectView(self, "mention_role_id", options)
        )

    @discord.ui.button(label="最大チケット数を設定", style=discord.ButtonStyle.secondary, emoji="🔢")
    async def set_max_tickets(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupTextModal(self, "max_tickets", "最大チケット数", "1〜10の数字")
        )

    @discord.ui.button(label="削除権限を設定", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def set_delete_permission(self, interaction, button):
        options = [
            discord.SelectOption(label="管理者のみ", value="admin"),
            discord.SelectOption(label="全員", value="everyone"),
        ]
        await interaction.response.edit_message(
            content="チケット削除権限を選択してください。",
            view=TicketSetupObjectSelectView(self, "delete_permission", options)
        )

    @discord.ui.button(label="パネルタイトル/説明を設定", style=discord.ButtonStyle.secondary, emoji="📝")
    async def set_panel_text(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupPanelTextModal(self)
        )

    @discord.ui.button(label="埋め込み設定", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def set_embed(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupEmbedModal(self)
        )

    @discord.ui.button(label="ウェルカムメッセージ", style=discord.ButtonStyle.secondary, emoji="👋")
    async def set_welcome(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupTextModal(self, "welcome_message", "ウェルカムメッセージ", "チケット作成後のメッセージ")
        )

    @discord.ui.button(label="アーカイブチャンネル", style=discord.ButtonStyle.secondary, emoji="📦")
    async def set_archive(self, interaction, button):
        channels = interaction.guild.text_channels[:25]
        if not channels:
            await interaction.response.send_message("テキストチャンネルがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in channels]
        await interaction.response.edit_message(
            content="アーカイブ（削除ログ）チャンネルを選択してください。",
            view=TicketSetupObjectSelectView(self, "archive_channel_id", options)
        )

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
            title="🎫 チケット",
            description=f"下のボタンからチケットを作成できます。\n1人につき最大 {s['max_tickets']} 件まで。",
            color=discord.Color.blurple()
        )

        view = TicketPanelView(self.cog, panel_id)
        view.create_button.label = s["button_label"]

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
            await interaction.response.send_message(
                "このセットアップは実行者本人のみ操作できます。",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="基本設定", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def basic_settings(self, interaction, button):
        await interaction.response.send_message(
            "基本設定を行います。各項目を設定してください。",
            view=TicketSetupMultiBasicView(self),
            ephemeral=True
        )

    @discord.ui.button(label="要件を追加", style=discord.ButtonStyle.success, emoji="➕")
    async def add_requirement(self, interaction, button):
        if len(self.settings["requirements"]) >= 25:
            await interaction.response.send_message("要件は最大25個までです。", ephemeral=True)
            return
        await interaction.response.send_modal(
            TicketRequirementModal(self)
        )

    @discord.ui.button(label="要件を確認", style=discord.ButtonStyle.secondary, emoji="📋")
    async def view_requirements(self, interaction, button):
        reqs = self.settings["requirements"]
        if not reqs:
            await interaction.response.send_message("要件がまだありません。", ephemeral=True)
            return
        lines = [f"{r.get('emoji', '📝')} **{r['name']}** - {r.get('description', '')}" for r in reqs]
        embed = discord.Embed(
            title="登録済みの要件",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )
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
        await interaction.response.edit_message(
            content="削除する要件を選択してください。",
            view=TicketRequirementRemoveView(self, options)
        )

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
            title="🎫 チケット",
            description=f"下のボタンからチケットを作成できます。\n1人につき最大 {s['max_tickets']} 件まで。",
            color=discord.Color.blurple()
        )

        req_lines = []
        for r in s["requirements"]:
            emoji = r.get("emoji", "📝")
            req_lines.append(f"{emoji} **{r['name']}**\n　{r.get('description', '') or '説明なし'}")

        if req_lines:
            embed.add_field(
                name="📋 要件一覧",
                value="\n\n".join(req_lines)[:1024],
                inline=False
            )

        view = TicketPanelView(self.cog, panel_id)
        view.create_button.label = s["button_label"]

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
            await interaction.response.send_message(
                "このセットアップは実行者本人のみ操作できます。",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="ボタン名", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def set_button_label(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupTextModal(self.parent, "button_label", "ボタン名", "チケット作成ボタンの名前")
        )

    @discord.ui.button(label="カテゴリー", style=discord.ButtonStyle.secondary, emoji="📁")
    async def set_category(self, interaction, button):
        categories = interaction.guild.categories[:25]
        if not categories:
            await interaction.response.send_message("カテゴリーがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in categories]
        await interaction.response.edit_message(
            content="カテゴリーを選択してください。",
            view=TicketSetupObjectSelectView(self.parent, "category_id", options, back_view=self)
        )

    @discord.ui.button(label="メンションロール", style=discord.ButtonStyle.secondary, emoji="🔔")
    async def set_mention_role(self, interaction, button):
        roles = [r for r in interaction.guild.roles if not r.is_default() and not r.managed][:25]
        if not roles:
            await interaction.response.send_message("ロールがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        await interaction.response.edit_message(
            content="メンションロールを選択してください。",
            view=TicketSetupObjectSelectView(self.parent, "mention_role_id", options, back_view=self)
        )

    @discord.ui.button(label="最大チケット数", style=discord.ButtonStyle.secondary, emoji="🔢")
    async def set_max_tickets(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupTextModal(self.parent, "max_tickets", "最大チケット数", "1〜10の数字")
        )

    @discord.ui.button(label="削除権限", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def set_delete_permission(self, interaction, button):
        options = [
            discord.SelectOption(label="管理者のみ", value="admin"),
            discord.SelectOption(label="全員", value="everyone"),
        ]
        await interaction.response.edit_message(
            content="削除権限を選択してください。",
            view=TicketSetupObjectSelectView(self.parent, "delete_permission", options, back_view=self)
        )

    @discord.ui.button(label="パネルタイトル/説明", style=discord.ButtonStyle.secondary, emoji="📝")
    async def set_panel_text(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupPanelTextModal(self.parent)
        )

    @discord.ui.button(label="埋め込み設定", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def set_embed(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupEmbedModal(self.parent)
        )

    @discord.ui.button(label="ウェルカムメッセージ", style=discord.ButtonStyle.secondary, emoji="👋")
    async def set_welcome(self, interaction, button):
        await interaction.response.send_modal(
            TicketSetupTextModal(self.parent, "welcome_message", "ウェルカムメッセージ", "チケット作成後のメッセージ")
        )

    @discord.ui.button(label="アーカイブチャンネル", style=discord.ButtonStyle.secondary, emoji="📦")
    async def set_archive(self, interaction, button):
        channels = interaction.guild.text_channels[:25]
        if not channels:
            await interaction.response.send_message("テキストチャンネルがありません。", ephemeral=True)
            return
        options = [discord.SelectOption(label=c.name[:100], value=str(c.id)) for c in channels]
        await interaction.response.edit_message(
            content="アーカイブチャンネルを選択してください。",
            view=TicketSetupObjectSelectView(self.parent, "archive_channel_id", options, back_view=self)
        )

    @discord.ui.button(label="戻る", style=discord.ButtonStyle.primary, emoji="↩️")
    async def back(self, interaction, button):
        await interaction.response.edit_message(
            content=(
                "**複数項目から選ぶ式**の設定画面です。\n"
                "「基本設定」で詳細を、「要件を追加」で項目を追加してください。"
            ),
            view=self.parent
        )


class TicketSetupTextModal(discord.ui.Modal):
    def __init__(self, setup_view, field, label, placeholder):
        super().__init__(title=f"設定: {label}")
        self.setup_view = setup_view
        self.field = field
        self.input = discord.ui.TextInput(
            label=label,
            placeholder=placeholder,
            max_length=1000,
            required=False
        )
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
        self.desc_input = discord.ui.TextInput(
            label="パネル説明", style=discord.TextStyle.paragraph, required=False, max_length=1000
        )
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
        self.desc_input = discord.ui.TextInput(
            label="埋め込み説明", style=discord.TextStyle.paragraph, required=False, max_length=1000
        )
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
        self.desc_input = discord.ui.TextInput(
            label="説明", placeholder="例: 商品の購入について", max_length=200, required=False
        )
        self.emoji_input = discord.ui.TextInput(
            label="絵文字", placeholder="例: 🛒", max_length=10, required=False
        )
        self.placeholder_input = discord.ui.TextInput(
            label="セレクトのプレースホルダー文言",
            placeholder="例: Please choose your payment method.",
            max_length=150,
            required=False
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
        await interaction.response.send_message(
            f"要件「{self.name_input.value.strip()}」を追加しました。",
            ephemeral=True
        )


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
            await interaction.response.edit_message(
                content=f"要件「{removed['name']}」を削除しました。",
                view=None
            )
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
        await interaction.response.edit_message(
            content=f"`{self.field}` を更新しました。",
            view=self.back_view or self.setup_view
        )


# =========================================================
# TICKET PANEL
# =========================================================

class TicketCloseView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.close_button.custom_id = f"ticket_close_{panel_id}"

    @discord.ui.button(
        label="🔒 チケットを閉じる",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_close_default"
    )
    async def close_button(self, interaction, button):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return

        if panel["delete_permission"] == "admin":
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "このチケットを削除するにはチャンネル管理権限が必要です。",
                    ephemeral=True
                )
                return

        await interaction.response.send_message(
            "チケットを削除します...",
            ephemeral=True
        )

        channel = interaction.channel

        archive_id = panel.get("archive_channel_id")
        if archive_id:
            archive = interaction.guild.get_channel(archive_id)
            if isinstance(archive, discord.TextChannel):
                embed = discord.Embed(
                    title="📦 チケット削除ログ",
                    description=f"チャンネル: `{channel.name}`",
                    color=discord.Color.dark_grey(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(
                    name="削除者",
                    value=interaction.user.mention,
                    inline=False
                )
                try:
                    await archive.send(embed=embed)
                except discord.HTTPException:
                    pass

        try:
            await channel.delete(
                reason=f"Ticket closed by {interaction.user}"
            )
        except discord.HTTPException:
            pass


class TicketPanelView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.create_button.custom_id = f"ticket_create_{panel_id}"

    @discord.ui.button(
        label="🎫 チケットを作成",
        style=discord.ButtonStyle.success,
        custom_id="ticket_create_default"
    )
    async def create_button(self, interaction, button):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel or not interaction.guild:
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return

        user_tickets = [
            ch for ch in interaction.guild.channels
            if isinstance(ch, discord.TextChannel)
            and ch.topic == f"ticket_owner:{interaction.user.id}:panel:{self.panel_id}"
        ]
        if len(user_tickets) >= panel["max_tickets"]:
            await interaction.response.send_message(
                f"あなたは既に {panel['max_tickets']} 件のチケットを作成しています。",
                ephemeral=True
            )
            return

        # パネルメッセージ自体を編集して、ボタンをセレクトに置き換える
        view = TicketPopupSelectView(self.cog, self.panel_id, panel)
        await interaction.response.edit_message(view=view)


class TicketPopupBackView(discord.ui.View):
    def __init__(self, cog, panel_id, panel):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel

    @discord.ui.button(
        label="↩️ 戻る",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_popup_back"
    )
    async def back_button(self, interaction, button):
        view = TicketPanelView(self.cog, self.panel_id)
        view.create_button.label = self.panel.get("button_label", "🎫 チケットを作成")
        await interaction.response.edit_message(view=view)


class TicketPopupSelectView(discord.ui.View):
    def __init__(self, cog, panel_id, panel):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel

        requirements = panel.get("requirements") or [
            {"name": "その他", "description": "", "emoji": "📝", "placeholder": "Please choose an option."}
        ]

        options = []
        for req in requirements[:25]:
            name = req.get("name", "無題")
            desc = req.get("description", "") or ""
            emoji = req.get("emoji", "📝")
            options.append(discord.SelectOption(
                label=name[:100],
                value=name,
                description=desc[:100] if desc else None,
                emoji=emoji[:1] if emoji else None
            ))

        placeholder = requirements[0].get("placeholder", "Please choose an option.")

        self.select.placeholder = placeholder[:150]
        self.select.options = options

        # 戻るボタンを追加
        self.add_item(TicketPopupBackButton(cog, panel_id, panel))


class TicketPopupBackButton(discord.ui.Button):
    def __init__(self, cog, panel_id, panel):
        super().__init__(
            label="↩️ 戻る",
            style=discord.ButtonStyle.secondary,
            custom_id="ticket_popup_back_btn"
        )
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel

    async def callback(self, interaction):
        view = TicketPanelView(self.cog, self.panel_id)
        view.create_button.label = self.panel.get("button_label", "🎫 チケットを作成")
        await interaction.response.edit_message(view=view)


class TicketPopupSelect(discord.ui.Select):
    def __init__(self, cog, panel_id, panel, options, placeholder):
        super().__init__(
            placeholder=placeholder,
            options=options,
            custom_id="ticket_popup_select"
        )
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel

    async def callback(self, interaction):
        requirement_name = self.values[0]

        requirement_desc = ""
        for req in self.panel.get("requirements", []):
            if req.get("name") == requirement_name:
                requirement_desc = req.get("description", "") or ""
                break

        modal = TicketDetailModal(
            self.cog, self.panel_id, self.panel,
            requirement_name, requirement_desc
        )
        await interaction.response.send_modal(modal)


# TicketPopupSelectView を正しく再定義（上で定義したものを上書き）
class TicketPopupSelectView(discord.ui.View):
    def __init__(self, cog, panel_id, panel):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel

        requirements = panel.get("requirements") or [
            {"name": "その他", "description": "", "emoji": "📝", "placeholder": "Please choose an option."}
        ]

        options = []
        for req in requirements[:25]:
            name = req.get("name", "無題")
            desc = req.get("description", "") or ""
            emoji = req.get("emoji", "📝")
            options.append(discord.SelectOption(
                label=name[:100],
                value=name,
                description=desc[:100] if desc else None,
                emoji=emoji[:1] if emoji else None
            ))

        placeholder = requirements[0].get("placeholder", "Please choose an option.")

        self.add_item(TicketPopupSelect(cog, panel_id, panel, options, placeholder[:150]))
        self.add_item(TicketPopupBackButton(cog, panel_id, panel))


class TicketDetailModal(discord.ui.Modal):
    def __init__(self, cog, panel_id, panel, requirement_name, requirement_desc):
        super().__init__(title="チケット詳細")
        self.cog = cog
        self.panel_id = panel_id
        self.panel = panel
        self.requirement_name = requirement_name
        self.requirement_desc = requirement_desc

        self.detail_input = discord.ui.TextInput(
            label="詳細（任意）",
            placeholder="要件の詳細を入力してください",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
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
            interaction.guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        mention_role_id = panel.get("mention_role_id")
        if mention_role_id:
            role = interaction.guild.get_role(mention_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        for rid in panel.get("access_role_ids", []):
            role = interaction.guild.get_role(rid)
            if role:
                ow = overwrites.get(role) or discord.PermissionOverwrite()
                ow.view_channel = True
                ow.send_messages = True
                ow.read_message_history = True
                overwrites[role] = ow

        for uid in panel.get("access_user_ids", []):
            member = interaction.guild.get_member(uid)
            if member:
                ow = overwrites.get(member) or discord.PermissionOverwrite()
                ow.view_channel = True
                ow.send_messages = True
                ow.read_message_history = True
                overwrites[member] = ow

        channel_name = f"ticket-{interaction.user.name}"[:100]

        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"ticket_owner:{interaction.user.id}:panel:{self.panel_id}"
            )
        except discord.HTTPException as error:
            return await interaction.followup.send(
                f"チケットの作成に失敗しました: {error}",
                ephemeral=True
            )

        embed = discord.Embed(
            title=panel.get("embed_title") or "チケット",
            description=panel.get("embed_description") or "サポートします。",
            color=discord.Color.blurple()
        )

        req_value = self.requirement_name
        if self.requirement_desc:
            req_value += f"\n{self.requirement_desc}"

        embed.add_field(
            name="要件",
            value=f"```{req_value}```",
            inline=False
        )

        if detail:
            embed.add_field(
                name="詳細",
                value=f"```{detail}```",
                inline=False
            )

        embed.add_field(
            name="作成者",
            value=interaction.user.mention,
            inline=False
        )

        mention_text = interaction.user.mention
        if mention_role_id:
            role = interaction.guild.get_role(mention_role_id)
            if role:
                mention_text += f" {role.mention}"

        welcome = panel.get("welcome_message") or "チケットを作成しました。"

        await channel.send(
            content=f"{mention_text}\n{welcome}",
            embed=embed,
            view=TicketCloseView(self.cog, self.panel_id)
        )

        await interaction.followup.send(
            f"チケットを作成しました: {channel.mention}",
            ephemeral=True
        )


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
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return

        destination = interaction.guild.get_channel(panel["destination_id"])

        if not isinstance(destination, discord.TextChannel):
            await interaction.response.send_message(
                "実績送信先チャンネルが見つかりません。",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛒 実績レビュー",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="購入者",
            value=interaction.user.mention,
            inline=True
        )
        embed.add_field(
            name="商品",
            value=self.product_name,
            inline=True
        )
        embed.add_field(
            name="個数",
            value=str(self.quantity),
            inline=True
        )
        embed.add_field(
            name="評価",
            value=f"{'⭐' * stars} `{stars}/5`",
            inline=False
        )
        embed.add_field(
            name="感想",
            value=self.impression,
            inline=False
        )

        embed.set_footer(
            text=f"Review by {interaction.user.display_name} / ID: {interaction.user.id}"
        )

        try:
            await destination.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Botに送信先への閲覧・送信権限がありません。",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "実績を送信できませんでした。",
                ephemeral=True
            )
            return

        panel["count"] += 1

        counter_id = panel.get("counter_id")
        if counter_id:
            counter = interaction.guild.get_channel(counter_id)

            if isinstance(counter, discord.TextChannel):
                name = f"{panel['counter_base_name']} -{panel['count']}"[:100]
                try:
                    await counter.edit(
                        name=name,
                        reason="実績カウント更新"
                    )
                except discord.HTTPException:
                    pass

        await interaction.response.edit_message(
            content="✅ 実績を送信しました。",
            view=None
        )

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary)
    async def star1(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True)
            return
        await self.send_review(interaction, 1)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary)
    async def star2(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True)
            return
        await self.send_review(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def star3(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True)
            return
        await self.send_review(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def star4(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True)
            return
        await self.send_review(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def star5(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("あなたのレビューではありません。", ephemeral=True)
            return
        await self.send_review(interaction, 5)


class VouchModal(discord.ui.Modal):
    def __init__(self, cog, panel_id):
        super().__init__(title="実績を送信")
        self.cog = cog
        self.panel_id = panel_id

        self.product_name = discord.ui.TextInput(
            label="商品名",
            placeholder="購入した商品名",
            max_length=100,
            required=True
        )
        self.quantity = discord.ui.TextInput(
            label="個数",
            placeholder="数字のみ",
            max_length=10,
            required=True
        )
        self.impression = discord.ui.TextInput(
            label="感想",
            placeholder="感想を入力",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )

        self.add_item(self.product_name)
        self.add_item(self.quantity)
        self.add_item(self.impression)

    async def on_submit(self, interaction):
        panel = self.cog.vouch_panels.get(self.panel_id)

        if not panel or not interaction.guild:
            await interaction.response.send_message(
                "パネルが見つからないか、サーバー外で使用されています。",
                ephemeral=True
            )
            return

        if not self.quantity.value.isdigit():
            await interaction.response.send_message(
                "個数は数字のみで入力してください。",
                ephemeral=True
            )
            return

        view = VouchRatingView(
            self.cog,
            self.panel_id,
            interaction.user.id,
            self.product_name.value,
            int(self.quantity.value),
            self.impression.value
        )

        await interaction.response.send_message(
            "レビュー内容を受け取りました。\n"
            f"**{self.product_name.value}** の評価を選んでください。",
            view=view,
            ephemeral=True
        )


class VouchView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.submit_button.custom_id = f"vouch_submit_{panel_id}"

    @discord.ui.button(
        label="📋 実績を送信",
        style=discord.ButtonStyle.success,
        custom_id="vouch_submit_default"
    )
    async def submit_button(self, interaction, button):
        await interaction.response.send_modal(
            VouchModal(self.cog, self.panel_id)
        )


# =========================================================
# STATUS PANEL
# =========================================================

def status_embed(guild, staff_list):
    colors = {
        "対応不可": discord.Color.red(),
        "対応遅延": discord.Color.orange(),
        "対応可能": discord.Color.green()
    }

    priority = {"対応不可": 0, "対応遅延": 1, "対応可能": 2}
    if staff_list:
        worst = min(staff_list, key=lambda s: priority.get(s["status"], 3))
        color = colors.get(worst["status"], discord.Color.blurple())
    else:
        color = discord.Color.blurple()

    embed = discord.Embed(
        title="対応状況",
        color=color
    )

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

        self.message_input = discord.ui.TextInput(
            label="一言",
            placeholder="現在の状況など",
            required=False,
            max_length=200
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction):
        panel = self.cog.status_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return

        staff_list = panel.get("staff", [])
        target = None
        for s in staff_list:
            if s["user_id"] == self.user_id:
                target = s
                break

        if not target:
            await interaction.response.send_message(
                "あなたはこのパネルのスタッフではありません。",
                ephemeral=True
            )
            return

        target["message"] = self.message_input.value.strip()
        await self.cog.refresh_status(panel)

        await interaction.response.send_message(
            "一言を更新しました。",
            ephemeral=True
        )


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
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return

        staff_list = panel.get("staff", [])
        target = None
        for s in staff_list:
            if s["user_id"] == interaction.user.id:
                target = s
                break

        if not target:
            await interaction.response.send_message(
                "あなたはこのパネルのスタッフではありません。\n"
                "管理者に `/対応状況スタッフ追加` を依頼してください。",
                ephemeral=True
            )
            return

        status = select.values[0]
        emojis = {
            "対応不可": "🔴",
            "対応遅延": "🟠",
            "対応可能": "🟢"
        }
        target["status"] = status
        target["emoji"] = emojis[status]

        await self.cog.refresh_status(panel)

        await interaction.response.send_message(
            f"あなたの状態を「{status}」に変更しました。",
            ephemeral=True
        )

    @discord.ui.button(
        label="✏️ 一言変更",
        style=discord.ButtonStyle.primary,
        custom_id="status_message_default"
    )
    async def message_button(self, interaction, button):
        panel = self.cog.status_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return

        staff_ids = [s["user_id"] for s in panel.get("staff", [])]
        if interaction.user.id not in staff_ids:
            await interaction.response.send_message(
                "あなたはこのパネルのスタッフではありません。",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            StatusMessageModal(self.cog, self.panel_id, interaction.user.id)
        )


# =========================================================
# TICKET EDIT
# =========================================================

class TicketEditSelectView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=120)
        self.cog = cog
        self.select.options = options

    @discord.ui.select(
        placeholder="編集するチケットパネルを選択",
        custom_id="ticket_edit_select"
    )
    async def select(self, interaction, select):
        panel_id = select.values[0]
        panel = self.cog.ticket_panels.get(panel_id)

        if not panel:
            await interaction.response.edit_message(
                content="パネルが見つかりません。",
                view=None
            )
            return

        view = TicketEditMenuView(self.cog, panel_id)
        await interaction.response.edit_message(
            content=f"パネル `{panel_id}` の編集メニューです。",
            view=view
        )


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

    @discord.ui.select(
        placeholder="編集する項目を選択",
        options=[],
        custom_id="ticket_edit_field"
    )
    async def field_select(self, interaction, select):
        field = select.values[0]

        if field == "category":
            categories = interaction.guild.categories[:25]
            if not categories:
                await interaction.response.send_message(
                    "カテゴリーがありません。",
                    ephemeral=True
                )
                return
            options = [
                discord.SelectOption(label=c.name[:100], value=str(c.id))
                for c in categories
            ]
            view = TicketEditObjectSelectView(
                self.cog, self.panel_id, field, options
            )
            await interaction.response.edit_message(
                content="新しいカテゴリーを選択してください。",
                view=view
            )

        elif field == "mention_role":
            roles = [
                r for r in interaction.guild.roles
                if not r.is_default() and not r.managed
            ][:25]
            if not roles:
                await interaction.response.send_message(
                    "ロールがありません。",
                    ephemeral=True
                )
                return
            options = [
                discord.SelectOption(label=r.name[:100], value=str(r.id))
                for r in roles
            ]
            view = TicketEditObjectSelectView(
                self.cog, self.panel_id, field, options
            )
            await interaction.response.edit_message(
                content="新しいメンションロールを選択してください。",
                view=view
            )

        elif field == "archive_channel":
            channels = [
                c for c in interaction.guild.text_channels
            ][:25]
            if not channels:
                await interaction.response.send_message(
                    "テキストチャンネルがありません。",
                    ephemeral=True
                )
                return
            options = [
                discord.SelectOption(label=c.name[:100], value=str(c.id))
                for c in channels
            ]
            view = TicketEditObjectSelectView(
                self.cog, self.panel_id, field, options
            )
            await interaction.response.edit_message(
                content="新しいアーカイブチャンネルを選択してください。",
                view=view
            )

        else:
            await interaction.response.send_modal(
                TicketEditModal(self.cog, self.panel_id, field)
            )


class TicketEditObjectSelectView(discord.ui.View):
    def __init__(self, cog, panel_id, field, options):
        super().__init__(timeout=120)
        self.cog = cog
        self.panel_id = panel_id
        self.field = field
        self.select.options = options

    @discord.ui.select(
        placeholder="選択してください",
        custom_id="ticket_edit_object_select"
    )
    async def select(self, interaction, select):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.edit_message(
                content="パネルが見つかりません。",
                view=None
            )
            return

        value = int(select.values[0])

        if self.field == "category":
            panel["category_id"] = value
        elif self.field == "mention_role":
            panel["mention_role_id"] = value
        elif self.field == "archive_channel":
            panel["archive_channel_id"] = value

        await interaction.response.edit_message(
            content=f"`{self.field}` を更新しました。",
            view=None
        )


class TicketEditModal(discord.ui.Modal):
    def __init__(self, cog, panel_id, field):
        super().__init__(title=f"編集: {field}")
        self.cog = cog
        self.panel_id = panel_id
        self.field = field

        self.value_input = discord.ui.TextInput(
            label="新しい値",
            placeholder="新しい値を入力してください",
            required=False,
            max_length=1000
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction):
        panel = self.cog.ticket_panels.get(self.panel_id)
        if not panel:
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return

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
            await interaction.response.send_message(
                f"値が不正です: {error}",
                ephemeral=True
            )
            return

        try:
            channel = interaction.guild.get_channel(panel["channel_id"])
            if isinstance(channel, discord.TextChannel):
                message = await channel.fetch_message(panel["message_id"])
                new_view = TicketPanelView(self.cog, self.panel_id)
                new_view.create_button.label = panel["button_label"]
                await message.edit(view=new_view)
        except (discord.HTTPException, AttributeError):
            pass

        await interaction.response.send_message(
            f"`{field}` を更新しました。",
            ephemeral=True
        )


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

        placeholder = (
            "入室通知チャンネルを選択（検索できます）"
            if log_type == "join"
            else "退室通知チャンネルを選択（検索できます）"
        )

        super().__init__(
            placeholder=placeholder,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            custom_id=f"member_log_select_{log_type}"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        channel = self.values[0]

        data = load_member_log_data()
        guild_id_str = str(interaction.guild.id)

        if guild_id_str not in data:
            data[guild_id_str] = {"join_channel_id": None, "leave_channel_id": None}

        if self.log_type == "join":
            data[guild_id_str]["join_channel_id"] = channel.id
        else:
            data[guild_id_str]["leave_channel_id"] = channel.id

        save_member_log_data(data)

        embed = build_member_log_embed(
            interaction.guild.id,
            data[guild_id_str].get("join_channel_id"),
            data[guild_id_str].get("leave_channel_id")
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class MemberLogRemoveButton(discord.ui.Button):
    def __init__(self, cog, log_type: str):
        self.cog = cog
        self.log_type = log_type

        label = "入室通知 解除" if log_type == "join" else "退室通知 解除"

        super().__init__(
            label=label,
            style=discord.ButtonStyle.danger,
            custom_id=f"member_log_remove_{log_type}"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_member_log_data()
        guild_id_str = str(interaction.guild.id)

        if guild_id_str in data:
            if self.log_type == "join":
                data[guild_id_str]["join_channel_id"] = None
            else:
                data[guild_id_str]["leave_channel_id"] = None
            save_member_log_data(data)

        embed = build_member_log_embed(
            interaction.guild.id,
            data.get(guild_id_str, {}).get("join_channel_id"),
            data.get(guild_id_str, {}).get("leave_channel_id")
        )

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
# 荒らし対策 (ANTI-RAID)
# =========================================================

def build_antiraid_embed(guild, data):
    embed = discord.Embed(
        title="荒らし対策設定",
        description=(
            f"サーバー名: {guild.name} ({guild.id})\n"
            f"下のドロップダウン（検索可）から各種設定を変更できます。"
        ),
        color=discord.Color.red()
    )
    embed.add_field(
        name="連投スパム",
        value="オン" if data.get("spam_enabled") else "オフ",
        inline=False
    )
    embed.add_field(
        name="リンク検知",
        value="オン" if data.get("link_enabled") else "オフ",
        inline=False
    )
    ignore_users = data.get("ignore_user_ids", [])
    embed.add_field(
        name="荒らし対策を検知しないメンバー",
        value="\n".join(f"<@{uid}>" for uid in ignore_users) if ignore_users else "なし",
        inline=False
    )
    ignore_roles = data.get("ignore_role_ids", [])
    embed.add_field(
        name="荒らし対策を検知しないロール",
        value="\n".join(f"<@&{rid}>" for rid in ignore_roles) if ignore_roles else "なし",
        inline=False
    )
    return embed


class AntiraidIgnoreUserSelect(discord.ui.UserSelect):
    def __init__(self, cog):
        super().__init__(
            placeholder="🔍 荒らし対策を検知しないメンバー（検索できます）",
            min_values=0,
            max_values=25,
            custom_id="antiraid_ignore_users"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False,
                         "ignore_user_ids": [], "ignore_role_ids": []}

        data[gid]["ignore_user_ids"] = [u.id for u in self.values]
        save_antiraid_data(data)

        embed = build_antiraid_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class AntiraidIgnoreRoleSelect(discord.ui.RoleSelect):
    def __init__(self, cog):
        super().__init__(
            placeholder="🔍 荒らし対策を検知しないロール（検索できます）",
            min_values=0,
            max_values=25,
            custom_id="antiraid_ignore_roles"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False,
                         "ignore_user_ids": [], "ignore_role_ids": []}

        data[gid]["ignore_role_ids"] = [r.id for r in self.values]
        save_antiraid_data(data)

        embed = build_antiraid_embed(interaction.guild, data[gid])
        await interaction.response.edit_message(embed=embed, view=self.view)


class AntiraidToggleButton(discord.ui.Button):
    def __init__(self, cog, toggle_type):
        self.cog = cog
        self.toggle_type = toggle_type
        label = "連投スパム 切替" if toggle_type == "spam" else "リンク検知 切替"
        super().__init__(label=label, style=discord.ButtonStyle.primary,
                         custom_id=f"antiraid_toggle_{toggle_type}")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False,
                         "ignore_user_ids": [], "ignore_role_ids": []}

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


# =========================================================
# 荒らし対策 検知アクション
# =========================================================

class AntiraidPunishView(discord.ui.View):
    def __init__(self, member, reason):
        super().__init__(timeout=300)
        self.member = member
        self.reason = reason

    async def interaction_check(self, interaction):
        if not interaction.user.guild_permissions.kick_members and \
           not interaction.user.guild_permissions.ban_members and \
           not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "この操作にはモデレーション権限が必要です。",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="BAN", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction, button):
        try:
            await self.member.ban(reason=f"Anti-raid: {self.reason} / by {interaction.user}")
            await interaction.response.send_message(
                f"{self.member.mention} をBANしました。",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message("BANできません。権限を確認してください。", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"BANに失敗しました: {e}", ephemeral=True)

    @discord.ui.button(label="KICK", style=discord.ButtonStyle.danger, emoji="👢")
    async def kick_button(self, interaction, button):
        try:
            await self.member.kick(reason=f"Anti-raid: {self.reason} / by {interaction.user}")
            await interaction.response.send_message(
                f"{self.member.mention} をKICKしました。",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message("KICKできません。権限を確認してください。", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"KICKに失敗しました: {e}", ephemeral=True)

    @discord.ui.button(label="TIMEOUT", style=discord.ButtonStyle.primary, emoji="⏳")
    async def timeout_button(self, interaction, button):
        view = TimeoutDurationView(self.member, self.reason)
        await interaction.response.send_message(
            "TIMEOUT期間を選択してください。",
            view=view,
            ephemeral=True
        )


class TimeoutDurationView(discord.ui.View):
    def __init__(self, member, reason):
        super().__init__(timeout=120)
        self.member = member
        self.reason = reason

    async def apply_timeout(self, interaction, seconds):
        try:
            until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
            await self.member.timeout(until, reason=f"Anti-raid: {self.reason} / by {interaction.user}")
            await interaction.response.send_message(
                f"{self.member.mention} を {seconds}秒間 TIMEOUT にしました。",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message("TIMEOUTできません。権限を確認してください。", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"TIMEOUTに失敗しました: {e}", ephemeral=True)

    @discord.ui.button(label="5分", style=discord.ButtonStyle.secondary)
    async def t5m(self, interaction, button):
        await self.apply_timeout(interaction, 5 * 60)

    @discord.ui.button(label="10分", style=discord.ButtonStyle.secondary)
    async def t10m(self, interaction, button):
        await self.apply_timeout(interaction, 10 * 60)

    @discord.ui.button(label="1時間", style=discord.ButtonStyle.secondary)
    async def t1h(self, interaction, button):
        await self.apply_timeout(interaction, 60 * 60)

    @discord.ui.button(label="1週間", style=discord.ButtonStyle.secondary)
    async def t1w(self, interaction, button):
        await self.apply_timeout(interaction, 7 * 24 * 60 * 60)


# =========================================================
# 固定メッセージ
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
# 自動リアクション（会話形式）
# =========================================================

def build_auto_reaction_embed(guild, data):
    embed = discord.Embed(
        title="自動リアクション設定",
        description=(
            f"サーバー名: {guild.name} ({guild.id})\n"
            f"下のドロップダウン（検索可）から各種設定を変更できます。"
        ),
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="自動リアクション",
        value="オン" if data else "オフ",
        inline=False
    )

    if data:
        lines = []
        for cid, emojis in data.items():
            channel = guild.get_channel(int(cid))
            ch_name = channel.mention if channel else f"<#{cid}>"
            lines.append(f"{ch_name} → {' '.join(emojis)}")
        embed.add_field(
            name="リアクションするチャンネル",
            value="\n".join(lines)[:1024] if lines else "なし",
            inline=False
        )
    else:
        embed.add_field(
            name="リアクションするチャンネル",
            value="なし",
            inline=False
        )

    return embed


class AutoReactionChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, cog, index):
        self.cog = cog
        self.index = index
        super().__init__(
            placeholder=f"🔍 リアクションチャンネル（検索できます）" if index == 0 else f"🔍 リアクションチャンネル{index + 1}",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            custom_id=f"auto_reaction_channel_{index}"
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        # チャンネル選択後に絵文字をモーダルで入力
        modal = AutoReactionEmojiModal(self.cog, self.values[0].id)
        await interaction.response.send_modal(modal)


class AutoReactionEmojiModal(discord.ui.Modal):
    def __init__(self, cog, channel_id):
        super().__init__(title="絵文字を設定")
        self.cog = cog
        self.channel_id = channel_id
        self.emoji_input = discord.ui.TextInput(
            label="絵文字（カンマ区切りで最大4つ）",
            placeholder="例: 👍,🎉,😊,🔥",
            required=True,
            max_length=200
        )
        self.add_item(self.emoji_input)

    async def on_submit(self, interaction):
        emojis = [e.strip() for e in self.emoji_input.value.split(",") if e.strip()]
        if not emojis:
            await interaction.response.send_message("絵文字を1つ以上指定してください。", ephemeral=True)
            return

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
        # 3つまでチャンネルセレクトを表示
        for i in range(3):
            self.add_item(AutoReactionChannelSelect(cog, i))


class AutoReactionRemoveSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="解除するチャンネルの絵文字を選択（複数可）",
                         min_values=1, max_values=25, options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_auto_reaction_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            await interaction.response.edit_message(content="設定がありません。", view=None)
            return
        removed = []
        for val in self.values:
            cid, emoji = val.split(":", 1)
            if cid in data[gid] and emoji in data[gid][cid]:
                data[gid][cid].remove(emoji)
                removed.append(emoji)
                if not data[gid][cid]:
                    del data[gid][cid]
        save_auto_reaction_data(data)
        await interaction.response.edit_message(
            content=f"以下の自動リアクションを解除しました: {' '.join(removed)}",
            view=None
        )


class AutoReactionRemoveView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120)
        self.add_item(AutoReactionRemoveSelect(options))


# =========================================================
# 招待キャンペーン
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
            await interaction.response.send_message("このキャンペーンは終了しています。", ephemeral=True)
            return

        # すでに作成済みのリンクがあればそれを返す
        user_links = campaign.setdefault("user_links", {})
        uid = str(interaction.user.id)
        if uid in user_links:
            invite_url = user_links[uid]
        else:
            try:
                target_channel = interaction.guild.get_channel(campaign["channel_id"])
                if not isinstance(target_channel, discord.TextChannel):
                    target_channel = interaction.channel
                invite = await target_channel.create_invite(
                    max_age=0,
                    max_uses=0,
                    unique=True,
                    reason=f"Invite campaign {self.campaign_id} by {interaction.user}"
                )
                invite_url = invite.url
                user_links[uid] = invite_url
                # 招待コードとユーザーの紐付けも保存
                campaign.setdefault("invite_map", {})[invite.code] = uid
                save_invite_campaign_data(data)
            except discord.HTTPException as e:
                await interaction.response.send_message(f"招待リンクの作成に失敗しました: {e}", ephemeral=True)
                return

        await interaction.response.send_message(
            f"あなた専用の招待リンクです。\n\n{invite_url}",
            ephemeral=True
        )

    @discord.ui.button(label="👤 現在の参加人数", style=discord.ButtonStyle.secondary)
    async def participants(self, interaction, button):
        data = load_invite_campaign_data()
        campaign = data.get(self.campaign_id)
        if not campaign:
            await interaction.response.send_message("キャンペーンが見つかりません。", ephemeral=True)
            return

        uid = str(interaction.user.id)
        counts = campaign.get("counts", {})
        my_count = counts.get(uid, 0)

        # 現在の参加人数 = キャンペーン開始以降に参加したユニーク人数
        total_joins = campaign.get("total_joins", 0)

        # 1位になるまでの招待数
        max_count = max(counts.values()) if counts else 0
        needed = max(0, max_count - my_count + 1) if max_count > 0 else 0

        embed = discord.Embed(
            title="あなたの招待状況",
            color=discord.Color.blurple()
        )
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
            await interaction.response.send_message("キャンペーンが見つかりません。", ephemeral=True)
            return

        counts = campaign.get("counts", {})
        if not counts:
            await interaction.response.send_message("まだ招待実績がありません。", ephemeral=True)
            return

        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        lines = []
        for i, (uid, cnt) in enumerate(sorted_counts[:10], start=1):
            member = interaction.guild.get_member(int(uid))
            name = member.mention if member else f"<@{uid}>"
            lines.append(f"{i}位 - {name} {cnt}回")

        embed = discord.Embed(
            title="🏆 招待ランキング",
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        # 自分の順位
        uid = str(interaction.user.id)
        my_count = counts.get(uid, 0)
        my_rank = 0
        for i, (u, c) in enumerate(sorted_counts, start=1):
            if u == uid:
                my_rank = i
                break

        if my_rank > 0:
            member = interaction.guild.get_member(int(uid))
            name = member.mention if member else f"<@{uid}>"
            embed.add_field(
                name="自分の成績",
                value=f"{my_rank}位 - {name} {my_count}回",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class InviteCampaignStopSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="停止するキャンペーンを選択", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_invite_campaign_data()
        cid = self.values[0]
        campaign = data.get(cid)
        if not campaign:
            await interaction.response.edit_message(content="キャンペーンが見つかりません。", view=None)
            return
        campaign["active"] = False
        save_invite_campaign_data(data)
        await interaction.response.edit_message(
            content=f"キャンペーン「{campaign.get('title', cid)}」を停止しました。",
            view=None
        )


class InviteCampaignStopView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=120)
        self.add_item(InviteCampaignStopSelect(options))


# =========================================================
# 定期メッセージ
# =========================================================

class PeriodicMessageModal(discord.ui.Modal):
    def __init__(self, cog, channel: discord.TextChannel):
        super().__init__(title="定期メッセージ設定")
        self.cog = cog
        self.channel = channel

        self.text_input = discord.ui.TextInput(
            label="送信するテキスト",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )
        self.interval_input = discord.ui.TextInput(
            label="送信間隔（例: 1m, 1h, 1d, 1w）",
            placeholder="1m / 1h / 1d / 1w",
            required=True,
            max_length=20
        )
        self.image_input = discord.ui.TextInput(
            label="画像URL（任意）",
            required=False,
            max_length=500
        )

        self.add_item(self.text_input)
        self.add_item(self.interval_input)
        self.add_item(self.image_input)

    async def on_submit(self, interaction):
        try:
            seconds = parse_duration(self.interval_input.value.strip())
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        pm_id = uuid.uuid4().hex[:10]
        data = load_periodic_message_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {}

        data[gid][pm_id] = {
            "id": pm_id,
            "channel_id": self.channel.id,
            "text": self.text_input.value,
            "interval": seconds,
            "image_url": self.image_input.value.strip() or None,
            "last_sent": 0,
            "active": True
        }
        save_periodic_message_data(data)

        await interaction.response.send_message(
            f"定期メッセージを設定しました。\n"
            f"チャンネル: {self.channel.mention}\n"
            f"間隔: {self.interval_input.value.strip()}",
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
        self.invite_cache = {}  # guild_id -> {invite_code: uses}

    async def cog_load(self):
        # 定期メッセージのタスクを復元
        data = load_periodic_message_data()
        for gid, items in data.items():
            for pid, info in items.items():
                if info.get("active"):
                    self._start_periodic_task(gid, pid, info)

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

    # -----------------------------------------------------
    # /nuke
    # -----------------------------------------------------

    @app_commands.command(
        name="nuke",
        description="現在のテキストチャンネルを再作成します"
    )
    async def nuke(self, interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "本当にこのチャンネルを再作成しますか？",
            view=ConfirmNukeView(interaction.channel),
            ephemeral=True
        )

    # -----------------------------------------------------
    # /配布作成
    # -----------------------------------------------------

    @app_commands.command(
        name="配布作成",
        description="景品の配布を作成し、同時に開始します"
    )
    @app_commands.describe(
        prize="景品名",
        duration="配布期間（例: 30m、1h、1d、1week）",
        winners="当選人数"
    )
    async def giveaway_create(
        self,
        interaction,
        prize: str,
        duration: str,
        winners: app_commands.Range[int, 1, 20] = 1
    ):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        try:
            seconds = parse_duration(duration)
        except ValueError as error:
            await interaction.response.send_message(
                str(error),
                ephemeral=True
            )
            return

        giveaway_id = uuid.uuid4().hex[:12]
        end_time = int(time.time() + seconds)

        view = GiveawayView(
            self, giveaway_id, prize, winners, end_time
        )

        await interaction.response.send_message(
            f"配布「{prize}」を開始しました。期間: {duration}",
            ephemeral=True
        )

        message = await interaction.channel.send(
            embed=view.make_embed(),
            view=view
        )
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
                    result = (
                        f"🎉 **{view.prize}** の配布が終了しました！\n"
                        f"当選者: {' '.join(f'<@{uid}>' for uid in chosen)}"
                    )
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

    # -----------------------------------------------------
    # /配布終了
    # -----------------------------------------------------

    @app_commands.command(
        name="配布終了",
        description="開催中の配布を選択して即座に終了し、当選者を発表します"
    )
    async def giveaway_stop(self, interaction):
        guild_giveaways = {}
        for mid, view in self.active_giveaways.items():
            if view.message and view.message.guild and \
               view.message.guild.id == interaction.guild_id and \
               not view.ended and not view.cancelled:
                guild_giveaways[mid] = view

        if not guild_giveaways:
            await interaction.response.send_message(
                "開催中の配布が見つかりません。",
                ephemeral=True
            )
            return

        options = []
        for mid, view in list(guild_giveaways.items())[:25]:
            options.append(
                discord.SelectOption(
                    label=f"{view.prize[:50]}",
                    description=f"ID: {mid} / 参加者: {len(view.participants)}人",
                    value=str(mid)
                )
            )

        view = StopGiveawayView(self, options)

        await interaction.response.send_message(
            "終了する配布を選択してください。",
            view=view,
            ephemeral=True
        )

    # -----------------------------------------------------
    # /配布再抽選
    # -----------------------------------------------------

    @app_commands.command(
        name="配布再抽選",
        description="終了した配布を選択して当選者を再抽選します"
    )
    async def giveaway_redraw(self, interaction):
        guild_giveaways = {}
        for mid, view in self.ended_giveaways.items():
            if view.message and view.message.guild and \
               view.message.guild.id == interaction.guild_id and \
               not view.cancelled:
                guild_giveaways[mid] = view

        if not guild_giveaways:
            await interaction.response.send_message(
                "再抽選できる配布が見つかりません。",
                ephemeral=True
            )
            return

        options = []
        for mid, view in list(guild_giveaways.items())[:25]:
            options.append(
                discord.SelectOption(
                    label=f"{view.prize[:50]}",
                    description=f"ID: {mid} / 参加者: {len(view.participants)}人",
                    value=str(mid)
                )
            )

        view = RedrawGiveawayView(self, options)

        await interaction.response.send_message(
            "再抽選する配布を選択してください。",
            view=view,
            ephemeral=True
        )

    # -----------------------------------------------------
    # /埋め込み送信
    # -----------------------------------------------------

    @app_commands.command(
        name="埋め込み送信",
        description="埋め込みメッセージを送信します（画像はファイル選択）"
    )
    @app_commands.describe(
        title="埋め込みのタイトル",
        description="埋め込みの説明",
        color="色（例: ff0000、00ff00）",
        footer="フッター",
        image="画像ファイル（自分のPCから選択）"
    )
    async def embed(
        self,
        interaction,
        title: str,
        description: str,
        color: str = None,
        footer: str = None,
        image: discord.Attachment = None
    ):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=parse_color(color) or discord.Color.blurple()
        )

        if footer:
            embed.set_footer(text=footer)

        file = None
        if image:
            file = await image.to_file()
            embed.set_image(url=f"attachment://{image.filename}")

        await interaction.response.send_message(
            "埋め込みを送信しました。",
            ephemeral=True
        )
        if file:
            await interaction.channel.send(embed=embed, file=file)
        else:
            await interaction.channel.send(embed=embed)

    # -----------------------------------------------------
    # /dm送信
    # -----------------------------------------------------

    @app_commands.command(
        name="dm送信",
        description="指定したユーザーにDMを送信します"
    )
    @app_commands.describe(
        user="送信先のユーザー",
        message="送信するメッセージ"
    )
    async def dm_anc(
        self,
        interaction,
        user: discord.User,
        message: str
    ):
        try:
            await user.send(message)
        except discord.Forbidden:
            await interaction.response.send_message(
                "このユーザーにはDMを送信できません（DMを拒否している可能性があります）。",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "DMの送信に失敗しました。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"{user.mention} にDMを送信しました。",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /認証パネル
    # -----------------------------------------------------

    @app_commands.command(
        name="認証パネル",
        description="認証パネルを作成します"
    )
    @app_commands.describe(
        type="認証方法（計算認証 or ボタン認証）",
        title="パネルのタイトル（任意）",
        description="パネルの説明（任意）",
        role="認証後に付与するロール（省略時は選択メニュー）"
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="計算認証", value="math"),
            app_commands.Choice(name="ボタン認証", value="button")
        ]
    )
    async def verify(
        self,
        interaction,
        type: app_commands.Choice[str] = None,
        title: str = "認証",
        description: str = "下のボタンから認証してください。",
        role: discord.Role = None
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "サーバー内で使用してください。",
                ephemeral=True
            )
            return

        verify_type = type.value if type else "button"

        if role is not None:
            if role.is_default() or role.managed:
                await interaction.response.send_message(
                    "このロールは設定できません。",
                    ephemeral=True
                )
                return

            view = VerifyView(self, role, verify_type)
            embed = build_verify_embed(
                title, description, role, interaction.guild_id
            )

            await interaction.response.send_message(
                "認証パネルを作成しました。",
                ephemeral=True
            )
            await interaction.channel.send(embed=embed, view=view)
            return

        roles = [
            r for r in interaction.guild.roles
            if not r.is_default()
            and not r.managed
            and not r.is_premium_subscriber()
        ]

        if not roles:
            await interaction.response.send_message(
                "設定できるロールがありません。",
                ephemeral=True
            )
            return

        options = [
            discord.SelectOption(
                label=r.name[:100],
                value=str(r.id)
            )
            for r in roles[:25]
        ]

        view = VerifyRoleSelectView(
            self, verify_type, title, description
        )
        view.role_select.options = options

        await interaction.response.send_message(
            "認証後に付与するロールを選択してください。",
            view=view,
            ephemeral=True
        )

    # -----------------------------------------------------
    # /実績パネル
    # -----------------------------------------------------

    @app_commands.command(
        name="実績パネル",
        description="実績送信パネルを作成します"
    )
    @app_commands.describe(
        destination="実績を送信するチャンネル",
        title="パネルタイトル",
        description="パネル説明",
        counter_channel="任意：実績数を表示するチャンネル"
    )
    async def vouch_panel(
        self,
        interaction,
        destination: discord.TextChannel,
        title: str,
        description: str,
        counter_channel: discord.TextChannel = None
    ):
        panel_id = uuid.uuid4().hex[:10]

        self.vouch_panels[panel_id] = {
            "destination_id": destination.id,
            "title": title,
            "description": description,
            "count": 0,
            "counter_id": counter_channel.id if counter_channel else None,
            "counter_base_name": (
                counter_channel.name if counter_channel else None
            )
        }

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Vouch Panel: {panel_id}")

        view = VouchView(self, panel_id)

        await interaction.response.send_message(
            "実績パネルを作成しました。",
            ephemeral=True
        )
        await interaction.channel.send(embed=embed, view=view)

    # -----------------------------------------------------
    # /対応状況
    # -----------------------------------------------------

    @app_commands.command(
        name="対応状況",
        description="対応状況パネルを表示します"
    )
    @app_commands.describe(
        description="パネルの説明（任意）"
    )
    async def status(
        self,
        interaction: discord.Interaction,
        description: str = "現在の対応状況です。"
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "サーバー内で使用してください。",
                ephemeral=True
            )
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        panel_id = uuid.uuid4().hex[:10]

        staff_data = load_status_staff_data()
        gid = str(interaction.guild.id)
        staff_ids = staff_data.get(gid, [])

        staff_list = []
        for uid in staff_ids:
            member = interaction.guild.get_member(uid)
            if not member:
                continue
            staff_list.append({
                "user_id": uid,
                "status": "対応可能",
                "emoji": "🟢",
                "message": ""
            })

        panel = {
            "id": panel_id,
            "creator_id": interaction.user.id,
            "description": description,
            "channel_id": interaction.channel.id,
            "message_id": None,
            "staff": staff_list,
        }

        view = StatusSelectView(self, panel_id)

        panel_message = await interaction.channel.send(
            embed=status_embed(interaction.guild, staff_list),
            view=view
        )

        panel["message_id"] = panel_message.id
        self.status_panels[panel_id] = panel

        data = load_status_panel_data()
        data[panel_id] = panel
        save_status_panel_data(data)

        await interaction.response.send_message(
            "ステータスパネルを作成しました。",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /対応状況スタッフ追加
    # -----------------------------------------------------

    @app_commands.command(
        name="対応状況スタッフ追加",
        description="対応状況パネルに表示するスタッフを追加します"
    )
    @app_commands.describe(
        user="追加するスタッフ"
    )
    async def status_staff_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "サーバー内で使用してください。",
                ephemeral=True
            )
            return

        data = load_status_staff_data()
        gid = str(interaction.guild.id)
        staff_ids = data.get(gid, [])

        if user.id in staff_ids:
            await interaction.response.send_message(
                f"{user.mention} は既にスタッフとして登録されています。",
                ephemeral=True
            )
            return

        staff_ids.append(user.id)
        data[gid] = staff_ids
        save_status_staff_data(data)

        for panel in self.status_panels.values():
            if panel.get("channel_id") and \
               interaction.guild.get_channel(panel["channel_id"]):
                if not any(s["user_id"] == user.id for s in panel["staff"]):
                    panel["staff"].append({
                        "user_id": user.id,
                        "status": "対応可能",
                        "emoji": "🟢",
                        "message": ""
                    })
                    await self.refresh_status(panel)

        await interaction.response.send_message(
            f"{user.mention} を対応状況スタッフに追加しました。",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /対応状況スタッフ削除
    # -----------------------------------------------------

    @app_commands.command(
        name="対応状況スタッフ削除",
        description="対応状況パネルからスタッフを削除します"
    )
    @app_commands.describe(
        user="削除するスタッフ"
    )
    async def status_staff_remove(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "サーバー内で使用してください。",
                ephemeral=True
            )
            return

        data = load_status_staff_data()
        gid = str(interaction.guild.id)
        staff_ids = data.get(gid, [])

        if user.id not in staff_ids:
            await interaction.response.send_message(
                f"{user.mention} はスタッフとして登録されていません。",
                ephemeral=True
            )
            return

        staff_ids.remove(user.id)
        data[gid] = staff_ids
        save_status_staff_data(data)

        for panel in self.status_panels.values():
            panel["staff"] = [s for s in panel["staff"] if s["user_id"] != user.id]
            await self.refresh_status(panel)

        await interaction.response.send_message(
            f"{user.mention} を対応状況スタッフから削除しました。",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /チケット
    # -----------------------------------------------------

    @app_commands.command(
        name="チケット",
        description="チケットパネルを対話形式で作成します"
    )
    async def ticket(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "サーバー内で使用してください。",
                ephemeral=True
            )
            return

        view = TicketSetupModeView(self, interaction.user.id)
        await interaction.response.send_message(
            "**チケットパネルの作成方式を選択してください。**\n\n"
            "・**1ボタン式**：シンプルに1つのボタンでチケットを作成します。\n"
            "・**複数項目から選ぶ式**：ユーザーが要件を選択してチケットを作成します。\n"
            "　要件ごとに絵文字とセレクトのプレースホルダー文言を設定できます。",
            view=view,
            ephemeral=True
        )

    # -----------------------------------------------------
    # /チケットパネル編集
    # -----------------------------------------------------

    @app_commands.command(
        name="チケットパネル編集",
        description="チケットパネルを編集します"
    )
    async def ticket_edit(self, interaction):
        guild_panels = {
            pid: panel for pid, panel in self.ticket_panels.items()
            if panel.get("channel_id")
        }

        if not guild_panels:
            await interaction.response.send_message(
                "編集できるチケットパネルがありません。",
                ephemeral=True
            )
            return

        options = []
        for pid, panel in list(guild_panels.items())[:25]:
            options.append(
                discord.SelectOption(
                    label=f"{panel['button_label'][:50]}",
                    description=f"ID: {pid}",
                    value=pid
                )
            )

        view = TicketEditSelectView(self, options)

        await interaction.response.send_message(
            "編集するチケットパネルを選択してください。",
            view=view,
            ephemeral=True
        )

    # -----------------------------------------------------
    # /入室退出通知
    # -----------------------------------------------------

    @app_commands.command(
        name="入室退出通知",
        description="メンバーの入室・退室通知を設定します"
    )
    async def member_log(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_member_log_data()
        guild_id_str = str(interaction.guild.id)
        entry = data.get(guild_id_str, {})

        embed = build_member_log_embed(
            interaction.guild.id,
            entry.get("join_channel_id"),
            entry.get("leave_channel_id")
        )
        view = MemberLogSettingView(self)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # -----------------------------------------------------
    # /荒らし対策
    # -----------------------------------------------------

    @app_commands.command(
        name="荒らし対策",
        description="荒らし対策の設定を行います"
    )
    async def antiraid(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_antiraid_data()
        gid = str(interaction.guild.id)
        if gid not in data:
            data[gid] = {"spam_enabled": False, "link_enabled": False,
                         "ignore_user_ids": [], "ignore_role_ids": []}
            save_antiraid_data(data)

        embed = build_antiraid_embed(interaction.guild, data[gid])
        view = AntiraidSettingView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # -----------------------------------------------------
    # /固定メッセージ
    # -----------------------------------------------------

    @app_commands.command(
        name="固定メッセージ",
        description="固定メッセージを設定します（チャンネルにメッセージが送信されると自動で投稿されます）"
    )
    @app_commands.describe(
        channel="対象チャンネル",
        text="固定メッセージ本文"
    )
    async def fixed_message(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        text: str
    ):
        await interaction.response.defer(ephemeral=True)

        # 見出し＋改行ありの形式に整形
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

        data[gid][str(channel.id)] = {
            "channel_id": channel.id,
            "text": formatted,
            "message_id": None,
            "last_trigger_user_id": None,
        }
        save_fixed_message_data(data)

        try:
            msg = await channel.send(formatted)
            data[gid][str(channel.id)]["message_id"] = msg.id
            save_fixed_message_data(data)
        except discord.HTTPException as e:
            await interaction.followup.send(f"送信に失敗しました: {e}", ephemeral=True)
            return

        await interaction.followup.send(
            f"固定メッセージを設定しました。\n"
            f"このチャンネルにメッセージが送信されると、Botが自動で固定メッセージを投稿します。",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /固定メッセージ解除
    # -----------------------------------------------------

    @app_commands.command(
        name="固定メッセージ解除",
        description="固定メッセージを解除します"
    )
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
            options.append(discord.SelectOption(
                label=f"#{ch_name}: {preview}",
                value=cid
            ))

        view = FixedMessageRemoveView(options)
        await interaction.response.send_message("解除する固定メッセージを選択してください。", view=view, ephemeral=True)

    # -----------------------------------------------------
    # /自動リアクション（会話形式）
    # -----------------------------------------------------

    @app_commands.command(
        name="自動リアクション",
        description="指定チャンネルのメッセージに自動でリアクションします"
    )
    async def auto_reaction(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_auto_reaction_data()
        gid = str(interaction.guild.id)
        guild_data = data.get(gid, {})

        embed = build_auto_reaction_embed(interaction.guild, guild_data)
        view = AutoReactionSettingView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # -----------------------------------------------------
    # /自動リアクション解除
    # -----------------------------------------------------

    @app_commands.command(
        name="自動リアクション解除",
        description="自動リアクションを解除します"
    )
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
                options.append(discord.SelectOption(
                    label=f"#{ch_name} : {e}",
                    value=f"{cid}:{e}"
                ))

        if not options:
            return await interaction.response.send_message("解除できるリアクションがありません。", ephemeral=True)

        view = AutoReactionRemoveView(options)
        await interaction.response.send_message("解除する絵文字を選択してください（複数可）。", view=view, ephemeral=True)

    # -----------------------------------------------------
    # /ロール付与パネル
    # -----------------------------------------------------

    @app_commands.command(
        name="ロール付与パネル",
        description="リアクションでロールを付与するパネルを作成します"
    )
    @app_commands.describe(
        role1="1つ目のロール",
        emoji1="1つ目のロールの絵文字",
        role2="2つ目のロール（任意）",
        emoji2="2つ目のロールの絵文字（任意）",
        role3="3つ目のロール（任意）",
        emoji3="3つ目のロールの絵文字（任意）",
        role4="4つ目のロール（任意）",
        emoji4="4つ目のロールの絵文字（任意）",
        role5="5つ目のロール（任意）",
        emoji5="5つ目のロールの絵文字（任意）",
        role6="6つ目のロール（任意）",
        emoji6="6つ目のロールの絵文字（任意）",
        title="パネルのタイトル（任意）",
        description="パネルの説明（任意）",
    )
    async def role_panel(
        self,
        interaction: discord.Interaction,
        role1: discord.Role,
        emoji1: str,
        role2: discord.Role = None,
        emoji2: str = None,
        role3: discord.Role = None,
        emoji3: str = None,
        role4: discord.Role = None,
        emoji4: str = None,
        role5: discord.Role = None,
        emoji5: str = None,
        role6: discord.Role = None,
        emoji6: str = None,
        title: str = "ロール付与パネル",
        description: str = "以下のリアクションからロールを受け取ってください",
    ):
        if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )

        pairs = []
        for role, emoji in [
            (role1, emoji1),
            (role2, emoji2),
            (role3, emoji3),
            (role4, emoji4),
            (role5, emoji5),
            (role6, emoji6),
        ]:
            if role and emoji:
                if role.is_default() or role.managed:
                    continue
                pairs.append({"role_id": role.id, "emoji": emoji})

        if not pairs:
            return await interaction.response.send_message(
                "有効なロールと絵文字の組み合わせがありません。",
                ephemeral=True
            )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )

        lines = []
        for p in pairs:
            role = interaction.guild.get_role(p["role_id"])
            if role:
                lines.append(f"{p['emoji']} → {role.mention}")

        embed.add_field(
            name="リアクション一覧",
            value="\n".join(lines) if lines else "設定なし",
            inline=False
        )
        embed.set_footer(text="もう一度押すとロールが外れます / Developer @anzy1m")

        await interaction.response.send_message("パネルを作成しました。", ephemeral=True)
        message = await interaction.channel.send(embed=embed)

        for p in pairs:
            try:
                await message.add_reaction(p["emoji"])
            except Exception as e:
                print(f"リアクション付与失敗: {e}")

        data = load_role_panel_data()
        data[str(message.id)] = {
            "guild_id": interaction.guild.id,
            "pairs": pairs
        }
        save_role_panel_data(data)

    # -----------------------------------------------------
    # /招待キャンペーン
    # -----------------------------------------------------

    @app_commands.command(
        name="招待キャンペーン",
        description="招待キャンペーンを作成します"
    )
    @app_commands.describe(
        duration="キャンペーン期間（例: 1d, 1w）",
        title="キャンペーンタイトル",
        description="キャンペーン説明"
    )
    async def invite_campaign(
        self,
        interaction: discord.Interaction,
        duration: str,
        title: str,
        description: str
    ):
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
            "id": campaign_id,
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "title": title,
            "description": description,
            "end_time": end_time,
            "active": True,
            "user_links": {},
            "invite_map": {},
            "counts": {},
            "total_joins": 0,
            "join_members": []
        }
        save_invite_campaign_data(data)

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.add_field(name="期間", value=f"<t:{end_time}:R>", inline=False)

        view = InviteCampaignView(self, campaign_id)
        await interaction.response.send_message("キャンペーンを作成しました。", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

        # 終了タスク
        async def finish():
            await asyncio.sleep(seconds)
            d = load_invite_campaign_data()
            c = d.get(campaign_id)
            if not c or not c.get("active"):
                return
            c["active"] = False
            save_invite_campaign_data(d)

        asyncio.create_task(finish())

    # -----------------------------------------------------
    # /招待キャンペーン停止
    # -----------------------------------------------------

    @app_commands.command(
        name="招待キャンペーン停止",
        description="招待キャンペーンを停止します"
    )
    async def invite_campaign_stop(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_invite_campaign_data()
        gid = str(interaction.guild.id)
        options = []
        for cid, c in data.items():
            if c.get("guild_id") == interaction.guild.id and c.get("active"):
                options.append(discord.SelectOption(
                    label=c.get("title", cid)[:100],
                    value=cid
                ))

        if not options:
            return await interaction.response.send_message("停止できるキャンペーンがありません。", ephemeral=True)

        view = InviteCampaignStopView(options)
        await interaction.response.send_message("停止するキャンペーンを選択してください。", view=view, ephemeral=True)

    # -----------------------------------------------------
    # /定期メッセージ送信
    # -----------------------------------------------------

    @app_commands.command(
        name="定期メッセージ送信",
        description="指定したチャンネルに定期的にメッセージを送信します"
    )
    @app_commands.describe(
        channel="送信先チャンネル",
        text="送信するテキスト",
        interval="送信間隔（例: 1m, 1h, 1d, 1w）",
        image_url="画像URL（任意）"
    )
    async def periodic_message(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        text: str,
        interval: str,
        image_url: str = None
    ):
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
            "id": pm_id,
            "channel_id": channel.id,
            "text": text,
            "interval": seconds,
            "image_url": image_url,
            "last_sent": 0,
            "active": True
        }
        save_periodic_message_data(data)

        self._start_periodic_task(gid, pm_id, data[gid][pm_id])

        await interaction.response.send_message(
            f"定期メッセージを設定しました。\nチャンネル: {channel.mention}\n間隔: {interval}",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /定期メッセージ送信解除
    # -----------------------------------------------------

    @app_commands.command(
        name="定期メッセージ送信解除",
        description="定期メッセージを解除します"
    )
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
                options.append(discord.SelectOption(
                    label=f"#{ch_name}: {info['text'][:50]}",
                    value=pid
                ))

        if not options:
            return await interaction.response.send_message("解除できる定期メッセージがありません。", ephemeral=True)

        view = PeriodicMessageRemoveView(options)
        await interaction.response.send_message("解除する定期メッセージを選択してください。", view=view, ephemeral=True)

    # -----------------------------------------------------
    # /定期メッセージ送信確認
    # -----------------------------------------------------

    @app_commands.command(
        name="定期メッセージ送信確認",
        description="設定済みの定期メッセージを確認します"
    )
    async def periodic_message_check(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)

        data = load_periodic_message_data()
        gid = str(interaction.guild.id)
        items = data.get(gid, {})
        active_items = {k: v for k, v in items.items() if v.get("active")}

        if not active_items:
            return await interaction.response.send_message("設定済みの定期メッセージはありません。", ephemeral=True)

        embed = discord.Embed(
            title="定期メッセージ一覧",
            color=discord.Color.blurple()
        )

        for pid, info in active_items.items():
            channel = interaction.guild.get_channel(info["channel_id"])
            ch_name = channel.mention if channel else f"<#{info['channel_id']}>"
            embed.add_field(
                name=f"ID: {pid} / {ch_name}",
                value=(
                    f"間隔: {info['interval']}秒\n"
                    f"テキスト: {info['text'][:100]}\n"
                    f"画像: {info.get('image_url') or 'なし'}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

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
                target = p
                break

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
                target = p
                break

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

        # 自動リアクション
        data_ar = load_auto_reaction_data()
        gid = str(message.guild.id)
        if gid in data_ar and str(message.channel.id) in data_ar[gid]:
            for emoji in data_ar[gid][str(message.channel.id)]:
                try:
                    await message.add_reaction(emoji)
                except discord.HTTPException:
                    pass

        # 固定メッセージ
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

        # 荒らし対策
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
                await self._handle_antiraid_detection(
                    message,
                    "リンク検知しました。",
                    "リンクの送信は禁止されています。"
                )
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
                        await self._handle_antiraid_detection(
                            message,
                            "連投スパムを検知しました。",
                            "連投は禁止されています。"
                        )
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
                    f"{message.author.mention}\n\n"
                    f"{description}\n\n"
                    f"**メッセージ内容:**\n"
                    f"```{message.content[:1000]}```"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"User ID: {message.author.id}")

            view = AntiraidPunishView(
                message.author,
                f"{title} / メッセージID: {message.id}"
            )

            await message.channel.send(
                content=message.author.mention,
                embed=embed,
                view=view
            )
        except Exception as e:
            print(f"_handle_antiraid_detection error: {e}")

    # -----------------------------------------------------
    # 入室・退室イベント
    # -----------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            # 招待キャンペーンのカウント
            data = load_invite_campaign_data()
            for cid, campaign in data.items():
                if campaign.get("guild_id") != member.guild.id:
                    continue
                if not campaign.get("active"):
                    continue
                # 招待コードを特定（簡易的に invites を取得）
                try:
                    invites = await member.guild.invites()
                except discord.HTTPException:
                    invites = []

                used_code = None
                for inv in invites:
                    if inv.uses and inv.uses > 0:
                        # キャッシュと比較
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

            # 入室通知
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
                    f"🕰️ **アカウント作成からの経過:**\n"
                    f"{created_str}\n"
                    f"経過: {elapsed_str}\n\n"
                    f"👥 現在のサーバー人数: {member.guild.member_count}"
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            try:
                embed.set_thumbnail(url=member.display_avatar.url)
            except Exception:
                pass

            embed.set_author(
                name=f"{member.display_name}",
                icon_url=member.display_avatar.url if member.display_avatar else None
            )

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
                    f"🕰️ **アカウント作成からの経過:**\n"
                    f"{created_str}\n"
                    f"経過: {elapsed_str}\n\n"
                    f"👥 現在のサーバー人数: {member.guild.member_count}"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            try:
                embed.set_thumbnail(url=member.display_avatar.url)
            except Exception:
                pass

            embed.set_author(
                name=f"{member.display_name}",
                icon_url=member.display_avatar.url if member.display_avatar else None
            )

            await channel.send(embed=embed)
        except Exception as e:
            print(f"on_member_remove error: {e}")

    # -----------------------------------------------------
    # 招待キャッシュ初期化
    # -----------------------------------------------------

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
