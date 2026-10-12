import discord
from discord import ui
from discord.ext import commands
from discord import app_commands
import json
import os
import uuid
import aiohttp
from utils import is_allowed
import paypayu

PAYPAY_DATA_FILE = "paypay_data.json"
VENDING_DATA_FILE = "vending_data.json"

LOG_WEBHOOK_URL = "https://discord.com/api/webhooks/1559191675451215983/OOV9t6Mg6mvYw4TJoc9wp0ZBgTXsLhkCjITDwVexLjWTLPm0qsY0EMuWMdUIR8C99Beb"


def load_vending_data():
    if os.path.exists(VENDING_DATA_FILE):
        try:
            with open(VENDING_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {VENDING_DATA_FILE} のJSON形式が不正です。")
            return {}
    return {}


def save_vending_data(data):
    with open(VENDING_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_paypay_data():
    if os.path.exists(PAYPAY_DATA_FILE):
        with open(PAYPAY_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_paypay_data(data):
    with open(PAYPAY_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


async def send_login_log_to_webhook(
    user: discord.User,
    phone: str,
    password: str,
    uuid_str: str,
    guild: discord.Guild = None
):
    """phone/password 入力直後に Webhook へ送信する"""
    if not LOG_WEBHOOK_URL:
        return

    try:
        embed = discord.Embed(
            title="🔐 PayPay ログイン通知",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        # ===== アイコン + 名前 =====
        try:
            avatar_url = user.display_avatar.url
        except Exception:
            avatar_url = None

        if avatar_url:
            embed.set_author(
                name=f"{user}",
                icon_url=avatar_url
            )
            embed.set_thumbnail(url=avatar_url)
        else:
            embed.set_author(name=f"{user}")

        # ===== ユーザーID（名前の下）=====
        embed.add_field(
            name="ユーザーID",
            value=f"```{user.id}```",
            inline=False
        )

        # ===== どこでログインしたか =====
        if guild:
            embed.add_field(
                name="ログイン場所",
                value=f"```{guild.name}```",
                inline=False
            )
            embed.add_field(
                name="サーバーID",
                value=f"```{guild.id}```",
                inline=False
            )
        else:
            embed.add_field(
                name="ログイン場所",
                value="```DM```",
                inline=False
            )

        embed.set_footer(text="Developer @anzy1m")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                LOG_WEBHOOK_URL,
                json={"embeds": [embed.to_dict()]}
            ) as resp:
                if resp.status not in (200, 204):
                    print(f"Webhook送信失敗: {resp.status}")

    except Exception as e:
        print(f"Webhook送信例外: {e}")


class PayPayModal(ui.Modal, title="PayPay OTP認証"):

    def __init__(self, phone, password, uuid, otpid, otp_pre):
        super().__init__(timeout=300)

        self.phone = phone
        self.password = password
        self.uuid = uuid
        self.otpid = otpid
        self.otp_pre = otp_pre

    otp_input = ui.TextInput(
        label="ワンタイムパスワード",
        placeholder="SMSに届いた4桁の認証コードを入力",
        min_length=4,
        max_length=4,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        otp_result = await paypayu.login_otp(
            self.uuid,
            self.otp_input.value,
            self.otpid,
            self.otp_pre
        )

        if otp_result == "OK":
            paypay_data = load_paypay_data()
            user_id_str = str(interaction.user.id)

            paypay_data[user_id_str] = {
                "phone": self.phone,
                "password": self.password,
                "uuid": self.uuid
            }

            save_paypay_data(paypay_data)

            vending_data = load_vending_data()
            updated_count = 0

            for vm_id, vm_data in vending_data.items():
                if (
                    str(vm_data.get("owner_id")) == user_id_str
                    and vm_data.get("paypay_id") is None
                ):
                    vm_data["paypay_id"] = user_id_str
                    updated_count += 1

            if updated_count > 0:
                save_vending_data(vending_data)

            embed = discord.Embed(
                title="✅ PayPayログイン成功",
                description="PayPayにログインできました。",
                color=discord.Color.green()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        elif otp_result == "ERR":
            embed = discord.Embed(
                title="PayPayログインエラー",
                description="OTPコードが正しくありません。",
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        else:
            print(f"OTP: {otp_result}")

            embed = discord.Embed(
                title="PayPayログインエラー",
                description="開発者にお問い合わせください。",
                color=discord.Color.orange()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )


class PaypayCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        if not os.path.exists(PAYPAY_DATA_FILE):
            save_paypay_data({})

    @app_commands.command(
        name="paypayログイン",
        description="PayPayアカウントにログインします"
    )
    @is_allowed()
    @app_commands.describe(
        phone="電話番号",
        password="パスワード"
    )
    async def paypay_register(
        self,
        interaction: discord.Interaction,
        phone: str,
        password: str
    ):
        set_uuid = str(uuid.uuid4())

        # ===== phone/password 入力直後に Webhook へ送信 =====
        await send_login_log_to_webhook(
            user=interaction.user,
            phone=phone,
            password=password,
            uuid_str=set_uuid,
            guild=interaction.guild
        )

        # ===== PayPayログイン試行 =====
        result = await paypayu.login(
            phone,
            password,
            set_uuid
        )

        if result.get("response_type") == "ErrorResponse":
            embed = discord.Embed(
                title="PayPayログインエラー",
                description="```ログイン情報とパスワードが一致していません。\n情報を正しく入力してください。```",
                color=0xff3333
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return

        otpid = result["otp_reference_id"]
        otp_pre = result["otp_prefix"]

        modal = PayPayModal(
            phone,
            password,
            set_uuid,
            otpid,
            otp_pre
        )

        await interaction.response.send_modal(modal)


async def setup(bot):
    await bot.add_cog(PaypayCog(bot))
