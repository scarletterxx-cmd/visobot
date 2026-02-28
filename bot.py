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
import asyncio
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
# Create a new client and connect to the server
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["visocoin_bot"]
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

users_col = db["users"]          # coin, inventory, daily
warnings_col = db["warnings"]    # uyari kayitlari
daily_col = db["daily"]          # günlük mesaj takibi

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

# ================= COINFLIP COOLDOWN =================
coinflip_cd = {}
COINFLIP_COOLDOWN = 15  # saniye


# -----------------
# DATA
# -----------------

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "money": 0,
            "inventory": {},
            "last_daily": 0
        }
        users_col.insert_one(user)
    return user

def save_user(user):
    users_col.update_one({"user_id": user["user_id"]}, {"$set": user}, upsert=True)


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

    return list(warnings_col.find())



def save_warning(guild_id, user_id, uyari):
    warnings_col.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$push": {"uyarilar": uyari}},
        upsert=True
    )


def load_daily_message():
    if not os.path.exists(DAILY_MESSAGE_FILE):
        return {}
    with open(DAILY_MESSAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_daily_message(data):
    with open(DAILY_MESSAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def should_send_daily_message(user_id):
    today = str(datetime.now(timezone.utc).date())
    record = daily_col.find_one({"user_id": user_id})
    
    if not record or record.get("last_date") != today:
        daily_col.update_one({"user_id": user_id}, {"$set": {"last_date": today}}, upsert=True)
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


@bot.command(name="coinflip", aliases=["cf", "yazitura", "yt"])
async def coinflip(ctx, choice: str = None, miktar: int = None):
    user_id = ctx.author.id
    now = int(time.time())

    # ================= COOLDOWN =================
    if user_id in coinflip_cd and coinflip_cd[user_id] > now:
        bitis = coinflip_cd[user_id]
        return await ctx.send(
            f"⏳ Bekleme süresindesin: <t:{bitis}:R>"
        )

    # ================= VALIDATION =================
    if choice is None or miktar is None:
        return await ctx.send("🪙 Kullanım: `!coinflip yazı/tura miktar`")

    choice = choice.lower()

    if choice not in ["yazı", "tura"]:
        return await ctx.send("❌ Seçenek olarak `yazı` veya `tura` girebilirsin.")

    if miktar <= 0:
        return await ctx.send("❌ Geçerli bir miktar gir.")

    user = get_user(user_id)

    if user["money"] < miktar:
        return await ctx.send("💸 Yetersiz bakiye.")

    # parayı düş
    user["money"] -= miktar
    save_user(user)

    msg = await ctx.send("🪙 | Hazırlanıyor...")

    frames = [
        "🎡 | Dönüyor...",
        "🔄 | Zar atılıyor...",
        "✨ | Havada süzülüyor...",
        "🎲 | Sonuç geliyor..."
    ]

    for frame in frames:
        await asyncio.sleep(0.7)
        await msg.edit(content=frame)

    result = random.choice(["yazı", "tura"])
    coinflip_cd[user_id] = now + 30  # ✅ COOLDOWN BURADA

    await asyncio.sleep(0.5)

    user = get_user(user_id)

    if result == choice:
        kazanc = miktar * 2
        user["money"] += kazanc
        save_user(user)

        await msg.edit(
            content=f"🎉 **{result.upper()}** geldi! +{kazanc} VisoCoin kazandın. 😎"
        )
    else:
        save_user(user)

        await msg.edit(
            content=f"💀 **{result.upper()}** geldi! {miktar} VisoCoin'ler kayboldu..."
        )


# ================== MUTE ==================
@bot.command(name="mute", aliases=["sustur"])
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

@bot.command(name="bakiye", aliases=["para", "visocoin", "money"])
async def bakiye(ctx):
    user = get_user(ctx.author.id)

    embed = discord.Embed(
        title="💵 Bakiye",
        description=f"{ctx.author.mention}, şu anki VisoCoin miktarın: **{user['money']}**",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)

@bot.command(name="daily", aliases=["günlük"])
async def günlük(ctx):
    user = get_user(ctx.author.id)

    now = time.time()
    if now - user["last_daily"] < 86400:
        kalan = int(86400 - (now - user["last_daily"]))
        saat = kalan // 3600
        embed = discord.Embed(
            title="⏳ Günlük",
            description=f"{ctx.author.mention}, günlük için {saat} saat bekle.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    miktar = random.randint(300, 500)
    user["money"] += miktar
    user["last_daily"] = now
    save_user(user)

    embed = discord.Embed(
        title="🎁 Günlük Alındı",
        description=f"{ctx.author.mention}, bugün **{miktar}** VisoCoin aldın!",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)

# -----------------
# KASA SISTEMI
# -----------------

KASA_FIYAT = 400

@bot.command(name="kasa", aliases=["crate", "case", "box"])
async def kasa(ctx):
    user = get_user(ctx.author.id)
    save_user(user)

    if user["money"] < KASA_FIYAT:
        embed = discord.Embed(
            title="❌ Yetersiz VisoCoin",
            description=f"{ctx.author.mention}, kasayı açmak için yeterli VisoCoin'in yok! ({KASA_FIYAT} gerekiyor.)",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

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
        rarity = "Destansı"

    user["money"] += kazanc
    save_user(user)

    embed = discord.Embed(
        title="📦 Kasa Açıldı",
        description=f"{ctx.author.mention}, kasanı açtın!",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="✨ Enderlik", value=rarity, inline=True)
    embed.add_field(name="💰 Kazanç", value=kazanc, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="envanter", aliases=["env", "inventory", "inv"])
async def envanter(ctx):
    user = get_user(ctx.author.id)
    save_user(user)

    inv = user.get("inventory", {})

    if not inv:
        embed = discord.Embed(
            title="🎒 Envanter",
            description=f"{ctx.author.mention}, envanterin boş 😢",
            color=discord.Color.greyple(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title="🎒 Envanter",
        description=f"{ctx.author.mention} şu anki eşyaların:",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )

    for item_id, amount in inv.items():
        name = SHOP_ITEMS.get(item_id, {}).get("name", item_id)
        embed.add_field(name=name, value=f"x{amount}", inline=True)

    await ctx.send(embed=embed)

@bot.command(name="market", aliases=["shop"])
async def market(ctx):
    embed = discord.Embed(
        title="🛒 Market",
        description="Satın almak için `!satinal <ürün>`",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )

    for item_id, item in SHOP_ITEMS.items():
        embed.add_field(
            name=f"{item['name']} ({item_id})",
            value=f"💰 Fiyat: {item['price']}",
            inline=False
        )

    await ctx.send(embed=embed)
    
SHOP_ITEMS = {
    "kumarbaz": {
        "price": 5000,
        "name": "🌟 Kumarbaz Rolü",
        "role_id": 1476980019262914612
    }
}

@bot.command(name="satinal", aliases=["buy"])
async def satinal(ctx, item_id: str):
    item_id = item_id.lower().strip()

    if item_id not in SHOP_ITEMS:
        embed = discord.Embed(
            title="❌ Hata",
            description="Böyle bir ürün yok!",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user = get_user(ctx.author.id)
    save_user(user)
    item = SHOP_ITEMS[item_id]

    if user["money"] < item["price"]:
        embed = discord.Embed(
            title="💸 Yetersiz VisoCoin",
            description="VisoCoin'in yetmiyor!",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= item["price"]
    inv = user.setdefault("inventory", {})
    inv[item_id] = inv.get(item_id, 0) + 1
    save_user(user)

    # Rol verme
    if "role_id" in item:
        role = ctx.guild.get_role(item["role_id"])
        if role:
            try:
                await ctx.author.add_roles(role)
                embed = discord.Embed(
                    title="✅ Satın Alındı",
                    description=f"{ctx.author.mention}, **{item['name']}** rolünü aldın!",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            except:
                embed = discord.Embed(
                    title="⚠️ Hata",
                    description="Rol veremedim! Yetkini ve rol sırasını kontrol et.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ Hata",
                description="Rol bulunamadı.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="✅ Satın Alındı",
            description=f"{ctx.author.mention}, **{item['name']}** satın alındı!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

@bot.command()
async def visocoinekle(ctx, miktar: int):
    YETKILI_USER_ID = 686628029987946600

    # kullanıcı kontrolü
    if ctx.author.id != YETKILI_USER_ID:
        return await ctx.send("❌ Bu komutu kullanamazsın.")

    if miktar <= 0:
        return await ctx.send("❌ Geçerli bir miktar gir.")

    user = get_user(ctx.author.id)

    user["money"] += miktar
    save_user(user)

    await ctx.send(f"💰 Kendine **{miktar}** VisoCoin ekledin.")

# ================== UYARILAR ==================
@bot.command(name="uyarılar", aliases=["warns", "warnings", "uyarı"])
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





























