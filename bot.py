import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import json
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import os
import random
import time

app = Flask("")

@app.route("/")
def home():
    return "BOT AYAKTA KARDES 😎"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

# Botu ayrı threadde çalıştır
Thread(target=run).start()

load_dotenv()
TOKEN = os.getenv("TOKEN")  # artık None olmayacakpip install PyNaClpip install PyNaCl

WARNINGS_FILE = "warnings.json"
LOG_CHANNEL_ID = 1435663818528129117
DAILY_MESSAGE_USER_ID = 594917441054834698
DAILY_MESSAGE_FILE = "daily_message.json"

# UYARI ROL ID'LERI
UYARI_ROLLERI = {
    1: 1404957774525239406,
    2: 1404958219553738883,
    3: 1404958311203471434
}

# ================== BOT ==================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1289651738046890086  # sunucu id
VOICE_CHANNEL_ID = 1289652557244792833  # botun gireceği sesli kanal id


DATA_FILE = "data.json"

# -----------------
# DATA
# -----------------

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(data, user_id):
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "money": 0,
            "last_daily": 0
        }
    return data[user_id]


# ================== DOSYA ==================
def load_warnings():
    if not os.path.exists(WARNINGS_FILE):
        return {}

    with open(WARNINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    simdi = datetime.now(timezone.utc)
    uc_gun = timedelta(days=3)
    degisti = False

    for gid in list(data.keys()):
        for uid in list(data[gid].keys()):
            yeni = []
            for u in data[gid][uid]:
                try:
                    tarih = datetime.fromisoformat(u["tarih"])
                    if simdi - tarih <= uc_gun:
                        yeni.append(u)
                    else:
                        degisti = True
                except:
                    continue

            if yeni:
                data[gid][uid] = yeni
            else:
                del data[gid][uid]
                degisti = True

        if not data[gid]:
            del data[gid]
            degisti = True

    if degisti:
        with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    return data


def save_warnings(data):
    with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_daily_message():
    if not os.path.exists(DAILY_MESSAGE_FILE):
        return {}
    with open(DAILY_MESSAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_daily_message(data):
    with open(DAILY_MESSAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def should_send_daily_message(user_id):
    data = load_daily_message()
    today = str(datetime.now(timezone.utc).date())
    last_date = data.get(str(user_id))
    
    if last_date != today:
        data[str(user_id)] = today
        save_daily_message(data)
        return True
    return False


async def temizle_ve_rolleri_guncelle():
    warnings = load_warnings()

    for gid, users in warnings.items():
        guild = bot.get_guild(int(gid))
        if not guild:
            continue

        for uid, warning_list in users.items():
            member = guild.get_member(int(uid))
            if not member:
                continue

            # tum uyari rollerini al
            for rid in UYARI_ROLLERI.values():
                role = guild.get_role(rid)
                if role and role in member.roles:
                    await member.remove_roles(role)

            # dogru rolu ver
            count = len(warning_list)
            if count in UYARI_ROLLERI:
                role = guild.get_role(UYARI_ROLLERI[count])
                if role:
                    await member.add_roles(role)


async def send_log(guild, embed):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# ================== READY ==================
@bot.event
async def on_ready():
    print(f"{bot.user} online 😎")
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(VOICE_CHANNEL_ID)
    
    if channel:
        # bot kanala giriyor ama sessiz
        await channel.connect()
        vc = bot.voice_clients[0]
        # await vc.disconnect()  # ilk başta bağlı değilken bağlantıyı kapat, isteğe göre kaldırabilirsin
        print(f"{bot.user} {channel.name} kanalında sessiz duruyor 🫡")

# ================== CEVAP ==================

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.lower().strip()

    if content == "selam":
        await message.channel.send(f"Selam, {message.author.mention}!")

    elif content == "içtim şarabı":
        await message.channel.send("siktim arabı :sunglasses:")

    elif content == "sa":
        await message.channel.send(f"Selam, {message.author.mention}!")

    if message.author.id == DAILY_MESSAGE_USER_ID:
        if should_send_daily_message(DAILY_MESSAGE_USER_ID):
            await message.channel.send(f"<@{DAILY_MESSAGE_USER_ID}> mal")

    await bot.process_commands(message)

# ================== MUTE ==================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, sure: int, *, sebep="Sebep belirtilmedi"):
    warnings = load_warnings()
    gid = str(ctx.guild.id)
    uid = str(member.id)

    warnings.setdefault(gid, {})
    warnings[gid].setdefault(uid, [])

    uyari_no = len(warnings[gid][uid]) + 1

    # 4. ceza -> BAN
    if uyari_no >= 4:
        try:
            await member.send(
                "🚫 **Sunucudan banlandin**\n"
                "Sebep: 3 uyaridan sonra tekrar ceza."
            )
        except:
            pass

        await ctx.guild.ban(member, reason="3 uyaridan sonra tekrar ceza")

        embed = discord.Embed(
            title="🔨 BAN ATILDI",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👤 Kullanici", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="🛡️ Yetkili", value=ctx.author.mention, inline=False)
        embed.add_field(name="📌 Sebep", value=sebep, inline=False)

        await send_log(ctx.guild, embed)
        await ctx.send(embed=embed)
        return

    # uyari kaydi
    uyari = {
        "uyari_no": uyari_no,
        "sebep": sebep,
        "sure": f"{sure} dk",
        "atan": ctx.author.name,
        "tarih": datetime.now(timezone.utc).isoformat()
    }

    warnings[gid][uid].append(uyari)
    save_warnings(warnings)

    # timeout
    until = datetime.now(timezone.utc) + timedelta(minutes=sure)
    await member.timeout(until, reason=sebep)

    await temizle_ve_rolleri_guncelle()

    # DM
    try:
        await member.send(
            f"⚠️ **{uyari_no}. Uyari Aldin**\n"
            f"Sebep: {sebep}\n"
            f"Sure: {sure} dakika"
        )
    except:
        pass

    # LOG
    embed = discord.Embed(
        title=f"⚠️ {uyari_no}. UYARI VERILDI",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="👤 Kullanici", value=f"{member.mention} ({member.id})", inline=False)
    embed.add_field(name="🛡️ Moderator", value=ctx.author.mention, inline=False)
    embed.add_field(name="⏳ Mute", value=f"{sure} dk", inline=True)
    embed.add_field(name="📝 Sebep", value=sebep, inline=False)

    await send_log(ctx.guild, embed)
    await ctx.send(embed=embed)

# ================== EKONOMI-KOMUT ==================

@bot.command()
async def bakiye(ctx):
    data = load_data()
    user = get_user(data, ctx.author.id)
    await ctx.send(f"💰 Paran: **{user['money']}**")

@bot.command()
async def daily(ctx):
    data = load_data()
    user = get_user(data, ctx.author.id)

    now = time.time()
    if now - user["last_daily"] < 86400:
        kalan = int(86400 - (now - user["last_daily"]))
        saat = kalan // 3600
        return await ctx.send(f"⏳ Günlük için {saat} saat bekle.")

    miktar = random.randint(100, 300)
    user["money"] += miktar
    user["last_daily"] = now

    save_data(data)
    await ctx.send(f"🎁 Günlük aldın: **{miktar}**")

# -----------------
# KASA SISTEMI
# -----------------

KASA_FIYAT = 250

@bot.command()
async def kasa(ctx):
    data = load_data()
    user = get_user(data, ctx.author.id)

    if user["money"] < KASA_FIYAT:
        return await ctx.send("❌ Paran yetmiyor.")

    user["money"] -= KASA_FIYAT

    roll = random.random()

    if roll < 0.60:
        kazanc = random.randint(50, 150)
        rarity = "Sıradan"

    elif roll < 0.90:
        kazanc = random.randint(200, 400)
        rarity = "Ender"

    else:
        kazanc = random.randint(600, 900)
        rarity = "DESTANSI"

    user["money"] += kazanc
    save_data(data)

    await ctx.send(
        f"📦 Kasanı açtın!\n"
        f"✨ Enderlik: **{rarity}**\n"
        f"💰 Para: **{kazanc}**"
    )

@bot.command()
async def envanter(ctx):
    data = load_data()
    user = get_user(data, ctx.author.id)

    inv = user["inventory"]

    if not inv:
        return await ctx.send("🎒 Envanterin boş.")

    msg = "🎒 **Envanterin**\n\n"

    for item_id, amount in inv.items():
        name = SHOP_ITEMS.get(item_id, {}).get("name", item_id)
        msg += f"{name} x{amount}\n"

    await ctx.send(msg)

@bot.command()
async def market(ctx):
    msg = "🛒 **Market**\n\n"

    for item_id, item in SHOP_ITEMS.items():
        msg += f"**{item_id}** — {item['name']} | 💰 {item['price']}\n"

    msg += "\nSatın almak için: `!satinal <ürün>`"
    await ctx.send(msg)


SHOP_ITEMS = {
    "kumarbaz": {
        "price": 5000,
        "name": "🌟 Kumarbaz Rolü",
        "role_id": 1476980019262914612  # BURAYA GERÇEK ROL ID
    }
}

@bot.command()
async def satinal(ctx, item_id: str):
    item_id = item_id.lower()

    if item_id not in SHOP_ITEMS:
        return await ctx.send("❌ Böyle bir ürün yok.")

    data = load_data()
    user = get_user(data, ctx.author.id)
    item = SHOP_ITEMS[item_id]

    if user["money"] < item["price"]:
        return await ctx.send("💸 Paran yetmiyor.")

    user["money"] -= item["price"]

    # envantere ekle
    inv = user["inventory"]
    inv[item_id] = inv.get(item_id, 0) + 1

    save_data(data)

    # 🔥 ROL VERME KISMI
    if "role_id" in item:
        role = ctx.guild.get_role(item["role_id"])
        if role:
            try:
                await ctx.author.add_roles(role)
                await ctx.send(f"✅ Satın aldın: **{item['name']}**")
            except discord.Forbidden:
                await ctx.send("⚠️ Rol veremedim (yetkim yok).")
        else:
            await ctx.send("⚠️ Rol kaldırıldı.")
    else:
        await ctx.send(f"✅ Satın alındı: **{item['name']}**")

# ================== UYARILAR ==================
@bot.command()
async def uyarilar(ctx, member: discord.Member = None):
    member = member or ctx.author
    warnings = load_warnings()

    gid = str(ctx.guild.id)
    uid = str(member.id)

    uyari_list = warnings.get(gid, {}).get(uid, [])

    if not uyari_list:
        embed = discord.Embed(
            title="🟢 Uyari Yok",
            description=f"{member.mention} tertemiz 😇",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=f"📄 {member.name} — Uyari Kayitlari",
        color=discord.Color.red()
    )

    for u in uyari_list:
        embed.add_field(
            name=f"{u['uyari_no']}. Uyari",
            value=(
                f"📝 Sebep: {u['sebep']}\n"
                f"⏱ Sure: {u['sure']}\n"
                f"🧑‍⚖ Atan: {u['atan']}\n"
                f"📅 Tarih: {u['tarih']}"
            ),
            inline=False
        )

    await ctx.send(embed=embed)

# ================== RUN ==================

bot.run(TOKEN)




