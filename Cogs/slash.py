
import asyncio
import random
import re
import time

import discord
from discord import app_commands
from discord.ext import commands


# ==============================
# 時間変換
# 例: 30m / 1h / 1d / 1week
# ==============================

def parse_duration(value: str) -> int:
    value = value.strip().lower()

    match = re.fullmatch(
        r"(\d+)\s*(m|h|d|w|minute|minutes|hour|hours|day|days|week|weeks)",
        value
    )

    if not match:
        raise ValueError(
            "時間の形式が正しくありません。例: 30m、2h、1d、1week"
        )

    amount = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "m": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "w": 604800,
        "week": 604800,
        "weeks": 604800,
    }

    seconds = amount * multipliers[unit]

    if amount < 1 or seconds > 365 * 86400:
        raise ValueError("時間は1以上、1年以内にしてください。")

    return seconds


# ==============================
# Nuke
# ==============================

class ConfirmNukeView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=30)
        self.channel = channel

    @discord.ui.button(
        label="チャンネルを再作成する",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
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
                reason=f"Nuke executed by {interaction.user}"
            )

            await new_channel.edit(
                category=old_channel.category,
                position=old_channel.position,
                reason="Nuke channel recreation"
            )

            await old_channel.delete(
                reason=f"Nuke executed by {interaction.user}"
            )

            await new_channel.send("**nukeが完了しました。**")

        except discord.Forbidden:
            if not old_channel.deleted:
                await interaction.followup.send(
                    "Botにチャンネル管理権限がありません。",
                    ephemeral=True
                )
        except discord.HTTPException as error:
            await interaction.followup.send(
                f"チャンネルの再作成に失敗しました: {error}",
                ephemeral=True
            )

        self.stop()

    @discord.ui.button(
        label="キャンセル",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="キャンセルしました。",
            view=None
        )
        self.stop()


# ==============================
# Giveaway
# ==============================

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.participants = set()
        self.ended = False

    @discord.ui.button(
        label="🎉 参加する",
        style=discord.ButtonStyle.success,
        custom_id="slash_giveaway_join"
    )
    async def join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.ended:
            await interaction.response.send_message(
                "この抽選は終了しています。",
                ephemeral=True
            )
            return

        if interaction.user.id in self.participants:
            self.participants.remove(interaction.user.id)
            message = "参加を取り消しました。"
        else:
            self.participants.add(interaction.user.id)
            message = "抽選に参加しました！"

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


# ==============================
# Verify
# ==============================

class MathAnswerModal(discord.ui.Modal):
    def __init__(
        self,
        cog,
        role: discord.Role,
        number1: int,
        number2: int
    ):
        super().__init__(title="認証")
        self.cog = cog
        self.role = role
        self.answer = number1 + number2

        self.answer_input = discord.ui.TextInput(
            label=f"{number1} + {number2} の答え",
            placeholder="答えを入力",
            required=True,
            max_length=10
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "サーバー内で実行してください。",
                ephemeral=True
            )
            return

        if not self.answer_input.value.strip().isdigit():
            await interaction.response.send_message(
                "数字を入力してください。",
                ephemeral=True
            )
            return

        if int(self.answer_input.value.strip()) != self.answer:
            await interaction.response.send_message(
                "答えが違います。もう一度お試しください。",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            try:
                member = await interaction.guild.fetch_member(
                    interaction.user.id
                )
            except discord.HTTPException:
                await interaction.response.send_message(
                    "ユーザー情報を取得できませんでした。",
                    ephemeral=True
                )
                return

        try:
            await member.add_roles(
                self.role,
                reason="Verification completed"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Botのロールが認証ロールより上にあるか確認してください。",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "ロール付与に失敗しました。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"認証成功！ {self.role.mention} を付与しました。",
            ephemeral=True
        )


class VerifyView(discord.ui.View):
    def __init__(self, cog, role: discord.Role, verify_type: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.role = role
        self.verify_type = verify_type

        if verify_type == "button":
            self.verify_button.label = "✅ 認証する"
            self.verify_button.custom_id = f"verify_button_{role.id}"
        else:
            self.verify_button.label = "🧮 計算して認証"
            self.verify_button.custom_id = f"verify_math_{role.id}"

    @discord.ui.button(
        label="認証する",
        style=discord.ButtonStyle.primary,
        custom_id="verify_button_default"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.verify_type == "button":
            if not interaction.guild:
                await interaction.response.send_message(
                    "サーバー内で実行してください。",
                    ephemeral=True
                )
                return

            member = interaction.guild.get_member(interaction.user.id)

            if member is None:
                try:
                    member = await interaction.guild.fetch_member(
                        interaction.user.id
                    )
                except discord.HTTPException:
                    await interaction.response.send_message(
                        "ユーザー情報を取得できませんでした。",
                        ephemeral=True
                    )
                    return

            if self.role in member.roles:
                await interaction.response.send_message(
                    "すでに認証済みです。",
                    ephemeral=True
                )
                return

            try:
                await member.add_roles(
                    self.role,
                    reason="Verification completed"
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "Botのロールを認証ロールより上に移動してください。",
                    ephemeral=True
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(
                    "ロール付与に失敗しました。",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"認証成功！ {self.role.mention} を付与しました。",
                ephemeral=True
            )

        else:
            number1 = random.randint(1, 20)
            number2 = random.randint(1, 20)

            await interaction.response.send_modal(
                MathAnswerModal(
                    self.cog,
                    self.role,
                    number1,
                    number2
                )
            )


# ==============================
# Slash Cog
# ==============================

class SlashCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_giveaways = {}

    # ==============================
    # /nuke
    # ==============================

    @app_commands.command(
        name="nuke",
        description="現在のチャンネルを再作成します"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def nuke(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "テキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "本当にこのチャンネルを再作成しますか？\n"
            "現在のメッセージ履歴は引き継がれません。",
            view=ConfirmNukeView(interaction.channel),
            ephemeral=True
        )

    @nuke.error
    async def nuke_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "このコマンドにはチャンネル管理権限が必要です。"
        else:
            message = "コマンドの実行中にエラーが発生しました。"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    # ==============================
    # /giveaway
    # ==============================

    @app_commands.command(
        name="giveaway",
        description="景品の抽選を開始します"
    )
    @app_commands.describe(
        prize="景品名",
        duration="時間（例: 30m、1h、1d、1week）",
        winners="当選人数"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(
        self,
        interaction: discord.Interaction,
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

        if not interaction.guild or not isinstance(
            interaction.channel, discord.TextChannel
        ):
            await interaction.response.send_message(
                "サーバーのテキストチャンネルで使用してください。",
                ephemeral=True
            )
            return

        end_timestamp = int(time.time() + seconds)

        embed = discord.Embed(
            title="🎉 Giveaway",
            description=(
                f"**景品:** {prize}\n"
                f"**当選人数:** {winners}人\n"
                f"**終了:** <t:{end_timestamp}:R>\n\n"
                "参加するには下のボタンを押してください！"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"主催者: {interaction.user}")

        view = GiveawayView()

        await interaction.response.send_message(
            "抽選を開始しました。",
            ephemeral=True
        )

        giveaway_message = await interaction.channel.send(
            embed=embed,
            view=view
        )

        self.active_giveaways[giveaway_message.id] = view

        await asyncio.sleep(seconds)

        view.ended = True
        view.stop()

        try:
            await giveaway_message.edit(view=None)
        except discord.HTTPException:
            pass

        participant_ids = list(view.participants)

        if not participant_ids:
            result = "参加者がいなかったため、抽選は終了しました。"
        else:
            chosen_ids = random.sample(
                participant_ids,
                min(winners, len(participant_ids))
            )
            mentions = " ".join(f"<@{user_id}>" for user_id in chosen_ids)
            result = (
                f"🎉 **{prize}** の抽選が終了しました！\n"
                f"当選者: {mentions}"
            )

        try:
            await interaction.channel.send(result)
        except discord.HTTPException:
            pass

        self.active_giveaways.pop(giveaway_message.id, None)

    @giveaway.error
    async def giveaway_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "このコマンドにはサーバー管理権限が必要です。"
        else:
            message = "コマンドの実行中にエラーが発生しました。"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    # ==============================
    # /verify
    # ==============================

    @app_commands.command(
        name="verify",
        description="認証パネルを作成します"
    )
    @app_commands.describe(
        type="認証方法",
        role="認証成功時に付与するロール",
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
        interaction: discord.Interaction,
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
                "このロールは認証ロールに設定できません。",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Verification")

        view = VerifyView(self, role, type.value)

        await interaction.response.send_message(
            "認証パネルを作成しました。",
            ephemeral=True
        )

        await interaction.channel.send(
            embed=embed,
            view=view
        )

    @verify.error
    async def verify_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "このコマンドにはサーバー管理権限が必要です。"
        else:
            message = "コマンドの実行中にエラーが発生しました。"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCog(bot))
