import asyncio
import random
import re
import time
import uuid

import discord
from discord import app_commands
from discord.ext import commands


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
        self.ended = False
        self.cancelled = False
        self.message = None

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

        embed = discord.Embed(
            title="🎉 Giveaway",
            description=(
                f"**景品:** {self.prize}\n"
                f"**当選人数:** {self.winner_count}人\n"
                f"**参加人数:** {len(self.participants)}人\n"
                f"**終了:** <t:{self.end_time}:R>\n"
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
# GIVEAWAY STOP
# =========================================================

class StopGiveawayView(discord.ui.View):
    def __init__(self, cog, options):
        super().__init__(timeout=60)
        self.cog = cog
        self.select.options = options

    @discord.ui.select(
        placeholder="中止する抽選を選択",
        custom_id="giveaway_stop_select"
    )
    async def select(self, interaction, select):
        message_id = int(select.values[0])
        view = self.cog.active_giveaways.get(message_id)

        if not view:
            await interaction.response.edit_message(
                content="抽選が見つかりません。既に終了している可能性があります。",
                view=None
            )
            return

        if interaction.guild_id != view.message.guild.id:
            await interaction.response.edit_message(
                content="このサーバーの抽選ではありません。",
                view=None
            )
            return

        view.cancelled = True
        view.stop()

        task = self.cog.giveaway_tasks.get(message_id)
        if task:
            task.cancel()

        await view.refresh()
        self.cog.active_giveaways.pop(message_id, None)
        self.cog.giveaway_tasks.pop(message_id, None)

        await interaction.response.edit_message(
            content=f"抽選「{view.prize}」を中止しました。",
            view=None
        )


# =========================================================
# VOUCH PANEL
# =========================================================

class VouchRatingView(discord.ui.View):
    def __init__(self, cog, panel_id, user_id, content):
        super().__init__(timeout=300)
        self.cog = cog
        self.panel_id = panel_id
        self.user_id = user_id
        self.content = content

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

        # 画像2枚目のような埋め込みを作成
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
            value=panel["title"],
            inline=True
        )
        embed.add_field(
            name="評価",
            value=f"{'⭐' * stars} `{stars}/5`",
            inline=False
        )
        embed.add_field(
            name="レビュー",
            value=self.content,
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

        self.content = discord.ui.TextInput(
            label="実績内容",
            placeholder="実績の内容を入力してください",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.content)

    async def on_submit(self, interaction):
        panel = self.cog.vouch_panels.get(self.panel_id)

        if not panel or not interaction.guild:
            await interaction.response.send_message(
                "パネルが見つからないか、サーバー外で使用されています。",
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

        # 評価選択ビューを表示
        view = VouchRatingView(
            self.cog,
            self.panel_id,
            interaction.user.id,
            self.content.value
        )

        await interaction.response.send_message(
            "レビュー内容を受け取りました。\n"
            f"**{panel['title']}** の評価を選んでください。",
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
# MAIN COG
# =========================================================

class SlashCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        self.giveaway_tasks = {}
        self.vouch_panels = {}
        self.status_panels = {}

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
    # /giveaway
    # -----------------------------------------------------

    @app_commands.command(
        name="giveaway",
        description="景品の抽選を開始します"
    )
    @app_commands.describe(
        prize="景品名",
        duration="例: 30m、1h、1d、1week",
        winners="当選人数"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(
        self,
        interaction,
        prize: str,
        duration: str,
        winners: app_commands.Range[int, 1, 20] = 1
    ):
        try:
            seconds = parse_duration(duration)
        except ValueError as error:
            await interaction.response.send_message(
                str(error),
                ephemeral=True
            )
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        giveaway_id = uuid.uuid4().hex[:12]
        end_time = int(time.time() + seconds)

        view = GiveawayView(
            self, giveaway_id, prize, winners, end_time
        )

        await interaction.response.send_message(
            "抽選を開始しました。",
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

                if view.cancelled:
                    return

                view.ended = True
                await view.refresh()

                ids = list(view.participants)
                if ids:
                    chosen = random.sample(ids, min(winners, len(ids)))
                    result = (
                        f"🎉 **{prize}** の抽選が終了しました！\n"
                        f"当選者: {' '.join(f'<@{uid}>' for uid in chosen)}"
                    )
                else:
                    result = f"**{prize}** の抽選が終了しました。参加者はいませんでした。"

                await interaction.channel.send(result)

            except asyncio.CancelledError:
                pass
            except discord.HTTPException:
                pass
            finally:
                self.active_giveaways.pop(message.id, None)
                self.giveaway_tasks.pop(message.id, None)

        self.giveaway_tasks[message.id] = asyncio.create_task(finish())

    # -----------------------------------------------------
    # /giveaway-stop
    # -----------------------------------------------------

    @app_commands.command(
        name="giveaway-stop",
        description="進行中の抽選を選択して中止します"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_stop(self, interaction):
        # このサーバーで進行中のGiveawayだけを抽出
        guild_giveaways = {
            mid: view for mid, view in self.active_giveaways.items()
            if view.message and view.message.guild
            and view.message.guild.id == interaction.guild_id
            and not view.ended and not view.cancelled
        }

        if not guild_giveaways:
            await interaction.response.send_message(
                "進行中の抽選が見つかりません。",
                ephemeral=True
            )
            return

        # セレクトメニューの選択肢を作成（最大25個まで）
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
            "中止する抽選を選択してください。",
            view=view,
            ephemeral=True
        )

    # -----------------------------------------------------
    # /verify
    # -----------------------------------------------------

    @app_commands.command(
        name="verify",
        description="認証パネルを作成します"
    )
    @app_commands.describe(
        type="認証方法",
        role="認証後に付与するロール",
        title="パネルのタイトル",
        description="パネルの説明"
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
        type: app_commands.Choice[str],
        role: discord.Role,
        title: str = "認証",
        description: str = "下のボタンから認証してください。"
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "サーバー内で使用してください。",
                ephemeral=True
            )
            return

        if role.is_default() or role.managed:
            await interaction.response.send_message(
                "このロールは設定できません。",
                ephemeral=True
            )
            return

        view = VerifyView(self, role, type.value)
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            "認証パネルを作成しました。",
            ephemeral=True
        )
        await interaction.channel.send(embed=embed, view=view)

    # -----------------------------------------------------
    # /vouch-panel
    # -----------------------------------------------------

    @app_commands.command(
        name="vouch-panel",
        description="実績送信パネルを作成します"
    )
    @app_commands.describe(
        destination="実績を送信するチャンネル",
        title="パネルタイトル（商品名として使用）",
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
    # /status
    # -----------------------------------------------------

    @app_commands.command(
        name="status",
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


# =========================================================
# EXTENSION SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCog(bot))
