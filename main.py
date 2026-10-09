
import discord
from discord.ext import commands
from discord import app_commands
import os
import traceback
import random
import asyncio
import re
import time
from flask import Flask
from threading import Thread

# =========================
# Render Web Server
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
# NUKE
# =========================

@bot.tree.command(
    name="nuke",
    description="現在のチャンネルを複製して再作成します"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def nuke(interaction: discord.Interaction):
    channel = interaction.channel
    guild = interaction.guild

    if guild is None or not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "サーバーのテキストチャンネルで実行してください。",
            ephemeral=True
        )
        return

    me = guild.me

    if me is None or not me.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "Botにチャンネル管理権限がありません。",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    new_channel = None

    try:
        old_position = channel.position
        old_category = channel.category

        # 元の設定・権限を複製
        new_channel = await channel.clone(
            name=channel.name,
            reason=f"Nuke requested by {interaction.user}"
        )

        # カテゴリーと位置を設定
        await new_channel.edit(
            category=old_category,
            position=old_position
        )

        # 複製に成功してから元のチャンネルを削除
        await channel.delete(
            reason=f"Nuke requested by {interaction.user}"
        )

        await new_channel.send("**nukeが完了しました。**")

        await interaction.followup.send(
            f"完了しました: {new_channel.mention}",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "権限不足です。Botのチャンネル管理権限を確認してください。",
            ephemeral=True
        )

    except discord.HTTPException as e:
        await interaction.followup.send(
            f"Discord APIエラー: {e}",
            ephemeral=True
        )


@nuke.error
async def nuke_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "チャンネル管理権限が必要です。"
    else:
        message = "nukeの実行中にエラーが発生しました。"
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(
            message, ephemeral=True
        )


# =========================
# GIVEAWAY
# =========================

def parse_duration(value: str):
    value = value.strip().lower()

    match = re.fullmatch(r"(\d+)\s*(m|h|d|week|w)", value)

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if amount <= 0:
        return None

    multipliers = {
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
        "week": 604800
    }

    return amount * multipliers[unit]


DURATION_HELP = (
    "`30m` = 30分\n"
    "`1h` = 1時間\n"
    "`1d` = 1日\n"
    "`1week` = 1週間\n"
    "`1w` = 1週間"
)


class GiveawayView(discord.ui.View):
    def __init__(self, prize, winner_count, end_time):
        super().__init__(timeout=None)
        self.prize = prize
        self.winner_count = winner_count
        self.end_time = end_time
        self.participants = set()
        self.message = None
        self.finished = False
        self.lock = asyncio.Lock()

    @discord.ui.button(
        label="🎉 参加する",
        style=discord.ButtonStyle.primary,
        custom_id="giveaway:join"
    )
    async def join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        async with self.lock:
            if self.finished or time.time() >= self.end_time:
                await interaction.response.send_message(
                    "この企画は終了しています。",
                    ephemeral=True
                )
                return

            if interaction.user.bot:
                await interaction.response.send_message(
                    "Botは参加できません。",
                    ephemeral=True
                )
                return

            user_id = interaction.user.id

            if user_id in self.participants:
                self.participants.remove(user_id)
                message = "参加を取り消しました。"
            else:
                self.participants.add(user_id)
                message = "企画への参加が完了しました！"

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

    async def finish(self):
        await asyncio.sleep(max(0, self.end_time - time.time()))

        async with self.lock:
            if self.finished:
                return

            self.finished = True
            participants = list(self.participants)

        if self.message is None:
            return

        winners = random.sample(
            participants,
            min(self.winner_count, len(participants))
        ) if participants else []

        embed = self.message.embeds[0]
        embed.title = "🎉 Giveaway 終了！"
        embed.add_field(
            name="当選者",
            value=(
                ", ".join(f"<@{uid}>" for uid in winners)
                if winners
                else "参加者がいなかったため、当選者はいません。"
            ),
            inline=False
        )

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        try:
            await self.message.edit(embed=embed, view=self)

            if winners:
                await self.message.channel.send(
                    f"🎉 **{self.prize}** の当選者: "
                    + ", ".join(f"<@{uid}>" for uid in winners),
                    allowed_mentions=discord.AllowedMentions(
                        users=True
                    )
                )

        except discord.HTTPException:
            traceback.print_exc()


@bot.tree.command(
    name="giveaway",
    description="景品の配布企画を作成します"
)
@app_commands.describe(
    prize="配布する景品",
    duration="開催時間（30m=30分、1d=1日、1week=1週間）",
    winners="当選人数"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def giveaway(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: app_commands.Range[int, 1, 100] = 1
):
    seconds = parse_duration(duration)

    if seconds is None:
        await interaction.response.send_message(
            "時間の形式が正しくありません。\n" + DURATION_HELP,
            ephemeral=True
        )
        return

    end_time = time.time() + seconds
    end_timestamp = int(end_time)

    embed = discord.Embed(
        title="🎉 Giveaway 開催中！",
        description=(
            f"**景品:** {prize}\n"
            f"**当選人数:** {winners}人\n"
            f"**終了時間:** <t:{end_timestamp}:F>\n"
            f"**残り時間:** <t:{end_timestamp}:R>\n\n"
            "下のボタンを押して参加してください！"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="開催時間の指定方法",
        value=DURATION_HELP,
        inline=False
    )

    view = GiveawayView(prize, winners, end_time)

    await interaction.response.send_message(
        embed=embed,
        view=view
    )

    view.message = await interaction.original_response()
    asyncio.create_task(view.finish())


@giveaway.error
async def giveaway_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "このコマンドにはサーバー管理権限が必要です。"
    else:
        message = "企画の作成に失敗しました。"
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(
            message, ephemeral=True
        )


# =========================
# VERIFY
# =========================

async def grant_verified_role(
    interaction: discord.Interaction,
    role: discord.Role
):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "サーバー内で実行してください。",
            ephemeral=True
        )
        return

    member = guild.get_member(interaction.user.id)

    if member is None:
        await interaction.response.send_message(
            "メンバー情報を取得できませんでした。",
            ephemeral=True
        )
        return

    me = guild.me

    if me is None or not me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "Botにロールの管理権限がありません。",
            ephemeral=True
        )
        return

    if role.is_default() or role.managed or role >= me.top_role:
        await interaction.response.send_message(
            "認証済みロールをBotのロールより下に配置してください。",
            ephemeral=True
        )
        return

    if role in member.roles:
        await interaction.response.send_message(
            "すでに認証済みです。",
            ephemeral=True
        )
        return

    try:
        await member.add_roles(
            role,
            reason="Server verification"
        )

        await interaction.response.send_message(
            "✅ 認証が完了しました！",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "ロールを付与できません。Botの権限とロール位置を確認してください。",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "ロールの付与に失敗しました。",
            ephemeral=True
        )


class MathVerifyModal(discord.ui.Modal):
    def __init__(self, role: discord.Role):
        super().__init__(title="計算式認証")
        self.role = role

        a = random.randint(1, 10)
        b = random.randint(1, 10)
        operator = random.choice(["+", "-", "×"])

        if operator == "+":
            self.answer = a + b
        elif operator == "-":
            if a < b:
                a, b = b, a
            self.answer = a - b
        else:
            self.answer = a * b

        self.question = discord.ui.TextInput(
            label=f"{a} {operator} {b} = ?",
            placeholder="答えを入力してください",
            required=True,
            max_length=10
        )

        self.add_item(self.question)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            answer = int(self.question.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "数字を入力してください。",
                ephemeral=True
            )
            return

        if answer != self.answer:
            await interaction.response.send_message(
                "答えが違います。もう一度認証してください。",
                ephemeral=True
            )
            return

        await grant_verified_role(interaction, self.role)


class VerifyView(discord.ui.View):
    def __init__(self, verify_type: str, role: discord.Role):
        super().__init__(timeout=None)
        self.verify_type = verify_type
        self.role = role

        self.verify_button.label = (
            "🧮 計算式に回答する"
            if verify_type == "math"
            else "✅ 認証する"
        )

        self.verify_button.custom_id = (
            f"verify:{verify_type}"
        )

    @discord.ui.button(
        label="認証する",
        style=discord.ButtonStyle.success
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.verify_type == "math":
            await interaction.response.send_modal(
                MathVerifyModal(self.role)
            )
        else:
            await grant_verified_role(interaction, self.role)


@bot.tree.command(
    name="verify",
    description="認証パネルを作成します"
)
@app_commands.describe(
    type="認証方式：計算式またはボタン式",
    role="認証成功時に付与するロール",
    title="認証パネルのタイトル（任意）",
    description="認証パネルの説明（任意）"
)
@app_commands.choices(
    type=[
        app_commands.Choice(name="計算式", value="math"),
        app_commands.Choice(name="ボタン式", value="button")
    ]
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verify(
    interaction: discord.Interaction,
    type: app_commands.Choice[str],
    role: discord.Role,
    title: str = "サーバー認証",
    description: str = "下のボタンから認証を行ってください。"
):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "サーバー内で実行してください。",
            ephemeral=True
        )
        return

    me = guild.me

    if me is None or not me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "Botにロールの管理権限がありません。",
            ephemeral=True
        )
        return

    if role.is_default() or role.managed or role >= me.top_role:
        await interaction.response.send_message(
            "認証済みロールをBotのロールより下に配置してください。",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )

    if type.value == "math":
        embed.add_field(
            name="計算式認証",
            value="ボタンを押し、表示された計算問題に回答してください。",
            inline=False
        )
    else:
        embed.add_field(
            name="ボタン認証",
            value="下の認証ボタンを押してください。",
            inline=False
        )

    embed.set_footer(
        text="認証に成功すると認証済みロールが付与されます。"
    )

    view = VerifyView(type.value, role)

    await interaction.response.send_message(
        embed=embed,
        view=view
    )


@verify.error
async def verify_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "このコマンドにはサーバー管理権限が必要です。"
    else:
        message = "認証パネルの作成に失敗しました。"
        traceback.print_exception(
            type(error), error, error.__traceback__
        )

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(
            message, ephemeral=True
        )


# =========================
# 起動
# =========================

if __name__ == "__main__":
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()

    bot.run(TOKEN)
