import asyncio
import json
import os
import random
import re
import time
import uuid

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
# TICKET
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

        category = interaction.guild.get_channel(panel["category_id"])
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "カテゴリーが見つかりません。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        channel_name = f"ticket-{interaction.user.name}"[:100]

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

        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"ticket_owner:{interaction.user.id}:panel:{self.panel_id}"
            )
        except discord.HTTPException as error:
            await interaction.followup.send(
                f"チケットの作成に失敗しました: {error}",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=panel.get("embed_title") or "チケット",
            description=panel.get("embed_description") or "サポートします。",
            color=discord.Color.blurple()
        )
        if panel.get("embed_image"):
            embed.set_image(url=panel["embed_image"])

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

def status_embed(panel):
    colors = {
        "対応不可": discord.Color.red(),
        "対応遅延": discord.Color.orange(),
        "対応可能": discord.Color.green()
    }

    embed = discord.Embed(
        title="対応状況",
        description=panel["description"],
        color=colors[panel["status"]]
    )

    embed.add_field(
        name="現在の状態",
        value=f"{panel['emoji']} **{panel['status']}**",
        inline=False
    )
    embed.add_field(
        name="一言",
        value=panel["message"] or "設定なし",
        inline=False
    )
    return embed


class StatusMessageModal(discord.ui.Modal):
    def __init__(self, cog, panel_id):
        super().__init__(title="一言を変更")
        self.cog = cog
        self.panel_id = panel_id

        self.message_input = discord.ui.TextInput(
            label="一言",
            placeholder="現在の状況など",
            required=False,
            max_length=200
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction):
        panel = self.cog.status_panels.get(self.panel_id)

        if not panel or interaction.user.id != panel["creator_id"]:
            await interaction.response.send_message(
                "このパネルの作成者だけが変更できます。",
                ephemeral=True
            )
            return

        panel["message"] = self.message_input.value.strip()
        await self.cog.refresh_status(panel)

        await interaction.response.send_message(
            "一言を更新しました。",
            ephemeral=True
        )


class StatusView(discord.ui.View):
    def __init__(self, cog, panel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.panel_id = panel_id
        self.status_select.custom_id = f"status_select_{panel_id}"
        self.message_button.custom_id = f"status_message_{panel_id}"

    async def check_creator(self, interaction):
        panel = self.cog.status_panels.get(self.panel_id)

        if not panel:
            await interaction.response.send_message(
                "パネルが見つかりません。",
                ephemeral=True
            )
            return False

        if interaction.user.id != panel["creator_id"]:
            await interaction.response.send_message(
                "このパネルを変更できるのは作成者本人だけです。",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.select(
        placeholder="対応状況を変更",
        options=[
            discord.SelectOption(
                label="対応不可", value="対応不可", emoji="🔴"
            ),
            discord.SelectOption(
                label="対応遅延", value="対応遅延", emoji="🟠"
            ),
            discord.SelectOption(
                label="対応可能", value="対応可能", emoji="🟢"
            )
        ],
        custom_id="status_select_default"
    )
    async def status_select(self, interaction, select):
        if not await self.check_creator(interaction):
            return

        panel = self.cog.status_panels[self.panel_id]
        panel["status"] = select.values[0]
        panel["emoji"] = {
            "対応不可": "🔴",
            "対応遅延": "🟠",
            "対応可能": "🟢"
        }[panel["status"]]

        await self.cog.refresh_status(panel)
        await interaction.response.send_message(
            f"状態を「{panel['status']}」に変更しました。",
            ephemeral=True
        )

    @discord.ui.button(
        label="✏️ 一言変更",
        style=discord.ButtonStyle.primary,
        custom_id="status_message_default"
    )
    async def message_button(self, interaction, button):
        if not await self.check_creator(interaction):
            return

        await interaction.response.send_modal(
            StatusMessageModal(self.cog, self.panel_id)
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
            discord.SelectOption(label="埋め込み画像", value="embed_image"),
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
            elif field == "embed_image":
                panel["embed_image"] = value
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
# MAIN COG
# =========================================================

class SlashCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        self.ended_giveaways = {}
        self.vouch_panels = {}
        self.status_panels = {}
        self.ticket_panels = {}

    async def refresh_status(self, panel):
        channel = self.bot.get_channel(panel["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(panel["message_id"])
            await message.edit(embed=status_embed(panel))
        except discord.HTTPException:
            pass

    # -----------------------------------------------------
    # /nuke
    # -----------------------------------------------------

    @app_commands.command(
        name="nuke",
        description="現在のテキストチャンネルを再作成します"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
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
    # /配布作成 (作成と同時に開始)
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
    @app_commands.checks.has_permissions(manage_guild=True)
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
    # /配布終了 (即座に終了して当選者発表)
    # -----------------------------------------------------

    @app_commands.command(
        name="配布終了",
        description="開催中の配布を選択して即座に終了し、当選者を発表します"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
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
    @app_commands.checks.has_permissions(manage_guild=True)
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
        description="埋め込みメッセージを送信します"
    )
    @app_commands.describe(
        title="埋め込みのタイトル",
        description="埋め込みの説明",
        color="色（例: ff0000、00ff00）",
        footer="フッター",
        image="画像URL"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def embed(
        self,
        interaction,
        title: str,
        description: str,
        color: str = None,
        footer: str = None,
        image: str = None
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
        if image:
            embed.set_image(url=image)

        await interaction.response.send_message(
            "埋め込みを送信しました。",
            ephemeral=True
        )
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
    @app_commands.checks.has_permissions(manage_guild=True)
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
    @app_commands.checks.has_permissions(manage_guild=True)
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
    @app_commands.checks.has_permissions(manage_guild=True)
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
        description="対応状況パネルを作成します"
    )
    @app_commands.describe(
        description="パネル説明",
        status="最初の対応状況",
        message="一言"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="対応不可", value="対応不可"),
            app_commands.Choice(name="対応遅延", value="対応遅延"),
            app_commands.Choice(name="対応可能", value="対応可能")
        ]
    )
    async def status(
        self,
        interaction,
        description: str = "現在の対応状況です。",
        status: app_commands.Choice[str] = None,
        message: str = ""
    ):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        selected_status = status.value if status else "対応可能"
        emojis = {
            "対応不可": "🔴",
            "対応遅延": "🟠",
            "対応可能": "🟢"
        }

        panel_id = uuid.uuid4().hex[:10]

        panel = {
            "id": panel_id,
            "creator_id": interaction.user.id,
            "title": "対応状況",
            "description": description,
            "status": selected_status,
            "emoji": emojis[selected_status],
            "message": message,
            "channel_id": interaction.channel.id,
            "message_id": None
        }

        view = StatusView(self, panel_id)

        await interaction.response.send_message(
            "ステータスパネルを作成しました。",
            ephemeral=True
        )

        panel_message = await interaction.channel.send(
            embed=status_embed(panel),
            view=view
        )

        panel["message_id"] = panel_message.id
        self.status_panels[panel_id] = panel

    # -----------------------------------------------------
    # /チケット
    # -----------------------------------------------------

    @app_commands.command(
        name="チケット",
        description="チケットパネルを作成します"
    )
    @app_commands.describe(
        button_label="ボタンの名前",
        max_tickets="1人が作成できるチケット数",
        mention_role="チケット作成時にメンションするロール",
        category="チケットを作成するカテゴリー",
        delete_permission="削除権限（管理者 or 全員）",
        embed_title="埋め込みタイトル（任意）",
        embed_description="埋め込み説明（任意）",
        embed_image="埋め込み画像URL（任意）",
        welcome_message="チケット作成後のメッセージ（任意）",
        archive_channel="削除されたときのログチャンネル（任意）"
    )
    @app_commands.choices(
        delete_permission=[
            app_commands.Choice(name="管理者", value="admin"),
            app_commands.Choice(name="全員", value="everyone")
        ]
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket(
        self,
        interaction,
        button_label: str,
        max_tickets: app_commands.Range[int, 1, 10],
        mention_role: discord.Role,
        category: discord.CategoryChannel,
        delete_permission: app_commands.Choice[str],
        embed_title: str = None,
        embed_description: str = None,
        embed_image: str = None,
        welcome_message: str = None,
        archive_channel: discord.TextChannel = None
    ):
        panel_id = uuid.uuid4().hex[:10]

        self.ticket_panels[panel_id] = {
            "id": panel_id,
            "button_label": button_label,
            "max_tickets": max_tickets,
            "mention_role_id": mention_role.id,
            "embed_title": embed_title,
            "embed_description": embed_description,
            "embed_image": embed_image,
            "welcome_message": welcome_message,
            "delete_permission": delete_permission.value,
            "category_id": category.id,
            "archive_channel_id": archive_channel.id if archive_channel else None,
            "channel_id": interaction.channel.id,
            "message_id": None
        }

        embed = discord.Embed(
            title="🎫 チケット",
            description=f"下のボタンからチケットを作成できます。\n1人につき最大 {max_tickets} 件まで。",
            color=discord.Color.blurple()
        )

        view = TicketPanelView(self, panel_id)
        view.create_button.label = button_label

        await interaction.response.send_message(
            "チケットパネルを作成しました。",
            ephemeral=True
        )

        message = await interaction.channel.send(embed=embed, view=view)
        self.ticket_panels[panel_id]["message_id"] = message.id

    # -----------------------------------------------------
    # /チケットパネル編集
    # -----------------------------------------------------

    @app_commands.command(
        name="チケットパネル編集",
        description="チケットパネルを編集します"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
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


# =========================================================
# EXTENSION SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCog(bot))
