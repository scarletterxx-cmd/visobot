import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import os
import random
import time
import asyncio
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import uuid

load_dotenv()

TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Create a new client and connect to the server
client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client["visocoin_bot"]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"MongoDB bağlantı hatası: {e}")

users_col = db["users"]
warnings_col = db["warnings"]
daily_col = db["daily"]
quests_col = db["quests"]
daily_messages_col = db["daily_messages"]
farms_col = db["farms"]
dungeons_col = db["dungeons"]
pirates_col = db["pirates"]
loncalar_col = db["loncalar"]

app = Flask("")

@app.route("/")
def home():
    return "BOT AYAKTA KARDES"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

Thread(target=run).start()

LOG_CHANNEL_ID = 1435663818528129117
DAILY_MESSAGE_USER_ID = 594917441054834698
PER_PAGE = 10
BOT_START_TIME = time.time()
STARTUP_LOCK_SECONDS = 90  # istersen 120 yap

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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

GUILD_ID = 1289651738046890086
VOICE_CHANNEL_ID = 1289652557244792833

@bot.check
async def global_startup_lock(ctx):
    if time.time() - BOT_START_TIME < STARTUP_LOCK_SECONDS:
        kalan = int(STARTUP_LOCK_SECONDS - (time.time() - BOT_START_TIME))
        await ctx.send(
            f"🔧 Bot başlatılıyor… {kalan}s sonra tekrar dene."
        )
        return False
    return True

# ================= COOLDOWNS =================
coinflip_cd = {}
COINFLIP_COOLDOWN = 15

blackjack_cd = {}
BLACKJACK_COOLDOWN = 10

slot_cd = {}
SLOT_COOLDOWN = 10

rulet_cd = {}
RULET_COOLDOWN = 15

duello_cd = {}
DUELLO_COOLDOWN = 30

hirsizlik_cd = {}
HIRSIZLIK_COOLDOWN = 300  # 5 dakika

transfer_cd = {}
TRANSFER_COOLDOWN = 10

tarla_cd = {}
TARLA_COOLDOWN = 5

zindan_cd = {}
ZINDAN_COOLDOWN = 10
zindan_savaş_cd = {}
ZINDAN_SAVAŞ_COOLDOWN = 5

# PvP Arena
pvp_istekleri = {}  # {hedef_id: {"saldıran": user_id, "bahis": miktar, "zaman": timestamp}}
PVP_ISTEK_SURESI = 60

# Lonca
LONCA_KURMA_UCRETI = 5000
LONCA_MAX_UYE = 20
LONCA_BOSS_COOLDOWN = 3600  # 1 saat
lonca_davetleri = {}  # {hedef_id: {"lonca_id": ..., "davet_eden": ..., "zaman": ...}}

# Hazine Odasi
HAZINE_ODASI_SANSI = 15  # %15 sans ile hazine odasi cikar
aktif_bilmeceler = {}  # {user_id: {"bilmece": ..., "zaman": ..., "odul": ...}}

# ================= SOHBET PARA ODULU =================
CHAT_REWARD_CHANNEL_ID = 1389166576242266175
CHAT_REWARD_CHANCE = 0.05
CHAT_REWARD_MIN = 10
CHAT_REWARD_MAX = 75
chat_reward_cd = {}
CHAT_REWARD_COOLDOWN = 30

# ================= SEVIYE / XP SISTEMI =================
XP_PER_MESSAGE = 5
XP_COOLDOWN = 10  # saniye (spam engeli)
xp_cd = {}

LEVEL_THRESHOLDS = [
    # (level, gereken_toplam_xp, bonus_visocoin)
    (1, 0, 0),
    (2, 100, 50),
    (3, 300, 100),
    (4, 600, 150),
    (5, 1000, 250),
    (6, 1500, 350),
    (7, 2100, 500),
    (8, 2800, 650),
    (9, 3600, 800),
    (10, 4500, 1000),
    (11, 5500, 1200),
    (12, 6600, 1400),
    (13, 7800, 1600),
    (14, 9100, 1800),
    (15, 10500, 2000),
    (16, 12000, 2300),
    (17, 13600, 2600),
    (18, 15300, 3000),
    (19, 17100, 3500),
    (20, 19000, 4000),
]

def get_level_from_xp(xp):
    """XP'ye gore seviye hesapla."""
    level = 1
    for lvl, threshold, _ in LEVEL_THRESHOLDS:
        if xp >= threshold:
            level = lvl
        else:
            break
    return level

def get_xp_for_next_level(current_level):
    """Bir sonraki seviyeye gereken XP."""
    for lvl, threshold, _ in LEVEL_THRESHOLDS:
        if lvl == current_level + 1:
            return threshold
    return None  # max seviye

def get_level_bonus(level):
    """Seviye atlayinca verilen bonus VisoCoin."""
    for lvl, _, bonus in LEVEL_THRESHOLDS:
        if lvl == level:
            return bonus
    return 0

# ================= GOREV SISTEMI =================
DAILY_QUESTS = [
    {"id": "mesaj_10", "name": "Sohbetçi", "desc": "10 mesaj gönder", "type": "mesaj", "goal": 10, "reward": 150},
    {"id": "mesaj_30", "name": "Konuşkan", "desc": "30 mesaj gönder", "type": "mesaj", "goal": 30, "reward": 350},
    {"id": "mesaj_75", "name": "Sohbet Ustası", "desc": "75 mesaj gönder", "type": "mesaj", "goal": 75, "reward": 750},
    {"id": "coinflip_3", "name": "Kumar Meraklısı", "desc": "3 coinflip oyna", "type": "coinflip", "goal": 3, "reward": 200},
    {"id": "coinflip_10", "name": "Kumarhane Kralı", "desc": "10 coinflip oyna", "type": "coinflip", "goal": 10, "reward": 500},
    {"id": "kasa_2", "name": "Kasa Acemisi", "desc": "2 kasa aç", "type": "kasa", "goal": 2, "reward": 300},
    {"id": "kasa_5", "name": "Kasa Baronu", "desc": "5 kasa aç", "type": "kasa", "goal": 5, "reward": 650},
    {"id": "daily_1", "name": "Gunluk Rutin", "desc": "Gunluk ödülünü topla", "type": "daily", "goal": 1, "reward": 100},
    {"id": "kazan_500", "name": "Kazanc Avcısı", "desc": "Coinflipte toplam 500 VisoCoin kazan", "type": "coinflip_kazan", "goal": 500, "reward": 400},
    {"id": "harca_1000", "name": "Buyuk Harcama", "desc": "Toplam 1000 VisoCoin harca (kasa/market)", "type": "harca", "goal": 1000, "reward": 500},
    {"id": "blackjack_3", "name": "Kart Cambazı", "desc": "3 blackjack oyna", "type": "blackjack", "goal": 3, "reward": 250},
    {"id": "slot_5", "name": "Slot Avcısı", "desc": "5 slot çevir", "type": "slot", "goal": 5, "reward": 300},
    {"id": "rulet_3", "name": "Rulet Ustası", "desc": "3 rulet oyna", "type": "rulet", "goal": 3, "reward": 250},
    {"id": "duello_2", "name": "Düellocu", "desc": "2 düello yap", "type": "duello", "goal": 2, "reward": 350},
    {"id": "hasat_3", "name": "Çiftçi", "desc": "3 hasat yap", "type": "hasat", "goal": 3, "reward": 250},
    {"id": "ek_5", "name": "Tohum Ustası", "desc": "5 tohum ek", "type": "tohum_ek", "goal": 5, "reward": 200},
    {"id": "zindan_3", "name": "Zindan Kaşifi", "desc": "3 zindan katı geç", "type": "zindan_kat", "goal": 3, "reward": 300},
    {"id": "canavar_5", "name": "Canavar Avcısı", "desc": "5 canavar öldür", "type": "canavar_öldür", "goal": 5, "reward": 250},
]

WEEKLY_QUESTS = [
    {"id": "w_mesaj_200", "name": "Aktif Sohbetçi", "desc": "200 mesaj gönder", "type": "mesaj", "goal": 200, "reward": 1500},
    {"id": "w_mesaj_500", "name": "Efsane Sohbetçi", "desc": "500 mesaj gönder", "type": "mesaj", "goal": 500, "reward": 3500},
    {"id": "w_coinflip_25", "name": "Haftalık Kumarbaz", "desc": "25 coinflip oyna", "type": "coinflip", "goal": 25, "reward": 1200},
    {"id": "w_kasa_10", "name": "Haftalık Kasa Avcısı", "desc": "10 kasa aç", "type": "kasa", "goal": 10, "reward": 1800},
    {"id": "w_kazan_3000", "name": "Zengin Ol", "desc": "Coinflipte toplam 3000 VisoCoin kazan", "type": "coinflip_kazan", "goal": 3000, "reward": 2500},
    {"id": "w_harca_5000", "name": "Para Yakıcı", "desc": "Toplam 5000 VisoCoin harca", "type": "harca", "goal": 5000, "reward": 2000},
    {"id": "w_blackjack_15", "name": "Kart Baronu", "desc": "15 blackjack oyna", "type": "blackjack", "goal": 15, "reward": 1500},
    {"id": "w_slot_20", "name": "Slot Imparatoru", "desc": "20 slot çevir", "type": "slot", "goal": 20, "reward": 1800},
    {"id": "w_hasat_20", "name": "Haftalık Çiftçi", "desc": "20 hasat yap", "type": "hasat", "goal": 20, "reward": 1500},
    {"id": "w_zindan_20", "name": "Zindan Efendisi", "desc": "20 zindan katı geç", "type": "zindan_kat", "goal": 20, "reward": 2000},
    {"id": "w_boss_3", "name": "Boss Katili", "desc": "3 boss öldür", "type": "boss_öldür", "goal": 3, "reward": 2500},
]

DAILY_QUEST_COUNT = 3
WEEKLY_QUEST_COUNT = 2

def get_user_quests(user_id):
    doc = quests_col.find_one({"user_id": user_id})
    now = datetime.now(timezone.utc)

    if not doc:
        doc = {
            "user_id": user_id,
            "daily": [],
            "weekly": [],
            "daily_reset": now.isoformat(),
            "weekly_reset": now.isoformat(),
        }
        quests_col.insert_one(doc)

    daily_reset = datetime.fromisoformat(doc["daily_reset"])
    if (now - daily_reset).total_seconds() >= 86400:
        new_daily = random.sample(DAILY_QUESTS, min(DAILY_QUEST_COUNT, len(DAILY_QUESTS)))
        doc["daily"] = [{"id": q["id"], "progress": 0, "claimed": False} for q in new_daily]
        doc["daily_reset"] = now.isoformat()

    if not doc["daily"]:
        new_daily = random.sample(DAILY_QUESTS, min(DAILY_QUEST_COUNT, len(DAILY_QUESTS)))
        doc["daily"] = [{"id": q["id"], "progress": 0, "claimed": False} for q in new_daily]
        doc["daily_reset"] = now.isoformat()

    weekly_reset = datetime.fromisoformat(doc["weekly_reset"])
    if (now - weekly_reset).total_seconds() >= 604800:
        new_weekly = random.sample(WEEKLY_QUESTS, min(WEEKLY_QUEST_COUNT, len(WEEKLY_QUESTS)))
        doc["weekly"] = [{"id": q["id"], "progress": 0, "claimed": False} for q in new_weekly]
        doc["weekly_reset"] = now.isoformat()

    if not doc["weekly"]:
        new_weekly = random.sample(WEEKLY_QUESTS, min(WEEKLY_QUEST_COUNT, len(WEEKLY_QUESTS)))
        doc["weekly"] = [{"id": q["id"], "progress": 0, "claimed": False} for q in new_weekly]
        doc["weekly_reset"] = now.isoformat()

    save_quests(doc)
    return doc

def save_quests(doc):
    quests_col.update_one({"user_id": doc["user_id"]}, {"$set": doc}, upsert=True)

def find_quest_def(quest_id):
    for q in DAILY_QUESTS + WEEKLY_QUESTS:
        if q["id"] == quest_id:
            return q
    return None

def update_quest_progress(user_id, quest_type, amount=1):
    doc = get_user_quests(user_id)
    changed = False

    for quest_list in [doc["daily"], doc["weekly"]]:
        for quest in quest_list:
            if quest["claimed"]:
                continue
            qdef = find_quest_def(quest["id"])
            if qdef and qdef["type"] == quest_type:
                quest["progress"] = min(quest["progress"] + amount, qdef["goal"])
                changed = True

    if changed:
        save_quests(doc)

# -----------------
# DATA
# -----------------

def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "money": 0,
            "inventory": {},
            "last_daily": 0,
            "xp": 0,
            "level": 1,
        }
        users_col.insert_one(user)
    # Eski kullanicilar icin xp/level alani yoksa ekle
    if "xp" not in user:
        user["xp"] = 0
    if "level" not in user:
        user["level"] = 1
    return user

def save_user(user):
    users_col.update_one({"user_id": user["user_id"]}, {"$set": user}, upsert=True)


# ================== DOSYA ==================
def load_warnings():
    """MongoDB'den uyarilari yukle ve 3 gunden eski olanlari temizle."""
    simdi = datetime.now(timezone.utc)
    uc_gun = timedelta(days=3)

    all_warnings = list(warnings_col.find())
    result = {}

    for doc in all_warnings:
        gid = str(doc["guild_id"])
        uid = str(doc["user_id"])
        uyarilar = doc.get("uyarilar", [])

        # 3 gunden eski uyarilari filtrele
        yeni = []
        for u in uyarilar:
            try:
                tarih = datetime.fromisoformat(u["tarih"])
                if simdi - tarih <= uc_gun:
                    yeni.append(u)
            except:
                continue

        # MongoDB'yi guncelle (eski uyarilar silindi)
        if len(yeni) != len(uyarilar):
            if yeni:
                warnings_col.update_one(
                    {"guild_id": gid, "user_id": uid},
                    {"$set": {"uyarilar": yeni}}
                )
            else:
                warnings_col.delete_one({"guild_id": gid, "user_id": uid})

        if yeni:
            result.setdefault(gid, {})[uid] = yeni

    return result


def save_warning(guild_id, user_id, uyari):
    warnings_col.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$push": {"uyarilar": uyari}},
        upsert=True
    )


def load_daily_message():
    """MongoDB'den daily message verisini yukle."""
    doc = daily_messages_col.find_one({"_type": "daily_message_config"})
    if not doc:
        return {}
    doc.pop("_id", None)
    doc.pop("_type", None)
    return doc


def save_daily_message(data):
    """MongoDB'ye daily message verisini kaydet."""
    daily_messages_col.update_one(
        {"_type": "daily_message_config"},
        {"$set": {**data, "_type": "daily_message_config"}},
        upsert=True
    )


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

            for rid in UYARI_ROLLERI.values():
                role = guild.get_role(rid)
                if role and role in member.roles:
                    await member.remove_roles(role)

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
    print(f"{bot.user} online")
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(VOICE_CHANNEL_ID)

    if channel:
        await channel.connect()
        print(f"{bot.user} {channel.name} kanalinda sessiz duruyor")

# ================== CEVAP / XP SISTEMI ==================

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.lower().strip()

    if content == "selam":
        await message.channel.send(f"Selam, {message.author.mention}!")
    elif content == "sa":
        await message.channel.send(f"Selam, {message.author.mention}!")

    if message.author.id == DAILY_MESSAGE_USER_ID:
        if should_send_daily_message(DAILY_MESSAGE_USER_ID):
            await message.channel.send(f"<@{DAILY_MESSAGE_USER_ID}> mal")

    # ================= GOREV ILERLEME (MESAJ) =================
    update_quest_progress(message.author.id, "mesaj", 1)

    # ================= SEVIYE / XP SISTEMI =================
    user_id = message.author.id
    now_ts = int(time.time())

    if user_id not in xp_cd or xp_cd[user_id] <= now_ts:
        xp_cd[user_id] = now_ts + XP_COOLDOWN

        user = get_user(user_id)
        old_level = user.get("level", 1)
        user["xp"] = user.get("xp", 0) + XP_PER_MESSAGE
        new_level = get_level_from_xp(user["xp"])

        if new_level > old_level:
            user["level"] = new_level
            bonus = get_level_bonus(new_level)
            user["money"] += bonus
            save_user(user)

            embed = discord.Embed(
                title="⏫ Seviye Atladın!",
                description=(
                    f"{message.author.mention}, **{new_level} Seviye** oldu!\n\n"
                    f"Bonus: **+{bonus} VisoCoin**\n"
                    f"Toplam XP: **{user['xp']}**\n"
                    f"Bakiye: **{user['money']}** VisoCoin"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )
            await message.channel.send(embed=embed)
        else:
            user["level"] = new_level
            save_user(user)

    # ================= SOHBET PARA ODULU =================
    if message.channel.id == CHAT_REWARD_CHANNEL_ID:
        uid = message.author.id
        now = int(time.time())

        if uid not in chat_reward_cd or chat_reward_cd[uid] <= now:
            chat_reward_cd[uid] = now + CHAT_REWARD_COOLDOWN

            if random.random() < CHAT_REWARD_CHANCE:
                kazanc = random.randint(CHAT_REWARD_MIN, CHAT_REWARD_MAX)
                user = get_user(uid)
                user["money"] += kazanc
                save_user(user)

                embed = discord.Embed(
                    title="🍀 Şanslı Mesaj!",
                    description=(
                        f"{message.author.mention}, sohbet ederken **{kazanc} VisoCoin** buldun!\n"
                        f"Yeni bakiyen: **{user['money']}** VisoCoin"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text="Sohbet et, şansını dene!")
                await message.channel.send(embed=embed)

    await bot.process_commands(message)


# ======================================================================
#                        EKONOMI KOMUTLARI
# ======================================================================

@bot.command(name="bakiye", aliases=["para", "visocoin", "money", "cash"])
async def bakiye(ctx):
    user = get_user(ctx.author.id)

    embed = discord.Embed(
        title="💰 Bakiye",
        description=f"{ctx.author.mention}, şu anki VisoCoin miktarın: **{user['money']}**",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)

@bot.command(name="daily", aliases=["günlük"])
async def gunluk(ctx):
    user = get_user(ctx.author.id)

    now = time.time()
    if now - user["last_daily"] < 86400:
        kalan = int(86400 - (now - user["last_daily"]))
        bitis_zamani = datetime.fromtimestamp(now + kalan, tz=timezone.utc)
        embed = discord.Embed(
            title="✨ Günlük",
            description=f"{ctx.author.mention}, günlük için <t:{int(bitis_zamani.timestamp())}:f> zamanına kadar bekle.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    miktar = random.randint(300, 500)
    user["money"] += miktar
    user["last_daily"] = now
    save_user(user)

    update_quest_progress(ctx.author.id, "daily", 1)

    embed = discord.Embed(
        title="✅ Günlük Alındı",
        description=f"{ctx.author.mention}, bugün **{miktar}** VisoCoin aldın!",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)

# ======================================================================
#                        COINFLIP
# ======================================================================

@bot.command(name="coinflip", aliases=["cf", "yazıtura", "yt", "yazitura"])
async def coinflip(ctx, choice: str = None, miktar: int = None):
    user_id = ctx.author.id
    now = int(time.time())

    if user_id in coinflip_cd and coinflip_cd[user_id] > now:
        bitis = coinflip_cd[user_id]
        embed = discord.Embed(
            description=f"Bekleme süresindesin: <t:{bitis}:R>",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    if choice is None or miktar is None:
        embed = discord.Embed(
            title="Yazı Tura - Nasıl Oynanır",
            description="Kullanım: `!coinflip <yazı/tura> <miktar>`\n\nÖrnek: `!coinflip tura 100`",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    choice = choice.lower()

    if choice not in ["yazı", "tura"]:
        embed = discord.Embed(
            description="Seçenek olarak `yazı` veya `tura` girebilirsin.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if miktar <= 0:
        embed = discord.Embed(
            description="Geçerli bir miktar gir.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user = get_user(user_id)

    if user["money"] < miktar:
        embed = discord.Embed(
            description="Yetersiz bakiye.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= miktar
    save_user(user)

    # Animasyon embed'leri
    anim_frames = [
        ("🎡 Dönüyor...", discord.Color.light_grey()),
        ("🍃 Havada süzülüyor...", discord.Color.light_grey()),
        ("💵 Sonuç geliyor...", discord.Color.dark_grey()),
    ]

    anim_embed = discord.Embed(
        title="Yazı Tura",
        description=f"Bahis: **{miktar:,}** VisoCoin\n{'━' * 20}\n\nHazırlanıyor...",
        color=discord.Color.light_grey(),
        timestamp=datetime.now(timezone.utc)
    )
    anim_embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    msg = await ctx.send(embed=anim_embed)

    for frame_text, frame_color in anim_frames:
        await asyncio.sleep(0.7)
        anim_embed.description = f"Bahis: **{miktar:,}** VisoCoin\n{'━' * 20}\n\n{frame_text}"
        anim_embed.color = frame_color
        await msg.edit(embed=anim_embed)

    result = random.choice(["yazı", "tura"])
    coinflip_cd[user_id] = now + COINFLIP_COOLDOWN

    update_quest_progress(user_id, "coinflip", 1)

    await asyncio.sleep(0.5)

    user = get_user(user_id)

    if result == choice:
        kazanc = miktar * 2
        user["money"] += kazanc
        save_user(user)
        update_quest_progress(user_id, "coinflip_kazan", kazanc)

        embed = discord.Embed(
            title="Yazı Tura - Kazandın!",
            description=(
                f"Bahis: **{miktar:,}** VisoCoin | Seçimin: **{choice.upper()}**\n"
                f"{'━' * 25}\n\n"
                f"Sonuç: **{result.upper()}**\n\n"
                f"**+{kazanc:,} VisoCoin** kazandın!\n"
                f"Bakiye: **{user['money']:,}** VisoCoin"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
    else:
        save_user(user)

        embed = discord.Embed(
            title="Yazı Tura - Kaybettin!",
            description=(
                f"Bahis: **{miktar:,}** VisoCoin | Seçimin: **{choice.upper()}**\n"
                f"{'━' * 25}\n\n"
                f"Sonuç: **{result.upper()}**\n\n"
                f"**{miktar:,} VisoCoin** kaybettin.\n"
                f"Bakiye: **{user['money']:,}** VisoCoin"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)


# ======================================================================
#                        BLACKJACK
# ======================================================================

def draw_card():
    """Rastgele bir kart çek (sadece sayılar)."""
    cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    return random.choice(cards)

def hand_value(hand):
    """Toplam ve soft durumunu döndür."""
    total = sum(hand)
    aces = hand.count(11)

    # Önce As'ları düşür
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    # Eğer hala 11 sayılan As varsa → soft
    soft = aces > 0

    return total, soft

def format_hand(hand):
    """Eli gösterim formatına çevir."""
    return " | ".join([f"`{c}`" for c in hand])

def bj_embed(author, miktar, player_hand, dealer_hand, durum="oyun", sonuc_text=""):
    """Blackjack embed oluştur."""
    p_val, p_soft = hand_value(player_hand)
    d_val, d_soft = hand_value(dealer_hand)

    # Ust bar
    bar = f"Bahis: **{miktar:,}** VisoCoin"
    p_text = f"{p_val}*" if p_soft else f"{p_val}"
    d_text = f"{d_val}*" if d_soft else f"{d_val}"

    if durum == "oyun":
        # Oyun devam ediyor - krupiyenin 2. karti gizli
        desc = (
            f"{bar}\n"
            f"{'━' * 25}\n\n"
            f"**Senin Elin:** ({p_text})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot:** (?)\n"
            f"`{dealer_hand[0]}` | `?`\n\n"
            f"{'━' * 25}\n"
            f"Kart çek veya dur."
        )
        renk = discord.Color.blue()
        baslik = f"🃏 Blackjack - {author.display_name}"

    elif durum == "blackjack":
        desc = (
            f"{bar}\n"
            f"{'━' * 25}\n\n"
            f"**Senin Elin:** ({p_text})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot** ({d_text})\n"
            f"{format_hand(dealer_hand)}\n\n"
            f"{'━' * 25}\n"
            f"{sonuc_text}"
        )
        renk = discord.Color.gold()
        baslik = "🃏 BLACKJACK!"

    elif durum == "kazan":
        desc = (
            f"{bar}\n"
            f"{'━' * 25}\n\n"
            f"**Senin Elin:** ({p_text})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot:** ({d_text})\n"
            f"{format_hand(dealer_hand)}\n\n"
            f"{'━' * 25}\n"
            f"{sonuc_text}"
        )
        renk = discord.Color.green()
        baslik = "🃏 Kazandın!"

    elif durum == "kaybet":
        desc = (
            f"{bar}\n"
            f"{'━' * 25}\n\n"
            f"**Senin Elin:** ({p_text})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot:** ({d_text})\n"
            f"{format_hand(dealer_hand)}\n\n"
            f"{'━' * 25}\n"
            f"{sonuc_text}"
        )
        renk = discord.Color.red()
        baslik = "🃏 Kaybettin!"

    elif durum == "berabere":
        desc = (
            f"{bar}\n"
            f"{'━' * 25}\n\n"
            f"**Senin Elin:** ({p_text})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot:** ({d_text})\n"
            f"{format_hand(dealer_hand)}\n\n"
            f"{'━' * 25}\n"
            f"{sonuc_text}"
        )
        renk = discord.Color.orange()
        baslik = "🃏 Berabere!"

    else:
        desc = sonuc_text
        renk = discord.Color.greyple()
        baslik = "🃏 Blackjack"

    embed = discord.Embed(title=baslik, description=desc, color=renk, timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=f"{author.display_name}", icon_url=author.display_avatar.url)
    return embed


class BlackjackView(discord.ui.View):
    """Blackjack buton kontrolleri."""

    def __init__(self, ctx, miktar, player_hand, dealer_hand):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.miktar = miktar
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.user_id = ctx.author.id
        self.msg = None
        self.bitti = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Sadece komutu kullanan kişi butonlara basabilir."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Bu senin oyunun değil!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        """Zamanaşımı - bütün butonları kapat."""
        if not self.bitti:
            self.bitti = True
            blackjack_cd[self.user_id] = int(time.time()) + BLACKJACK_COOLDOWN
            update_quest_progress(self.user_id, "blackjack", 1)
            for item in self.children:
                item.disabled = True
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="kaybet", sonuc_text=f"Zamanaşımı! **{self.miktar:,} VisoCoin** kaybettin.")
            if self.msg:
                await self.msg.edit(embed=embed, view=self)

    async def sonuclandir(self, interaction: discord.Interaction):
        """VisoBot turunu oyna ve sonucu göster."""
        self.bitti = True
        now = int(time.time())
        blackjack_cd[self.user_id] = now + BLACKJACK_COOLDOWN
        update_quest_progress(self.user_id, "blackjack", 1)

        p_val, _ = hand_value(self.player_hand)

        # Krupiye 17'ye kadar cekmeli
        d_val, _ = hand_value(self.dealer_hand)
        while d_val < 17:
            self.dealer_hand.append(draw_card())
            d_val, _ = hand_value(self.dealer_hand)

        # Butonlari kapat
        for item in self.children:
            item.disabled = True

        user = get_user(self.user_id)

        if d_val > 21:
            kazanc = self.miktar * 2
            user["money"] += kazanc
            save_user(user)
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="kazan", sonuc_text=f"VisoBot patladı! **+{kazanc:,} VisoCoin** kazandın!")
        elif p_val > d_val:
            kazanc = self.miktar * 2
            user["money"] += kazanc
            save_user(user)
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="kazan", sonuc_text=f"**+{kazanc:,} VisoCoin** kazandın!")
        elif p_val == d_val:
            user["money"] += self.miktar
            save_user(user)
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="berabere", sonuc_text=f"Bahsin geri verildi.")
        else:
            save_user(user)
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="kaybet", sonuc_text=f"**{self.miktar:,} VisoCoin** kaybettin.")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Kart Çek", style=discord.ButtonStyle.primary, emoji=None, custom_id="bj_cek")
    async def cek_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kart çek butonu"""
        self.player_hand.append(draw_card())
        p_val, _ = hand_value(self.player_hand)

        if p_val > 21:
            # Bust - oyuncu patladi
            self.bitti = True
            now = int(time.time())
            blackjack_cd[self.user_id] = now + BLACKJACK_COOLDOWN
            update_quest_progress(self.user_id, "blackjack", 1)
            for item in self.children:
                item.disabled = True
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="kaybet", sonuc_text=f"Patladın! ({p_val}) **{self.miktar:,} VisoCoin** kaybettin.")
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
            return

        if p_val == 21:
            # Tam 21 - otomatik dur
            await self.sonuclandir(interaction)
            self.stop()
            return

        # Oyun devam ediyor
        embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand, durum="oyun")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Dur", style=discord.ButtonStyle.secondary, emoji=None, custom_id="bj_dur")
    async def dur_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Dur butonu - VisoBot'un turu başlar."""
        await self.sonuclandir(interaction)
        self.stop()

    @discord.ui.button(label="2x Bahis", style=discord.ButtonStyle.danger, emoji=None, custom_id="bj_double")
    async def double_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Çiftaşağı - bahisi ikiye katla, 1 kart çek ve dur."""
        user = get_user(self.user_id)
        if user["money"] < self.miktar:
            await interaction.response.send_message("2x için yeterli bakiyen yok!", ephemeral=True)
            return

        # Ek bahsi kes
        user["money"] -= self.miktar
        save_user(user)
        self.miktar *= 2

        # 1 kart cek
        self.player_hand.append(draw_card())
        p_val, _ = hand_value(self.player_hand)

        if p_val > 21:
            # Bust
            self.bitti = True
            now = int(time.time())
            blackjack_cd[self.user_id] = now + BLACKJACK_COOLDOWN
            update_quest_progress(self.user_id, "blackjack", 1)
            for item in self.children:
                item.disabled = True
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="kaybet", sonuc_text=f"Patladın! ({p_val}) **{self.miktar:,} VisoCoin** kaybettin.")
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
            return

        # Krupiye turuna gec
        await self.sonuclandir(interaction)
        self.stop()


@bot.command(name="blackjack", aliases=["bj", "21"])
async def blackjack(ctx, miktar: int = None):
    user_id = ctx.author.id
    now = int(time.time())

    if user_id in blackjack_cd and blackjack_cd[user_id] > now:
        bitis = blackjack_cd[user_id]
        return await ctx.send(f"Bekleme süresindesin: <t:{bitis}:R>")

    if miktar is None:
        return await ctx.send("Kullanım: `!blackjack <miktar>`")

    if miktar <= 0:
        return await ctx.send("Geçerli bir miktar gir.")

    user = get_user(user_id)
    if user["money"] < miktar:
        return await ctx.send("Yetersiz bakiye.")

    user["money"] -= miktar
    save_user(user)

    # Kartlari dagit
    player_hand = [draw_card(), draw_card()]
    dealer_hand = [draw_card(), draw_card()]

    p_val, _ = hand_value(player_hand)

    # Blackjack kontrolu (ilk dagitimda 21)
    if p_val == 21:
        kazanc = int(miktar * 2.5)
        user = get_user(user_id)
        user["money"] += kazanc
        save_user(user)
        blackjack_cd[user_id] = now + BLACKJACK_COOLDOWN
        update_quest_progress(user_id, "blackjack", 1)

        embed = bj_embed(ctx.author, miktar, player_hand, dealer_hand,
                         durum="blackjack", sonuc_text=f"BLACKJACK! **+{kazanc:,} VisoCoin** kazandın!")
        return await ctx.send(embed=embed)

    # Oyunu baslat - butonlu embed
    view = BlackjackView(ctx, miktar, player_hand, dealer_hand)
    embed = bj_embed(ctx.author, miktar, player_hand, dealer_hand, durum="oyun")
    msg = await ctx.send(embed=embed, view=view)
    view.msg = msg


# ======================================================================
#                        🎰 SLOT MAKINESI
# ======================================================================

SLOT_SYMBOLS = ["7", "BAR", "Kiraz", "Limon", "Üzüm", "Elma", "Yıldız"]

SLOT_PAYOUTS = {
    "7": 10,        # 3x 7 = 10x bahis
    "BAR": 7,       # 3x BAR = 7x bahis
    "Yıldız": 5,    # 3x Yildiz = 5x bahis
    "Kiraz": 4,     # 3x Kiraz = 4x bahis
    "Üzüm": 3,      # 3x Uzum = 3x bahis
    "Limon": 2,     # 3x Limon = 2x bahis
    "Elma": 2,      # 3x Elma = 2x bahis
}

@bot.command(name="slot", aliases=["slots", "slotmakinesi"])
async def slot(ctx, miktar: int = None):
    user_id = ctx.author.id
    now = int(time.time())

    if user_id in slot_cd and slot_cd[user_id] > now:
        bitis = slot_cd[user_id]
        embed = discord.Embed(
            description=f"Bekleme süresindesin: <t:{bitis}:R>",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    if miktar is None:
        embed = discord.Embed(
            title="Slot Makinesi - Nasıl Oynanır",
            description=(
                "Kullanım: `!slot <miktar>`\n\n"
                "**Ödemeler:**\n"
                "3x 7 = **10x** bahis\n"
                "3x BAR = **7x** bahis\n"
                "3x Yıldız = **5x** bahis\n"
                "3x Kiraz = **4x** bahis\n"
                "3x Üzüm = **3x** bahis\n"
                "3x Limon/Elma = **2x** bahis\n"
                "2x Eşleşme = **1.5x** bahis"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    if miktar <= 0:
        embed = discord.Embed(
            description="Geçerli bir miktar gir.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user = get_user(user_id)
    if user["money"] < miktar:
        embed = discord.Embed(
            description="Yetersiz bakiye.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= miktar
    save_user(user)

    slot_cd[user_id] = now + SLOT_COOLDOWN
    update_quest_progress(user_id, "slot", 1)
    update_quest_progress(user_id, "harca", miktar)

    # Animasyon embed'leri
    anim_embed = discord.Embed(
        title="Slot Makinesi",
        description=(
            f"Bahis: **{miktar:,}** VisoCoin\n"
            f"{'━' * 25}\n\n"
            f"[ **?** | **?** | **?** ]\n\n"
            f"Çevriliyor..."
        ),
        color=discord.Color.light_grey(),
        timestamp=datetime.now(timezone.utc)
    )
    anim_embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    msg = await ctx.send(embed=anim_embed)

    for _ in range(3):
        r1, r2, r3 = random.choice(SLOT_SYMBOLS), random.choice(SLOT_SYMBOLS), random.choice(SLOT_SYMBOLS)
        await asyncio.sleep(0.6)
        anim_embed.description = (
            f"Bahis: **{miktar:,}** VisoCoin\n"
            f"{'━' * 25}\n\n"
            f"[ **{r1}** | **{r2}** | **{r3}** ]\n\n"
            f"Çevriliyor..."
        )
        await msg.edit(embed=anim_embed)

    # Gercek sonuc
    reel1 = random.choice(SLOT_SYMBOLS)
    reel2 = random.choice(SLOT_SYMBOLS)
    reel3 = random.choice(SLOT_SYMBOLS)

    user = get_user(user_id)

    # 3 ayni sembol
    if reel1 == reel2 == reel3:
        carpan = SLOT_PAYOUTS.get(reel1, 2)
        kazanc = miktar * carpan
        user["money"] += kazanc
        save_user(user)

        embed = discord.Embed(
            title="Slot Makinesi - JACKPOT!",
            description=(
                f"Bahis: **{miktar:,}** VisoCoin\n"
                f"{'━' * 25}\n\n"
                f"[ **{reel1}** | **{reel2}** | **{reel3}** ]\n\n"
                f"3x **{reel1}**! ({carpan}x çarpan)\n"
                f"**+{kazanc:,} VisoCoin** kazandın!\n"
                f"Bakiye: **{user['money']:,}** VisoCoin"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )

    # 2 ayni sembol
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        kazanc = int(miktar * 1.5)
        user["money"] += kazanc
        save_user(user)

        embed = discord.Embed(
            title="Slot Makinesi - İkili Eşleşme!",
            description=(
                f"Bahis: **{miktar:,}** VisoCoin\n"
                f"{'━' * 25}\n\n"
                f"[ **{reel1}** | **{reel2}** | **{reel3}** ]\n\n"
                f"İkili eşleşme!\n"
                f"**+{kazanc:,} VisoCoin** kazandın!\n"
                f"Bakiye: **{user['money']:,}** VisoCoin"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )

    # Hic eslesmedi
    else:
        save_user(user)

        embed = discord.Embed(
            title="Slot Makinesi - Kaybettin!",
            description=(
                f"Bahis: **{miktar:,}** VisoCoin\n"
                f"{'━' * 25}\n\n"
                f"[ **{reel1}** | **{reel2}** | **{reel3}** ]\n\n"
                f"Eşleşme yok.\n"
                f"**{miktar:,} VisoCoin** kaybettin.\n"
                f"Bakiye: **{user['money']:,}** VisoCoin"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)


# ======================================================================
#                        RULET
# ======================================================================

RULET_KIRMIZI = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
RULET_SIYAH = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

@bot.command(name="rulet", aliases=["roulette"])
async def rulet(ctx, secim: str = None, miktar: int = None):
    user_id = ctx.author.id
    now = int(time.time())

    if user_id in rulet_cd and rulet_cd[user_id] > now:
        bitis = rulet_cd[user_id]
        return await ctx.send(f"Bekleme süresindesin <t:{bitis}:R>")

    if secim is None or miktar is None:
        embed = discord.Embed(
            title="🎱 Rulet - Nasil Oynanir",
            description=(
                "Kullanım: `!rulet <seçim> <miktar>`\n\n"
                "**Renk bahisleri (2x):**\n"
                "`!rulet kırmızı 100`\n"
                "`!rulet siyah 100`\n"
                "`!rulet yeşil 100` (0 = 14x)\n\n"
                "**Sayı bahisleri (36x):**\n"
                "`!rulet 17 100`\n\n"
                "**Tek/Çift Sayı (2x):**\n"
                "`!rulet tek 100`\n"
                "`!rulet çift 100`"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    secim = secim.lower()

    if miktar <= 0:
        return await ctx.send("Geçerli bir miktar gir.")

    user = get_user(user_id)
    if user["money"] < miktar:
        return await ctx.send("Yetersiz bakiye.")

    # Secim kontrolu
    valid_colors = ["kırmızı", "siyah", "yeşil"]
    valid_parity = ["tek", "çift"]
    is_number = False

    try:
        secim_sayi = int(secim)
        if 0 <= secim_sayi <= 36:
            is_number = True
        else:
            return await ctx.send("Sayi 0-36 arasında olmalı.")
    except ValueError:
        if secim not in valid_colors and secim not in valid_parity:
            return await ctx.send("Gecersiz secim! `kırmızı`, `siyah`, `yeşil`, `tek`, `çift` veya `0-36` arası sayı gir.")

    user["money"] -= miktar
    save_user(user)

    rulet_cd[user_id] = now + RULET_COOLDOWN
    update_quest_progress(user_id, "rulet", 1)
    update_quest_progress(user_id, "harca", miktar)

    # Animasyon
    msg = await ctx.send("🎱 Rulet çevriliyor...")
    await asyncio.sleep(1)
    await msg.edit(content="Top yuvarlanıyor...")
    await asyncio.sleep(1)

    # Sonuc
    result_number = random.randint(0, 36)

    if result_number in RULET_KIRMIZI:
        result_color = "kırmızı"
        color_emoji = "Kırmızı"
    elif result_number in RULET_SIYAH:
        result_color = "siyah"
        color_emoji = "Siyah"
    else:
        result_color = "yeşil"
        color_emoji = "Yeşil"

    result_parity = "tek" if result_number % 2 == 1 else "çift"

    # Kazanc hesapla
    kazanc = 0
    user = get_user(user_id)

    if is_number:
        if result_number == secim_sayi:
            kazanc = miktar * 36
    elif secim in valid_colors:
        if secim == result_color:
            if secim == "yeşil":
                kazanc = miktar * 14
            else:
                kazanc = miktar * 2
    elif secim in valid_parity:
        if result_number != 0 and secim == result_parity:
            kazanc = miktar * 2

    if kazanc > 0:
        user["money"] += kazanc
        save_user(user)

        embed = discord.Embed(
            title="🎱 Rulet - Kazandın!",
            description=(
                f"Top durdu: **{result_number}** ({color_emoji})\n\n"
                f"{ctx.author.mention}, bahsin: `{secim}` | **+{kazanc} VisoCoin** kazandın!\n"
                f"Bakiye: **{user['money']}** VisoCoin"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
    else:
        save_user(user)

        embed = discord.Embed(
            title="🎱 Rulet - Kaybettin!",
            description=(
                f"Top durdu: **{result_number}** ({color_emoji})\n\n"
                f"{ctx.author.mention}, bahsin: `{secim}` | **{miktar} VisoCoin** kaybettin.\n"
                f"Bakiye: **{user['money']}** VisoCoin"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

    await msg.edit(content=None, embed=embed)


# ======================================================================
#                        DUELLO
# ======================================================================

# Aktif duello davetleri {davet_edilen_id: {challenger, amount, timestamp}}
active_duels = {}

@bot.command(name="düello", aliases=["duel", "duello", "vs"])
async def duello(ctx, member: discord.Member = None, miktar: int = None):
    user_id = ctx.author.id
    now = int(time.time())

    if user_id in duello_cd and duello_cd[user_id] > now:
        bitis = duello_cd[user_id]
        return await ctx.send(f"Bekleme süresindesin: <t:{bitis}:R>")

    if member is None or miktar is None:
        return await ctx.send("Kullanım: `!duello @kisi <miktar>`")

    if member.id == user_id:
        return await ctx.send("Kendinle düello yapamazsın.")

    if member.bot:
        return await ctx.send("Botlarla düello yapamazsın.")

    if miktar <= 0:
        return await ctx.send("Geçerli bir miktar gir.")

    challenger = get_user(user_id)
    opponent = get_user(member.id)

    if challenger["money"] < miktar:
        return await ctx.send("Yetersiz bakiye.")

    if opponent["money"] < miktar:
        return await ctx.send(f"{member.mention} bu düello için yeterli VisoCoin'e sahip degil.")

    # Daveti kaydet
    active_duels[member.id] = {
        "challenger_id": user_id,
        "amount": miktar,
        "timestamp": now,
        "channel_id": ctx.channel.id
    }

    embed = discord.Embed(
        title="🤺 Düello Daveti!",
        description=(
            f"{ctx.author.mention} seni **{miktar} VisoCoin** bahisli düelloya davet ediyor!\n\n"
            f"{member.mention}, kabul etmek için `!kabul` yaz.\n"
            f"Reddetmek için `!reddet` yaz.\n\n"
            f"*30 saniye içinde cevap vermezsen davet iptal olur.*"
        ),
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)

@bot.command(name="kabul", aliases=["accept"])
async def kabul(ctx):
    user_id = ctx.author.id

    if user_id not in active_duels:
        return await ctx.send("Aktif bir düello davetin yok.")

    duel = active_duels[user_id]
    now = int(time.time())

    # Zaman asimi
    if now - duel["timestamp"] > 30:
        del active_duels[user_id]
        return await ctx.send("Düello daveti zaşımına uğradı.")

    if duel["channel_id"] != ctx.channel.id:
        return await ctx.send("Düelloyu başlanan kanalda kabul etmelisin.")

    challenger_id = duel["challenger_id"]
    miktar = duel["amount"]

    challenger = get_user(challenger_id)
    opponent = get_user(user_id)

    # Para kontrolu tekrar
    if challenger["money"] < miktar:
        del active_duels[user_id]
        return await ctx.send("Rakibinin yeterli VisoCoin'i yok.")

    if opponent["money"] < miktar:
        del active_duels[user_id]
        return await ctx.send("Yeterli VisoCoin'in yok.")

    # Paralari dus
    challenger["money"] -= miktar
    opponent["money"] -= miktar
    save_user(challenger)
    save_user(opponent)

    del active_duels[user_id]

    # Animasyon
    challenger_member = ctx.guild.get_member(challenger_id)
    msg = await ctx.send(f"Düello başlıyor! {challenger_member.mention} vs {ctx.author.mention}")

    frames = [
        "Kılıçlar çekildi...",
        "Savas kızışıyor...",
        "Son darbe vuruluyor...",
    ]

    for frame in frames:
        await asyncio.sleep(1)
        await msg.edit(content=frame)

    await asyncio.sleep(1)

    # Kazanan belirle
    winner_id = random.choice([challenger_id, user_id])
    loser_id = user_id if winner_id == challenger_id else challenger_id
    kazanc = miktar * 2

    winner = get_user(winner_id)
    winner["money"] += kazanc
    save_user(winner)

    winner_member = ctx.guild.get_member(winner_id)
    loser_member = ctx.guild.get_member(loser_id)

    duello_cd[challenger_id] = int(time.time()) + DUELLO_COOLDOWN
    duello_cd[user_id] = int(time.time()) + DUELLO_COOLDOWN

    update_quest_progress(challenger_id, "duello", 1)
    update_quest_progress(user_id, "duello", 1)

    embed = discord.Embed(
        title="🤺 Düello Sonucu!",
        description=(
            f"{winner_member.mention} düelloyu kazandın!\n"
            f"Kazanc: **+{kazanc} VisoCoin**\n"
            f"{loser_member.mention} **{miktar} VisoCoin** kaybetti."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    await msg.edit(content=None, embed=embed)

@bot.command(name="reddet", aliases=["decline", "reject"])
async def reddet(ctx):
    user_id = ctx.author.id

    if user_id not in active_duels:
        return await ctx.send("Aktif bir düello davetin yok.")

    challenger_id = active_duels[user_id]["challenger_id"]
    del active_duels[user_id]

    challenger_member = ctx.guild.get_member(challenger_id)

    embed = discord.Embed(
        title="🤺 Düello Reddedildi",
        description=f"{ctx.author.mention}, {challenger_member.mention} tarafından gelen düelloyu reddetti.",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


# ======================================================================
#                        HIRSIZLIK
# ======================================================================

@bot.command(name="rob", aliases=["çal", "hırsızlık"])
async def caldir(ctx, member: discord.Member = None):
    user_id = ctx.author.id
    now = int(time.time())

    if user_id in hirsizlik_cd and hirsizlik_cd[user_id] > now:
        bitis = hirsizlik_cd[user_id]
        return await ctx.send(f"Bekleme süresindesin: <t:{bitis}:R>")

    if member is None:
        return await ctx.send("Kullanım: `!çal @kişi`")

    if member.id == user_id:
        return await ctx.send("Kendinden çalamazsın.")

    if member.bot:
        return await ctx.send("Botlardan çalamazsın.")

    thief = get_user(user_id)
    victim = get_user(member.id)

    # Minimum para kontrolu
    if thief["money"] < 1000:
        return await ctx.send("Hırsızlık yapabilmek için en az **1000 VisoCoin**'in olmali (yakalanırsan ceza).")

    if victim["money"] < 100:
        return await ctx.send(f"{member.mention} çalmaya değer bir şeyi yok (100 VisoCoin'den az).")

    hirsizlik_cd[user_id] = now + HIRSIZLIK_COOLDOWN

    # Basari sansi: %30
    basari = random.random() < 0.30

    if basari:
        # Kurbandan %5-%15 arasi cal
        max_calma = int(victim["money"] * 0.15)
        min_calma = int(victim["money"] * 0.05)
        min_calma = max(min_calma, 50)
        max_calma = max(max_calma, min_calma + 1)

        calinti = random.randint(min_calma, max_calma)

        thief["money"] += calinti
        victim["money"] -= calinti
        save_user(thief)
        save_user(victim)

        embed = discord.Embed(
            title="🏴‍☠️ Hırsızlık Başarılı!",
            description=(
                f"{ctx.author.mention}, {member.mention} kişisinden **{calinti} VisoCoin** çaldın!\n\n"
                f"Bakiyen: **{thief['money']}** VisoCoin"
            ),
            color=discord.Color.dark_green(),
            timestamp=datetime.now(timezone.utc)
        )
    else:
        # Yakalandin! Para cezasi
        ceza = random.randint(100, 300)
        ceza = min(ceza, thief["money"])

        thief["money"] -= ceza
        save_user(thief)

        embed = discord.Embed(
            title="🏴‍☠️ Yakalandın!",
            description=(
                f"{ctx.author.mention}, {member.mention} kişisinden çalmayı denedin ama yakalandın!\n\n"
                f"Ceza: **-{ceza} VisoCoin**\n"
                f"Bakiyen: **{thief['money']}** VisoCoin"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

    await ctx.send(embed=embed)


# ======================================================================
#                        LEADERBOARD (SIRALAMA)
# ======================================================================

class LeaderboardView(discord.ui.View):
    def __init__(self, ctx, mode="money"):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.mode = mode  # "money" or "level"
        self.page = 0

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Bu butonlar sana ait degil 😏", ephemeral=True
            )
            return False
        return True

    def get_sorted(self):
        if self.mode == "money":
            return list(users_col.find().sort("money", -1))
        else:
            return list(users_col.find().sort("level", -1))

    def build_embed(self):
        data = self.get_sorted()
        start = self.page * PER_PAGE
        end = start + PER_PAGE
        sliced = data[start:end]

        medal_emojis = {0: "🥇", 1: "🥈", 2: "🥉"}
        desc = ""

        for i, u in enumerate(sliced, start=start):
            uid = u["user_id"]
            money = u.get("money", 0)
            level = u.get("level", 1)
            prefix = medal_emojis.get(i, f"{i + 1}.")

            member = self.ctx.guild.get_member(uid)
            name = member.display_name if member else f"Bilinmeyen ({uid})"

            if self.mode == "money":
                desc += f"**{prefix}** {name} — **{money:,}** VisoCoin (Sv. {level})\n"
            else:
                desc += f"**{prefix}** {name} — **Sv. {level}** ({money:,} VisoCoin)\n"

        title = "💰 VisoCoin Sıralaması" if self.mode == "money" else "⭐ Seviye Sıralaması"

        embed = discord.Embed(
            title=title,
            description=desc or "Veri yok.",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )

        max_page = max(1, (len(data) - 1) // PER_PAGE + 1)
        embed.set_footer(text=f"Sayfa {self.page + 1}/{max_page}")

        return embed

    # ===== MODE BUTTONS =====

    @discord.ui.button(label="💰 Para", style=discord.ButtonStyle.success)
    async def money_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "money"
        self.page = 0
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⭐ Seviye", style=discord.ButtonStyle.primary)
    async def level_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "level"
        self.page = 0
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    # ===== PAGE BUTTONS =====

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data_len = len(self.get_sorted())
        max_page = (data_len - 1) // PER_PAGE
        if self.page < max_page:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


# ================= KOMUT =================

@bot.command(name="leaderboard", aliases=["lb", "top", "siralama"])
async def leaderboard(ctx):
    view = LeaderboardView(ctx, mode="money")
    embed = view.build_embed()
    await ctx.send(embed=embed, view=view)


# ======================================================================
#                        SEVIYE KOMUTU
# ======================================================================

@bot.command(name="seviye", aliases=["level", "xp", "rank"])
async def seviye(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_user(target.id)

    current_level = user.get("level", 1)
    current_xp = user.get("xp", 0)
    next_level_xp = get_xp_for_next_level(current_level)

    if next_level_xp:
        # Mevcut seviyenin baslangic XP'si
        current_level_xp = 0
        for lvl, threshold, _ in LEVEL_THRESHOLDS:
            if lvl == current_level:
                current_level_xp = threshold
                break

        progress_xp = current_xp - current_level_xp
        needed_xp = next_level_xp - current_level_xp
        pct = min(progress_xp / needed_xp, 1.0) if needed_xp > 0 else 1.0
        filled = int(pct * 20)
        bar = "🟩" * filled + "⬛" * (20 - filled)
        xp_text = f"`[{bar}]` {progress_xp}/{needed_xp} XP"
    else:
        xp_text = "MAKS. SEVİYE!"

    embed = discord.Embed(
        title=f"⏫ {target.display_name} - Seviye Bilgisi",
        description=(
            f"Seviye: **{current_level}**\n"
            f"Toplam XP: **{current_xp}**\n"
            f"İlerleme: {xp_text}\n"
            f"VisoCoin: **{user['money']:,}**"
        ),
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


# ======================================================================
#                        TRANSFER (PARA gönderME)
# ======================================================================

@bot.command(name="gönder", aliases=["transfer", "pay", "ver"])
async def gönder(ctx, member: discord.Member = None, miktar: int = None):
    user_id = ctx.author.id
    now = int(time.time())

    if user_id in transfer_cd and transfer_cd[user_id] > now:
        bitis = transfer_cd[user_id]
        return await ctx.send(f"Bekleme süresindesin: <t:{bitis}:R>")

    if member is None or miktar is None:
        return await ctx.send("Kullanım: `!gönder @kişi <miktar>`")

    if member.id == user_id:
        return await ctx.send("Kendine para gönderemezsin.")

    if member.bot:
        return await ctx.send("Botlara para gönderemezsin.")

    if miktar <= 0:
        return await ctx.send("Geçerli bir miktar gir.")

    sender = get_user(user_id)
    if sender["money"] < miktar:
        return await ctx.send("Yetersiz bakiye.")

    receiver = get_user(member.id)

    # %5 vergi (komisyon)
    vergi = max(int(miktar * 0.05), 1)
    net_miktar = miktar - vergi

    sender["money"] -= miktar
    receiver["money"] += net_miktar
    save_user(sender)
    save_user(receiver)

    transfer_cd[user_id] = now + TRANSFER_COOLDOWN

    embed = discord.Embed(
        title="🤝 Transfer Başarılı!",
        description=(
            f"{ctx.author.mention} -> {member.mention}\n\n"
            f"Gönderilen: **{miktar}** VisoCoin\n"
            f"Komisyon (%5): **{vergi}** VisoCoin\n"
            f"Alıcının aldığı: **{net_miktar}** VisoCoin\n\n"
            f"Gönderen Kişinin Bakiyesi: **{sender['money']:,}** VisoCoin\n"
            f"Alıcının Bakiyesi: **{receiver['money']:,}** VisoCoin"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


# ======================================================================
#                        HEDIYE SISTEMI
# ======================================================================

@bot.command(name="hediye", aliases=["gift"])
async def hediye(ctx, member: discord.Member = None, miktar: int = None):
    user_id = ctx.author.id

    if member is None or miktar is None:
        return await ctx.send("Kullanım: `!hediye @kişi <miktar>`")

    if member.id == user_id:
        return await ctx.send("Kendine hediye gönderemezsin.")

    if member.bot:
        return await ctx.send("Botlara hediye gönderemezsin.")

    if miktar <= 0:
        return await ctx.send("Geçerli bir miktar gir.")

    sender = get_user(user_id)
    if sender["money"] < miktar:
        return await ctx.send("Yetersiz bakiye.")

    receiver = get_user(member.id)

    # Hediyede komisyon yok!
    sender["money"] -= miktar
    receiver["money"] += miktar
    save_user(sender)
    save_user(receiver)

    embed = discord.Embed(
        title="🎁 Hediye!",
        description=(
            f"{ctx.author.mention} kişisinden {member.mention} kişisine hediye!\n\n"
            f"**{miktar} VisoCoin** hediye edildi!\n\n"
            f"*Güzel bir jest! Hediye etmenin hiçbir komisyonu yok.*"
        ),
        color=discord.Color.magenta(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)

    # Aliciya DM
    try:
        dm_embed = discord.Embed(
            title="🎁 Hediye Aldın!",
            description=(
                f"**{ctx.author.display_name}** sana **{miktar} VisoCoin** hediye etti!\n"
                f"Yeni bakiyen: **{receiver['money']:,}** VisoCoin"
            ),
            color=discord.Color.magenta(),
            timestamp=datetime.now(timezone.utc)
        )
        await member.send(embed=dm_embed)
    except:
        pass  # DM kapali olabilir


# ======================================================================
#                        KASA SISTEMI
# ======================================================================

KASA_FIYAT = 400

@bot.command(name="kasa", aliases=["crate", "case", "box"])
async def kasa(ctx):
    user = get_user(ctx.author.id)
    save_user(user)

    if user["money"] < KASA_FIYAT:
        embed = discord.Embed(
            title="Yetersiz VisoCoin",
            description=f"{ctx.author.mention}, kasayı açmak için yeterli VisoCoin'in yok! ({KASA_FIYAT} gerekiyor.)",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    user["money"] -= KASA_FIYAT

    update_quest_progress(ctx.author.id, "kasa", 1)
    update_quest_progress(ctx.author.id, "harca", KASA_FIYAT)

    roll = random.random()
    if roll < 0.60:
        kazanc = random.randint(200, 300)
        rarity = "🟩 Sıradan"
    elif roll < 0.90:
        kazanc = random.randint(300, 500)
        rarity = "🟦 Ender"
    else:
        kazanc = random.randint(600, 900)
        rarity = "🟥 Destansı"

    user["money"] += kazanc
    save_user(user)

    embed = discord.Embed(
        title="Kasa Açıldı! (-400 VisoCoin)",
        description=f"{ctx.author.mention}, kasanı açtın!",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Enderlik:", value=rarity, inline=True)
    embed.add_field(name="Kazanç:", value=kazanc, inline=True)
    await ctx.send(embed=embed)


# ======================================================================
#                        ENVANTER & MARKET
# ======================================================================

@bot.command(name="envanter", aliases=["env", "inventory", "inv"])
async def envanter(ctx):
    user = get_user(ctx.author.id)
    save_user(user)

    inv = user.get("inventory", {})

    if not inv:
        embed = discord.Embed(
            title="Envanter",
            description=f"{ctx.author.mention}, envanterin boş.",
            color=discord.Color.greyple(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title="Envanter",
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
        title="Market",
        description="Satın almak için: `!satınal <ürün>`",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )

    for item_id, item in SHOP_ITEMS.items():
        embed.add_field(
            name=f"{item['name']} ({item_id})",
            value=f"Fiyat: {item['price']}",
            inline=False
        )

    await ctx.send(embed=embed)

SHOP_ITEMS = {
    "kumarbaz": {
        "price": 100000,
        "name": "🌟 Kumarbaz Rolü",
        "role_id": 1476980019262914612
    }
}

@bot.command(name="satınal", aliases=["buy"])
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
            title="❌ Yetersiz VisoCoin",
            description="VisoCoin'in yetmiyor!",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= item["price"]
    inv = user.setdefault("inventory", {})
    inv[item_id] = inv.get(item_id, 0) + 1
    save_user(user)

    update_quest_progress(ctx.author.id, "harca", item["price"])

    if "role_id" in item:
        role = ctx.guild.get_role(item["role_id"])
        if role:
            try:
                await ctx.author.add_roles(role)
                embed = discord.Embed(
                    title="✅ Satın Alındı!",
                    description=f"{ctx.author.mention}, **{item['name']}** rolünü aldın!",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            except:
                embed = discord.Embed(
                    title="❌ Hata",
                    description="Rol veremedim! Yetkini ve rol sırasını kontrol et.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Hata",
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


# ======================================================================
#                        ADMIN KOMUTLARI
# ======================================================================

@bot.command()
async def visocoinekle(ctx, miktar: int):
    YETKILI_USER_ID = 686628029987946600

    if ctx.author.id != YETKILI_USER_ID:
        return await ctx.send("Bu komutu kullanamazsın.")

    if miktar <= 0:
        return await ctx.send("Geçerli bir miktar gir.")

    user = get_user(ctx.author.id)

    user["money"] += miktar
    save_user(user)

    await ctx.send(f"Kendine **{miktar}** VisoCoin ekledin.")


# ======================================================================
#                        MUTE / UYARI SISTEMI
# ======================================================================

@bot.command(name="mute", aliases=["sustur"])
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, sure: int, *, sebep="Sebep belirtilmedi"):
    warnings = load_warnings()
    gid = str(ctx.guild.id)
    uid = str(member.id)

    warnings.setdefault(gid, {})
    warnings[gid].setdefault(uid, [])

    uyari_no = len(warnings[gid][uid]) + 1

    if uyari_no >= 4:
        try:
            await member.send(
                "**Sunucudan banlandın**\n"
                "Sebep: 3 uyarıdan sonra tekrar ceza almak."
            )
        except:
            pass

        await ctx.guild.ban(member, reason="3 uyarıdan sonra tekrar ceza")

        embed = discord.Embed(
            title="🔨 BAN ATILDI",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=False)
        embed.add_field(name="Sebep", value=sebep, inline=False)

        await send_log(ctx.guild, embed)
        await ctx.send(embed=embed)
        return

    uyari = {
        "uyari_no": uyari_no,
        "sebep": sebep,
        "sure": f"{sure} dk",
        "atan": ctx.author.name,
        "tarih": datetime.now(timezone.utc).isoformat()
    }

    warnings[gid][uid].append(uyari)
    save_warning(gid, uid, uyari)

    until = datetime.now(timezone.utc) + timedelta(minutes=sure)
    await member.timeout(until, reason=sebep)

    await temizle_ve_rolleri_guncelle()

    try:
        await member.send(
            f"**{uyari_no}. Uyarı Aldın**\n"
            f"Sebep: {sebep}\n"
            f"Süre: {sure} dakika"
        )
    except:
        pass

    embed = discord.Embed(
        title=f"{uyari_no}. ❗ UYARI VERİLDİ",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Kullanıcı", value=f"{member.mention} ({member.id})", inline=False)
    embed.add_field(name="Moderatör", value=ctx.author.mention, inline=False)
    embed.add_field(name="Mute", value=f"{sure} dk", inline=True)
    embed.add_field(name="Sebep", value=sebep, inline=False)

    await send_log(ctx.guild, embed)
    await ctx.send(embed=embed)


# ======================================================================
#                        UYARILAR
# ======================================================================

@bot.command(name="uyarilar", aliases=["warns", "warnings", "uyari"])
async def uyarilar(ctx, member: discord.Member = None):
    member = member or ctx.author
    warnings = load_warnings()

    gid = str(ctx.guild.id)
    uid = str(member.id)

    uyari_list = warnings.get(gid, {}).get(uid, [])

    if not uyari_list:
        embed = discord.Embed(
            title="Uyarı Yok",
            description=f"{member.mention} tertemiz.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=f"{member.name} - Uyarı Kayıtları",
        color=discord.Color.red()
    )

    for u in uyari_list:
        embed.add_field(
            name=f"{u['uyari_no']}. Uyarı",
            value=(
                f"Sebep: {u['sebep']}\n"
                f"Süre: {u['sure']}\n"
                f"Atan: {u['atan']}\n"
                f"Tarih: {u['tarih']}"
            ),
            inline=False
        )

    await ctx.send(embed=embed)


# ======================================================================
#                        GOREV KOMUTLARI
# ======================================================================

@bot.command(name="gorevler", aliases=["quests", "gorev", "görevler"])
async def gorevler(ctx):
    doc = get_user_quests(ctx.author.id)
    now = datetime.now(timezone.utc)

    daily_reset = datetime.fromisoformat(doc["daily_reset"])
    daily_remaining = int(86400 - (now - daily_reset).total_seconds())
    daily_remaining = max(daily_remaining, 0)

    weekly_reset = datetime.fromisoformat(doc["weekly_reset"])
    weekly_remaining = int(604800 - (now - weekly_reset).total_seconds())
    weekly_remaining = max(weekly_remaining, 0)

    embed = discord.Embed(
        title="-- 🔥 GÖREV PANELİ --",
        description=f"{ctx.author.mention}, aktif görevlerin aşağıda:",
        color=discord.Color.blue(),
        timestamp=now
    )

    daily_text = ""
    for quest in doc["daily"]:
        qdef = find_quest_def(quest["id"])
        if not qdef:
            continue
        prog = quest["progress"]
        goal = qdef["goal"]
        pct = min(prog / goal, 1.0)
        filled = int(pct * 10)
        bar = "🟩" * filled + "⬛" * (10 - filled)

        if quest["claimed"]:
            status = "[TOPLANDI]"
        elif prog >= goal:
            status = "[✅ HAZIR!]"
        else:
            status = f"{prog}/{goal}"

        daily_text += (
            f"**{qdef['name']}** - {qdef['desc']}\n"
            f"`[{bar}]` {status} | Ödül: **{qdef['reward']}** VisoCoin\n\n"
        )

    if not daily_text:
        daily_text = "Görev yok."

    daily_reset_ts = int((daily_reset + timedelta(seconds=86400)).timestamp())
    embed.add_field(
        name=f"-- Günlük Görevler -- (Yenilenme: <t:{daily_reset_ts}:R>)",
        value=daily_text,
        inline=False
    )

    weekly_text = ""
    for quest in doc["weekly"]:
        qdef = find_quest_def(quest["id"])
        if not qdef:
            continue
        prog = quest["progress"]
        goal = qdef["goal"]
        pct = min(prog / goal, 1.0)
        filled = int(pct * 10)
        bar = "🟩" * filled + "⬛" * (10 - filled)

        if quest["claimed"]:
            status = "[TOPLANDI]"
        elif prog >= goal:
            status = "[✅ HAZIR!]"
        else:
            status = f"{prog}/{goal}"

        weekly_text += (
            f"**{qdef['name']}** - {qdef['desc']}\n"
            f"`[{bar}]` {status} | Ödül: **{qdef['reward']}** VisoCoin\n\n"
        )

    if not weekly_text:
        weekly_text = "Görev yok."

    weekly_reset_ts = int((weekly_reset + timedelta(seconds=604800)).timestamp())
    embed.add_field(
        name=f"-- Haftalık Görevler -- (Yenilenme: <t:{weekly_reset_ts}:R>)",
        value=weekly_text,
        inline=False
    )

    embed.set_footer(text="Tamamlanan görevleri toplamak için: !görevtopla")
    await ctx.send(embed=embed)


@bot.command(name="gorevtopla", aliases=["questclaim", "görevtopla", "gt"])
async def gorevtopla(ctx):
    doc = get_user_quests(ctx.author.id)
    user = get_user(ctx.author.id)

    toplam_odul = 0
    toplanan = []

    for quest_list in [doc["daily"], doc["weekly"]]:
        for quest in quest_list:
            if quest["claimed"]:
                continue
            qdef = find_quest_def(quest["id"])
            if not qdef:
                continue
            if quest["progress"] >= qdef["goal"]:
                quest["claimed"] = True
                toplam_odul += qdef["reward"]
                toplanan.append(qdef)

    if not toplanan:
        embed = discord.Embed(
            title="-- Görev Toplama --",
            description=f"{ctx.author.mention}, toplanacak tamamlanmış görev yok!\n`!görevler` ile görevlerini kontrol et.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    user["money"] += toplam_odul
    save_user(user)
    save_quests(doc)

    gorev_listesi = "\n".join([f"  {q['name']} (+{q['reward']} VisoCoin)" for q in toplanan])

    embed = discord.Embed(
        title="-- ✅ Görev Ödülleri Toplandı! --",
        description=(
            f"{ctx.author.mention}, tebrikler!\n\n"
            f"**Toplanan görevler:**\n{gorev_listesi}\n\n"
            f"**Toplam ödül:** +{toplam_odul} VisoCoin\n"
            f"**Yeni bakiye:** {user['money']} VisoCoin"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


# ======================================================================
#                        YARDIM KOMUTU
# ======================================================================

@bot.command(name="yardim", aliases=["help", "komutlar", "yardım"])
async def yardim(ctx):
    embed = discord.Embed(
        title="VisoBot - Komut Listesi",
        description="Tum komutlar aşağıda listelenmiştir.",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="-- Ekonomi --",
        value=(
            "`!bakiye` - Bakiyeni gör\n"
            "`!daily` - Günlük ödülünü topla\n"
            "`!kasa` - Kasa aç (400 VisoCoin)\n"
            "`!market` - Marketi gör\n"
            "`!satinal <urun>` - Ürün satın al\n"
            "`!envanter` - Envanterini gör\n"
            "`!siralama` - En zenginler listesi\n"
            "`!seviye` - Seviye ve XP bilgisi\n"
        ),
        inline=False
    )

    embed.add_field(
        name="-- Kumar --",
        value=(
            "`!coinflip <yazı/tura> <miktar>` - Yazı Tura oyna\n"
            "`!blackjack <miktar>` - Blackjack oyna\n"
            "`!slot <miktar>` - Slot makinesi oyna\n"
            "`!rulet <seçim> <miktar>` - Rulet oyna\n"
        ),
        inline=False
    )

    embed.add_field(
        name="-- Sosyal --",
        value=(
            "`!düello @kisi <miktar>` - Duello davet et\n"
            "`!kabul` - Duelloyu kabul et\n"
            "`!reddet` - Duelloyu reddet\n"
            "`!gönder @kişi <miktar>` - Para gönder (%5 komisyon)\n"
            "`!hediye @kişi <miktar>` - Hediye gönder (komisyonsuz)\n"
            "`!çal @kişi` - Hırsızlık (Düşük başarı oranı)\n"
        ),
        inline=False
    )

    embed.add_field(
        name="-- Görevler --",
        value=(
            "`!görevler` - Aktif görevlerini gör\n"
            "`!görevtopla` - Tamamlanan görevleri topla\n"
        ),
        inline=False
    )

    embed.add_field(
        name="-- Moderasyon --",
        value=(
            "`!mute @kişi <dakika> [sebep]` - Kullanıcıyı sustur\n"
            "`!uyarilar [@kisi]` - Uyarı kayıtlarını gör\n"
        ),
        inline=False
    )

    embed.add_field(
        name="-- Tarla / Çiftlik --",
        value=(
            "`!tarla` - Tarla durumunu gör\n"
            "`!tohumlar` - Tohum listesini gör\n"
            "`!ek <tohum> [adet]` - Tohum ek\n"
            "`!hasat` - Hazır ürünleri topla\n"
            "`!sat <ürün> [adet]` - Ürün sat\n"
            "`!sat hepsi` - Tüm ürünleri sat\n"
            "`!gübresat [adet]` - Gübre satın al (150 VisoCoin)\n"
            "`!gübrele <slot>` - Slota gübre at\n"
        ),
        inline=False
    )

    embed.add_field(
        name="-- PvP Arena --",
        value=(
            "`!pvp @kişi <bahis>` - PvP düellosu\n"
            "`!pvpkabul` - Düelloyu kabul et\n"
            "`!pvpreddet` - Düelloyu reddet\n"
        ),
        inline=False
    )

    embed.add_field(
        name="-- Lonca --",
        value=(
            "`!loncakur <isim>` - Lonca kur (5000 VC)\n"
            "`!lonca` - Lonca bilgisi\n"
            "`!loncalar` - Lonca listesi\n"
            "`!loncadavet @kişi` - Üye davet et\n"
            "`!loncakabulet` - Daveti kabul et\n"
            "`!loncaçık` - Loncadan ayrıl\n"
            "`!loncaboss` - Lonca bossu savaşı\n"
        ),
        inline=False
    )

    await ctx.send(embed=embed)



# ======================================================================
#                        TARLA / ÇİFTLİK SİSTEMİ
# ======================================================================
# Bu kodu mevcut bot dosyanıza ekleyin.
# Aşağıdaki adımları izleyin:
#
# 1) En üste (importların yanına) farms_col ekleyin:
#    
#
# 2) Cooldown tanımlarını ekleyin (cooldown bölümüne):

#
# 3) Görev sistemiyle entegrasyon için DAILY_QUESTS ve WEEKLY_QUESTS'e
#    aşağıdaki görevleri ekleyin (opsiyonel):
#
#    DAILY_QUESTS içine:
#    
#
#    WEEKLY_QUESTS içine:
#    
#
# 4) Yardım komutuna (!yardım) Tarla bölümünü ekleyin
#
# 5) Bu dosyadaki tüm komutları ve fonksiyonları ana bot dosyanıza kopyalayın
# ======================================================================


TOHUMLAR = {
    "buğday": {
        "isim": "Buğday",
        "emoji": "🌾",
        "fiyat": 50,
        "süre": 300,          # 5 dakika
        "satış_min": 75,
        "satış_max": 100,
        "xp": 5,
    },
    "domates": {
        "isim": "Domates",
        "emoji": "🍅",
        "fiyat": 120,
        "süre": 600,          # 10 dakika
        "satış_min": 180,
        "satış_max": 240,
        "xp": 10,
    },
    "mısır": {
        "isim": "Mısır",
        "emoji": "🌽",
        "fiyat": 200,
        "süre": 600,          # 10 dakika
        "satış_min": 300,
        "satış_max": 400,
        "xp": 15,
    },
    "havuc": {
        "isim": "Havuc",
        "emoji": "🥕",
        "fiyat": 80,
        "süre": 600,          # 10 dakika
        "satış_min": 120,
        "satış_max": 160,
        "xp": 7,
    },
    "patates": {
        "isim": "Patates",
        "emoji": "🥔",
        "fiyat": 100,
        "süre": 1800,         # 30 dakika
        "satış_min": 150,
        "satış_max": 200,
        "xp": 8,
    },
    "cilek": {
        "isim": "Cilek",
        "emoji": "🍓",
        "fiyat": 300,
        "süre": 3600,         # 1 saat
        "satış_min": 450,
        "satış_max": 600,
        "xp": 20,
    },
    "karpuz": {
        "isim": "Karpuz",
        "emoji": "🍉",
        "fiyat": 500,
        "süre": 10800,        # 3 saat
        "satış_min": 750,
        "satış_max": 1000,
        "xp": 30,
    },
    "altin_elma": {
        "isim": "Altin Elma",
        "emoji": "🍎",
        "fiyat": 1000,
        "süre": 43200,        # 12 saat
        "satış_min": 1500,
        "satış_max": 2000,
        "xp": 50,
    },
    "ananas": {
        "isim": "Ananas",
        "emoji": "🍍",
        "fiyat": 2500,
        "süre": 86400,        # 24 saat
        "satış_min": 3000,
        "satış_max": 4500,
        "xp": 75,
    },
}

# Tarla seviye sistemi - her seviyede yeni slot açılır (XP'ye göre)
TARLA_SEVİYELERİ = {
    1: {"slot": 2, "bonus": 0},
    2: {"slot": 4, "bonus": 0},       # 100 XP
    3: {"slot": 6, "bonus": 0},       # 350 XP
    4: {"slot": 8, "bonus": 5},       # 750 XP   (%5 bonus satış)
    5: {"slot": 10, "bonus": 10},      # 1500 XP  (%10 bonus satış)
}

TARLA_SEVİYE_GEREKSİNİMLERİ = {
    2: 100,
    3: 350,
    4: 750,
    5: 1500,
}

# Gübre türleri
GÜBRELER = {
    "normal": {
        "isim": "Normal Gübre",
        "emoji": "🧪",
        "fiyat": 150,
        "azaltma": 0.10,   # Kalan süreyi %10 azaltır
    },
    "altın": {
        "isim": "Altın Gübre",
        "emoji": "🧫",
        "fiyat": 500,
        "azaltma": 0.25,   # Kalan süreyi %25 azaltır
    },
    "elmas": {
        "isim": "Elmas Gübre",
        "emoji": "💎",
        "fiyat": 1000,
        "azaltma": 0.40,   # Kalan süreyi %40 azaltır
    },
}


# ================= TARLA VERİTABANI =================

def get_farm(user_id):
    """Kullanıcının tarla verisini getir veya oluştur."""
    farm = farms_col.find_one({"user_id": user_id})
    if not farm:
        farm = {
            "user_id": user_id,
            "seviye": 1,
            "toplam_hasat": 0,
            "toplam_xp": 0,
            "slotlar": [],       # [{"tohum": "buğday", "ekim_zamanı": timestamp, "gübreli": False}, ...]
            "ambar": {},         # {"buğday": 5, "domates": 3, ...}
            "gübreler": {"normal": 0, "altın": 0, "elmas": 0},
        }
        farms_col.insert_one(farm)
    # Eski veriler için alan kontrolü (gübre -> gübreler migrasyonu)
    if "gübreler" not in farm:
        eski_gübre = farm.get("gübre", 0)
        farm["gübreler"] = {"normal": eski_gübre, "altın": 0, "elmas": 0}
    # Eksik gübre türleri kontrolü
    for gubre_id in GÜBRELER:
        if gubre_id not in farm["gübreler"]:
            farm["gübreler"][gubre_id] = 0
    if "toplam_hasat" not in farm:
        farm["toplam_hasat"] = 0
    if "toplam_xp" not in farm:
        farm["toplam_xp"] = 0
    return farm


def save_farm(farm):
    """Tarla verisini kaydet."""
    farms_col.update_one({"user_id": farm["user_id"]}, {"$set": farm}, upsert=True)


def get_farm_level(toplam_xp):
    """Toplam XP'ye göre tarla seviyesini hesapla."""
    seviye = 1
    for lvl, gereksinim in sorted(TARLA_SEVİYE_GEREKSİNİMLERİ.items()):
        if toplam_xp >= gereksinim:
            seviye = lvl
        else:
            break
    return seviye


def get_max_slot(seviye):
    """Tarla seviyesine göre maksimum slot sayısını getir."""
    return TARLA_SEVİYELERİ.get(seviye, TARLA_SEVİYELERİ[1])["slot"]


def get_satış_bonus(seviye):
    """Tarla seviyesine göre satış bonus yüzdesi."""
    return TARLA_SEVİYELERİ.get(seviye, TARLA_SEVİYELERİ[1])["bonus"]


# ================= TARLA KOMUTLARI =================

@bot.command(name="tarla", aliases=["farm", "çiftlik", "bahçe"])
async def tarla(ctx):
    """Tarla durumunu göster."""
    farm = get_farm(ctx.author.id)
    seviye = get_farm_level(farm["toplam_xp"])
    farm["seviye"] = seviye
    save_farm(farm)

    max_slot = get_max_slot(seviye)
    bonus = get_satış_bonus(seviye)
    sonraki_seviye = seviye + 1
    sonraki_gereksinim = TARLA_SEVİYE_GEREKSİNİMLERİ.get(sonraki_seviye)

    now = time.time()

    # Tarla durumu
    slot_text = ""
    for i, slot in enumerate(farm["slotlar"], 1):
        tohum = TOHUMLAR[slot["tohum"]]
        süre = tohum["süre"]
        geçen = now - slot["ekim_zamanı"]

        if geçen >= süre:
            slot_text += f"**{i}.** {tohum['emoji']} {tohum['isim']} -- Hasat icin hazir!\n"
        else:
            kalan = int(süre - geçen)
            dk = kalan // 60
            sn = kalan % 60
            gübre_tip = slot.get("gübre_tip")
            if gübre_tip and gübre_tip in GÜBRELER:
                gübre_text = f" ({GÜBRELER[gübre_tip]['emoji']} {GÜBRELER[gübre_tip]['isim']})"
            else:
                gübre_text = ""
            slot_text += f"**{i}.** {tohum['emoji']} {tohum['isim']} -- {dk}dk {sn}sn kaldi{gübre_text}\n"

    boş_slot = max_slot - len(farm["slotlar"])
    for i in range(len(farm["slotlar"]) + 1, max_slot + 1):
        slot_text += f"**{i}.** Boş slot\n"

    if not slot_text:
        slot_text = "Tarlan boş! `!ek <tohum>` ile ekim yap."

    # Ambar durumu
    ambar_text = ""
    for ürün_id, miktar in farm.get("ambar", {}).items():
        if miktar > 0:
            tohum = TOHUMLAR.get(ürün_id)
            if tohum:
                ambar_text += f"{tohum['emoji']} {tohum['isim']}: **{miktar}** adet\n"

    if not ambar_text:
        ambar_text = "Ambar boş."

    # Seviye ilerleme (XP'ye göre)
    if sonraki_gereksinim:
        ilerleme = farm["toplam_xp"]
        pct = min(ilerleme / sonraki_gereksinim, 1.0)
        filled = int(pct * 15)
        bar = "🟩" * filled + "⬛" * (15 - filled)
        seviye_text = f"Seviye **{seviye}** `[{bar}]` {ilerleme}/{sonraki_gereksinim} XP"
    else:
        seviye_text = f"Seviye **{seviye}** (MAKSİMUM!)"

    # Gübre bilgisi
    gübreler = farm.get("gübreler", {"normal": 0, "altın": 0, "elmas": 0})
    gübre_text = ""
    for gubre_id, gubre in GÜBRELER.items():
        miktar = gübreler.get(gubre_id, 0)
        gübre_text += f"{gubre['emoji']} {gubre['isim']}: **{miktar}**  "

    embed = discord.Embed(
        title=f"🌾 {ctx.author.display_name} - Tarla",
        description=(
            f"{seviye_text}\n"
            f"{'━' * 30}\n\n"
            f"**Tarlalar ({len(farm['slotlar'])}/{max_slot}):**\n"
            f"{slot_text}\n"
            f"**Ambar:**\n"
            f"{ambar_text}\n"
            f"**Gübreler:**\n{gübre_text}"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )

    if bonus > 0:
        embed.set_footer(text=f"Satis bonusu: +%{bonus}")
    else:
        embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


@bot.command(name="tohumlar", aliases=["seeds", "tohumlistesi"])
async def tohumlar(ctx):
    """Mevcut tohumları listele."""
    embed = discord.Embed(
        title="🌱 Tohum Listesi",
        description="Tohum ekmek için: `!ek <tohum>`",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )

    for tohum_id, tohum in TOHUMLAR.items():
        dk = tohum["süre"] // 60
        embed.add_field(
            name=f"{tohum['emoji']} {tohum['isim']} (`{tohum_id}`)",
            value=(
                f"Fiyat: **{tohum['fiyat']}** VisoCoin\n"
                f"Büyüme: **{dk}** dakika\n"
                f"Satış: **{tohum['satış_min']}-{tohum['satış_max']}** VisoCoin\n"
                f"XP: **+{tohum['xp']}**"
            ),
            inline=True
        )

    embed.set_footer(text="Gübre türleri: Normal (%10), altın (%25), Elmas (%40)")
    await ctx.send(embed=embed)


@bot.command(name="ek", aliases=["plant", "tohum"])
async def ek(ctx, tohum_id: str = None, adet: int = 1):
    """Tohum ek."""
    user_id = ctx.author.id

    if tohum_id is None:
        embed = discord.Embed(
            title="🌱 Tohum Ekme",
            description=(
                "Kullanım: `!ek <tohum> [adet]`\n\n"
                "Örnek: `!ek buğday` veya `!ek domates 3`\n\n"
                "Tohumları görmek için: `!tohumlar`"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    tohum_id = tohum_id.lower().strip()

    if tohum_id not in TOHUMLAR:
        embed = discord.Embed(
            description="Böyle bir tohum yok! `!tohumlar` ile mevcut tohumları gör.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if adet <= 0:
        embed = discord.Embed(
            description="Geçerli bir adet gir.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    tohum = TOHUMLAR[tohum_id]
    farm = get_farm(user_id)
    seviye = get_farm_level(farm["toplam_xp"])
    farm["seviye"] = seviye
    max_slot = get_max_slot(seviye)

    boş_slot = max_slot - len(farm["slotlar"])

    if boş_slot <= 0:
        embed = discord.Embed(
            description=f"Tarlanda boş slot yok! Önce hasat yap (`!hasat`) veya seviye atla.\nMevcut: {len(farm['slotlar'])}/{max_slot}",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Eklenebilecek miktarı sınırla
    adet = min(adet, boş_slot)
    toplam_fiyat = tohum["fiyat"] * adet

    user = get_user(user_id)
    if user["money"] < toplam_fiyat:
        embed = discord.Embed(
            description=f"Yetersiz bakiye! {adet}x {tohum['isim']} için **{toplam_fiyat}** VisoCoin gerekiyor.\nBakiyen: **{user['money']}** VisoCoin",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Parayı düşür
    user["money"] -= toplam_fiyat
    save_user(user)

    # Tohumları ek
    now = time.time()
    for _ in range(adet):
        farm["slotlar"].append({
            "tohum": tohum_id,
            "ekim_zamanı": now,
            "gübreli": False,
        })

    save_farm(farm)

    # Görev ilerlemesi
    update_quest_progress(user_id, "tohum_ek", adet)
    update_quest_progress(user_id, "harca", toplam_fiyat)

    embed = discord.Embed(
        title="🌱 Tohum Ekildi!",
        description=(
            f"{ctx.author.mention}, **{adet}x {tohum['emoji']} {tohum['isim']}** ekildi!\n\n"
            f"Maliyet: **{toplam_fiyat}** VisoCoin\n"
            f"Büyüme süresi: **{tohum['süre'] // 60}** dakika\n"
            f"Tarla: {len(farm['slotlar'])}/{max_slot} slot dolu\n\n"
            f"Hasat için: `!hasat`"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="hasat", aliases=["harvest", "topla"])
async def hasat(ctx):
    """Hazır olan ürünleri hasat et."""
    user_id = ctx.author.id
    farm = get_farm(user_id)
    user = get_user(user_id)
    now = time.time()

    hazır_ürünler = []
    kalan_slotlar = []

    for slot in farm["slotlar"]:
        tohum = TOHUMLAR[slot["tohum"]]
        süre = tohum["süre"]

        geçen = now - slot["ekim_zamanı"]

        if geçen >= süre:
            # Hasat hazır
            hazır_ürünler.append(slot["tohum"])
        else:
            # Henüz hazır değil
            kalan_slotlar.append(slot)

    if not hazır_ürünler:
        embed = discord.Embed(
            title="🌾 Hasat",
            description=f"{ctx.author.mention}, hasat edilecek hazır ürün yok!\n`!tarla` ile durumu kontrol et.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    # Ürünleri ambara ekle
    ambar = farm.get("ambar", {})
    hasat_detay = {}
    toplam_xp = 0

    for ürün_id in hazır_ürünler:
        tohum = TOHUMLAR[ürün_id]
        ambar[ürün_id] = ambar.get(ürün_id, 0) + 1
        hasat_detay[ürün_id] = hasat_detay.get(ürün_id, 0) + 1
        toplam_xp += tohum["xp"]

    farm["ambar"] = ambar
    farm["slotlar"] = kalan_slotlar
    farm["toplam_hasat"] = farm.get("toplam_hasat", 0) + len(hazır_ürünler)
    farm["toplam_xp"] = farm.get("toplam_xp", 0) + toplam_xp

    # Seviye kontrolü (XP'ye göre)
    eski_seviye = farm.get("seviye", 1)
    yeni_seviye = get_farm_level(farm["toplam_xp"])
    farm["seviye"] = yeni_seviye
    save_farm(farm)

    # XP ekle
    user["xp"] = user.get("xp", 0) + toplam_xp
    save_user(user)

    # Görev ilerlemesi
    update_quest_progress(user_id, "hasat", len(hazır_ürünler))

    # Hasat detayları
    detay_text = ""
    for ürün_id, adet in hasat_detay.items():
        tohum = TOHUMLAR[ürün_id]
        detay_text += f"{tohum['emoji']} {tohum['isim']}: **{adet}** adet\n"

    embed = discord.Embed(
        title="🌾 Hasat Tamamlandı!",
        description=(
            f"{ctx.author.mention}, hasat başarılı!\n\n"
            f"**Toplanan ürünler:**\n"
            f"{detay_text}\n"
            f"**+{toplam_xp} XP** kazandın!\n"
            f"Toplam XP: **{farm['toplam_xp']}**"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

    # Seviye atladı mı?
    if yeni_seviye > eski_seviye:
        yeni_slot = get_max_slot(yeni_seviye)
        yeni_bonus = get_satış_bonus(yeni_seviye)
        level_embed = discord.Embed(
            title="🎉 Tarla Seviye Atladı!",
            description=(
                f"{ctx.author.mention}, tarla seviyen **{yeni_seviye}** oldu!\n\n"
                f"Yeni slot sayısı: **{yeni_slot}**\n"
                f"Satış bonusu: **+%{yeni_bonus}**"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=level_embed)


@bot.command(name="sat", aliases=["sell", "ürünsat"])
async def sat(ctx, ürün_id: str = None, adet: int = None):
    """Ambardaki ürünleri sat."""
    user_id = ctx.author.id

    if ürün_id is None:
        embed = discord.Embed(
            title="💰 Ürün Satışı",
            description=(
                "Kullanım: `!sat <ürün> [adet]` veya `!sat hepsi`\n\n"
                "Örnek: `!sat buğday 5` veya `!sat domates`\n"
                "Tüm ürünleri satmak için: `!sat hepsi`\n\n"
                "Ambarını görmek için: `!tarla`"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    ürün_id = ürün_id.lower().strip()
    farm = get_farm(user_id)
    user = get_user(user_id)
    seviye = get_farm_level(farm["toplam_xp"])
    bonus_pct = get_satış_bonus(seviye)
    ambar = farm.get("ambar", {})

    # Hepsini sat
    if ürün_id == "hepsi":
        toplam_kazanç = 0
        satış_detay = {}

        for uid, miktar in list(ambar.items()):
            if miktar <= 0:
                continue
            tohum = TOHUMLAR.get(uid)
            if not tohum:
                continue

            for _ in range(miktar):
                fiyat = random.randint(tohum["satış_min"], tohum["satış_max"])
                if bonus_pct > 0:
                    fiyat = int(fiyat * (1 + bonus_pct / 100))
                toplam_kazanç += fiyat

            satış_detay[uid] = miktar
            ambar[uid] = 0

        if toplam_kazanç == 0:
            embed = discord.Embed(
                description="Ambarında satılacak ürün yok!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        user["money"] += toplam_kazanç
        farm["ambar"] = ambar
        save_user(user)
        save_farm(farm)

        detay_text = ""
        for uid, miktar in satış_detay.items():
            tohum = TOHUMLAR[uid]
            detay_text += f"{tohum['emoji']} {tohum['isim']}: **{miktar}** adet\n"

        embed = discord.Embed(
            title="💰 Toplu Satış!",
            description=(
                f"{ctx.author.mention}, tüm ürünler satıldı!\n\n"
                f"**Satılan ürünler:**\n"
                f"{detay_text}\n"
                f"Toplam kazanç: **+{toplam_kazanç:,}** VisoCoin"
                f"{f' (Bonus: +%{bonus_pct})' if bonus_pct > 0 else ''}\n"
                f"Bakiye: **{user['money']:,}** VisoCoin"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        return await ctx.send(embed=embed)

    # Tek ürün sat
    if ürün_id not in TOHUMLAR:
        embed = discord.Embed(
            description="Böyle bir ürün yok!",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    mevcut = ambar.get(ürün_id, 0)
    if mevcut <= 0:
        embed = discord.Embed(
            description=f"Ambarında **{TOHUMLAR[ürün_id]['isim']}** yok!",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if adet is None:
        adet = mevcut  # Belirtilmezse hepsini sat

    adet = min(adet, mevcut)
    if adet <= 0:
        embed = discord.Embed(
            description="Geçerli bir adet gir.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    tohum = TOHUMLAR[ürün_id]
    toplam_kazanç = 0

    for _ in range(adet):
        fiyat = random.randint(tohum["satış_min"], tohum["satış_max"])
        if bonus_pct > 0:
            fiyat = int(fiyat * (1 + bonus_pct / 100))
        toplam_kazanç += fiyat

    ambar[ürün_id] = mevcut - adet
    farm["ambar"] = ambar
    user["money"] += toplam_kazanç
    save_user(user)
    save_farm(farm)

    embed = discord.Embed(
        title="💰 Ürün Satıldı!",
        description=(
            f"{ctx.author.mention}, **{adet}x {tohum['emoji']} {tohum['isim']}** satıldı!\n\n"
            f"Kazanç: **+{toplam_kazanç:,}** VisoCoin"
            f"{f' (Bonus: +%{bonus_pct})' if bonus_pct > 0 else ''}\n"
            f"Bakiye: **{user['money']:,}** VisoCoin\n"
            f"Ambarda kalan: **{ambar.get(ürün_id, 0)}** adet"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="gübrele", aliases=["fertilize", "gübre"])
async def gübrele(ctx, slot_no: int = None, gübre_türü: str = "normal"):
    """Belirli bir slota gübre at. Türler: normal, altın, elmas"""
    user_id = ctx.author.id
    farm = get_farm(user_id)

    if slot_no is None:
        # Gübre türlerini listele
        gübre_list = ""
        for gubre_id, gubre in GÜBRELER.items():
            miktar = farm.get("gübreler", {}).get(gubre_id, 0)
            gübre_list += f"{gubre['emoji']} **{gubre['isim']}** (`{gubre_id}`) - %{int(gubre['azaltma'] * 100)} hızlandırma - Elinde: **{miktar}**\n"

        embed = discord.Embed(
            title="Gübre Kullanımı",
            description=(
                f"Kullanım: `!gübrele <slot_no> [tür]`\n\n"
                f"**Gübre Türleri:**\n{gübre_list}\n"
                f"Örnek: `!gübrele 1 normal` veya `!gübrele 2 elmas`\n"
                f"Tür belirtilmezse **normal** gübre kullanılır.\n\n"
                f"Satın almak için: `!gübresat <tür> [adet]`"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    gübre_türü = gübre_türü.lower().strip()

    if gübre_türü not in GÜBRELER:
        embed = discord.Embed(
            description=f"Geçersiz gübre türü! Mevcut türler: `normal`, `altın`, `elmas`",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    gübreler = farm.get("gübreler", {"normal": 0, "altın": 0, "elmas": 0})

    if gübreler.get(gübre_türü, 0) <= 0:
        gubre = GÜBRELER[gübre_türü]
        embed = discord.Embed(
            description=f"{gubre['emoji']} **{gubre['isim']}** yok! `!gübresat {gübre_türü}` ile satın al.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if slot_no < 1 or slot_no > len(farm["slotlar"]):
        embed = discord.Embed(
            description=f"Geçersiz slot numarası! 1-{len(farm['slotlar'])} arası gir.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    slot = farm["slotlar"][slot_no - 1]

    if slot.get("gübreli"):
        embed = discord.Embed(
            description="Bu slot zaten gübreli!",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    # Gübre kullan - kalan süreyi azalt (ekim zamanini ileriye kaydir)
    gubre = GÜBRELER[gübre_türü]
    gübreler[gübre_türü] -= 1
    farm["gübreler"] = gübreler
    farm["slotlar"][slot_no - 1]["gübreli"] = True
    farm["slotlar"][slot_no - 1]["gübre_tip"] = gübre_türü

    tohum = TOHUMLAR[slot["tohum"]]
    now = time.time()
    geçen = now - slot["ekim_zamanı"]
    kalan = max(tohum["süre"] - geçen, 0)
    yeni_kalan = kalan * (1 - gubre["azaltma"])
    # ekim_zamanini ileriye kaydir
    farm["slotlar"][slot_no - 1]["ekim_zamanı"] = now - (tohum["süre"] - yeni_kalan)
    save_farm(farm)

    kalan_dk = int(yeni_kalan) // 60
    kalan_sn = int(yeni_kalan) % 60

    embed = discord.Embed(
        title=f"{gubre['emoji']} {gubre['isim']} Kullanildi!",
        description=(
            f"{ctx.author.mention}, **{slot_no}. slot**'a **{gubre['isim']}** atildi!\n\n"
            f"{tohum['emoji']} {tohum['isim']} kalan süre: **{kalan_dk}dk {kalan_sn}sn**'ye düstü! (-%{int(gubre['azaltma'] * 100)})\n"
            f"Kalan {gubre['isim']}: **{gübreler[gübre_türü]}**"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


@bot.command(name="gübresat", aliases=["buyfertilizer", "gübresal", "gübredükkanı"])
async def gübresat(ctx, gübre_türü: str = None, adet: int = 1):
    """Gübre satin al. Türler: normal, altın, elmas"""
    user_id = ctx.author.id

    if gübre_türü is None:
        # Gübre dükkanini goster
        gübre_list = ""
        for gubre_id, gubre in GÜBRELER.items():
            gübre_list += (
                f"{gubre['emoji']} **{gubre['isim']}** (`{gubre_id}`)\n"
                f"   Fiyat: **{gubre['fiyat']}** VisoCoin | Hizlandirma: **%{int(gubre['azaltma'] * 100)}**\n\n"
            )

        embed = discord.Embed(
            title="Gübre Dükkani",
            description=(
                f"Kullanim: `!gübresat <tür> [adet]`\n\n"
                f"{gübre_list}"
                f"Ornek: `!gübresat normal 5` veya `!gübresat elmas`"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        return await ctx.send(embed=embed)

    gübre_türü = gübre_türü.lower().strip()

    if gübre_türü not in GÜBRELER:
        embed = discord.Embed(
            description=f"Geçersiz gübre türü! Mevcut türler: `normal`, `altın`, `elmas`",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if adet <= 0:
        embed = discord.Embed(
            description="Geçerli bir adet gir.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    gubre = GÜBRELER[gübre_türü]
    toplam_fiyat = gubre["fiyat"] * adet
    user = get_user(user_id)

    if user["money"] < toplam_fiyat:
        embed = discord.Embed(
            description=f"Yetersiz bakiye! {adet}x {gubre['isim']} icin **{toplam_fiyat}** VisoCoin gerekiyor.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= toplam_fiyat
    save_user(user)

    farm = get_farm(user_id)
    gübreler = farm.get("gübreler", {"normal": 0, "altın": 0, "elmas": 0})
    gübreler[gübre_türü] = gübreler.get(gübre_türü, 0) + adet
    farm["gübreler"] = gübreler
    save_farm(farm)

    update_quest_progress(user_id, "harca", toplam_fiyat)

    embed = discord.Embed(
        title=f"{gubre['emoji']} {gubre['isim']} Satın Alındı!",
        description=(
            f"{ctx.author.mention}, **{adet}x {gubre['emoji']} {gubre['isim']}** satın aldın!\n\n"
            f"Maliyet: **{toplam_fiyat}** VisoCoin\n"
            f"Toplam {gubre['isim']}: **{gübreler[gübre_türü]}**\n"
            f"Bakiye: **{user['money']:,}** VisoCoin\n\n"
            f"Kullanmak için: `!gübrele <slot_no> {gübre_türü}`"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)




# ================= SINIF TANIMLARI =================

SINIFLAR = {
    "savaşçı": {
        "isim": "Savaşçı",
        "emoji": "⚔️",
        "açıklama": "Yüksek saldırı ve dayanıklılık. Yakın dövüş uzmanı.",
        "temel_can": 120,
        "temel_saldırı": 18,
        "temel_savunma": 14,
        "temel_şans": 5,
        "vuruş_mana_kazanç": 12,  # Her vuruşta kazanılan mana (güçlü sınıf = düşük)
        "özel_yetenek": "Öfke Darbesi",
        "özel_açıklama": "Saldırı gücünü %50 artırarak tek vuruş yapar. (Mana dolunca)",
        "özel_çarpan": 1.5,
    },
    "büyücü": {
        "isim": "Büyücü",
        "emoji": "🧙",
        "açıklama": "Güçlü büyüler ve kritik hasar. Düşük dayanıklılık.",
        "temel_can": 80,
        "temel_saldırı": 25,
        "temel_savunma": 8,
        "temel_şans": 12,
        "vuruş_mana_kazanç": 20,  # Her vuruşta kazanılan mana (en güçlü özel = en düşük)
        "özel_yetenek": "Ateş Topu",
        "özel_açıklama": "Düşmana %80 ekstra hasar veren büyü fırlatır. (Mana dolunca)",
        "özel_çarpan": 1.8,
    },
    "okçu": {
        "isim": "Okçu",
        "emoji": "🏹",
        "açıklama": "Dengeli saldırı, yüksek kritik şansı. Uzak mesafe.",
        "temel_can": 95,
        "temel_saldırı": 20,
        "temel_savunma": 10,
        "temel_şans": 18,
        "vuruş_mana_kazanç": 14,  # Her vuruşta kazanılan mana (dengeli)
        "özel_yetenek": "Zehirli Ok",
        "özel_açıklama": "3 tur boyunca her tur ekstra hasar verir. (Mana dolunca)",
        "özel_çarpan": 1.3,
    },
    "şövalye": {
        "isim": "Şövalye",
        "emoji": "🛡️",
        "açıklama": "En yüksek savunma ve can. Tank sınıfı.",
        "temel_can": 150,
        "temel_saldırı": 14,
        "temel_savunma": 22,
        "temel_şans": 3,
        "vuruş_mana_kazanç": 18,  # Her vuruşta kazanılan mana (tank = yüksek)
        "özel_yetenek": "Kalkan Duvarı",
        "özel_açıklama": "Savunmayı 2 katına çıkararak 2 tur boyunca hasar azaltır. (Mana dolunca)",
        "özel_çarpan": 0.5,  # hasar çarpanı (savunma modu)
    },
    "suikastçi": {
        "isim": "Suikastçi",
        "emoji": "🗡️",
        "açıklama": "Gölgelerde hareket eden, düşmana ıskalattırma şansı veren sınıf.",
        "temel_can": 85,
        "temel_saldırı": 22,
        "temel_savunma": 9,
        "temel_şans": 20,
        "vuruş_mana_kazanç": 10,  # Her vuruşta kazanılan mana (güçlü = düşük)
        "özel_yetenek": "Gölge Adımı",
        "özel_açıklama": "3 tur boyunca %25 kaçınma şansı kazanır. (Mana dolunca)",
        "özel_çarpan": 1.4,
        "kaçınma": 10,  # Pasif kaçınma şansı (%)
    },
    "doktor": {
        "isim": "Doktor",
        "emoji": "💉",
        "açıklama": "Şifa uzmanı. Kendini iyileştirebilir ve kalkan kazanabilir.",
        "temel_can": 100,
        "temel_saldırı": 15,
        "temel_savunma": 12,
        "temel_şans": 8,
        "vuruş_mana_kazanç": 35,  # Her vuruşta kazanılan mana (destek = yüksek)
        "özel_yetenek": "Acil Müdahale",
        "özel_açıklama": "Canı tamamen doldurur ve maksimum canın %25'i kadar kalkan kazanır. (Mana dolunca)",
        "özel_çarpan": 1.0,
        "iyileşme": 100,  # Maks canın yüzdesi olarak iyileşme
        "kalkan": 25,  # Maks canın yüzdesi olarak kalkan
    },
}

# Sabit mana değerleri
MAKS_MANA = 100  # Tüm sınıflar için sabit maksimum mana
KAT_BAŞLANGIÇ_MANA = 0  # Kat başında mana sıfırlanır


# ================= EKİPMAN SİSTEMİ =================

EKİPMANLAR = {
    # ================= KILIÇLAR =================
    "paslı_kılıç": {"isim": "Paslı Kılıç", "emoji": "🗡️", "tür": "silah", "saldırı": 3, "savunma": 0, "can": 0, "nadirlik": "Yaygın", "fiyat": 0},
    "demir_kılıç": {"isim": "Demir Kılıç", "emoji": "🗡️", "tür": "silah", "saldırı": 8, "savunma": 0, "can": 0, "nadirlik": "Sıradan", "fiyat": 500},
    "çelik_kılıç": {"isim": "Çelik Kılıç", "emoji": "⚔️", "tür": "silah", "saldırı": 15, "savunma": 0, "can": 0, "nadirlik": "Nadir", "fiyat": 1500},
    "ateş_kılıcı": {"isim": "Ateş Kılıcı", "emoji": "🔥", "tür": "silah", "saldırı": 25, "savunma": 0, "can": 5, "nadirlik": "Epik", "fiyat": 5000},
    "ejderha_kılıcı": {"isim": "Ejderha Kılıcı", "emoji": "🐉", "tür": "silah", "saldırı": 40, "savunma": 5, "can": 10, "nadirlik": "Efsanevi", "fiyat": 15000},
    "karanlık_asa": {"isim": "Karanlık Asa", "emoji": "🪄", "tür": "silah", "saldırı": 35, "savunma": 0, "can": 0, "nadirlik": "Epik", "fiyat": 6000},
    "yıldırım_yayı": {"isim": "Yıldırım Yayı", "emoji": "⚡", "tür": "silah", "saldırı": 30, "savunma": 0, "can": 0, "nadirlik": "Epik", "fiyat": 5500},
    # Yeni Kılıçlar
    "gümüş_kılıç": {"isim": "Gümüş Kılıç", "emoji": "🌙", "tür": "silah", "saldırı": 12, "savunma": 2, "can": 0, "nadirlik": "Nadir", "fiyat": 1800},
    "buz_kılıcı": {"isim": "Buz Kılıcı", "emoji": "❄️", "tür": "silah", "saldırı": 28, "savunma": 0, "can": 10, "nadirlik": "Epik", "fiyat": 5500},
    "şimşek_kılıcı": {"isim": "Şimşek Kılıcı", "emoji": "⚡", "tür": "silah", "saldırı": 32, "savunma": 0, "can": 0, "nadirlik": "Epik", "fiyat": 6500},
    "zehir_kılıcı": {"isim": "Zehir Kılıcı", "emoji": "☠️", "tür": "silah", "saldırı": 22, "savunma": 0, "can": 0, "nadirlik": "Nadir", "fiyat": 2500},
    "ruh_kesici": {"isim": "Ruh Kesici", "emoji": "💀", "tür": "silah", "saldırı": 45, "savunma": 8, "can": 15, "nadirlik": "Efsanevi", "fiyat": 18000},
    "kaos_kılıcı": {"isim": "Kaos Kılıcı", "emoji": "🌀", "tür": "silah", "saldırı": 55, "savunma": 10, "can": 25, "nadirlik": "Tanrısal", "fiyat": 20000},
    "güneş_kılıcı": {"isim": "Güneş Kılıcı", "emoji": "☀️", "tür": "silah", "saldırı": 60, "savunma": 15, "can": 30, "nadirlik": "Tanrısal", "fiyat": 10000},
    "kader_kılıcı": {"isim": "Kader Kılıcı", "emoji": "🌟", "tür": "silah", "saldırı": 70, "savunma": 20, "can": 50, "nadirlik": "Tanrısal", "fiyat": 10000},
    "cehennem_baltası": {"isim": "Cehennem Baltası", "emoji": "🪓", "tür": "silah", "saldırı": 50, "savunma": 0, "can": 20, "nadirlik": "Efsanevi", "fiyat": 20000},
    "fırtına_mızrağı": {"isim": "Fırtına Mızrağı", "emoji": "🔱", "tür": "silah", "saldırı": 38, "savunma": 5, "can": 10, "nadirlik": "Epik", "fiyat": 7500},

    # ================= ZIRHLAR =================
    "deri_zırh": {"isim": "Deri Zırh", "emoji": "🦺", "tür": "zırh", "saldırı": 0, "savunma": 5, "can": 10, "nadirlik": "Yaygın", "fiyat": 0},
    "demir_zırh": {"isim": "Demir Zırh", "emoji": "🛡️", "tür": "zırh", "saldırı": 0, "savunma": 12, "can": 20, "nadirlik": "Sıradan", "fiyat": 800},
    "çelik_zırh": {"isim": "Çelik Zırh", "emoji": "🛡️", "tür": "zırh", "saldırı": 0, "savunma": 20, "can": 35, "nadirlik": "Nadir", "fiyat": 2000},
    "elmas_zırh": {"isim": "Elmas Zırh", "emoji": "💎", "tür": "zırh", "saldırı": 5, "savunma": 35, "can": 50, "nadirlik": "Epik", "fiyat": 7000},
    "ejderha_zırhı": {"isim": "Ejderha Zırhı", "emoji": "🐲", "tür": "zırh", "saldırı": 10, "savunma": 50, "can": 80, "nadirlik": "Efsanevi", "fiyat": 18000},
    # Yeni Zırhlar
    "gümüş_zırh": {"isim": "Gümüş Zırh", "emoji": "🌙", "tür": "zırh", "saldırı": 0, "savunma": 18, "can": 30, "nadirlik": "Nadir", "fiyat": 2500},
    "buz_zırhı": {"isim": "Buz Zırhı", "emoji": "❄️", "tür": "zırh", "saldırı": 0, "savunma": 30, "can": 45, "nadirlik": "Epik", "fiyat": 6000},
    "ateş_zırhı": {"isim": "Ateş Zırhı", "emoji": "🔥", "tür": "zırh", "saldırı": 8, "savunma": 32, "can": 40, "nadirlik": "Epik", "fiyat": 6500},
    "gölge_zırhı": {"isim": "Gölge Zırhı", "emoji": "🖤", "tür": "zırh", "saldırı": 5, "savunma": 28, "can": 35, "nadirlik": "Nadir", "fiyat": 3000},
    "titan_zırhı": {"isim": "Titan Zırhı", "emoji": "🗿", "tür": "zırh", "saldırı": 15, "savunma": 55, "can": 100, "nadirlik": "Efsanevi", "fiyat": 10000},
    "cennet_zırhı": {"isim": "Cennet Zırhı", "emoji": "👼", "tür": "zırh", "saldırı": 20, "savunma": 70, "can": 150, "nadirlik": "Tanrısal", "fiyat": 13000},
    "kaos_zırhı": {"isim": "Kaos Zırhı", "emoji": "🌀", "tür": "zırh", "saldırı": 25, "savunma": 80, "can": 180, "nadirlik": "Tanrısal", "fiyat": 15000},
    "sonsuzluk_zırhı": {"isim": "Sonsuzluk Zırhı", "emoji": "♾️", "tür": "zırh", "saldırı": 30, "savunma": 100, "can": 250, "nadirlik": "Tanrısal", "fiyat": 30000},
    "kemik_zırhı": {"isim": "Kemik Zırhı", "emoji": "🦴", "tür": "zırh", "saldırı": 3, "savunma": 15, "can": 25, "nadirlik": "Sıradan", "fiyat": 1000},
    "kristal_zırhı": {"isim": "Kristal Zırhı", "emoji": "💠", "tür": "zırh", "saldırı": 12, "savunma": 45, "can": 70, "nadirlik": "Efsanevi", "fiyat": 12000},

    # ================= YÜZÜKLER =================
    "şans_yüzüğü": {"isim": "Şans Yüzüğü", "emoji": "💍", "tür": "yüzük", "saldırı": 0, "savunma": 0, "can": 0, "nadirlik": "Nadir", "şans": 10, "fiyat": 3000},
    "güç_yüzüğü": {"isim": "Güç Yüzüğü", "emoji": "💍", "tür": "yüzük", "saldırı": 12, "savunma": 5, "can": 15, "nadirlik": "Epik", "şans": 0, "fiyat": 5500},
    "hayalet_yüzüğü": {"isim": "Hayalet Yüzüğü", "emoji": "👻", "tür": "yüzük", "saldırı": 8, "savunma": 8, "can": 25, "nadirlik": "Efsanevi", "şans": 15, "fiyat": 12000},
    # Yeni Yüzükler
    "demir_yüzük": {"isim": "Demir Yüzük", "emoji": "⚙️", "tür": "yüzük", "saldırı": 3, "savunma": 3, "can": 5, "nadirlik": "Sıradan", "şans": 2, "fiyat": 600},
    "ateş_yüzüğü": {"isim": "Ateş Yüzüğü", "emoji": "🔥", "tür": "yüzük", "saldırı": 15, "savunma": 0, "can": 10, "nadirlik": "Epik", "şans": 5, "fiyat": 6000},
    "buz_yüzüğü": {"isim": "Buz Yüzüğü", "emoji": "❄️", "tür": "yüzük", "saldırı": 5, "savunma": 10, "can": 20, "nadirlik": "Epik", "şans": 8, "fiyat": 5800},
    "vampir_yüzüğü": {"isim": "Vampir Yüzüğü", "emoji": "🧛", "tür": "yüzük", "saldırı": 10, "savunma": 5, "can": 30, "nadirlik": "Efsanevi", "şans": 12, "fiyat": 1400},
    "ejderha_yüzüğü": {"isim": "Ejderha Yüzüğü", "emoji": "🐉", "tür": "yüzük", "saldırı": 18, "savunma": 12, "can": 40, "nadirlik": "Efsanevi", "şans": 10, "fiyat": 1600},
    "karanlık_yüzük": {"isim": "Karanlık Yüzük", "emoji": "🖤", "tür": "yüzük", "saldırı": 20, "savunma": 0, "can": 0, "nadirlik": "Epik", "şans": 18, "fiyat": 7000},
    "tanrı_yüzüğü": {"isim": "Tanrı Yüzüğü", "emoji": "👑", "tür": "yüzük", "saldırı": 30, "savunma": 20, "can": 60, "nadirlik": "Tanrısal", "şans": 25, "fiyat": 8000},
    "sonsuzluk_yüzüğü": {"isim": "Sonsuzluk Yüzüğü", "emoji": "♾️", "tür": "yüzük", "saldırı": 35, "savunma": 25, "can": 80, "nadirlik": "Tanrısal", "şans": 30, "fiyat": 10000},
    "kader_yüzüğü": {"isim": "Kader Yüzüğü", "emoji": "🌟", "tür": "yüzük", "saldırı": 40, "savunma": 30, "can": 100, "nadirlik": "Tanrısal", "şans": 35, "fiyat": 15000},
    "koruma_yüzüğü": {"isim": "Koruma Yüzüğü", "emoji": "🛡️", "tür": "yüzük", "saldırı": 0, "savunma": 15, "can": 35, "nadirlik": "Nadir", "şans": 5, "fiyat": 3500},

    # ================= VISORED ADASI EKİPMANLARI =================
    # Silahlar
    "okyanus_kılıcı": {"isim": "Okyanus Kılıcı", "emoji": "🌊", "tür": "silah", "saldırı": 45, "savunma": 8, "can": 20, "nadirlik": "Epik", "fiyat": 12000},
    "sirena_asası": {"isim": "Sirena Asası", "emoji": "🧜", "tür": "silah", "saldırı": 55, "savunma": 5, "can": 15, "nadirlik": "Efsanevi", "fiyat": 18000},
    "fırtına_baltası": {"isim": "Fırtına Baltası", "emoji": "⛈️", "tür": "silah", "saldırı": 65, "savunma": 10, "can": 30, "nadirlik": "Efsanevi", "fiyat": 25000},
    "kraken_mızrağı": {"isim": "Kraken Mızrağı", "emoji": "🦑", "tür": "silah", "saldırı": 80, "savunma": 15, "can": 40, "nadirlik": "Tanrısal", "fiyat": 40000},
    "poseidon_mızrağı": {"isim": "Poseidon Mızrağı", "emoji": "🔱", "tür": "silah", "saldırı": 100, "savunma": 25, "can": 60, "nadirlik": "Tanrısal", "fiyat": 60000},
    "visored_kılıcı": {"isim": "Visored Kılıcı", "emoji": "💀", "tür": "silah", "saldırı": 130, "savunma": 35, "can": 100, "nadirlik": "Tanrısal", "fiyat": 100000},
    "mercan_kılıcı": {"isim": "Mercan Kılıcı", "emoji": "🪸", "tür": "silah", "saldırı": 35, "savunma": 5, "can": 15, "nadirlik": "Nadir", "fiyat": 8000},
    "köpekbalığı_dişi": {"isim": "Köpekbalığı Dişi", "emoji": "🦈", "tür": "silah", "saldırı": 50, "savunma": 0, "can": 10, "nadirlik": "Epik", "fiyat": 14000},

    # Zırhlar
    "korsan_zırhı": {"isim": "Korsan Zırhı", "emoji": "🏴‍☠️", "tür": "zırh", "saldırı": 8, "savunma": 40, "can": 60, "nadirlik": "Epik", "fiyat": 12000},
    "inci_zırhı": {"isim": "İnci Zırhı", "emoji": "🦪", "tür": "zırh", "saldırı": 10, "savunma": 55, "can": 80, "nadirlik": "Efsanevi", "fiyat": 20000},
    "şimşek_zırhı": {"isim": "Şimşek Zırhı", "emoji": "⚡", "tür": "zırh", "saldırı": 15, "savunma": 70, "can": 100, "nadirlik": "Efsanevi", "fiyat": 28000},
    "kraken_zırhı": {"isim": "Kraken Zırhı", "emoji": "🦑", "tür": "zırh", "saldırı": 25, "savunma": 90, "can": 150, "nadirlik": "Tanrısal", "fiyat": 45000},
    "tanrı_zırhı": {"isim": "Deniz Tanrısı Zırhı", "emoji": "🔱", "tür": "zırh", "saldırı": 35, "savunma": 120, "can": 200, "nadirlik": "Tanrısal", "fiyat": 70000},
    "visored_zırhı": {"isim": "Visored Zırhı", "emoji": "💀", "tür": "zırh", "saldırı": 50, "savunma": 150, "can": 300, "nadirlik": "Tanrısal", "fiyat": 120000},
    "denizci_zırhı": {"isim": "Denizci Zırhı", "emoji": "⚓", "tür": "zırh", "saldırı": 5, "savunma": 30, "can": 45, "nadirlik": "Nadir", "fiyat": 7000},
    "kabuk_zırhı": {"isim": "Kabuk Zırhı", "emoji": "🐚", "tür": "zırh", "saldırı": 3, "savunma": 25, "can": 35, "nadirlik": "Sıradan", "fiyat": 4000},

    # Yüzükler
    "deniz_yüzüğü": {"isim": "Deniz Yüzüğü", "emoji": "🌊", "tür": "yüzük", "saldırı": 12, "savunma": 8, "can": 25, "nadirlik": "Epik", "şans": 12, "fiyat": 10000},
    "büyülü_deniz_yüzüğü": {"isim": "Büyülü Deniz Yüzüğü", "emoji": "✨", "tür": "yüzük", "saldırı": 20, "savunma": 15, "can": 45, "nadirlik": "Efsanevi", "şans": 18, "fiyat": 18000},
    "fırtına_yüzüğü": {"isim": "Fırtına Yüzüğü", "emoji": "⛈️", "tür": "yüzük", "saldırı": 28, "savunma": 18, "can": 60, "nadirlik": "Efsanevi", "şans": 22, "fiyat": 25000},
    "kraken_yüzüğü": {"isim": "Kraken Yüzüğü", "emoji": "🦑", "tür": "yüzük", "saldırı": 40, "savunma": 25, "can": 80, "nadirlik": "Tanrısal", "şans": 28, "fiyat": 40000},
    "deniz_tanrısı_yüzüğü": {"isim": "Deniz Tanrısı Yüzüğü", "emoji": "🔱", "tür": "yüzük", "saldırı": 55, "savunma": 35, "can": 120, "nadirlik": "Tanrısal", "şans": 35, "fiyat": 65000},
    "visored_yüzüğü": {"isim": "Visored Yüzüğü", "emoji": "💀", "tür": "yüzük", "saldırı": 75, "savunma": 50, "can": 180, "nadirlik": "Tanrısal", "şans": 45, "fiyat": 110000},
    "mercan_yüzüğü": {"isim": "Mercan Yüzüğü", "emoji": "🪸", "tür": "yüzük", "saldırı": 8, "savunma": 6, "can": 18, "nadirlik": "Nadir", "şans": 8, "fiyat": 6000},

    # ================= SCARLET SETİ EKİPMANLARI (ZİNDANA) =================
    # %0.001 düşme şansı - Oyundaki en nadir ekipmanlar
    "scarlet_kılıcı": {"isim": "Scarlet Kılıcı", "emoji": "🩸", "tür": "silah", "saldırı": 250, "savunma": 60, "can": 200, "nadirlik": "Zindana", "fiyat": 100000},
    "scarlet_zırhı": {"isim": "Scarlet Zırhı", "emoji": "🩸", "tür": "zırh", "saldırı": 80, "savunma": 300, "can": 500, "nadirlik": "Zindana", "fiyat": 100000},
    "scarlet_yüzüğü": {"isim": "Scarlet Yüzüğü", "emoji": "🩸", "tür": "yüzük", "saldırı": 120, "savunma": 80, "can": 300, "nadirlik": "Zindana", "şans": 50, "fiyat": 100000},
}

NADİRLİK_RENKLERİ = {
    "Yaygın": "⬜",
    "Sıradan": "🟩",
    "Nadir": "🟦",
    "Epik": "🟪",
    "Efsanevi": "🟧",
    "Tanrısal": "🟥",
    "Zindana": "❓",  # Ultra-nadir enderlik - %0.001 düşme şansı
}

# ================= CANAVAR TANIMLARI =================

CANAVARLAR = {
    # Kat 1-5: Kolay
    "fare": {"isim": "Dev Fare", "emoji": "🐀", "can": 30, "saldırı": 5, "savunma": 2, "xp": 8, "altın_min": 10, "altın_max": 30, "kat_min": 1, "kat_max": 5},
    "yarasa": {"isim": "Vampir Yarasa", "emoji": "🦇", "can": 40, "saldırı": 8, "savunma": 3, "xp": 12, "altın_min": 15, "altın_max": 45, "kat_min": 1, "kat_max": 5},
    "örümcek": {"isim": "Zehirli Örümcek", "emoji": "🕷️", "can": 50, "saldırı": 10, "savunma": 4, "xp": 15, "altın_min": 20, "altın_max": 60, "kat_min": 1, "kat_max": 8},

    # Kat 5-10: Orta
    "iskelet": {"isim": "İskelet Savaşçı", "emoji": "💀", "can": 80, "saldırı": 15, "savunma": 8, "xp": 25, "altın_min": 40, "altın_max": 100, "kat_min": 5, "kat_max": 10},
    "goblin": {"isim": "Goblin Şef", "emoji": "👺", "can": 100, "saldırı": 18, "savunma": 10, "xp": 30, "altın_min": 50, "altın_max": 120, "kat_min": 5, "kat_max": 12},
    "kurt_adam": {"isim": "Kurt Adam", "emoji": "🐺", "can": 120, "saldırı": 22, "savunma": 12, "xp": 40, "altın_min": 70, "altın_max": 160, "kat_min": 6, "kat_max": 15},

    # Kat 10-20: Zor
    "büyücü_canavar": {"isim": "Karanlık Büyücü", "emoji": "🧛", "can": 160, "saldırı": 30, "savunma": 15, "xp": 55, "altın_min": 100, "altın_max": 250, "kat_min": 10, "kat_max": 20},
    "golem": {"isim": "Taş Golem", "emoji": "🗿", "can": 250, "saldırı": 20, "savunma": 35, "xp": 65, "altın_min": 120, "altın_max": 300, "kat_min": 12, "kat_max": 25},
    "ejderha_yavrusu": {"isim": "Ejderha Yavrusu", "emoji": "🐉", "can": 200, "saldırı": 35, "savunma": 20, "xp": 80, "altın_min": 150, "altın_max": 400, "kat_min": 15, "kat_max": 30},

    # Kat 20+: Çok Zor
    "şeytan": {"isim": "Cehennem Şeytanı", "emoji": "😈", "can": 350, "saldırı": 45, "savunma": 25, "xp": 120, "altın_min": 250, "altın_max": 600, "kat_min": 20, "kat_max": 50},
    "lich": {"isim": "Lich Kralı", "emoji": "☠️", "can": 400, "saldırı": 50, "savunma": 30, "xp": 150, "altın_min": 300, "altın_max": 800, "kat_min": 25, "kat_max": 50},
}

# ================= BOSS TANIMLARI =================

BOSSLAR = {
    5: {"isim": "Kemik Şövalyesi", "emoji": "🦴", "can": 200, "saldırı": 22, "savunma": 15, "xp": 100, "altın_min": 200, "altın_max": 500, "loot": ["demir_kılıç", "demir_zırh"]},
    10: {"isim": "Goblin Kralı", "emoji": "👑", "can": 400, "saldırı": 35, "savunma": 22, "xp": 250, "altın_min": 500, "altın_max": 1200, "loot": ["çelik_kılıç", "çelik_zırh", "şans_yüzüğü"]},
    15: {"isim": "Vampir Lordu", "emoji": "🧛", "can": 600, "saldırı": 45, "savunma": 28, "xp": 400, "altın_min": 800, "altın_max": 2000, "loot": ["ateş_kılıcı", "karanlık_asa", "güç_yüzüğü"]},
    20: {"isim": "Ateş Ejderhası", "emoji": "🔥", "can": 900, "saldırı": 60, "savunma": 35, "xp": 600, "altın_min": 1500, "altın_max": 4000, "loot": ["ejderha_kılıcı", "ejderha_zırhı", "hayalet_yüzüğü"]},
    30: {"isim": "Karanlık İmparator", "emoji": "👹", "can": 1500, "saldırı": 80, "savunma": 50, "xp": 1000, "altın_min": 3000, "altın_max": 8000, "loot": ["ejderha_kılıcı", "ejderha_zırhı", "hayalet_yüzüğü"]},
    50: {"isim": "Kaos Tanrısı", "emoji": "🌑", "can": 3000, "saldırı": 120, "savunma": 70, "xp": 2500, "altın_min": 8000, "altın_max": 20000, "loot": ["ejderha_kılıcı", "ejderha_zırhı", "hayalet_yüzüğü"]},
}


# ================= PRESTİJ SİSTEMİ =================

PRESTİJ_SEVİYELERİ = {
    0: {"isim": "Çaylak Kaşif", "emoji": "🌱", "bonus_saldırı": 0, "bonus_can": 0, "bonus_altın": 0},
    1: {"isim": "Deneyimli Savaşçı", "emoji": "⭐", "bonus_saldırı": 5, "bonus_can": 20, "bonus_altın": 10},
    2: {"isim": "Usta Maceraperest", "emoji": "⭐⭐", "bonus_saldırı": 12, "bonus_can": 50, "bonus_altın": 20},
    3: {"isim": "Efsane Kahraman", "emoji": "⭐⭐⭐", "bonus_saldırı": 20, "bonus_can": 100, "bonus_altın": 35},
    4: {"isim": "Mistik Şampiyon", "emoji": "💫", "bonus_saldırı": 30, "bonus_can": 150, "bonus_altın": 50},
    5: {"isim": "Tanrısal Güç", "emoji": "👑", "bonus_saldırı": 50, "bonus_can": 250, "bonus_altın": 75},
    6: {"isim": "Antik Koruyucu", "emoji": "🏛️", "bonus_saldırı": 75, "bonus_can": 400, "bonus_altın": 100},
    7: {"isim": "Kadim Savaş Lordu", "emoji": "⚔️", "bonus_saldırı": 100, "bonus_can": 600, "bonus_altın": 125},
    8: {"isim": "Ölümsüz Titan", "emoji": "🗿", "bonus_saldırı": 130, "bonus_can": 850, "bonus_altın": 150},
    9: {"isim": "Evrenin Hakimi", "emoji": "🌌", "bonus_saldırı": 170, "bonus_can": 1150, "bonus_altın": 200},
    10: {"isim": "Yaratılışın Efendisi", "emoji": "✨", "bonus_saldırı": 220, "bonus_can": 1500, "bonus_altın": 250},
}

PRESTİJ_GEREKSİNİMLERİ = {
    1: {"kat": 20, "boss": 3, "seviye": 10},
    2: {"kat": 35, "boss": 6, "seviye": 15},
    3: {"kat": 50, "boss": 10, "seviye": 20},
    4: {"kat": 75, "boss": 15, "seviye": 25},
    5: {"kat": 100, "boss": 20, "seviye": 30},
    6: {"kat": 130, "boss": 28, "seviye": 35},
    7: {"kat": 165, "boss": 38, "seviye": 40},
    8: {"kat": 200, "boss": 50, "seviye": 45},
    9: {"kat": 250, "boss": 65, "seviye": 50},
    10: {"kat": 300, "boss": 80, "seviye": 55},
}


# ================= SET SİSTEMİ =================

SETLER = {
    "visored": {
        "isim": "Visored Seti",
        "emoji": "💀",
        "parçalar": ["visored_kılıcı", "visored_zırhı", "visored_yüzüğü"],
        "pasif_isim": "Ölümün Eli",
        "pasif_açıklama": "Her saldırıda verilen hasarın %15'i kadar can çalar. Kritik şansı +10%.",
        "bonus": {"can_çalma": 15, "kritik_bonus": 10},
    },
    "kraken": {
        "isim": "Kraken Seti",
        "emoji": "🦑",
        "parçalar": ["kraken_mızrağı", "kraken_zırhı", "kraken_yüzüğü"],
        "pasif_isim": "Derin Denizin Gazabı",
        "pasif_açıklama": "Alınan hasarın %20'si düşmana yansır. Savunma +15.",
        "bonus": {"hasar_yansıtma": 20, "savunma_bonus": 15},
    },
    "deniz_tanrısı": {
        "isim": "Deniz Tanrısı Seti",
        "emoji": "🔱",
        "parçalar": ["poseidon_mızrağı", "tanrı_zırhı", "deniz_tanrısı_yüzüğü"],
        "pasif_isim": "Poseidon'un Lütfu",
        "pasif_açıklama": "Her 3 turda bir %25 ekstra hasar. Mana kazanımı 2 katına çıkar.",
        "bonus": {"ekstra_hasar": 25, "mana_çarpanı": 2},
    },
    "fırtına": {
        "isim": "Fırtına Seti",
        "emoji": "⛈️",
        "parçalar": ["fırtına_baltası", "şimşek_zırhı", "fırtına_yüzüğü"],
        "pasif_isim": "Şimşek Çarpması",
        "pasif_açıklama": "Her saldırıda %20 şansla ekstra şimşek hasarı (saldırının %30'u).",
        "bonus": {"şimşek_şansı": 20, "şimşek_hasar": 30},
    },
    "ejderha": {
        "isim": "Ejderha Seti",
        "emoji": "🐉",
        "parçalar": ["ejderha_kılıcı", "ejderha_zırhı", "ejderha_yüzüğü"],
        "pasif_isim": "Ejderhanın Nefesi",
        "pasif_açıklama": "Saldırı gücü %20 artar. Ateş hasarına karşı bağışıklık.",
        "bonus": {"saldırı_artışı": 20, "ateş_bağışıklık": True},
    },
    "vampir": {
        "isim": "Vampir Seti",
        "emoji": "🧛",
        "parçalar": ["karanlık_asa", "elmas_zırh", "vampir_yüzüğü"],
        "pasif_isim": "Kan Emici",
        "pasif_açıklama": "Verilen hasarın %10'u kadar can çalar. Gece savaşlarında hasar +25%.",
        "bonus": {"can_çalma": 10, "gece_bonus": 25},
    },
    "tanrısal": {
        "isim": "Tanrısal Set",
        "emoji": "👑",
        "parçalar": ["ruh_kesici", "titan_zırhı", "tanrı_yüzüğü"],
        "pasif_isim": "İlahi Güç",
        "pasif_açıklama": "Tüm statlar %15 artar. Ölümden bir kez kurtulma şansı.",
        "bonus": {"stat_artışı": 15, "ikinci_şans": True},
    },
    "scarlet": {
        "isim": "Scarlet Seti",
        "emoji": "🩸",
        "parçalar": ["scarlet_kılıcı", "scarlet_zırhı", "scarlet_yüzüğü"],
        "pasif_isim": "Kanlı İntikam",
        "pasif_açıklama": "Tüm statlar %50 artar. Verilen hasarın %30'u kadar can çalar. Her turda %5 can yenilenir. Ölümden 2 kez kurtulma şansı. Düşmana verilen hasar %10 artar.",
        "bonus": {"stat_artışı": 50, "can_çalma": 30, "can_yenilenme": 5, "ölümsüzlük": 2, "hasar_çarpanı": 1.10},
    },
}


# ================= BOLGE SİSTEMİ =================

BOLGELER = {
    "zindan": {
        "isim": "Karanlık Zindan",
        "emoji": "🏰",
        "açıklama": "Klasik zindan macerası. Tüm maceracılar için açık.",
        "gerekli_prestij": 0,
    },
    "visored": {
        "isim": "Visored Adası",
        "emoji": "🏝️",
        "açıklama": "Gizemli ada. Tehlikeli yaratıklar ve efsanevi hazineler barındırır.",
        "gerekli_prestij": 5,
    },
}

# ================= VISORED ADASI CANAVAR TANIMLARI =================

VISORED_CANAVARLAR = {
    # Kat 1-5: Orta-Zor (Zindan 10-15 seviyesi gibi)
    "ada_yengeci": {"isim": "Dev Yengeç", "emoji": "🦀", "can": 150, "saldırı": 25, "savunma": 20, "xp": 45, "altın_min": 80, "altın_max": 200, "kat_min": 1, "kat_max": 5},
    "deniz_yılanı": {"isim": "Deniz Yılanı", "emoji": "🐍", "can": 180, "saldırı": 35, "savunma": 15, "xp": 55, "altın_min": 100, "altın_max": 250, "kat_min": 1, "kat_max": 8},
    "hayalet_korsan": {"isim": "Hayalet Korsan", "emoji": "👻", "can": 200, "saldırı": 30, "savunma": 18, "xp": 60, "altın_min": 120, "altın_max": 300, "kat_min": 3, "kat_max": 10},

    # Kat 5-15: Zor
    "sirena": {"isim": "Karanlık Sirena", "emoji": "🧜", "can": 280, "saldırı": 45, "savunma": 22, "xp": 85, "altın_min": 180, "altın_max": 450, "kat_min": 5, "kat_max": 15},
    "kraken_yavrusu": {"isim": "Kraken Yavrusu", "emoji": "🐙", "can": 350, "saldırı": 50, "savunma": 28, "xp": 100, "altın_min": 220, "altın_max": 550, "kat_min": 8, "kat_max": 18},
    "dev_köpekbalığı": {"isim": "Megalodon", "emoji": "🦈", "can": 400, "saldırı": 55, "savunma": 25, "xp": 120, "altın_min": 280, "altın_max": 700, "kat_min": 10, "kat_max": 20},

    # Kat 15-30: Cok Zor
    "fırtına_elementi": {"isim": "Fırtına Elementi", "emoji": "🌪️", "can": 500, "saldırı": 70, "savunma": 35, "xp": 160, "altın_min": 400, "altın_max": 1000, "kat_min": 15, "kat_max": 30},
    "deniz_canavarı": {"isim": "Leviathan", "emoji": "🐋", "can": 650, "saldırı": 80, "savunma": 40, "xp": 200, "altın_min": 500, "altın_max": 1200, "kat_min": 18, "kat_max": 35},
    "lanetli_kaptan": {"isim": "Lanetli Kaptan", "emoji": "☠️", "can": 550, "saldırı": 90, "savunma": 30, "xp": 220, "altın_min": 600, "altın_max": 1500, "kat_min": 20, "kat_max": 40},

    # Kat 30+: Efsanevi
    "deniz_tanrısı": {"isim": "Poseidon'un Gazabı", "emoji": "🔱", "can": 900, "saldırı": 110, "savunma": 50, "xp": 350, "altın_min": 1000, "altın_max": 2500, "kat_min": 30, "kat_max": 50},
    "kraken": {"isim": "Antik Kraken", "emoji": "🦑", "can": 1200, "saldırı": 130, "savunma": 60, "xp": 450, "altın_min": 1500, "altın_max": 4000, "kat_min": 35, "kat_max": 50},
}

# ================= VISORED ADASI BOSS TANIMLARI =================

VISORED_BOSSLAR = {
    5: {"isim": "Korsan Kralı", "emoji": "🏴‍☠️", "can": 600, "saldırı": 50, "savunma": 30, "xp": 300, "altın_min": 800, "altın_max": 2000, "loot": ["okyanus_kılıcı", "korsan_zırhı", "deniz_yüzüğü"]},
    10: {"isim": "Sirena Kraliçesi", "emoji": "👑", "can": 1000, "saldırı": 70, "savunma": 40, "xp": 500, "altın_min": 1500, "altın_max": 4000, "loot": ["sirena_asası", "inci_zırhı", "büyülü_deniz_yüzüğü"]},
    15: {"isim": "Fırtına Lordu", "emoji": "⛈️", "can": 1500, "saldırı": 90, "savunma": 50, "xp": 750, "altın_min": 2500, "altın_max": 6000, "loot": ["fırtına_baltası", "şimşek_zırhı", "fırtına_yüzüğü"]},
    20: {"isim": "Kraken Efendisi", "emoji": "🦑", "can": 2200, "saldırı": 120, "savunma": 65, "xp": 1200, "altın_min": 4000, "altın_max": 10000, "loot": ["kraken_mızrağı", "kraken_zırhı", "kraken_yüzüğü"]},
    30: {"isim": "Deniz Tanrısı", "emoji": "🔱", "can": 4000, "saldırı": 160, "savunma": 85, "xp": 2500, "altın_min": 10000, "altın_max": 25000, "loot": ["poseidon_mızrağı", "tanrı_zırhı", "deniz_tanrısı_yüzüğü"]},
    50: {"isim": "Visored'in Ruhu", "emoji": "💀", "can": 8000, "saldırı": 220, "savunma": 110, "xp": 5000, "altın_min": 25000, "altın_max": 60000, "loot": ["visored_kılıcı", "visored_zırhı", "visored_yüzüğü"]},
}


# ================= LOOT DROP TABLOLARI =================

LOOT_TABLOSU = {
    "kolay": [
        {"eşya": "paslı_kılıç", "şans": 20},
        {"eşya": "deri_zırh", "şans": 20},
        {"eşya": "demir_yüzük", "şans": 8},
        {"eşya": None, "şans": 52},  # eşya düşmez
    ],
    "orta": [
        {"eşya": "demir_kılıç", "şans": 12},
        {"eşya": "demir_zırh", "şans": 12},
        {"eşya": "gümüş_kılıç", "şans": 8},
        {"eşya": "gümüş_zırh", "şans": 8},
        {"eşya": "şans_yüzüğü", "şans": 5},
        {"eşya": "kemik_zırhı", "şans": 6},
        {"eşya": None, "şans": 49},
    ],
    "zor": [
        {"eşya": "çelik_kılıç", "şans": 10},
        {"eşya": "çelik_zırh", "şans": 10},
        {"eşya": "ateş_kılıcı", "şans": 5},
        {"eşya": "karanlık_asa", "şans": 5},
        {"eşya": "güç_yüzüğü", "şans": 3},
        {"eşya": "buz_kılıcı", "şans": 5},
        {"eşya": "buz_zırhı", "şans": 5},
        {"eşya": "şimşek_kılıcı", "şans": 4},
        {"eşya": "ateş_zırhı", "şans": 4},
        {"eşya": "ateş_yüzüğü", "şans": 3},
        {"eşya": "buz_yüzüğü", "şans": 3},
        {"eşya": None, "şans": 43},
    ],
    "çok_zor": [
        {"eşya": "ateş_kılıcı", "şans": 6},
        {"eşya": "ejderha_kılıcı", "şans": 3},
        {"eşya": "elmas_zırh", "şans": 5},
        {"eşya": "ejderha_zırhı", "şans": 2},
        {"eşya": "hayalet_yüzüğü", "şans": 2},
        {"eşya": "yıldırım_yayı", "şans": 4},
        {"eşya": "ruh_kesici", "şans": 2},
        {"eşya": "titan_zırhı", "şans": 2},
        {"eşya": "vampir_yüzüğü", "şans": 2},
        {"eşya": "ejderha_yüzüğü", "şans": 2},
        {"eşya": "cehennem_baltası", "şans": 2},
        {"eşya": "kristal_zırhı", "şans": 2},
        {"eşya": None, "şans": 66},
    ],
    "efsanevi": [
        {"eşya": "ejderha_kılıcı", "şans": 5},
        {"eşya": "ejderha_zırhı", "şans": 5},
        {"eşya": "ruh_kesici", "şans": 4},
        {"eşya": "titan_zırhı", "şans": 4},
        {"eşya": "cehennem_baltası", "şans": 4},
        {"eşya": "kaos_kılıcı", "şans": 1},
        {"eşya": "güneş_kılıcı", "şans": 1},
        {"eşya": "cennet_zırhı", "şans": 1},
        {"eşya": "kaos_zırhı", "şans": 1},
        {"eşya": "tanrı_yüzüğü", "şans": 1},
        {"eşya": "sonsuzluk_yüzüğü", "şans": 1},
        {"eşya": None, "şans": 72},
    ],
    "tanrısal": [
        {"eşya": "kaos_kılıcı", "şans": 3},
        {"eşya": "güneş_kılıcı", "şans": 3},
        {"eşya": "kader_kılıcı", "şans": 2},
        {"eşya": "cennet_zırhı", "şans": 3},
        {"eşya": "kaos_zırhı", "şans": 3},
        {"eşya": "sonsuzluk_zırhı", "şans": 2},
        {"eşya": "tanrı_yüzüğü", "şans": 3},
        {"eşya": "sonsuzluk_yüzüğü", "şans": 2},
        {"eşya": "kader_yüzüğü", "şans": 1},
        {"eşya": None, "şans": 78},
    ],
    # ================= ZİNDANA NADİRLİĞİ =================
    # %0.001 düşme şansı - Götünüz tutuşsun diye
    "zindana": [
        {"eşya": "scarlet_kılıcı", "şans": 0.001},   # 1/100.000 şans
        {"eşya": "scarlet_zırhı", "şans": 0.001},   # 1/100.000 şans
        {"eşya": "scarlet_yüzüğü", "şans": 0.001}, # 1/100.000 şans
        {"eşya": None, "şans": 99.997},
    ],
}

# ================= VISORED ADASI LOOT TABLOSU =================

VISORED_LOOT_TABLOSU = {
    "kolay": [  # Kat 1-5
        {"eşya": "mercan_kılıcı", "şans": 12},
        {"eşya": "kabuk_zırhı", "şans": 12},
        {"eşya": "denizci_zırhı", "şans": 8},
        {"eşya": "mercan_yüzüğü", "şans": 6},
        {"eşya": None, "şans": 62},
    ],
    "orta": [  # Kat 5-10
        {"eşya": "mercan_kılıcı", "şans": 8},
        {"eşya": "denizci_zırhı", "şans": 8},
        {"eşya": "okyanus_kılıcı", "şans": 6},
        {"eşya": "korsan_zırhı", "şans": 6},
        {"eşya": "deniz_yüzüğü", "şans": 5},
        {"eşya": "köpekbalığı_dişi", "şans": 5},
        {"eşya": None, "şans": 62},
    ],
    "zor": [  # Kat 10-18
        {"eşya": "okyanus_kılıcı", "şans": 8},
        {"eşya": "korsan_zırhı", "şans": 8},
        {"eşya": "köpekbalığı_dişi", "şans": 6},
        {"eşya": "sirena_asası", "şans": 4},
        {"eşya": "inci_zırhı", "şans": 4},
        {"eşya": "deniz_yüzüğü", "şans": 5},
        {"eşya": "büyülü_deniz_yüzüğü", "şans": 3},
        {"eşya": None, "şans": 62},
    ],
    "çok_zor": [  # Kat 18-30
        {"eşya": "sirena_asası", "şans": 6},
        {"eşya": "inci_zırhı", "şans": 6},
        {"eşya": "fırtına_baltası", "şans": 4},
        {"eşya": "şimşek_zırhı", "şans": 4},
        {"eşya": "büyülü_deniz_yüzüğü", "şans": 5},
        {"eşya": "fırtına_yüzüğü", "şans": 3},
        {"eşya": None, "şans": 72},
    ],
    "efsanevi": [  # Kat 30-45
        {"eşya": "fırtına_baltası", "şans": 5},
        {"eşya": "şimşek_zırhı", "şans": 5},
        {"eşya": "kraken_mızrağı", "şans": 3},
        {"eşya": "kraken_zırhı", "şans": 3},
        {"eşya": "fırtına_yüzüğü", "şans": 4},
        {"eşya": "kraken_yüzüğü", "şans": 2},
        {"eşya": None, "şans": 78},
    ],
    "tanrısal": [  # Kat 45+
        {"eşya": "kraken_mızrağı", "şans": 4},
        {"eşya": "kraken_zırhı", "şans": 4},
        {"eşya": "poseidon_mızrağı", "şans": 2},
        {"eşya": "tanrı_zırhı", "şans": 2},
        {"eşya": "kraken_yüzüğü", "şans": 3},
        {"eşya": "deniz_tanrısı_yüzüğü", "şans": 2},
        {"eşya": "visored_kılıcı", "şans": 1},
        {"eşya": "visored_zırhı", "şans": 1},
        {"eşya": "visored_yüzüğü", "şans": 1},
        {"eşya": None, "şans": 80},
    ],
}


def get_loot_zorluk(kat, bolge="zindan"):
    """Kata ve bolgeye göre loot zorluk seviyesi."""
    if bolge == "visored":
        # Visored Adası daha yüksek katlarda başlıyor gibi davran
        if kat <= 5:
            return "kolay"
        elif kat <= 10:
            return "orta"
        elif kat <= 18:
            return "zor"
        elif kat <= 30:
            return "çok_zor"
        elif kat <= 45:
            return "efsanevi"
        else:
            return "tanrısal"
    else:
        if kat <= 5:
            return "kolay"
        elif kat <= 12:
            return "orta"
        elif kat <= 25:
            return "zor"
        elif kat <= 40:
            return "çok_zor"
        elif kat <= 60:
            return "efsanevi"
        else:
            return "tanrısal"


def roll_loot(kat, bolge="zindan"):
    """Katta eşya düşürme şansını hesapla."""
    zorluk = get_loot_zorluk(kat, bolge)
    if bolge == "visored":
        tablo = VISORED_LOOT_TABLOSU[zorluk]
    else:
        tablo = LOOT_TABLOSU[zorluk]
    toplam = sum(item["şans"] for item in tablo)
    zar = random.randint(1, toplam)
    birikmiş = 0
    for item in tablo:
        birikmiş += item["şans"]
        if zar <= birikmiş:
            return item["eşya"]
    return None


# ================= VERİTABANI FONKSİYONLARI =================

def get_dungeon(user_id):
    """Kullanıcının zindan verisini getir veya oluştur."""
    dungeon = dungeons_col.find_one({"user_id": user_id})
    if not dungeon:
        dungeon = {
            "user_id": user_id,
            "sınıf": None,
            "seviye": 1,
            "xp": 0,
            "mevcut_kat": 0,
            "en_yüksek_kat": 0,
            "toplam_öldürme": 0,
            "boss_öldürme": 0,
            "toplam_ölüm": 0,
            "prestiж": 0,  # prestij seviyesi
            "envanter": [],  # [{"id": "benzersiz-uuid", "eşya_tipi": "demir_kılıç"}, ...]
            "kuşanılmış": {"silah": None, "zırh": None, "yüzük": None},  # Benzersiz ID'ler tutulur
            "can": 0,
            "maks_can": 0,
            "mana": 0,
            "maks_mana": 0,
            "kalkan": 0,  # Kalkan miktarı
            "iksir": 0,
            "mana_iksiri": 0,
            "aktif_savaş": None,  # aktif canavar savaşı
            "bolge": "zindan",  # aktif bolge
            "visored_kat": 0,  # Visored Adası mevcut katı
            "visored_en_yuksek": 0,  # Visored Adası en yüksek katı
        }
        dungeons_col.insert_one(dungeon)

    # Eski veriler için alan kontrolü
    for alan in ["prestiж", "boss_öldürme", "toplam_ölüm", "iksir", "mana", "maks_mana", "mana_iksiri", "visored_kat", "visored_en_yuksek", "kalkan"]:
        if alan not in dungeon:
            dungeon[alan] = 0
    if "bolge" not in dungeon:
        dungeon["bolge"] = "zindan"
    if "kuşanılmış" not in dungeon:
        dungeon["kuşanılmış"] = {"silah": None, "zırh": None, "yüzük": None}
    if "envanter" not in dungeon:
        dungeon["envanter"] = []
    if "aktif_savaş" not in dungeon:
        dungeon["aktif_savaş"] = None

    return dungeon


def save_dungeon(dungeon):
    """Zindan verisini kaydet."""
    dungeons_col.update_one({"user_id": dungeon["user_id"]}, {"$set": dungeon}, upsert=True)


def get_karakter_statları(dungeon):
    """Sınıf + ekipman + prestij bonuslarıyla toplam statları hesapla."""
    sınıf = SINIFLAR.get(dungeon["sınıf"])
    if not sınıf:
        return None

    seviye = dungeon.get("seviye", 1)
    prestij = dungeon.get("prestiж", 0)
    prestij_bonus = PRESTİJ_SEVİYELERİ.get(prestij, PRESTİJ_SEVİYELERİ[0])

    # Temel statlar + seviye bonusu
    can = sınıf["temel_can"] + (seviye - 1) * 8 + prestij_bonus["bonus_can"]
    mana = MAKS_MANA  # Mana artık sabit 100
    saldırı = sınıf["temel_saldırı"] + (seviye - 1) * 3 + prestij_bonus["bonus_saldırı"]
    savunma = sınıf["temel_savunma"] + (seviye - 1) * 2
    şans = sınıf["temel_şans"]
    vuruş_mana = sınıf.get("vuruş_mana_kazanç", 10)  # Her vuruşta kazanılan mana

    # Ekipman bonusları (kuşanılmış eşyaların ID'leri tutulur)
    kuşanılmış = dungeon.get("kuşanılmış", {})
    envanter = dungeon.get("envanter", [])
    for slot, kuşanılmış_id in kuşanılmış.items():
        if kuşanılmış_id:
            # Envanterde bu ID'yi bul
            for item in envanter:
                if item.get("id") == kuşanılmış_id:
                    eşya_tipi = item.get("eşya_tipi") or item.get("eşya_id")  # Eski format uyumluluğu
                    if eşya_tipi and eşya_tipi in EKİPMANLAR:
                        eşya = EKİPMANLAR[eşya_tipi]
                        saldırı += eşya.get("saldırı", 0)
                        savunma += eşya.get("savunma", 0)
                        can += eşya.get("can", 0)
                        şans += eşya.get("şans", 0)
                    break

    # Set bonuslarını hesapla (kuşanılmış eşyalardan)
    aktif_setler = []
    kuşanılmış_tipler = set()
    for slot, kuşanılmış_id in kuşanılmış.items():
        if kuşanılmış_id:
            for item in envanter:
                if item.get("id") == kuşanılmış_id:
                    eşya_tipi = item.get("eşya_tipi") or item.get("eşya_id")
                    if eşya_tipi:
                        kuşanılmış_tipler.add(eşya_tipi)
                    break
    
    for set_id, set_bilgi in SETLER.items():
        parçalar = set(set_bilgi["parçalar"])
        if parçalar.issubset(kuşanılmış_tipler):
            aktif_setler.append((set_id, set_bilgi))
            bonus = set_bilgi.get("bonus", {})
            # Kraken seti savunma bonusu
            if bonus.get("savunma_bonus"):
                savunma += bonus["savunma_bonus"]
            # Ejderha seti saldırı artışı
            if bonus.get("saldırı_artışı"):
                saldırı = int(saldırı * (1 + bonus["saldırı_artışı"] / 100))
            # Tanrısal set stat artışı
            if bonus.get("stat_artışı"):
                çarpan = 1 + bonus["stat_artışı"] / 100
                saldırı = int(saldırı * çarpan)
                savunma = int(savunma * çarpan)
                can = int(can * çarpan)
            # Visored seti kritik bonus
            if bonus.get("kritik_bonus"):
                şans += bonus["kritik_bonus"]

    return {
        "can": can,
        "mana": mana,
        "saldırı": saldırı,
        "savunma": savunma,
        "şans": şans,
        "vuruş_mana": vuruş_mana,  # Her vuruşta kazanılan mana miktarı
        "aktif_setler": aktif_setler,  # Aktif set listesi
    }


def get_zindan_seviye(xp):
    """XP'ye göre zindan seviyesi."""
    seviye = 1
    gereken = 50
    while xp >= gereken:
        seviye += 1
        gereken += seviye * 40
    return seviye


def get_canavarlar_for_kat(kat, bolge="zindan"):
    """Kata ve bolgeye uygun canavarları filtrele."""
    uygun = []
    canavar_listesi = VISORED_CANAVARLAR if bolge == "visored" else CANAVARLAR
    for canavar_id, canavar in canavar_listesi.items():
        if canavar["kat_min"] <= kat <= canavar["kat_max"]:
            uygun.append((canavar_id, canavar))
    if not uygun:
        # Hiç canavar yoksa en güçlüleri döndür
        uygun = list(canavar_listesi.items())[-3:]
    return uygun


def get_aktif_setler(dungeon):
    """Kuşanılmış ekipmanlardan aktif setleri bul.
    Returns: list of (set_id, set_bilgi) tuples
    """
    kuşanılmış = dungeon.get("kuşanılmış", {})
    envanter = dungeon.get("envanter", [])
    
    # Kuşanılmış eşya tiplerini topla
    kuşanılmış_tipler = set()
    for slot, kuşanılmış_id in kuşanılmış.items():
        if kuşanılmış_id:
            for item in envanter:
                if item.get("id") == kuşanılmış_id:
                    eşya_tipi = item.get("eşya_tipi") or item.get("eşya_id")
                    if eşya_tipi:
                        kuşanılmış_tipler.add(eşya_tipi)
                    break
    
    # Aktif setleri kontrol et
    aktif_setler = []
    for set_id, set_bilgi in SETLER.items():
        parçalar = set(set_bilgi["parçalar"])
        if parçalar.issubset(kuşanılmış_tipler):
            aktif_setler.append((set_id, set_bilgi))
    
    return aktif_setler


def hasar_hesapla(saldırı, savunma, şans):
    """Hasar hesaplama: saldırı - savunma/3 + rastgele + kritik."""
    temel = max(saldırı - savunma // 3, 1)
    rastgele = random.randint(int(temel * 0.7), int(temel * 1.3))
    kritik = random.randint(1, 100) <= şans
    if kritik:
        rastgele = int(rastgele * 1.8)
    return rastgele, kritik


def can_bar_hesapla(can, maks_can, kalkan=0):
    """Can barını kalkan ile birlikte hesapla.
    Görünüm: ⬜⬜🟩🟩🟩🟩🟩🟩⬛⬛ (beyaz=kalkan, yeşil=can, siyah=kayıp)
    """
    toplam_kare = 10
    
    # Kalkan kareleri (beyaz) - maksimum canın yüzdesine göre
    kalkan_yuzde = kalkan / maks_can if maks_can > 0 else 0
    kalkan_kare = min(int(kalkan_yuzde * toplam_kare), toplam_kare)
    
    # Kalan karelerden can kareleri (yeşil)
    kalan_kare = toplam_kare - kalkan_kare
    can_yuzde = can / maks_can if maks_can > 0 else 0
    can_kare = min(int(can_yuzde * kalan_kare), kalan_kare)
    
    # Boş kareler (siyah)
    bos_kare = kalan_kare - can_kare
    
    return "⬜" * kalkan_kare + "🟩" * can_kare + "⬛" * bos_kare


def hasar_al(dungeon, hasar):
    """Hasar al - önce kalkan absorbe eder, sonra cana gelir.
    Returns: (alınan_hasar, kalkan_hasarı, kalan_kalkan)
    """
    kalkan = dungeon.get("kalkan", 0)
    kalkan_hasarı = 0
    can_hasarı = 0
    
    if kalkan > 0:
        if hasar <= kalkan:
            # Kalkan tüm hasarı absorbe etti
            kalkan_hasarı = hasar
            dungeon["kalkan"] = kalkan - hasar
            can_hasarı = 0
        else:
            # Kalkan kırıldı, kalan hasar cana geldi
            kalkan_hasarı = kalkan
            can_hasarı = hasar - kalkan
            dungeon["kalkan"] = 0
            dungeon["can"] = max(0, dungeon["can"] - can_hasarı)
    else:
        # Kalkan yok, direkt cana
        can_hasarı = hasar
        dungeon["can"] = max(0, dungeon["can"] - can_hasarı)
    
    return can_hasarı, kalkan_hasarı, dungeon.get("kalkan", 0)


# ================= ZİNDAN KOMUTLARI =================

@bot.command(name="zindan", aliases=["dungeon", "rpg"])
async def zindan(ctx):
    """Zindan profilini göster."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if dungeon["sınıf"] is None:
        embed = discord.Embed(
            title="Zindan Sistemi",
            description=(
                f"{ctx.author.mention}, henüz bir karakter oluşturmadın!\n\n"
                "`!sınıfseç <sınıf>` ile karakter oluştur.\n\n"
                "Mevcut sınıflar: `!sınıflar`"
            ),
            color=discord.Color.dark_grey(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Zindan Sistemi")
        return await ctx.send(embed=embed)

    sınıf = SINIFLAR[dungeon["sınıf"]]
    statlar = get_karakter_statları(dungeon)
    prestij = dungeon.get("prestiж", 0)
    prestij_bilgi = PRESTİJ_SEVİYELERİ.get(prestij, PRESTİJ_SEVİYELERİ[0])

    # Seviye ilerleme çubuğu
    mevcut_xp = dungeon.get("xp", 0)
    mevcut_seviye = dungeon.get("seviye", 1)
    sonraki_xp = 50
    toplam = 50
    for i in range(2, mevcut_seviye + 1):
        sonraki_xp += i * 40
    önceki_xp = sonraki_xp - (mevcut_seviye * 40) if mevcut_seviye > 1 else 0
    ilerleme = mevcut_xp - önceki_xp
    gereken = sonraki_xp - önceki_xp
    if gereken > 0:
        pct = min(ilerleme / gereken, 1.0)
    else:
        pct = 1.0
    filled = int(pct * 15)
    bar = "▰" * filled + "▱" * (15 - filled)

    # Kuşanılmış ekipman
    ekipman_text = ""
    kuşanılmış = dungeon.get("kuşanılmış", {})
    envanter = dungeon.get("envanter", [])
    for slot_adı, slot_tr in [("silah", "Silah"), ("zırh", "Zırh"), ("yüzük", "Yüzük")]:
        kuşanılmış_id = kuşanılmış.get(slot_adı)
        if kuşanılmış_id:
            # Envanterde bu ID'yi bul
            eşya_tipi = None
            for item in envanter:
                if item.get("id") == kuşanılmış_id:
                    eşya_tipi = item.get("eşya_tipi") or item.get("eşya_id")
                    break
            # Eski format uyumluluğu (direkt eşya tipi kayıtlıysa)
            if not eşya_tipi and kuşanılmış_id in EKİPMANLAR:
                eşya_tipi = kuşanılmış_id
            
            if eşya_tipi and eşya_tipi in EKİPMANLAR:
                eşya = EKİPMANLAR[eşya_tipi]
                ekipman_text += f"**{slot_tr}:** {eşya['emoji']} {eşya['isim']} ({NADİRLİK_RENKLERİ[eşya['nadirlik']]} {eşya['nadirlik']}) `[{kuşanılmış_id}]`\n"
            else:
                ekipman_text += f"**{slot_tr}:** Boş\n"
        else:
            ekipman_text += f"**{slot_tr}:** Boş\n"

    embed = discord.Embed(
        title=f"{sınıf['emoji']} {ctx.author.display_name} — {sınıf['isim']}",
        color=discord.Color.dark_purple(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="Prestij",
        value=f"{prestij_bilgi['emoji']} **{prestij_bilgi['isim']}** (Prestij {prestij})",
        inline=False
    )

    embed.add_field(
        name="Seviye",
        value=f"Seviye **{mevcut_seviye}** `[{bar}]` {ilerleme}/{gereken} XP",
        inline=False
    )

    embed.add_field(
        name="Statlar",
        value=(
            f"Can: **{statlar['can']}** | "
            f"Saldırı: **{statlar['saldırı']}** | "
            f"Savunma: **{statlar['savunma']}** | "
            f"Kritik: **%{statlar['şans']}**\n"
            f"Vuruş Mana Kazancı: **+{statlar['vuruş_mana']}** (Maks: {MAKS_MANA})"
        ),
        inline=False
    )

    embed.add_field(
        name="Ekipman",
        value=ekipman_text,
        inline=False
    )

    # Aktif bolge bilgisi
    aktif_bolge = dungeon.get("bolge", "zindan")
    aktif_bolge_bilgi = BOLGELER.get(aktif_bolge, BOLGELER["zindan"])
    
    embed.add_field(
        name=f"{aktif_bolge_bilgi['emoji']} Aktif Bölge: {aktif_bolge_bilgi['isim']}",
        value=(
            f"**Karanlık Zindan:** Kat **{dungeon['mevcut_kat']}** | En Yüksek: **{dungeon['en_yüksek_kat']}**\n"
            f"**Visored Adası:** Kat **{dungeon.get('visored_kat', 0)}** | En Yüksek: **{dungeon.get('visored_en_yuksek', 0)}**"
        ),
        inline=False
    )
    
    embed.add_field(
        name="İstatistikler",
        value=(
            f"Öldürme: **{dungeon['toplam_öldürme']}** | "
            f"Boss: **{dungeon['boss_öldürme']}** | "
            f"Ölüm: **{dungeon['toplam_ölüm']}**\n"
            f"Can İksiri: **{dungeon.get('iksir', 0)}** | Mana İksiri: **{dungeon.get('mana_iksiri', 0)}**"
        ),
        inline=False
    )

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Zindan Sistemi | {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="sınıflar", aliases=["classes", "sınıflistesi"])
async def sınıflar(ctx):
    """Mevcut sınıfları listele."""
    embed = discord.Embed(
        title="Zindan Sınıfları",
        description="Sınıf seçmek için: `!sınıfseç <sınıf>`",
        color=discord.Color.dark_purple(),
        timestamp=datetime.now(timezone.utc)
    )

    for sınıf_id, sınıf in SINIFLAR.items():
        embed.add_field(
            name=f"{sınıf['emoji']} {sınıf['isim']} (`{sınıf_id}`)",
            value=(
                f"{sınıf['açıklama']}\n\n"
                f"Can: **{sınıf['temel_can']}** | "
                f"Saldırı: **{sınıf['temel_saldırı']}** | "
                f"Savunma: **{sınıf['temel_savunma']}** | "
                f"Kritik: **%{sınıf['temel_şans']}**\n"
                f"Vuruş Mana Kazancı: **+{sınıf['vuruş_mana_kazanç']}** (Maks: 100)\n"
                f"Yetenek: **{sınıf['özel_yetenek']}** — {sınıf['özel_açıklama']}"
            ),
            inline=False
        )

    embed.set_footer(text="Zindan Sistemi")
    await ctx.send(embed=embed)


@bot.command(name="sınıfseç", aliases=["classchoose", "sınıf"])
async def sınıfseç(ctx, sınıf_id: str = None):
    """Zindan sınıfı seç."""
    user_id = ctx.author.id

    if sınıf_id is None:
        embed = discord.Embed(
            description="Kullanım: `!sınıfseç <sınıf>`\nÖrnek: `!sınıfseç savaşçı`\n\nSınıfları görmek için: `!sınıflar`",
            color=discord.Color.blue()
        )
        return await ctx.send(embed=embed)

    sınıf_id = sınıf_id.lower().strip()

    if sınıf_id not in SINIFLAR:
        embed = discord.Embed(
            description="Böyle bir sınıf yok! `!sınıflar` ile mevcut sınıfları gör.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    dungeon = get_dungeon(user_id)

    if dungeon["sınıf"] is not None:
        embed = discord.Embed(
            description=f"Zaten bir sınıfın var: **{SINIFLAR[dungeon['sınıf']]['isim']}**\nSınıf değiştirmek için prestij yapman gerekiyor!",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    sınıf = SINIFLAR[sınıf_id]

    dungeon["sınıf"] = sınıf_id
    dungeon["seviye"] = 1
    dungeon["xp"] = 0
    dungeon["can"] = sınıf["temel_can"]
    dungeon["maks_can"] = sınıf["temel_can"]
    dungeon["mana"] = 0  # Mana başlangıçta 0
    dungeon["maks_mana"] = MAKS_MANA  # Mana hep 100
    dungeon["mevcut_kat"] = 0
    dungeon["envanter"] = [
        {"eşya_id": "paslı_kılıç", "kuşanılmış": True},
        {"eşya_id": "deri_zırh", "kuşanılmış": True},
    ]
    dungeon["kuşanılmış"] = {"silah": "paslı_kılıç", "zırh": "deri_zırh", "yüzük": None}
    save_dungeon(dungeon)

    embed = discord.Embed(
        title=f"{sınıf['emoji']} Karakter Oluşturuldu!",
        description=(
            f"{ctx.author.mention}, **{sınıf['isim']}** olarak yolculuğun başlıyor!\n\n"
            f"**Statların:**\n"
            f"Can: **{sınıf['temel_can']}** | "
            f"Saldırı: **{sınıf['temel_saldırı']}** | "
            f"Savunma: **{sınıf['temel_savunma']}** | Kritik: **%{sınıf['temel_şans']}**\n\n"
            f"**Mana Sistemi:**\n"
            f"Her vuruşta **+{sınıf['vuruş_mana_kazanç']}** mana kazanırsın (Maks: 100)\n"
            f"Mana dolunca özel yeteneğini kullanabilirsin!\n\n"
            f"**Başlangıç Ekipmanı:**\n"
            f"🗡️ Paslı Kılıç | 🦺 Deri Zırh\n\n"
            f"**Yetenek:** {sınıf['özel_yetenek']} — {sınıf['özel_açıklama']}\n\n"
            f"Zindana girmek için: `!gir`"
        ),
        color=discord.Color.dark_purple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Zindan Sistemi")
    await ctx.send(embed=embed)


@bot.command(name="gir", aliases=["enter", "zindangir", "dalış"])
async def zindan_gir(ctx):
    """Bölgenin bir sonraki katına gir."""
    user_id = ctx.author.id

    # Cooldown kontrolü
    now = time.time()
    if user_id in zindan_cd and now - zindan_cd[user_id] < ZINDAN_COOLDOWN:
        kalan = int(ZINDAN_COOLDOWN - (now - zindan_cd[user_id]))
        embed = discord.Embed(
            description=f"Dinleniyorsun... **{kalan}** saniye bekle.",
            color=discord.Color.orange()
        )
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            if e.status == 429:
                await asyncio.sleep(3)
                await ctx.send(embed=embed)

    dungeon = get_dungeon(user_id)

    if dungeon["sınıf"] is None:
        embed = discord.Embed(
            description="Önce bir sınıf seç! `!sınıfseç <sınıf>`",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if dungeon.get("aktif_savaş"):
        embed = discord.Embed(
            description="Zaten aktif bir savaşın var! `!saldır` ile devam et veya `!kaç` ile kaç.",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    # Canı sıfırsa yenile, mana artık kata geçince sıfırlanmıyor
    statlar = get_karakter_statları(dungeon)
    if dungeon.get("can", 0) <= 0:
        dungeon["can"] = statlar["can"]
    # Mana kata geçince sıfırlanmıyor - önceki kattan devam ediyor
    save_dungeon(dungeon)

    zindan_cd[user_id] = now

    # Bölge kontrolü
    bolge = dungeon.get("bolge", "zindan")
    bolge_bilgi = BOLGELER.get(bolge, BOLGELER["zindan"])
    
    # Kat ilerle (bölgeye göre)
    if bolge == "visored":
        dungeon["visored_kat"] = dungeon.get("visored_kat", 0) + 1
        kat = dungeon["visored_kat"]
        if kat > dungeon.get("visored_en_yuksek", 0):
            dungeon["visored_en_yuksek"] = kat
        boss_listesi = VISORED_BOSSLAR
    else:
        dungeon["mevcut_kat"] += 1
        kat = dungeon["mevcut_kat"]
        if kat > dungeon["en_yüksek_kat"]:
            dungeon["en_yüksek_kat"] = kat
        boss_listesi = BOSSLAR

    # Boss katı mı?
    if kat in boss_listesi:
        boss = boss_listesi[kat]
        dungeon["aktif_savaş"] = {
            "tür": "boss",
            "isim": boss["isim"],
            "emoji": boss["emoji"],
            "can": boss["can"],
            "maks_can": boss["can"],
            "saldırı": boss["saldırı"],
            "savunma": boss["savunma"],
            "xp": boss["xp"],
            "altın_min": boss["altın_min"],
            "altın_max": boss["altın_max"],
            "loot": boss.get("loot", []),
            "kat": kat,
            "bolge": bolge,
        }
        save_dungeon(dungeon)

        sınıf = SINIFLAR[dungeon["sınıf"]]
        mana_hazır = "⚡ ÖZEL HAZIR!" if dungeon['mana'] >= MAKS_MANA else ""
        embed = discord.Embed(
            title=f"{bolge_bilgi['emoji']} Kat {kat} — BOSS SAVAŞI!",
            description=(
                f"{'━' * 30}\n"
                f"{boss['emoji']} **{boss['isim']}** yolunu kesiyor!\n"
                f"{'━' * 30}\n\n"
                f"**Boss Statları:**\n"
                f"Can: **{boss['can']}** | Saldırı: **{boss['saldırı']}** | Savunma: **{boss['savunma']}**\n\n"
                f"**Senin Durumun:**\n"
                f"{sınıf['emoji']} Can: **{dungeon['can']}/{statlar['can']}** | Mana: **{dungeon['mana']}/{MAKS_MANA}** {mana_hazır}\n\n"
                f"`!saldır` — Saldır (+{sınıf['vuruş_mana_kazanç']} mana)\n"
                f"`!özel` — {sınıf['özel_yetenek']} (Mana dolunca)\n"
                f"`!iksir` — Can iksiri\n"
                f"`!kaç` — Kaç (katı kaybedersin)"
            ),
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"{bolge_bilgi['isim']} | Boss Savaşı")
        return await ctx.send(embed=embed)

    # Hazine odası kontrolü (boss değilse) - sadece zindan için
    if bolge == "zindan":
        hazine_bulundu = await hazine_odası_kontrol(ctx, dungeon, kat)
        if hazine_bulundu:
            save_dungeon(dungeon)

    # Normal canavar
    uygun_canavarlar = get_canavarlar_for_kat(kat, bolge)
    canavar_id, canavar = random.choice(uygun_canavarlar)

    # Kat bonusu (zorluk artışı) - Visored için daha yüksek çarpan
    if bolge == "visored":
        kat_çarpan = 1 + (kat - 1) * 0.08  # %8 artış per kat
    else:
        kat_çarpan = 1 + (kat - 1) * 0.05  # %5 artış per kat
    canavar_can = int(canavar["can"] * kat_çarpan)
    canavar_saldırı = int(canavar["saldırı"] * kat_çarpan)
    canavar_savunma = int(canavar["savunma"] * kat_çarpan)

    dungeon["aktif_savaş"] = {
        "tür": "canavar",
        "id": canavar_id,
        "isim": canavar["isim"],
        "emoji": canavar["emoji"],
        "bolge": bolge,
        "can": canavar_can,
        "maks_can": canavar_can,
        "saldırı": canavar_saldırı,
        "savunma": canavar_savunma,
        "xp": canavar["xp"],
        "altın_min": canavar["altın_min"],
        "altın_max": canavar["altın_max"],
        "kat": kat,
    }
    save_dungeon(dungeon)

    sınıf = SINIFLAR[dungeon["sınıf"]]
    can_bar_düşman = "🟥" * 10
    # Kalkan ile can bar hesapla
    kalkan = dungeon.get("kalkan", 0)
    can_bar_sen = can_bar_hesapla(dungeon["can"], statlar["can"], kalkan)
    mana_bar_sen = "🟦" * int(dungeon["mana"] / MAKS_MANA * 10) + "⬛" * (10 - int(dungeon["mana"] / MAKS_MANA * 10))
    mana_hazır = " ⚡" if dungeon['mana'] >= MAKS_MANA else ""
    kalkan_text = f" 🛡️ +{kalkan}" if kalkan > 0 else ""

    # Bölgeye göre renk
    embed_renk = discord.Color.teal() if bolge == "visored" else discord.Color.dark_grey()

    embed = discord.Embed(
        title=f"{bolge_bilgi['emoji']} Kat {kat} — {canavar['emoji']} {canavar['isim']}",
        description=(
            f"{'━' * 30}\n\n"
            f"**{canavar['emoji']} {canavar['isim']}**\n"
            f"Can: {can_bar_düşman} **{canavar_can}/{canavar_can}**\n"
            f"Saldırı: **{canavar_saldırı}** | Savunma: **{canavar_savunma}**\n\n"
            f"{'━' * 30}\n\n"
            f"**{sınıf['emoji']} {ctx.author.display_name}**\n"
            f"Can: {can_bar_sen} **{dungeon['can']}/{statlar['can']}**{kalkan_text}\n"
            f"Mana: {mana_bar_sen} **{dungeon['mana']}/{MAKS_MANA}**{mana_hazır}\n\n"
            f"`!saldır` (+{sınıf['vuruş_mana_kazanç']} mana) | `!özel` (Mana dolunca)\n"
            f"`!iksir` | `!kaç`"
        ),
        color=embed_renk,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{bolge_bilgi['isim']} | Kat {kat}")
    await ctx.send(embed=embed)

    # Görev ilerlemesi
    update_quest_progress(user_id, "zindan_kat", 1)


@bot.command(name="saldır", aliases=["attack", "vuruş", "saldırı"])
async def zsaldır(ctx):
    """Aktif canavara saldır."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if not dungeon.get("aktif_savaş"):
        embed = discord.Embed(
            description="Aktif bir savaşın yok! `!gir` ile zindana gir.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    savaş = dungeon["aktif_savaş"]
    statlar = get_karakter_statları(dungeon)
    sınıf = SINIFLAR[dungeon["sınıf"]]

    # Oyuncu saldırısı
    hasar, kritik = hasar_hesapla(statlar["saldırı"], savaş["savunma"], statlar["şans"])

    # Her vuruşta mana kazan
    mana_kazanç = statlar["vuruş_mana"]
    
    # Deniz Tanrısı seti - Mana çarpanı
    aktif_setler = statlar.get("aktif_setler", [])
    for set_id, set_bilgi in aktif_setler:
        bonus = set_bilgi.get("bonus", {})
        if bonus.get("mana_çarpanı"):
            mana_kazanç = int(mana_kazanç * bonus["mana_çarpanı"])
    
    eski_mana = dungeon.get("mana", 0)
    dungeon["mana"] = min(MAKS_MANA, eski_mana + mana_kazanç)
    
    # Mana bar gösterimi
    mana_dolumu = dungeon["mana"] >= MAKS_MANA
    mana_text = f"*+{mana_kazanç} mana ({dungeon['mana']}/{MAKS_MANA})*"
    if mana_dolumu:
        mana_text += " **⚡ ÖZEL HAZIR!**"

    savaş_log = f"{mana_text}\n"
    if kritik:
        savaş_log += f"**KRİTİK VURUŞ!** {sınıf['emoji']} **{hasar}** hasar verdin!\n"
    else:
        savaş_log += f"{sınıf['emoji']} **{hasar}** hasar verdin.\n"

    # Zehir efekti kontrolu (Okcu)
    zehir = dungeon.get("zehir_efekti")
    if zehir and zehir["tur"] > 0:
        zehir_hasar = zehir["hasar"]
        savaş["can"] = max(0, savaş["can"] - zehir_hasar)
        zehir["tur"] -= 1
        dungeon["zehir_efekti"] = zehir if zehir["tur"] > 0 else None
        savaş_log += f"☠️ **ZEHİR!** Düşman **{zehir_hasar}** hasar aldı! ({zehir['tur']} tur kaldı)\n"

    # Kalkan Duvarı kontrolu (Sovalye)
    kalkan_duvarı = dungeon.get("kalkan_duvarı", 0)
    if kalkan_duvarı > 0:
        dungeon["kalkan_duvarı"] = kalkan_duvarı - 1
        if dungeon["kalkan_duvarı"] > 0:
            savaş_log += f"🛡️ **Kalkan Duvarı** aktif! ({dungeon['kalkan_duvarı']} tur kaldı)\n"

    # Set pasiflerini uygula
    aktif_setler = statlar.get("aktif_setler", [])
    ekstra_hasar = 0
    can_çalma = 0
    
    for set_id, set_bilgi in aktif_setler:
        bonus = set_bilgi.get("bonus", {})
        
        # Visored/Vampir seti - Can çalma
        if bonus.get("can_çalma"):
            çalınan = int(hasar * bonus["can_çalma"] / 100)
            can_çalma += çalınan
        
        # Fırtına seti - Şimşek hasarı
        if bonus.get("şimşek_şansı"):
            if random.randint(1, 100) <= bonus["şimşek_şansı"]:
                şimşek = int(statlar["saldırı"] * bonus["şimşek_hasar"] / 100)
                ekstra_hasar += şimşek
                savaş_log += f"⚡ **Şimşek Çarpması!** Ekstra **{şimşek}** hasar!\n"
        
        # Deniz Tanrısı seti - Her 3 turda ekstra hasar
        if bonus.get("ekstra_hasar"):
            tur_sayısı = dungeon.get("savaş_turu", 0) + 1
            dungeon["savaş_turu"] = tur_sayısı
            if tur_sayısı % 3 == 0:
                ekstra = int(hasar * bonus["ekstra_hasar"] / 100)
                ekstra_hasar += ekstra
                savaş_log += f"🔱 **Poseidon'un Lütfu!** Ekstra **{ekstra}** hasar!\n"
    
    # Can çalma uygula
    if can_çalma > 0:
        dungeon["can"] = min(dungeon["can"] + can_çalma, statlar["can"])
        savaş_log += f"🧛 **Can Çaldın!** +**{can_çalma}** can!\n"
    
    # Toplam hasarı uygula (ana hasar + ekstra hasar)
    toplam_hasar = hasar + ekstra_hasar
    savaş["can"] = max(0, savaş["can"] - toplam_hasar)

    # Canavar öldü mü?
    if savaş["can"] <= 0:
        altın = random.randint(savaş["altın_min"], savaş["altın_max"])
        xp = savaş["xp"]

        # Prestij altın bonusu
        prestij = dungeon.get("prestiж", 0)
        prestij_bilgi = PRESTİJ_SEVİYELERİ.get(prestij, PRESTİJ_SEVİYELERİ[0])
        altın_bonus = int(altın * prestij_bilgi["bonus_altın"] / 100)
        altın += altın_bonus

        # XP ekle
        dungeon["xp"] = dungeon.get("xp", 0) + xp
        eski_seviye = dungeon.get("seviye", 1)
        yeni_seviye = get_zindan_seviye(dungeon["xp"])
        dungeon["seviye"] = yeni_seviye

        # Kullanıcıya altın ver
        user = get_user(user_id)
        user["money"] += altın
        save_user(user)

        dungeon["toplam_öldürme"] += 1

        # Boss mu?
        boss_mu = savaş["tür"] == "boss"
        if boss_mu:
            dungeon["boss_öldürme"] += 1

        # Loot kontrolü (bolgeye gore)
        savas_bolge = savaş.get("bolge", "zindan")
        düşen_eşya = None
        düşen_id = None
        if boss_mu and savaş.get("loot"):
            # Boss garantili loot
            düşen_eşya_tipi = random.choice(savaş["loot"])
            düşen_eşya = EKİPMANLAR.get(düşen_eşya_tipi)
            if düşen_eşya:
                düşen_id = str(uuid.uuid4())[:8]  # Kısa benzersiz ID
                dungeon["envanter"].append({"id": düşen_id, "eşya_tipi": düşen_eşya_tipi})
        else:
            # Normal loot şansı (bolgeye gore)
            loot_tipi = roll_loot(savaş["kat"], savas_bolge)
            if loot_tipi:
                düşen_eşya = EKİPMANLAR.get(loot_tipi)
                if düşen_eşya:
                    düşen_id = str(uuid.uuid4())[:8]  # Kısa benzersiz ID
                    dungeon["envanter"].append({"id": düşen_id, "eşya_tipi": loot_tipi})

        dungeon["aktif_savaş"] = None
        dungeon["zehir_efekti"] = None  # Zehir sıfırlanır
        dungeon["kalkan_duvarı"] = 0  # Kalkan duvarı sıfırlanır
        save_dungeon(dungeon)

        # Zafer embed
        başlık = "BOSS YENİLDİ!" if boss_mu else f"{savaş['emoji']} {savaş['isim']} Yenildi!"
        renk = discord.Color.gold() if boss_mu else discord.Color.green()

        sonuç_text = (
            f"{savaş_log}\n"
            f"{savaş['emoji']} **{savaş['isim']}** yenildi!\n\n"
            f"**Kazanımlar:**\n"
            f"Altın: **+{altın:,}** VisoCoin"
            f"{f' (+{altın_bonus} prestij bonusu)' if altın_bonus > 0 else ''}\n"
            f"XP: **+{xp}** Zindan XP\n"
        )

        if düşen_eşya:
            sonuç_text += f"\n**EŞYA DÜŞTÜ!**\n{düşen_eşya['emoji']} {düşen_eşya['isim']} ({NADİRLİK_RENKLERİ[düşen_eşya['nadirlik']]} {düşen_eşya['nadirlik']}) `[{düşen_id}]`\n"

        sonuç_text += f"\nDevam etmek için: `!gir`"

        embed = discord.Embed(
            title=başlık,
            description=sonuç_text,
            color=renk,
            timestamp=datetime.now(timezone.utc)
        )

        if yeni_seviye > eski_seviye:
            embed.add_field(
                name="SEVİYE ATLADIN!",
                value=f"Seviye **{eski_seviye}** -> **{yeni_seviye}**",
                inline=False
            )

        embed.set_footer(text=f"Zindan Sistemi | Kat {savaş['kat']}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

        # Görev ilerlemesi
        update_quest_progress(user_id, "canavar_öldür", 1)
        if boss_mu:
            update_quest_progress(user_id, "boss_öldür", 1)

        return

    # Canavar saldırısı
    # Suikastçi kaçınma kontrolü
    kaçındı = False
    if dungeon["sınıf"] == "suikastçi":
        kaçınma_şansı = SINIFLAR["suikastçi"].get("kaçınma", 10)
        if random.randint(1, 100) <= kaçınma_şansı:
            kaçındı = True
            savaş_log += f"**KAÇINDIN!** {sınıf['emoji']} {savaş['emoji']} saldırısından kaçındın!\n"

    if not kaçındı:
        # Kalkan Duvarı aktifse savunma 2 katı
        etkili_savunma = statlar["savunma"]
        if dungeon.get("kalkan_duvarı", 0) > 0:
            etkili_savunma = statlar["savunma"] * 2
        
        düşman_hasar, düşman_kritik = hasar_hesapla(savaş["saldırı"], etkili_savunma, 8)

        # Kalkan sistemi ile hasar al
        can_hasarı, kalkan_hasarı, kalan_kalkan = hasar_al(dungeon, düşman_hasar)

        if düşman_kritik:
            if kalkan_hasarı > 0:
                savaş_log += f"**KRİTİK!** {savaş['emoji']} **{düşman_hasar}** hasar verdi! (🛡️ -{kalkan_hasarı} kalkan"
                if can_hasarı > 0:
                    savaş_log += f", ❤️ -{can_hasarı} can)\n"
                else:
                    savaş_log += ")\n"
            else:
                savaş_log += f"**KRİTİK!** {savaş['emoji']} **{düşman_hasar}** hasar verdi!\n"
        else:
            if kalkan_hasarı > 0:
                savaş_log += f"{savaş['emoji']} **{düşman_hasar}** hasar verdi! (🛡️ -{kalkan_hasarı} kalkan"
                if can_hasarı > 0:
                    savaş_log += f", ❤️ -{can_hasarı} can)\n"
                else:
                    savaş_log += ")\n"
            else:
                savaş_log += f"{savaş['emoji']} **{düşman_hasar}** hasar verdi.\n"
        
        # Kraken seti - Hasar yansıtma
        for set_id, set_bilgi in aktif_setler:
            bonus = set_bilgi.get("bonus", {})
            if bonus.get("hasar_yansıtma"):
                yansıyan = int(düşman_hasar * bonus["hasar_yansıtma"] / 100)
                savaş["can"] = max(0, savaş["can"] - yansıyan)
                savaş_log += f"🦑 **Hasar Yansıdı!** Düşmana **{yansıyan}** hasar!\n"

    # Doktor pasif iyilesme (her 3 turda bir %10)
    if dungeon["sınıf"] == "doktor" and savaş.get("tur", 0) % 3 == 0 and savaş.get("tur", 0) > 0:
        iyileşme = int(statlar["can"] * 0.10)
        eski_can = dungeon["can"]
        dungeon["can"] = min(dungeon["can"] + iyileşme, statlar["can"])
        if dungeon["can"] > eski_can:
            savaş_log += f"{sınıf['emoji']} **+{iyileşme}** can iyileşti! (Doktor pasif)\n"
    
    # Tur sayacı
    savaş["tur"] = savaş.get("tur", 0) + 1

    # Oyuncu öldü mü?
    if dungeon["can"] <= 0:
        # Tanrısal set - İkinci şans kontrolü
        ikinci_şans_kullanıldı = dungeon.get("ikinci_şans_kullanıldı", False)
        for set_id, set_bilgi in aktif_setler:
            bonus = set_bilgi.get("bonus", {})
            if bonus.get("ikinci_şans") and not ikinci_şans_kullanıldı:
                dungeon["can"] = int(statlar["can"] * 0.3)  # %30 can ile diriliş
                dungeon["ikinci_şans_kullanıldı"] = True
                savaş_log += f"👑 **İLAHİ GÜÇ!** Ölümden döndün! (%30 can ile)\n"
                save_dungeon(dungeon)
                
                # Savaş devam embed'i göster
                savas_bolge = savaş.get("bolge", "zindan")
                bolge_bilgi = BOLGELER.get(savas_bolge, BOLGELER["zindan"])
                
                kalkan = dungeon.get("kalkan", 0)
                can_bar_sen = can_bar_hesapla(dungeon["can"], statlar["can"], kalkan)
                düşman_can_pct = max(0, savaş["can"] / savaş["maks_can"])
                düşman_bar_dolu = int(düşman_can_pct * 10)
                can_bar_düşman = "🟥" * düşman_bar_dolu + "⬛" * (10 - düşman_bar_dolu)
                mana_pct = max(0, dungeon["mana"] / MAKS_MANA)
                mana_bar_dolu = int(mana_pct * 10)
                mana_bar_sen = "🟦" * mana_bar_dolu + "⬛" * (10 - mana_bar_dolu)
                
                embed = discord.Embed(
                    title=f"{bolge_bilgi['emoji']} Kat {savaş['kat']} — İKİNCİ ŞANS!",
                    description=(
                        f"{savaş_log}\n"
                        f"{'━' * 30}\n\n"
                        f"**{savaş['emoji']} {savaş['isim']}**\n"
                        f"Can: {can_bar_düşman} **{savaş['can']}/{savaş['maks_can']}**\n\n"
                        f"**{sınıf['emoji']} {ctx.author.display_name}**\n"
                        f"Can: {can_bar_sen} **{dungeon['can']}/{statlar['can']}**\n"
                        f"Mana: {mana_bar_sen} **{dungeon['mana']}/{MAKS_MANA}**\n"
                    ),
                    color=discord.Color.gold(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text=f"{bolge_bilgi['isim']} | Kat {savaş['kat']}")
                return await ctx.send(embed=embed)
        
        # Ölüm - 5 kat geri at (bölgeye göre)
        dungeon["ikinci_şans_kullanıldı"] = False  # Yeni savaşta sıfırla
        dungeon["toplam_ölüm"] += 1
        savas_bolge = savaş.get("bolge", "zindan")
        
        if savas_bolge == "visored":
            eski_kat = dungeon.get("visored_kat", 0)
            dungeon["visored_kat"] = max(0, eski_kat - 6)
            mevcut_kat = dungeon["visored_kat"]
        else:
            eski_kat = dungeon["mevcut_kat"]
            dungeon["mevcut_kat"] = max(0, dungeon["mevcut_kat"] - 6)
            mevcut_kat = dungeon["mevcut_kat"]
            
        dungeon["can"] = statlar["can"]  # Canı yenile
        dungeon["mana"] = 0  # Mana sıfırlanır (ölümde)
        dungeon["kalkan"] = 0  # Kalkan sıfırlanır
        dungeon["zehir_efekti"] = None  # Zehir sıfırlanır
        dungeon["kalkan_duvarı"] = 0  # Kalkan duvarı sıfırlanır
        dungeon["aktif_savaş"] = None
        save_dungeon(dungeon)

        bolge_bilgi = BOLGELER.get(savas_bolge, BOLGELER["zindan"])
        embed = discord.Embed(
            title="YENİLDİN!",
            description=(
                f"{savaş_log}\n"
                f"**{savaş['emoji']} {savaş['isim']}** seni yendi!\n\n"
                f"**5 kat** geri düştün. Mevcut kat: **{mevcut_kat}**\n"
                f"Can ve manan yenilendi.\n\n"
                f"Tekrar denemek icin: `!gir`"
            ),
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Zindan Sistemi | Yenilgi")
        return await ctx.send(embed=embed)

    # Savaş devam ediyor
    dungeon["aktif_savaş"] = savaş
    save_dungeon(dungeon)

    düşman_can_pct = max(0, savaş["can"] / savaş["maks_can"])
    düşman_bar_dolu = int(düşman_can_pct * 10)
    can_bar_düşman = "🟥" * düşman_bar_dolu + "⬛" * (10 - düşman_bar_dolu)

    # Kalkan ile can bar hesapla
    kalkan = dungeon.get("kalkan", 0)
    can_bar_sen = can_bar_hesapla(dungeon["can"], statlar["can"], kalkan)

    mana_pct = max(0, dungeon["mana"] / MAKS_MANA)
    mana_bar_dolu = int(mana_pct * 10)
    mana_bar_sen = "🟦" * mana_bar_dolu + "⬛" * (10 - mana_bar_dolu)
    mana_hazır = " ⚡" if dungeon['mana'] >= MAKS_MANA else ""

    # Kalkan bilgisi
    kalkan_text = f" 🛡️ +{kalkan}" if kalkan > 0 else ""
    
    # Aktif efektler
    efekt_text = ""
    zehir = dungeon.get("zehir_efekti")
    if zehir and zehir["tur"] > 0:
        efekt_text += f"☠️ Zehir ({zehir['hasar']}/tur, {zehir['tur']} tur)\n"
    if dungeon.get("kalkan_duvarı", 0) > 0:
        efekt_text += f"🛡️ Kalkan Duvarı ({dungeon['kalkan_duvarı']} tur)\n"
    
    # Düşman durumu (zehirli mi)
    düşman_durum = ""
    if zehir and zehir["tur"] > 0:
        düşman_durum = " ☠️"

    embed = discord.Embed(
        title=f"Kat {savaş['kat']} — Savas Devam Ediyor",
        description=(
            f"{savaş_log}\n"
            f"{'━' * 30}\n\n"
            f"**{savaş['emoji']} {savaş['isim']}**{düşman_durum}\n"
            f"Can: {can_bar_düşman} **{savaş['can']}/{savaş['maks_can']}**\n\n"
            f"**{sınıf['emoji']} {ctx.author.display_name}**\n"
            f"Can: {can_bar_sen} **{dungeon['can']}/{statlar['can']}**{kalkan_text}\n"
            f"Mana: {mana_bar_sen} **{dungeon['mana']}/{MAKS_MANA}**{mana_hazır}\n"
            + (f"\n**Aktif Efektler:**\n{efekt_text}" if efekt_text else "") +
            f"\n`!saldır` (+{sınıf['vuruş_mana_kazanç']}) | `!özel` (Mana dolunca) | `!iksir` | `!kaç`"
        ),
        color=discord.Color.gold() if efekt_text else discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Zindan Sistemi | Kat {savaş['kat']}")
    await ctx.send(embed=embed)


@bot.command(name="özel", aliases=["special", "yetenek"])
async def özel_saldırı(ctx):
    """Özel yetenek kullan (mana gerektirir)."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if not dungeon.get("aktif_savaş"):
        embed = discord.Embed(description="Aktif bir savaşın yok!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    savaş = dungeon["aktif_savaş"]
    statlar = get_karakter_statları(dungeon)
    sınıf = SINIFLAR[dungeon["sınıf"]]

    # Mana kontrolü - özel yetenek için mana tamamen dolu olmalı (100)
    mevcut_mana = dungeon.get("mana", 0)
    if mevcut_mana < MAKS_MANA:
        embed = discord.Embed(
            description=f"⚡ **{sınıf['özel_yetenek']}** için mana tamamen dolu olmalı!\nMevcut manan: **{mevcut_mana}/{MAKS_MANA}**\n\nSaldırı yaparak mana kazan!",
            color=discord.Color.blue()
        )
        return await ctx.send(embed=embed)

    # Mana sıfırla (özel yetenek kullanıldı)
    dungeon["mana"] = 0
    savaş_log = f"⚡ *Mana harcandı (100 → 0)*\n"

    # Şövalye - Kalkan Duvarı: 2 tur boyunca savunma 2 katı
    if dungeon["sınıf"] == "şövalye":
        dungeon["kalkan_duvarı"] = 2  # 2 tur boyunca aktif
        savaş_log += f"\n{'━' * 25}\n"
        savaş_log += f"🛡️ **{sınıf['özel_yetenek']} AKTİF!**\n"
        savaş_log += f"┌─────────────────────┐\n"
        savaş_log += f"│  SAVUNMA x2 (2 TUR)  │\n"
        savaş_log += f"└─────────────────────┘\n"
        savaş_log += f"{'━' * 25}\n\n"
        
        # Düşman saldırır ama savunma 2 katı
        düşman_hasar, _ = hasar_hesapla(savaş["saldırı"], int(statlar["savunma"] * 2), 5)
        savaş_log += f"{savaş['emoji']} **{düşman_hasar}** hasar vermeye calisti!\n"
        can_hasarı, kalkan_hasarı, _ = hasar_al(dungeon, düşman_hasar)
        if kalkan_hasarı > 0:
            savaş_log += f"   (Kalkan -{kalkan_hasarı} absorbe etti)\n"
    
    # Okcu - Zehirli Ok: 3 tur boyunca zehir hasari
    elif dungeon["sınıf"] == "okçu":
        zehir_hasar = int(statlar["saldırı"] * 0.4)  # Her tur saldirinin %40'i
        dungeon["zehir_efekti"] = {"tur": 3, "hasar": zehir_hasar}
        
        # Ilk ok hasari
        güçlü_saldırı = int(statlar["saldırı"] * sınıf["özel_çarpan"])
        hasar, kritik = hasar_hesapla(güçlü_saldırı, savaş["savunma"], statlar["şans"] + 15)
        savaş["can"] = max(0, savaş["can"] - hasar)
        
        savaş_log += f"\n{'━' * 25}\n"
        savaş_log += f"🏹 **{sınıf['özel_yetenek']} FIRLATTI!**\n"
        savaş_log += f"┌─────────────────────┐\n"
        if kritik:
            savaş_log += f"│ KRİTİK! {hasar} hasar!   │\n"
        else:
            savaş_log += f"│   {hasar} hasar verdin!  │\n"
        savaş_log += f"│ ☠️ ZEHİR: {zehir_hasar}/tur (3 tur) │\n"
        savaş_log += f"└─────────────────────┘\n"
        savaş_log += f"{'━' * 25}\n\n"
        
        # Canavar karşı saldırı
        düşman_hasar, düşman_kritik = hasar_hesapla(savaş["saldırı"], statlar["savunma"], 8)
        can_hasarı, kalkan_hasarı, _ = hasar_al(dungeon, düşman_hasar)
        
        if düşman_kritik:
            savaş_log += f"**KRİTİK!** {savaş['emoji']} **{düşman_hasar}** hasar verdi!"
        else:
            savaş_log += f"{savaş['emoji']} **{düşman_hasar}** hasar verdi."
        
        if kalkan_hasarı > 0:
            savaş_log += f" (Kalkan -{kalkan_hasarı})\n"
        else:
            savaş_log += "\n"
    # Doktor - Acil Müdahale: Can fullenir + %25 kalkan
    elif dungeon["sınıf"] == "doktor":
        eski_can = dungeon["can"]
        dungeon["can"] = statlar["can"]  # Can tamamen dolar
        iyileşme = statlar["can"] - eski_can
        
        # %25 kalkan ver
        kalkan_miktarı = int(statlar["can"] * 0.25)
        dungeon["kalkan"] = dungeon.get("kalkan", 0) + kalkan_miktarı
        
        savaş_log += f"💉 **{sınıf['özel_yetenek']}!**\n"
        savaş_log += f"❤️ **+{iyileşme}** can iyileşti! (Can: {dungeon['can']}/{statlar['can']})\n"
        savaş_log += f"🛡️ **+{kalkan_miktarı}** kalkan kazandın! (Toplam kalkan: {dungeon['kalkan']})\n"
        
        # Canavar karşı saldırı (kalkan sistemi ile)
        düşman_hasar, düşman_kritik = hasar_hesapla(savaş["saldırı"], statlar["savunma"], 8)
        can_hasarı, kalkan_hasarı, kalan_kalkan = hasar_al(dungeon, düşman_hasar)
        
        if düşman_kritik:
            savaş_log += f"**KRİTİK!** {savaş['emoji']} **{düşman_hasar}** hasar verdi!"
        else:
            savaş_log += f"{savaş['emoji']} **{düşman_hasar}** hasar verdi."
        
        if kalkan_hasarı > 0:
            savaş_log += f" (🛡️ -{kalkan_hasarı} kalkan"
            if can_hasarı > 0:
                savaş_log += f", ❤️ -{can_hasarı} can)\n"
            else:
                savaş_log += ")\n"
        else:
            savaş_log += "\n"
    else:
        # Güçlü saldırı (diğer sınıflar için)
        güçlü_saldırı = int(statlar["saldırı"] * sınıf["özel_çarpan"])
        hasar, kritik = hasar_hesapla(güçlü_saldırı, savaş["savunma"], statlar["şans"] + 15)

        savaş_log += f"**{sınıf['özel_yetenek']}!** "
        if kritik:
            savaş_log += f"**KRİTİK! {hasar}** hasar!\n"
        else:
            savaş_log += f"**{hasar}** hasar!\n"

        savaş["can"] = max(0, savaş["can"] - hasar)

        # Canavar karşı saldırı (kalkan sistemi ile)
        düşman_hasar, düşman_kritik = hasar_hesapla(savaş["saldırı"], statlar["savunma"], 8)
        can_hasarı, kalkan_hasarı, _ = hasar_al(dungeon, düşman_hasar)
        
        if kalkan_hasarı > 0:
            savaş_log += f"{savaş['emoji']} **{düşman_hasar}** hasar verdi! (🛡️ -{kalkan_hasarı} kalkan"
            if can_hasarı > 0:
                savaş_log += f", ❤️ -{can_hasarı} can)\n"
            else:
                savaş_log += ")\n"
        else:
            savaş_log += f"{savaş['emoji']} **{düşman_hasar}** hasar verdi.\n"

    # Canavar öldü mü kontrol et (basitleştirilmiş)
    if savaş["can"] <= 0:
        altın = random.randint(savaş["altın_min"], savaş["altın_max"])
        xp = savaş["xp"]
        prestij = dungeon.get("prestiж", 0)
        prestij_bilgi = PRESTİJ_SEVİYELERİ.get(prestij, PRESTİJ_SEVİYELERİ[0])
        altın_bonus = int(altın * prestij_bilgi["bonus_altın"] / 100)
        altın += altın_bonus

        dungeon["xp"] = dungeon.get("xp", 0) + xp
        dungeon["seviye"] = get_zindan_seviye(dungeon["xp"])
        dungeon["toplam_öldürme"] += 1
        if savaş["tür"] == "boss":
            dungeon["boss_öldürme"] += 1

        user = get_user(user_id)
        user["money"] += altın
        save_user(user)

        düşen_eşya = None
        if savaş["tür"] == "boss" and savaş.get("loot"):
            düşen_eşya_id = random.choice(savaş["loot"])
            düşen_eşya = EKİPMANLAR.get(düşen_eşya_id)
            if düşen_eşya:
                dungeon["envanter"].append({"eşya_id": düşen_eşya_id, "kuşanılmış": False})
        else:
            loot_id = roll_loot(savaş["kat"])
            if loot_id:
                düşen_eşya = EKİPMANLAR.get(loot_id)
                if düşen_eşya:
                    dungeon["envanter"].append({"eşya_id": loot_id, "kuşanılmış": False})

        dungeon["aktif_savaş"] = None
        save_dungeon(dungeon)

        sonuç = f"{savaş_log}\n{savaş['emoji']} **{savaş['isim']}** yenildi!\nAltın: **+{altın:,}** | XP: **+{xp}**"
        if düşen_eşya:
            sonuç += f"\nEşya: {düşen_eşya['emoji']} {düşen_eşya['isim']}"

        embed = discord.Embed(title="Zafer!", description=sonuç, color=discord.Color.gold())
        return await ctx.send(embed=embed)

    if dungeon["can"] <= 0:
        # Ölüm - 5 kat geri at (bölgeye göre)
        dungeon["toplam_ölüm"] += 1
        savas_bolge = savaş.get("bolge", "zindan")
        
        if savas_bolge == "visored":
            dungeon["visored_kat"] = max(0, dungeon.get("visored_kat", 0) - 6)
            mevcut_kat = dungeon["visored_kat"]
        else:
            dungeon["mevcut_kat"] = max(0, dungeon["mevcut_kat"] - 6)
            mevcut_kat = dungeon["mevcut_kat"]
            
        dungeon["can"] = statlar["can"]
        dungeon["mana"] = 0  # Mana sıfırlanır
        dungeon["kalkan"] = 0  # Kalkan sıfırlanır
        dungeon["aktif_savaş"] = None
        save_dungeon(dungeon)
        embed = discord.Embed(title="YENİLDİN!", description=f"{savaş_log}\n**5 kat** geri düştün. Mevcut kat: **{mevcut_kat}**\nCan yenilendi, mana ve kalkan sıfırlandı.\n`!gir` ile tekrar dene.", color=discord.Color.dark_red())
        return await ctx.send(embed=embed)

    dungeon["aktif_savaş"] = savaş
    save_dungeon(dungeon)

    # Savaş devam ediyor - aynı embed formatı
    savas_bolge = savaş.get("bolge", "zindan")
    bolge_bilgi = BOLGELER.get(savas_bolge, BOLGELER["zindan"])
    
    düşman_can_pct = max(0, savaş["can"] / savaş["maks_can"])
    düşman_bar_dolu = int(düşman_can_pct * 10)
    can_bar_düşman = "🟥" * düşman_bar_dolu + "⬛" * (10 - düşman_bar_dolu)

    # Kalkan ile can bar hesapla
    kalkan = dungeon.get("kalkan", 0)
    can_bar_sen = can_bar_hesapla(dungeon["can"], statlar["can"], kalkan)

    mana_pct = max(0, dungeon["mana"] / MAKS_MANA)
    mana_bar_dolu = int(mana_pct * 10)
    mana_bar_sen = "🟦" * mana_bar_dolu + "⬛" * (10 - mana_bar_dolu)
    mana_hazır = " ⚡" if dungeon['mana'] >= MAKS_MANA else ""

    # Kalkan bilgisi
    kalkan_text = f" 🛡️ +{kalkan}" if kalkan > 0 else ""

    embed = discord.Embed(
        title=f"{bolge_bilgi['emoji']} Kat {savaş['kat']} — Savaş Devam Ediyor",
        description=(
            f"{savaş_log}\n"
            f"{'━' * 30}\n\n"
            f"**{savaş['emoji']} {savaş['isim']}**\n"
            f"Can: {can_bar_düşman} **{savaş['can']}/{savaş['maks_can']}**\n\n"
            f"**{sınıf['emoji']} {ctx.author.display_name}**\n"
            f"Can: {can_bar_sen} **{dungeon['can']}/{statlar['can']}**{kalkan_text}\n"
            f"Mana: {mana_bar_sen} **{dungeon['mana']}/{MAKS_MANA}**{mana_hazır}\n\n"
            f"`!saldır` (+{sınıf['vuruş_mana_kazanç']}) | `!özel` (Mana dolunca) | `!iksir` | `!kaç`"
        ),
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{bolge_bilgi['isim']} | Kat {savaş['kat']}")
    await ctx.send(embed=embed)


@bot.command(name="kaç", aliases=["flee", "kaçış"])
async def kaç(ctx):
    """Savastan kac (ayni kattan devam edersin)."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if not dungeon.get("aktif_savaş"):
        embed = discord.Embed(description="Aktif bir savasin yok!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    savaş = dungeon["aktif_savaş"]
    savas_bolge = savaş.get("bolge", "zindan")
    bolge_bilgi = BOLGELER.get(savas_bolge, BOLGELER["zindan"])
    
    # Kacinca ayni kattan devam et (bolgeye gore)
    if savas_bolge == "visored":
        dungeon["visored_kat"] = max(0, dungeon.get("visored_kat", 0) - 1)
        mevcut_kat = dungeon["visored_kat"]
    else:
        dungeon["mevcut_kat"] = max(0, dungeon["mevcut_kat"] - 1)
        mevcut_kat = dungeon["mevcut_kat"]
        
    dungeon["aktif_savaş"] = None
    save_dungeon(dungeon)

    embed = discord.Embed(
        title="Kaçış Başarılı!",
        description=(
            f"{savaş['emoji']} **{savaş['isim']}** karsisindan kactin!\n\n"
            f"Ayni kattan devam ediyorsun. Mevcut kat: **{mevcut_kat}**\n\n"
            f"Tekrar girmek icin: `!gir`"
        ),
        color=discord.Color.light_grey(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{bolge_bilgi['isim']}")
    await ctx.send(embed=embed)


@bot.command(name="iksir", aliases=["potion", "heal", "iyileş"])
async def iksir(ctx):
    """Can iksiri kullan."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if dungeon.get("iksir", 0) <= 0:
        embed = discord.Embed(
            description="Can iksirin yok! `!iksirsat` ile satın al.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    statlar = get_karakter_statları(dungeon)
    if dungeon["can"] >= statlar["can"]:
        embed = discord.Embed(description="Canın zaten dolu!", color=discord.Color.orange())
        return await ctx.send(embed=embed)

    iyileşme = int(statlar["can"] * 0.4)  # %40 can iyileştirme
    dungeon["iksir"] -= 1
    dungeon["can"] = min(statlar["can"], dungeon["can"] + iyileşme)
    save_dungeon(dungeon)

    embed = discord.Embed(
        title="Can İksiri Kullanıldı!",
        description=(
            f"**+{iyileşme}** can iyileştirdin!\n\n"
            f"Can: **{dungeon['can']}/{statlar['can']}**\n"
            f"Kalan can iksiri: **{dungeon['iksir']}**"
        ),
        color=discord.Color.teal(),
    )
    await ctx.send(embed=embed)


@bot.command(name="manaiksir", aliases=["manapotion", "mp"])
async def mana_iksiri(ctx):
    """Mana iksiri kullan - Mana tamamen doldurur."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if dungeon.get("mana_iksiri", 0) <= 0:
        embed = discord.Embed(
            description="Mana iksirin yok! `!dükkan` ile satın al.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if dungeon.get("mana", 0) >= MAKS_MANA:
        embed = discord.Embed(description="Manan zaten dolu!", color=discord.Color.orange())
        return await ctx.send(embed=embed)

    eski_mana = dungeon.get("mana", 0)
    dungeon["mana_iksiri"] -= 1
    dungeon["mana"] = MAKS_MANA  # Mana tamamen dolar
    save_dungeon(dungeon)

    embed = discord.Embed(
        title="⚡ Mana İksiri Kullanıldı!",
        description=(
            f"Mana tamamen doldu! ({eski_mana} → {MAKS_MANA})\n\n"
            f"**ÖZEL YETENEĞİN HAZIR!**\n"
            f"Kalan mana iksiri: **{dungeon['mana_iksiri']}**"
        ),
        color=discord.Color.blue(),
    )
    await ctx.send(embed=embed)


@bot.command(name="dükkan", aliases=["iksirdukkan"])
async def dukkan(ctx):
    """İksir dükkanını göster."""
    embed = discord.Embed(
        title="İksir Dükkanı",
        description="İksir satın almak için aşağıdaki komutları kullan:",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="Can İksiri",
        value=(
            f"Fiyat: **200 VC**\n"
            f"Etki: Maksimum canının **%40**'ını yeniler\n"
            f"Komut: `!iksirsat <adet>`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚡ Mana İksiri",
        value=(
            f"Fiyat: **150 VC**\n"
            f"Etki: Mana tamamen doldurur (100) - Özel yeteneğini hemen kullanabilirsin!\n"
            f"Komut: `!manaiksirsatinal <adet>`"
        ),
        inline=False
    )
    
    embed.set_footer(text="Zindan Sistemi | Dükkan")
    await ctx.send(embed=embed)


@bot.command(name="iksirsat", aliases=["buypotion", "iksirsatınal", "caniksir"])
async def iksir_satın_al(ctx, adet: int = 1):
    """Can iksiri satın al (200 VisoCoin)."""
    user_id = ctx.author.id
    İKSİR_FİYAT = 200

    if adet <= 0:
        return await ctx.send(embed=discord.Embed(description="Geçerli adet gir.", color=discord.Color.red()))

    toplam = İKSİR_FİYAT * adet
    user = get_user(user_id)

    if user["money"] < toplam:
        return await ctx.send(embed=discord.Embed(description=f"Yetersiz bakiye! {adet}x can iksiri için **{toplam}** VC gerekiyor.", color=discord.Color.red()))

    user["money"] -= toplam
    save_user(user)

    dungeon = get_dungeon(user_id)
    dungeon["iksir"] = dungeon.get("iksir", 0) + adet
    save_dungeon(dungeon)

    update_quest_progress(user_id, "harca", toplam)

    embed = discord.Embed(
        title="Can İksiri Satın Alındı!",
        description=f"**{adet}x** can iksiri aldın!\nMaliyet: **{toplam}** VC | Toplam can iksiri: **{dungeon['iksir']}**\nBakiye: **{user['money']:,}** VC",
        color=discord.Color.teal(),
    )
    await ctx.send(embed=embed)


@bot.command(name="manaiksirsatinal", aliases=["buymanapotion", "manaiksirsat", "manasat"])
async def mana_iksiri_satın_al(ctx, adet: int = 1):
    """Mana iksiri satın al (150 VisoCoin)."""
    user_id = ctx.author.id
    MANA_İKSİR_FİYAT = 150

    if adet <= 0:
        return await ctx.send(embed=discord.Embed(description="Geçerli adet gir.", color=discord.Color.red()))

    toplam = MANA_İKSİR_FİYAT * adet
    user = get_user(user_id)

    if user["money"] < toplam:
        return await ctx.send(embed=discord.Embed(description=f"Yetersiz bakiye! {adet}x mana iksiri için **{toplam}** VC gerekiyor.", color=discord.Color.red()))

    user["money"] -= toplam
    save_user(user)

    dungeon = get_dungeon(user_id)
    dungeon["mana_iksiri"] = dungeon.get("mana_iksiri", 0) + adet
    save_dungeon(dungeon)

    update_quest_progress(user_id, "harca", toplam)

    embed = discord.Embed(
        title="Mana İksiri Satın Alındı!",
        description=f"**{adet}x** mana iksiri aldın!\nMaliyet: **{toplam}** VC | Toplam mana iksiri: **{dungeon['mana_iksiri']}**\nBakiye: **{user['money']:,}** VC",
        color=discord.Color.blue(),
    )
    await ctx.send(embed=embed)


# ================= BOLGE KOMUTLARI =================

@bot.command(name="zbölgeler", aliases=["zbölge"])
async def zbölgeler(ctx):
    """Mevcut bölgeleri göster."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)
    prestij = dungeon.get("prestiж", 0)

    embed = discord.Embed(
        title="Bolgeler",
        description="Macera bölgeleri ve gereksinimleri:",
        color=discord.Color.teal(),
        timestamp=datetime.now(timezone.utc)
    )

    for bolge_id, bolge in BOLGELER.items():
        açık = prestij >= bolge["gerekli_prestij"]
        aktif = dungeon.get("bolge", "zindan") == bolge_id
        
        durum = ""
        if aktif:
            durum = " **[AKTIF]**"
        elif açık:
            durum = " *(Açık)*"
        else:
            durum = f" *(Prestij {bolge['gerekli_prestij']} gerekli)*"
        
        if bolge_id == "zindan":
            kat_bilgi = f"Mevcut Kat: **{dungeon['mevcut_kat']}** | En Yüksek: **{dungeon['en_yüksek_kat']}**"
        else:
            kat_bilgi = f"Mevcut Kat: **{dungeon.get('visored_kat', 0)}** | En Yüksek: **{dungeon.get('visored_en_yuksek', 0)}**"
        
        embed.add_field(
            name=f"{bolge['emoji']} {bolge['isim']}{durum}",
            value=f"{bolge['açıklama']}\n{kat_bilgi}",
            inline=False
        )

    embed.add_field(
        name="Bolge Degistirme",
        value="`!bolgesec <zindan/visored>` ile bolge degistir.",
        inline=False
    )
    
    embed.set_footer(text=f"Prestij Seviyen: {prestij}")
    await ctx.send(embed=embed)


@bot.command(name="bolgesec", aliases=["selectregion", "bolgeseç"])
async def bolge_sec(ctx, bolge_id: str = None):
    """Bolge sec."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if not bolge_id:
        return await ctx.send(embed=discord.Embed(
            description="Bolge belirt! `!bolgesec zindan` veya `!bolgesec visored`",
            color=discord.Color.red()
        ))

    bolge_id = bolge_id.lower()
    
    if bolge_id not in BOLGELER:
        return await ctx.send(embed=discord.Embed(
            description=f"Gecersiz bolge! Mevcut bölgeler: {', '.join(BOLGELER.keys())}",
            color=discord.Color.red()
        ))

    bolge = BOLGELER[bolge_id]
    prestij = dungeon.get("prestiж", 0)

    if prestij < bolge["gerekli_prestij"]:
        return await ctx.send(embed=discord.Embed(
            description=f"**{bolge['isim']}** icin **Prestij {bolge['gerekli_prestij']}** gerekiyor!\nMevcut prestijin: **{prestij}**",
            color=discord.Color.red()
        ))

    # Aktif savas varsa bolge degistiremez
    if dungeon.get("aktif_savaş"):
        return await ctx.send(embed=discord.Embed(
            description="Aktif bir savasin var! Once savasi bitir veya `!kaç` ile kaç.",
            color=discord.Color.orange()
        ))

    eski_bolge = dungeon.get("bolge", "zindan")
    if eski_bolge == bolge_id:
        return await ctx.send(embed=discord.Embed(
            description=f"Zaten **{bolge['isim']}** bolgesindesin!",
            color=discord.Color.orange()
        ))

    dungeon["bolge"] = bolge_id
    save_dungeon(dungeon)

    embed = discord.Embed(
        title=f"{bolge['emoji']} Bolge Degistirildi!",
        description=(
            f"Artik **{bolge['isim']}** bolgesindesin!\n\n"
            f"{bolge['açıklama']}\n\n"
            f"`!gir` ile maceraya başla!"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Zindan Sistemi | Bolge Sistemi")
    await ctx.send(embed=embed)


@bot.command(name="zindanenvanteri", aliases=["zenv", "ze", "ekipman"])
async def envanter(ctx, sayfa: int = 1):
    """Ekipman envanterini göster (sayfa sistemi)."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if dungeon["sınıf"] is None:
        return await ctx.send(embed=discord.Embed(description="Once sinif sec! `!sınıfseç <sınıf>`", color=discord.Color.red()))

    envanter_liste = dungeon.get("envanter", [])
    kuşanılmış = dungeon.get("kuşanılmış", {})

    if not envanter_liste:
        return await ctx.send(embed=discord.Embed(description="Envanterin bos!", color=discord.Color.dark_grey()))

    # Gruplanmis ekipmanlar
    silahlar = []
    zırhlar = []
    yüzükler = []

    envanter_güncellendi = False
    for item in envanter_liste:
        # Yeni ve eski format uyumlulugu
        item_id = item.get("id")
        eşya_tipi = item.get("eşya_tipi") or item.get("eşya_id")
        
        # Eski formattaki eşyalara ID ata
        if not item_id:
            item_id = str(uuid.uuid4())[:8]
            item["id"] = item_id
            if item.get("eşya_id"):
                item["eşya_tipi"] = item.pop("eşya_id")
            envanter_güncellendi = True
        
        eşya = EKİPMANLAR.get(eşya_tipi)
        if not eşya:
            continue
        
        kuşanılmış_mı = item_id in kuşanılmış.values() if item_id else eşya_tipi in kuşanılmış.values()
        
        # ID'yi her zaman göster
        satır = f"`{item_id}` {eşya['emoji']} **{eşya['isim']}** ({NADİRLİK_RENKLERİ[eşya['nadirlik']]} {eşya['nadirlik']})"
        if kuşanılmış_mı:
            satır += " **[K]**"
        stat_text = []
        if eşya.get("saldırı", 0) > 0:
            stat_text.append(f"+{eşya['saldırı']}S")
        if eşya.get("savunma", 0) > 0:
            stat_text.append(f"+{eşya['savunma']}D")
        if eşya.get("can", 0) > 0:
            stat_text.append(f"+{eşya['can']}C")
        if eşya.get("şans", 0) > 0:
            stat_text.append(f"+{eşya['şans']}%")
        satır += f" ({', '.join(stat_text)})" if stat_text else ""

        if eşya["tür"] == "silah":
            silahlar.append(satır)
        elif eşya["tür"] == "zırh":
            zırhlar.append(satır)
        elif eşya["tür"] == "yüzük":
            yüzükler.append(satır)

    # Eski formattaki eşyalar güncellendiyse kaydet
    if envanter_güncellendi:
        save_dungeon(dungeon)

    # Sayfa sistemi - her sayfada maksimum 8 eşya göster
    EŞYA_PER_SAYFA = 8
    tüm_eşyalar = []
    
    if silahlar:
        tüm_eşyalar.append(("Silahlar", silahlar))
    if zırhlar:
        tüm_eşyalar.append(("Zırhlar", zırhlar))
    if yüzükler:
        tüm_eşyalar.append(("Yüzükler", yüzükler))

    # Toplam eşya sayısı
    toplam_eşya = len(silahlar) + len(zırhlar) + len(yüzükler)
    toplam_sayfa = max(1, (toplam_eşya + EŞYA_PER_SAYFA - 1) // EŞYA_PER_SAYFA)

    # Sayfa kontrolü
    if sayfa < 1:
        sayfa = 1
    if sayfa > toplam_sayfa:
        sayfa = toplam_sayfa
    
    # Sayfa için eşyaları hesapla
    başlangıç_idx = (sayfa - 1) * EŞYA_PER_SAYFA
    bitiş_idx = sayfa * EŞYA_PER_SAYFA

    # Tüm eşyaları düz liste yap
    düz_liste = []
    for kategori, eşyalar in tüm_eşyalar:
        for eşya in eşyalar:
            düz_liste.append((kategori, eşya))

    # Bu sayfadaki eşyalar
    sayfa_eşyaları = düz_liste[başlangıç_idx:bitiş_idx]
    
    # Kategorilere gore grupla
    sayfa_gruplu = {}
    for kategori, eşya in sayfa_eşyaları:
        if kategori not in sayfa_gruplu:
            sayfa_gruplu[kategori] = []
        sayfa_gruplu[kategori].append(eşya)
    
    # Aktif setleri kontrol et
    aktif_setler = get_aktif_setler(dungeon)
    
    # Embed açıklaması
    açıklama = f"Toplam **{toplam_eşya}** eşya | Sayfa **{sayfa}/{toplam_sayfa}**"
    
    embed = discord.Embed(
        title=f"Envanter - {ctx.author.display_name}",
        description=açıklama,
        color=discord.Color.gold() if aktif_setler else discord.Color.dark_purple(),
        timestamp=datetime.now(timezone.utc)
    )
    
    # Aktif set pasiflerini göster
    if aktif_setler:
        set_text = ""
        for set_id, set_bilgi in aktif_setler:
            set_text += f"{set_bilgi['emoji']} **{set_bilgi['isim']}** - *{set_bilgi['pasif_isim']}*\n"
            set_text += f"└ {set_bilgi['pasif_açıklama']}\n\n"
        embed.add_field(name="Aktif Set Pasifleri", value=set_text.strip(), inline=False)
    
    # Her kategori icin field ekle (1024 karakter limitini asma)
    for kategori, eşyalar in sayfa_gruplu.items():
        field_text = "\n".join(eşyalar)
        if len(field_text) > 1020:
            # Çok uzunsa böl
            parçalar = []
            mevcut_parça = ""
            for eşya in eşyalar:
                if len(mevcut_parça) + len(eşya) + 1 > 1020:
                    parçalar.append(mevcut_parça)
                    mevcut_parça = eşya
                else:
                    mevcut_parça += ("\n" if mevcut_parça else "") + eşya
            if mevcut_parça:
                parçalar.append(mevcut_parça)
            
            for i, parça in enumerate(parçalar):
                field_name = f"{kategori}" if i == 0 else f"{kategori} (devam)"
                embed.add_field(name=field_name, value=parça, inline=False)
        else:
            embed.add_field(name=kategori, value=field_text, inline=False)
    
    # Navigasyon bilgisi
    nav_text = "Kusan: `!kuşan <ID>` | Sat: `!eşyasat <ID>`"
    if toplam_sayfa > 1:
        nav_text += f"\nSayfa: `!zenv <sayfa>` (1-{toplam_sayfa})"
    embed.set_footer(text=nav_text)
    await ctx.send(embed=embed)


@bot.command(name="kuşan", aliases=["equip", "giy"])
async def kuşan(ctx, *, girdi: str = None):
    """Ekipman kuşan (ID veya eşya adı ile)."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if girdi is None:
        return await ctx.send(embed=discord.Embed(description="Kullanım: `!kuşan <ID veya eşya_adı>`\nÖrnek: `!kuşan abc123` veya `!kuşan demir kılıç`", color=discord.Color.blue()))

    girdi = girdi.strip()
    envanter = dungeon.get("envanter", [])

    # Önce ID ile ara
    bulunan_item = None
    for item in envanter:
        item_id = item.get("id")
        if item_id and item_id.lower() == girdi.lower():
            bulunan_item = item
            break
    
    # ID bulunamadıysa eşya adı ile ara
    if not bulunan_item:
        girdi_normalize = girdi.lower().replace(" ", "_")
        for item in envanter:
            eşya_tipi = item.get("eşya_tipi") or item.get("eşya_id")
            if eşya_tipi == girdi_normalize:
                bulunan_item = item
                break

    if not bulunan_item:
        return await ctx.send(embed=discord.Embed(description="Bu eşya envanterinde yok!", color=discord.Color.red()))

    eşya_tipi = bulunan_item.get("eşya_tipi") or bulunan_item.get("eşya_id")
    eşya = EKİPMANLAR.get(eşya_tipi)
    if not eşya:
        return await ctx.send(embed=discord.Embed(description="Geçersiz eşya!", color=discord.Color.red()))

    # Kuşan (benzersiz ID kullan)
    kuşanılacak_id = bulunan_item.get("id") or eşya_tipi
    dungeon["kuşanılmış"][eşya["tür"]] = kuşanılacak_id
    save_dungeon(dungeon)

    statlar = get_karakter_statları(dungeon)

    embed = discord.Embed(
        title=f"{eşya['emoji']} {eşya['isim']} Kuşanıldı!",
        description=(
            f"Eşya ID: `{kuşanılacak_id}`\n\n"
            f"**Güncel Statlar:**\n"
            f"Can: **{statlar['can']}** | Saldırı: **{statlar['saldırı']}** | "
            f"Savunma: **{statlar['savunma']}** | Kritik: **%{statlar['şans']}**"
        ),
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="eşyasat", aliases=["sellitem", "eşyasatış"])
async def eşya_sat(ctx, *, girdi: str = None):
    """Ekipman sat (ID veya eşya adı ile)."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if girdi is None:
        return await ctx.send(embed=discord.Embed(description="Kullanım: `!eşyasat <ID veya eşya_adı>`", color=discord.Color.blue()))

    girdi = girdi.strip()
    envanter = dungeon.get("envanter", [])
    kuşanılmış = dungeon.get("kuşanılmış", {})

    # Önce ID ile ara
    bulunan_index = None
    bulunan_item = None
    for i, item in enumerate(envanter):
        item_id = item.get("id")
        if item_id and item_id.lower() == girdi.lower():
            bulunan_index = i
            bulunan_item = item
            break
    
    # ID bulunamadıysa eşya adı ile ara
    if bulunan_item is None:
        girdi_normalize = girdi.lower().replace(" ", "_")
        for i, item in enumerate(envanter):
            eşya_tipi = item.get("eşya_tipi") or item.get("eşya_id")
            if eşya_tipi == girdi_normalize:
                bulunan_index = i
                bulunan_item = item
                break

    if bulunan_item is None:
        return await ctx.send(embed=discord.Embed(description="Bu eşya envanterinde yok!", color=discord.Color.red()))

    # Kuşanılmış eşya satılamaz
    item_id = bulunan_item.get("id")
    if item_id and item_id in kuşanılmış.values():
        return await ctx.send(embed=discord.Embed(description="Kuşanılmış eşya satılamaz! Önce başka eşya kuşan.", color=discord.Color.orange()))

    eşya_tipi = bulunan_item.get("eşya_tipi") or bulunan_item.get("eşya_id")
    eşya = EKİPMANLAR.get(eşya_tipi)
    if not eşya:
        return await ctx.send(embed=discord.Embed(description="Geçersiz eşya!", color=discord.Color.red()))

    satış_fiyatı = eşya["fiyat"] // 2  # Yarı fiyatına sat
    dungeon["envanter"].pop(bulunan_index)
    save_dungeon(dungeon)

    user = get_user(user_id)
    user["money"] += satış_fiyatı
    save_user(user)

    embed = discord.Embed(
        title=f"{eşya['emoji']} Eşya Satıldı!",
        description=f"**{eşya['isim']}** `[{item_id}]` satıldı!\nKazanç: **+{satış_fiyatı:,}** VC\nBakiye: **{user['money']:,}** VC",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="prestij", aliases=["prestige"])
async def prestij(ctx):
    """Prestij durumunu göster veya prestij yap."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if dungeon["sınıf"] is None:
        return await ctx.send(embed=discord.Embed(description="Önce sınıf seç!", color=discord.Color.red()))

    mevcut_prestij = dungeon.get("prestiж", 0)
    sonraki_prestij = mevcut_prestij + 1

    if sonraki_prestij not in PRESTİJ_GEREKSİNİMLERİ:
        # Maks prestij
        prestij_bilgi = PRESTİJ_SEVİYELERİ[mevcut_prestij]
        embed = discord.Embed(
            title=f"{prestij_bilgi['emoji']} Prestij — MAKSİMUM!",
            description=(
                f"Tebrikler! En yüksek prestij seviyesindesin!\n\n"
                f"**{prestij_bilgi['isim']}** (Prestij {mevcut_prestij})\n"
                f"Bonus Saldırı: **+{prestij_bilgi['bonus_saldırı']}**\n"
                f"Bonus Can: **+{prestij_bilgi['bonus_can']}**\n"
                f"Altın Bonus: **+%{prestij_bilgi['bonus_altın']}**"
            ),
            color=discord.Color.gold(),
        )
        return await ctx.send(embed=embed)

    gereksinimler = PRESTİJ_GEREKSİNİMLERİ[sonraki_prestij]
    mevcut_prestij_bilgi = PRESTİJ_SEVİYELERİ[mevcut_prestij]
    sonraki_bilgi = PRESTİJ_SEVİYELERİ[sonraki_prestij]

    kat_ok = dungeon["en_yüksek_kat"] >= gereksinimler["kat"]
    boss_ok = dungeon["boss_öldürme"] >= gereksinimler["boss"]
    seviye_ok = dungeon["seviye"] >= gereksinimler["seviye"]

    tamamlandı = kat_ok and boss_ok and seviye_ok

    embed = discord.Embed(
        title=f"Prestij — {mevcut_prestij_bilgi['emoji']} {mevcut_prestij_bilgi['isim']}",
        description=(
            f"Mevcut Prestij: **{mevcut_prestij}**\n"
            f"Sonraki: **{sonraki_bilgi['emoji']} {sonraki_bilgi['isim']}**\n\n"
            f"**Gereksinimler:**\n"
            f"{'[x]' if kat_ok else '[ ]'} En yüksek kat: **{dungeon['en_yüksek_kat']}/{gereksinimler['kat']}**\n"
            f"{'[x]' if boss_ok else '[ ]'} Boss öldürme: **{dungeon['boss_öldürme']}/{gereksinimler['boss']}**\n"
            f"{'[x]' if seviye_ok else '[ ]'} Zindan seviyesi: **{dungeon['seviye']}/{gereksinimler['seviye']}**\n\n"
            f"**Sonraki Prestij Bonusları:**\n"
            f"Bonus Saldırı: **+{sonraki_bilgi['bonus_saldırı']}**\n"
            f"Bonus Can: **+{sonraki_bilgi['bonus_can']}**\n"
            f"Altın Bonus: **+%{sonraki_bilgi['bonus_altın']}**\n\n"
        ),
        color=discord.Color.gold() if tamamlandı else discord.Color.dark_grey(),
    )

    if tamamlandı:
        embed.description += "Prestij yapabilirsin! `!prestijyap` ile ilerle.\n**Dikkat:** Seviye, kat, ekipman sıfırlanır ama prestij bonusları kalır!"
    else:
        embed.description += "Gereksinimleri tamamla ve prestij yap!"

    embed.set_footer(text="Zindan Sistemi | Prestij")
    await ctx.send(embed=embed)


@bot.command(name="prestijyap", aliases=["doprestige"])
async def prestij_yap(ctx):
    """Prestij yap — her şey sıfırlanır ama kalıcı bonuslar artar."""
    user_id = ctx.author.id
    dungeon = get_dungeon(user_id)

    if dungeon["sınıf"] is None:
        return await ctx.send(embed=discord.Embed(description="Önce sınıf seç!", color=discord.Color.red()))

    mevcut_prestij = dungeon.get("prestiж", 0)
    sonraki_prestij = mevcut_prestij + 1

    if sonraki_prestij not in PRESTİJ_GEREKSİNİMLERİ:
        return await ctx.send(embed=discord.Embed(description="Maksimum prestij seviyesindesin!", color=discord.Color.gold()))

    gereksinimler = PRESTİJ_GEREKSİNİMLERİ[sonraki_prestij]

    if (dungeon["en_yüksek_kat"] < gereksinimler["kat"] or
        dungeon["boss_öldürme"] < gereksinimler["boss"] or
        dungeon["seviye"] < gereksinimler["seviye"]):
        return await ctx.send(embed=discord.Embed(description="Gereksinimleri karşılamıyorsun! `!prestij` ile kontrol et.", color=discord.Color.red()))

    # Prestij bonusu VisoCoin ödülü
    ödül = sonraki_prestij * 5000
    user = get_user(user_id)
    user["money"] += ödül
    save_user(user)

    prestij_bilgi = PRESTİJ_SEVİYELERİ[sonraki_prestij]
    sınıf = SINIFLAR[dungeon["sınıf"]]

    # Sıfırla ama prestij ve istatistikleri koru
    dungeon["prestiж"] = sonraki_prestij
    dungeon["seviye"] = 1
    dungeon["xp"] = 0
    dungeon["mevcut_kat"] = 0
    dungeon["visored_kat"] = 0  # Visored kati da sifirla
    dungeon["bolge"] = "zindan"  # Bolgeyi zindana cevir
    dungeon["sınıf"] = None  # Yeni sınıf seçebilir
    dungeon["envanter"] = []
    dungeon["kuşanılmış"] = {"silah": None, "zırh": None, "yüzük": None}
    dungeon["can"] = 0
    dungeon["mana"] = 0
    dungeon["aktif_savaş"] = None
    save_dungeon(dungeon)

    # Prestij 5 ise Visored Adası açıldı mesajı
    visored_mesaj = ""
    if sonraki_prestij >= 5:
        visored_mesaj = "\n**VISORED ADASI AÇILDI!** `!bolgesec visored` ile yeni maceraya başla!\n"

    embed = discord.Embed(
        title=f"PRESTIJ {sonraki_prestij}!",
        description=(
            f"{'━' * 30}\n\n"
            f"{prestij_bilgi['emoji']} **{prestij_bilgi['isim']}** oldun!\n\n"
            f"**Kalici Bonuslar:**\n"
            f"Saldırı: **+{prestij_bilgi['bonus_saldırı']}**\n"
            f"Can: **+{prestij_bilgi['bonus_can']}**\n"
            f"Altın: **+%{prestij_bilgi['bonus_altın']}**\n\n"
            f"**Ödül:** +{ödül:,} VisoCoin\n"
            f"{visored_mesaj}\n"
            f"**Sifirlanan:** Seviye, kat, ekipman, sinif\n"
            f"**Korunan:** Prestij bonusları, istatistikler, en yüksek kat\n\n"
            f"Yeni sinif secmek icin: `!sınıfseç <sınıf>`"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Zindan Sistemi | Prestij")
    await ctx.send(embed=embed)


@bot.command(name="indeks", aliases=["index", "ekipmanlar", "items"])
async def indeks(ctx, kategori: str = None):
    """Tüm ekipmanları, nadirlikleri ve set bonuslarını göster."""
    
    # Nadirlik sıralaması (en düşükten en yükseğe)
    nadirlik_sırası = ["Yaygın", "Sıradan", "Nadir", "Epik", "Efsanevi", "Tanrısal", "Zindana"]
    
    # Nadirlik renkleri (Discord embed renkleri)
    nadirlik_discord_renkleri = {
        "Yaygın": 0x9e9e9e,      # Gri
        "Sıradan": 0x4caf50,     # Yeşil
        "Nadir": 0x2196f3,       # Mavi
        "Epik": 0x9c27b0,        # Mor
        "Efsanevi": 0xff9800,    # Turuncu
        "Tanrısal": 0xf44336,    # Kırmızı
        "Zindana": 0x000000,     # Siyah (gizemli)
    }
    
    # Düşme şansları
    düşme_şansları = {
        "Yaygın": "%30",
        "Sıradan": "%20",
        "Nadir": "%10",
        "Epik": "%5",
        "Efsanevi": "%1",
        "Tanrısal": "%0.1",
        "Zindana": "%0.001",  # Götünüz tutuşsun
    }
    
    if kategori is None:
        # Ana menü - kategorileri göster
        embed = discord.Embed(
            title="📜 EKİPMAN İNDEKSİ",
            description=(
                "Zindan dünyasındaki tüm ekipmanları keşfet!\n\n"
                "**Kategoriler:**\n"
                "`!indeks nadirlik` - Nadirlik seviyelerini göster\n"
                "`!indeks silahlar` - Tüm silahları göster\n"
                "`!indeks zırhlar` - Tüm zırhları göster\n"
                "`!indeks yüzükler` - Tüm yüzükleri göster\n"
                "`!indeks setler` - Set bonuslarını göster\n"
                "`!indeks zindana` - Zindana enderliğini göster\n\n"
                f"**Toplam Ekipman:** {len(EKİPMANLAR)}\n"
                f"**Toplam Set:** {len(SETLER)}"
            ),
            color=0xc9a44a,  # Altın rengi
        )
        embed.set_footer(text="Zindan Sistemi | Ekipman İndeksi")
        return await ctx.send(embed=embed)
    
    kategori = kategori.lower()
    
    if kategori in ["nadirlik", "nadir", "rarity"]:
        # Nadirlik tablosu
        embed = discord.Embed(
            title="💎 NADİRLİK SEVİYELERİ",
            description="Her nadirlik seviyesinin düşme şansı ve özellikleri:\n\n",
            color=0xc9a44a,
        )
        
        for nadirlik in nadirlik_sırası:
            emoji = NADİRLİK_RENKLERİ.get(nadirlik, "⬜")
            şans = düşme_şansları.get(nadirlik, "?")
            
            # Her nadirlik için ekipman sayısı
            ekipman_sayısı = len([e for e in EKİPMANLAR.values() if e.get("nadirlik") == nadirlik])
            
            if nadirlik == "Zindana":
                embed.add_field(
                    name=f"{emoji} {nadirlik} — ULTRA NADİR",
                    value=f"Düşme: **{şans}** (1/100.000)\nEkipman: **{ekipman_sayısı}** adet\n*Efsanelerin bile göremediği...*",
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"{emoji} {nadirlik}",
                    value=f"Düşme: **{şans}**\nEkipman: **{ekipman_sayısı}** adet",
                    inline=True,
                )
        
        embed.set_footer(text="Zindan Sistemi | Nadirlik Tablosu")
        return await ctx.send(embed=embed)
    
    elif kategori in ["silah", "silahlar", "weapons", "weapon"]:
        # Silahlar listesi
        silahlar = {k: v for k, v in EKİPMANLAR.items() if v.get("tür") == "silah"}
        
        # Nadirliğe göre grupla
        embed = discord.Embed(
            title="⚔️ SİLAH İNDEKSİ",
            description=f"Toplam **{len(silahlar)}** silah bulundu.\n\n",
            color=0xf44336,
        )
        
        for nadirlik in nadirlik_sırası:
            nadirlik_silahlar = [v for v in silahlar.values() if v.get("nadirlik") == nadirlik]
            if nadirlik_silahlar:
                emoji = NADİRLİK_RENKLERİ.get(nadirlik, "⬜")
                silah_listesi = "\n".join([
                    f"{s['emoji']} **{s['isim']}** — Saldırı: {s.get('saldırı', 0)} | Fiyat: {s.get('fiyat', 0):,}"
                    for s in sorted(nadirlik_silahlar, key=lambda x: x.get('saldırı', 0), reverse=True)
                ])
                embed.add_field(
                    name=f"{emoji} {nadirlik} Silahlar",
                    value=silah_listesi[:1024],  # Discord limit
                    inline=False,
                )
        
        embed.set_footer(text="Zindan Sistemi | Silah İndeksi")
        return await ctx.send(embed=embed)
    
    elif kategori in ["zırh", "zırhlar", "armor", "armors"]:
        # Zırhlar listesi
        zırhlar = {k: v for k, v in EKİPMANLAR.items() if v.get("tür") == "zırh"}
        
        embed = discord.Embed(
            title="🛡️ ZIRH İNDEKSİ",
            description=f"Toplam **{len(zırhlar)}** zırh bulundu.\n\n",
            color=0x2196f3,
        )
        
        for nadirlik in nadirlik_sırası:
            nadirlik_zırhlar = [v for v in zırhlar.values() if v.get("nadirlik") == nadirlik]
            if nadirlik_zırhlar:
                emoji = NADİRLİK_RENKLERİ.get(nadirlik, "⬜")
                zırh_listesi = "\n".join([
                    f"{z['emoji']} **{z['isim']}** — Savunma: {z.get('savunma', 0)} | Can: {z.get('can', 0)}"
                    for z in sorted(nadirlik_zırhlar, key=lambda x: x.get('savunma', 0), reverse=True)
                ])
                embed.add_field(
                    name=f"{emoji} {nadirlik} Zırhlar",
                    value=zırh_listesi[:1024],
                    inline=False,
                )
        
        embed.set_footer(text="Zindan Sistemi | Zırh İndeksi")
        return await ctx.send(embed=embed)
    
    elif kategori in ["yüzük", "yüzükler", "ring", "rings"]:
        # Yüzükler listesi
        yüzükler = {k: v for k, v in EKİPMANLAR.items() if v.get("tür") == "yüzük"}
        
        embed = discord.Embed(
            title="💍 YÜZÜK İNDEKSİ",
            description=f"Toplam **{len(yüzükler)}** yüzük bulundu.\n\n",
            color=0x9c27b0,
        )
        
        for nadirlik in nadirlik_sırası:
            nadirlik_yüzükler = [v for v in yüzükler.values() if v.get("nadirlik") == nadirlik]
            if nadirlik_yüzükler:
                emoji = NADİRLİK_RENKLERİ.get(nadirlik, "⬜")
                yüzük_listesi = "\n".join([
                    f"{y['emoji']} **{y['isim']}** — Saldırı: {y.get('saldırı', 0)} | Şans: +{y.get('şans', 0)}%"
                    for y in sorted(nadirlik_yüzükler, key=lambda x: x.get('saldırı', 0), reverse=True)
                ])
                embed.add_field(
                    name=f"{emoji} {nadirlik} Yüzükler",
                    value=yüzük_listesi[:1024],
                    inline=False,
                )
        
        embed.set_footer(text="Zindan Sistemi | Yüzük İndeksi")
        return await ctx.send(embed=embed)
    
    elif kategori in ["set", "setler", "sets"]:
        # Set bonusları
        embed = discord.Embed(
            title="🎭 SET BONUSLARI",
            description="3 parça tamamlandığında aktif olan özel güçler:\n\n",
            color=0xff9800,
        )
        
        for set_id, set_bilgi in SETLER.items():
            parça_isimleri = []
            for parça_id in set_bilgi["parçalar"]:
                ekipman = EKİPMANLAR.get(parça_id)
                if ekipman:
                    parça_isimleri.append(f"{ekipman['emoji']} {ekipman['isim']}")
            
            bonus_açıklama = set_bilgi.get("pasif_açıklama", "Bilinmiyor")
            
            # Zindana seti için özel görünüm
            if set_id == "scarlet":
                embed.add_field(
                    name=f"❓ {set_bilgi['emoji']} {set_bilgi['isim']} — ZİNDANA",
                    value=(
                        f"**Pasif:** {set_bilgi['pasif_isim']}\n"
                        f"*{bonus_açıklama}*\n"
                        f"**Parçalar:**\n" + "\n".join(parça_isimleri) + "\n"
                        f"⚠️ *%0.001 düşme şansı — Efsanelerin bile göremediği set...*"
                    ),
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"{set_bilgi['emoji']} {set_bilgi['isim']}",
                    value=(
                        f"**Pasif:** {set_bilgi['pasif_isim']}\n"
                        f"*{bonus_açıklama}*\n"
                        f"**Parçalar:**\n" + "\n".join(parça_isimleri)
                    ),
                    inline=False,
                )
        
        embed.set_footer(text="Zindan Sistemi | Set Bonusları")
        return await ctx.send(embed=embed)
    
    elif kategori in ["zindana", "???", "scarlet"]:
        # Zindana özel sayfası
        zindana_ekipmanlar = [v for v in EKİPMANLAR.values() if v.get("nadirlik") == "Zindana"]
        scarlet_set = SETLER.get("scarlet", {})
        
        embed = discord.Embed(
            title="❓ ZİNDANA ENDERLİĞİ",
            description=(
                "```\n"
                "░▒▓█ UYARI █▓▒░\n"
                "```\n"
                "**Düşme Şansı:** %0.001 (1/100.000)\n"
                "*Bu ekipmanları görenler... bir daha göremez.*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            ),
            color=0x000000,  # Siyah
        )
        
        # Zindana ekipmanlarını listele
        for ekipman in zindana_ekipmanlar:
            embed.add_field(
                name=f"{ekipman['emoji']} {ekipman['isim']}",
                value=(
                    f"Tür: **{ekipman['tür'].capitalize()}**\n"
                    f"Saldırı: **{ekipman.get('saldırı', 0)}**\n"
                    f"Savunma: **{ekipman.get('savunma', 0)}**\n"
                    f"Can: **{ekipman.get('can', 0)}**\n"
                    f"Fiyat: **{ekipman.get('fiyat', 0):,}** VC"
                ),
                inline=True,
            )
        
        # Scarlet set bonusu
        if scarlet_set:
            embed.add_field(
                name=f"\n🩸 SCARLET SETİ — Kanlı İntikam",
                value=(
                    f"*{scarlet_set.get('pasif_açıklama', '')}*\n\n"
                    f"**Bonus Detayları:**\n"
                    f"• Tüm statlar **+%50**\n"
                    f"• Hasarın **%30**'u kadar can çalma\n"
                    f"• Her turda **%5** can yenilenme\n"
                    f"• **2 kez** ölümden kurtulma\n"
                    f"• Verilen hasar **%10** artar"
                ),
                inline=False,
            )
        
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="*\"Karanlığın derinliklerinde, kanla yazılmış bir efsane...\"*",
            inline=False,
        )
        
        embed.set_footer(text="Zindan Sistemi | Zindana Enderliği")
        return await ctx.send(embed=embed)
    
    else:
        # Bilinmeyen kategori
        embed = discord.Embed(
            title="❌ Geçersiz Kategori",
            description=(
                "Geçerli kategoriler:\n"
                "`nadirlik`, `silahlar`, `zırhlar`, `yüzükler`, `setler`, `zindana`\n\n"
                "Örnek: `!indeks silahlar`"
            ),
            color=0xf44336,
        )
        return await ctx.send(embed=embed)

# ================= GEMİ TİPLERİ =================

GEMİLER = {
    "sandal": {
        "isim": "Sandal",
        "emoji": "🚣",
        "fiyat": 0,            # Başlangıç gemisi (ücretsiz)
        "hp": 50,
        "saldırı": 5,
        "zırh": 2,
        "hız": 3,
        "kargo": 10,           # Maksimum kargo kapasitesi
        "mürettebat_max": 2,
        "seviye_gereksinim": 1,
    },
    "yelkenli": {
        "isim": "Yelkenli",
        "emoji": "⛵",
        "fiyat": 5000,
        "hp": 120,
        "saldırı": 12,
        "zırh": 8,
        "hız": 5,
        "kargo": 25,
        "mürettebat_max": 5,
        "seviye_gereksinim": 3,
    },
    "brik": {
        "isim": "Brik",
        "emoji": "🚢",
        "fiyat": 20000,
        "hp": 250,
        "saldırı": 25,
        "zırh": 18,
        "hız": 7,
        "kargo": 50,
        "mürettebat_max": 10,
        "seviye_gereksinim": 6,
    },
    "kalyon": {
        "isim": "Kalyon",
        "emoji": "🏴‍☠️",
        "fiyat": 75000,
        "hp": 500,
        "saldırı": 50,
        "zırh": 35,
        "hız": 6,
        "kargo": 100,
        "mürettebat_max": 20,
        "seviye_gereksinim": 10,
    },
    "hayalet_gemi": {
        "isim": "Hayalet Gemi",
        "emoji": "👻",
        "fiyat": 200000,
        "hp": 800,
        "saldırı": 80,
        "zırh": 50,
        "hız": 10,
        "kargo": 150,
        "mürettebat_max": 30,
        "seviye_gereksinim": 15,
    },
}


# ================= MÜRETTEBAT TİPLERİ =================

MÜRETTEBAT = {
    "tayfa": {
        "isim": "Tayfa",
        "emoji": "👤",
        "fiyat": 200,
        "saldırı_bonus": 1,
        "savunma_bonus": 1,
        "özel": None,
    },
    "topçu": {
        "isim": "Topçu",
        "emoji": "💣",
        "fiyat": 500,
        "saldırı_bonus": 4,
        "savunma_bonus": 0,
        "özel": "Kritik vuruş şansı +%10",
    },
    "doktor": {
        "isim": "Doktor",
        "emoji": "🩺",
        "fiyat": 600,
        "saldırı_bonus": 0,
        "savunma_bonus": 2,
        "özel": "Savaş sonrası HP onarımı +%15",
    },
    "kaptan_yardımcısı": {
        "isim": "Kaptan Yardımcısı",
        "emoji": "🧭",
        "fiyat": 1000,
        "saldırı_bonus": 2,
        "savunma_bonus": 3,
        "özel": "Keşif XP +%20",
    },
    "silahçı": {
        "isim": "Silahçı",
        "emoji": "⚔️",
        "fiyat": 800,
        "saldırı_bonus": 6,
        "savunma_bonus": 1,
        "özel": "Yağma miktarı +%15",
    },
}


# ================= ADALAR / BÖLGELER =================

BÖLGELER = {
    "kıyı_suları": {
        "isim": "Kıyı Suları",
        "emoji": "🏖️",
        "seviye_min": 1,
        "sefer_süresi": 300,       # 5 dakika
        "tehlike": 10,             # %10 saldırı riski
        "hazine_min": 100,
        "hazine_max": 500,
        "xp_min": 10,
        "xp_max": 25,
        "nadir_eşya_şansı": 5,    # %5
        "olaylar": [
            {"isim": "Balıkçı teknesi buldun!", "tip": "hazine", "miktar_min": 50, "miktar_max": 150},
            {"isim": "Sahilde sandık keşfettin!", "tip": "hazine", "miktar_min": 100, "miktar_max": 300},
            {"isim": "Deniz sakin, huzurlu bir yolculuk.", "tip": "xp", "miktar_min": 5, "miktar_max": 15},
            {"isim": "Korsanlar seni gördü!", "tip": "savaş", "düşman_güç": 15},
        ],
    },
    "açık_deniz": {
        "isim": "Açık Deniz",
        "emoji": "🌊",
        "seviye_min": 3,
        "sefer_süresi": 600,       # 10 dakika
        "tehlike": 25,
        "hazine_min": 300,
        "hazine_max": 1200,
        "xp_min": 20,
        "xp_max": 50,
        "nadir_eşya_şansı": 10,
        "olaylar": [
            {"isim": "Batık gemi enkazı buldun!", "tip": "hazine", "miktar_min": 200, "miktar_max": 800},
            {"isim": "Tüccar gemisi ile karşılaştın, ticaret yaptın.", "tip": "hazine", "miktar_min": 300, "miktar_max": 600},
            {"isim": "Fırtına çıktı! Gemi hasar aldı.", "tip": "hasar", "miktar_min": 10, "miktar_max": 30},
            {"isim": "Korsan filosu saldırıyor!", "tip": "savaş", "düşman_güç": 35},
            {"isim": "Gizemli bir ada keşfettin!", "tip": "xp", "miktar_min": 30, "miktar_max": 60},
        ],
    },
    "şeytan_üçgeni": {
        "isim": "Şeytan Üçgeni",
        "emoji": "🔺",
        "seviye_min": 6,
        "sefer_süresi": 1200,      # 20 dakika
        "tehlike": 40,
        "hazine_min": 800,
        "hazine_max": 3500,
        "xp_min": 50,
        "xp_max": 120,
        "nadir_eşya_şansı": 20,
        "olaylar": [
            {"isim": "Lanetli hazine sandığı buldun!", "tip": "hazine", "miktar_min": 500, "miktar_max": 2000},
            {"isim": "Dev deniz canavarı saldırdı!", "tip": "savaş", "düşman_güç": 70},
            {"isim": "Gizemli bir sis... Kayıp ada ortaya çıktı!", "tip": "xp", "miktar_min": 80, "miktar_max": 150},
            {"isim": "Hayalet gemi ile karşılaştın!", "tip": "savaş", "düşman_güç": 90},
            {"isim": "Antik bir tapınak keşfettin!", "tip": "hazine", "miktar_min": 1000, "miktar_max": 3000},
        ],
    },
    "kraken_yuvası": {
        "isim": "Kraken'in Yuvası",
        "emoji": "🐙",
        "seviye_min": 10,
        "sefer_süresi": 1800,      # 30 dakika
        "tehlike": 55,
        "hazine_min": 2000,
        "hazine_max": 8000,
        "xp_min": 100,
        "xp_max": 250,
        "nadir_eşya_şansı": 30,
        "olaylar": [
            {"isim": "Kraken tentakülleri gemiyi sardı!", "tip": "savaş", "düşman_güç": 150},
            {"isim": "Denizin dibinde altın şehir buldun!", "tip": "hazine", "miktar_min": 3000, "miktar_max": 7000},
            {"isim": "Poseidon'un mızrağını keşfettin!", "tip": "nadir_eşya"},
            {"isim": "Devasa girdap! Gemi sürükleniyor!", "tip": "hasar", "miktar_min": 30, "miktar_max": 60},
            {"isim": "Kayıp korsan kaptanın hazinesi!", "tip": "hazine", "miktar_min": 5000, "miktar_max": 10000},
        ],
    },
    "cehennem_boğazı": {
        "isim": "Cehennem Boğazı",
        "emoji": "🔥",
        "seviye_min": 15,
        "sefer_süresi": 2700,      # 45 dakika
        "tehlike": 70,
        "hazine_min": 5000,
        "hazine_max": 20000,
        "xp_min": 200,
        "xp_max": 500,
        "nadir_eşya_şansı": 40,
        "olaylar": [
            {"isim": "Ateş denizi! Gemi yanıyor!", "tip": "hasar", "miktar_min": 40, "miktar_max": 80},
            {"isim": "Cehennem Kaptanı ile yüz yüzesin!", "tip": "savaş", "düşman_güç": 250},
            {"isim": "Efsanevi hazine odasını buldun!", "tip": "hazine", "miktar_min": 10000, "miktar_max": 20000},
            {"isim": "Şeytan'ın pusulasını keşfettin!", "tip": "nadir_eşya"},
            {"isim": "Volkanik ada patladı! Kaç!", "tip": "hasar", "miktar_min": 50, "miktar_max": 100},
            {"isim": "Atlantis'in kapısını buldun!", "tip": "xp", "miktar_min": 300, "miktar_max": 600},
        ],
    },
}


# ================= NADİR EŞYALAR =================

NADİR_EŞYALAR = {
    "poseidon_mızrağı": {
        "isim": "Poseidon'un Mızrağı",
        "emoji": "🔱",
        "tip": "silah",
        "bonus": {"saldırı": 20},
        "açıklama": "Denizlerin tanrısının silahı. Saldırı +20.",
        "satış_fiyat": 15000,
    },
    "hayalet_pusula": {
        "isim": "Hayalet Pusulası",
        "emoji": "🧭",
        "tip": "navigasyon",
        "bonus": {"xp_bonus": 25},
        "açıklama": "Gizli adalara yol gösterir. XP kazancı +%25.",
        "satış_fiyat": 12000,
    },
    "kraken_kalbi": {
        "isim": "Kraken'in Kalbi",
        "emoji": "💜",
        "tip": "zırh",
        "bonus": {"zırh": 25, "hp": 100},
        "açıklama": "Kraken'in taşlaşmış kalbi. Zırh +25, HP +100.",
        "satış_fiyat": 25000,
    },
    "şeytan_pusulası": {
        "isim": "Şeytan'ın Pusulası",
        "emoji": "🧿",
        "tip": "navigasyon",
        "bonus": {"hazine_bonus": 30},
        "açıklama": "Her zaman hazineyi gösterir. Hazine kazancı +%30.",
        "satış_fiyat": 20000,
    },
    "deniz_kızı_gözyaşı": {
        "isim": "Deniz Kızı Gözyaşı",
        "emoji": "💧",
        "tip": "iyileştirme",
        "bonus": {"onarım_bonus": 50},
        "açıklama": "Gemiyi anında iyileştirir. Onarım hızı +%50.",
        "satış_fiyat": 10000,
    },
    "altın_çapa": {
        "isim": "Altın Çapa",
        "emoji": "⚓",
        "tip": "zırh",
        "bonus": {"zırh": 15, "kargo": 20},
        "açıklama": "Efsanevi çapa. Zırh +15, kargo +20.",
        "satış_fiyat": 18000,
    },
    "lanetli_kılıç": {
        "isim": "Lanetli Kılıç",
        "emoji": "🗡️",
        "tip": "silah",
        "bonus": {"saldırı": 35, "hp": -50},
        "açıklama": "Muazzam güç, ama HP -50 lanetli. Saldırı +35.",
        "satış_fiyat": 22000,
    },
    "fırtına_şişesi": {
        "isim": "Fırtına Şişesi",
        "emoji": "🌪️",
        "tip": "savaş",
        "bonus": {"saldırı": 15, "hız": 5},
        "açıklama": "Şişedeki fırtına. Saldırı +15, Hız +5.",
        "satış_fiyat": 16000,
    },
}


# ================= GEMİ YÜKSELTMELERİ =================

GEMİ_YÜKSELTMELERİ = {
    "top": {
        "isim": "Top Yükseltmesi",
        "emoji": "💣",
        "fiyat_baz": 1000,         # Her seviye x2
        "max_seviye": 5,
        "bonus_per_level": {"saldırı": 5},
    },
    "zırh_plaka": {
        "isim": "Zırh Plakası",
        "emoji": "🛡️",
        "fiyat_baz": 1200,
        "max_seviye": 5,
        "bonus_per_level": {"zırh": 4, "hp": 20},
    },
    "yelken": {
        "isim": "Yelken İyileştirmesi",
        "emoji": "🏳️",
        "fiyat_baz": 800,
        "max_seviye": 5,
        "bonus_per_level": {"hız": 2},
    },
    "kargo_genişletme": {
        "isim": "Kargo Genişletmesi",
        "emoji": "📦",
        "fiyat_baz": 600,
        "max_seviye": 5,
        "bonus_per_level": {"kargo": 10},
    },
}


# ================= SEVİYE SİSTEMİ =================

KORSAN_SEVİYE_GEREKSİNİMLERİ = {
    2: 50,
    3: 150,
    4: 350,
    5: 700,
    6: 1200,
    7: 2000,
    8: 3200,
    9: 5000,
    10: 7500,
    11: 11000,
    12: 15500,
    13: 21000,
    14: 28000,
    15: 37000,
    16: 48000,
    17: 62000,
    18: 80000,
    19: 100000,
    20: 130000,
}

KORSAN_RÜTBELER = {
    1: "Acemi Denizci",
    3: "Tayfa",
    5: "Dümenci",
    7: "Çavuş",
    10: "Kaptan",
    13: "Amiral",
    15: "Korsan Lordu",
    18: "Denizlerin Hakimi",
    20: "Efsanevi Korsan",
}


# ================= VERİTABANI =================

def get_pirate(user_id):
    """Kullanıcının korsan verisini getir veya oluştur."""
    pirate = pirates_col.find_one({"user_id": user_id})
    if not pirate:
        pirate = {
            "user_id": user_id,
            "seviye": 1,
            "xp": 0,
            "gemi": "sandal",
            "gemi_hp": GEMİLER["sandal"]["hp"],
            "mürettebat": [],           # [{"tip": "tayfa", "isim": "Ali"}, ...]
            "yükseltmeler": {},          # {"top": 2, "zırh_plaka": 1, ...}
            "envanter": [],              # ["poseidon_mızrağı", "hayalet_pusula", ...]
            "sefer": None,               # {"bölge": "açık_deniz", "başlangıç": timestamp, "bitiş": timestamp}
            "toplam_sefer": 0,
            "toplam_yağma": 0,
            "toplam_batırılan": 0,
            "pvp_galibiyet": 0,
            "pvp_mağlubiyet": 0,
            "koruma_süresi": 0,          # PvP koruma bitiş zamanı (timestamp)
        }
        pirates_col.insert_one(pirate)

    # Eski veriler için alan kontrolü
    if "yükseltmeler" not in pirate:
        pirate["yükseltmeler"] = {}
    if "envanter" not in pirate:
        pirate["envanter"] = []
    if "koruma_süresi" not in pirate:
        pirate["koruma_süresi"] = 0
    if "pvp_galibiyet" not in pirate:
        pirate["pvp_galibiyet"] = 0
    if "pvp_mağlubiyet" not in pirate:
        pirate["pvp_mağlubiyet"] = 0
    return pirate


def save_pirate(pirate):
    """Korsan verisini kaydet."""
    pirates_col.update_one({"user_id": pirate["user_id"]}, {"$set": pirate}, upsert=True)


def get_pirate_level(xp):
    """XP'ye göre korsan seviyesini hesapla."""
    seviye = 1
    for lvl, gereksinim in sorted(KORSAN_SEVİYE_GEREKSİNİMLERİ.items()):
        if xp >= gereksinim:
            seviye = lvl
        else:
            break
    return seviye


def get_rütbe(seviye):
    """Seviyeye göre rütbe ismi."""
    rütbe = "Acemi Denizci"
    for lvl, isim in sorted(KORSAN_RÜTBELER.items()):
        if seviye >= lvl:
            rütbe = isim
        else:
            break
    return rütbe


def hesapla_gemi_statları(pirate):
    """Gemi statlarını yükseltmeler ve eşyalar dahil hesapla."""
    gemi = GEMİLER[pirate["gemi"]]
    statlar = {
        "hp": gemi["hp"],
        "saldırı": gemi["saldırı"],
        "zırh": gemi["zırh"],
        "hız": gemi["hız"],
        "kargo": gemi["kargo"],
        "mürettebat_max": gemi["mürettebat_max"],
    }

    # Yükseltme bonusları
    for yükseltme_id, seviye in pirate.get("yükseltmeler", {}).items():
        yükseltme = GEMİ_YÜKSELTMELERİ.get(yükseltme_id)
        if yükseltme:
            for stat, bonus in yükseltme["bonus_per_level"].items():
                if stat in statlar:
                    statlar[stat] += bonus * seviye

    # Mürettebat bonusları
    for üye in pirate.get("mürettebat", []):
        mürettebat = MÜRETTEBAT.get(üye["tip"])
        if mürettebat:
            statlar["saldırı"] += mürettebat["saldırı_bonus"]
            statlar["zırh"] += mürettebat["savunma_bonus"]

    # Nadir eşya bonusları
    for eşya_id in pirate.get("envanter", []):
        eşya = NADİR_EŞYALAR.get(eşya_id)
        if eşya:
            for stat, bonus in eşya["bonus"].items():
                if stat in statlar:
                    statlar[stat] += bonus

    return statlar


def hesapla_xp_bonus(pirate):
    """Eşyalardan gelen XP bonus yüzdesi."""
    bonus = 0
    for eşya_id in pirate.get("envanter", []):
        eşya = NADİR_EŞYALAR.get(eşya_id)
        if eşya:
            bonus += eşya["bonus"].get("xp_bonus", 0)
    # Kaptan yardımcısı bonusu
    for üye in pirate.get("mürettebat", []):
        if üye["tip"] == "kaptan_yardımcısı":
            bonus += 20
    return bonus


def hesapla_hazine_bonus(pirate):
    """Eşyalardan gelen hazine bonus yüzdesi."""
    bonus = 0
    for eşya_id in pirate.get("envanter", []):
        eşya = NADİR_EŞYALAR.get(eşya_id)
        if eşya:
            bonus += eşya["bonus"].get("hazine_bonus", 0)
    # Silahçı bonusu
    for üye in pirate.get("mürettebat", []):
        if üye["tip"] == "silahçı":
            bonus += 15
    return bonus


# ================= KOMUTLAR =================

@bot.command(name="gemi", aliases=["ship", "korsan"])
async def gemi(ctx):
    """Gemi durumunu ve korsan profilini göster."""
    pirate = get_pirate(ctx.author.id)
    seviye = get_pirate_level(pirate["xp"])
    pirate["seviye"] = seviye
    save_pirate(pirate)

    gemi_bilgi = GEMİLER[pirate["gemi"]]
    statlar = hesapla_gemi_statları(pirate)
    rütbe = get_rütbe(seviye)
    now = time.time()

    # Seviye ilerleme
    sonraki_seviye = seviye + 1
    sonraki_gereksinim = KORSAN_SEVİYE_GEREKSİNİMLERİ.get(sonraki_seviye)

    if sonraki_gereksinim:
        önceki_gereksinim = KORSAN_SEVİYE_GEREKSİNİMLERİ.get(seviye, 0)
        ilerleme = pirate["xp"] - önceki_gereksinim
        gerekli = sonraki_gereksinim - önceki_gereksinim
        pct = min(ilerleme / gerekli, 1.0) if gerekli > 0 else 1.0
        filled = int(pct * 15)
        bar = "🟦" * filled + "⬛" * (15 - filled)
        seviye_text = f"Seviye **{seviye}** `[{bar}]` {pirate['xp']}/{sonraki_gereksinim} XP"
    else:
        seviye_text = f"Seviye **{seviye}** (MAKSİMUM!)"

    # Gemi HP durumu
    hp_pct = pirate["gemi_hp"] / statlar["hp"]
    if hp_pct > 0.7:
        hp_emoji = "🟢"
    elif hp_pct > 0.3:
        hp_emoji = "🟡"
    else:
        hp_emoji = "🔴"

    # Mürettebat listesi
    mürettebat_text = ""
    if pirate["mürettebat"]:
        mürettebat_sayı = {}
        for üye in pirate["mürettebat"]:
            tip = üye["tip"]
            mürettebat_sayı[tip] = mürettebat_sayı.get(tip, 0) + 1
        for tip, sayı in mürettebat_sayı.items():
            m = MÜRETTEBAT[tip]
            mürettebat_text += f"{m['emoji']} {m['isim']}: **{sayı}**\n"
    else:
        mürettebat_text = "Kimse yok, yalnızsın!"

    # Envanter
    envanter_text = ""
    if pirate["envanter"]:
        for eşya_id in pirate["envanter"]:
            eşya = NADİR_EŞYALAR.get(eşya_id)
            if eşya:
                envanter_text += f"{eşya['emoji']} {eşya['isim']}\n"
    else:
        envanter_text = "Boş."

    # Sefer durumu
    sefer_text = ""
    if pirate.get("sefer"):
        sefer = pirate["sefer"]
        kalan = sefer["bitiş"] - now
        if kalan > 0:
            dk = int(kalan) // 60
            sn = int(kalan) % 60
            bölge = BÖLGELER[sefer["bölge"]]
            sefer_text = f"\n{bölge['emoji']} **Seferde:** {bölge['isim']} -- {dk}dk {sn}sn kaldı"
        else:
            sefer_text = "\nSefer tamamlandı! `!dön` ile geri dön."

    # Yükseltme bilgisi
    yükseltme_text = ""
    for yük_id, yük in GEMİ_YÜKSELTMELERİ.items():
        mevcut = pirate.get("yükseltmeler", {}).get(yük_id, 0)
        yükseltme_text += f"{yük['emoji']} {yük['isim']}: **Lv.{mevcut}/{yük['max_seviye']}**\n"

    embed = discord.Embed(
        title=f"{gemi_bilgi['emoji']} {ctx.author.display_name} -- {rütbe}",
        description=(
            f"{seviye_text}\n"
            f"{'━' * 30}\n\n"
            f"**Gemi: {gemi_bilgi['emoji']} {gemi_bilgi['isim']}**\n"
            f"{hp_emoji} HP: **{pirate['gemi_hp']}/{statlar['hp']}**\n"
            f"Saldırı: **{statlar['saldırı']}** | Zırh: **{statlar['zırh']}** | Hız: **{statlar['hız']}**\n"
            f"Kargo: **{statlar['kargo']}** | Mürettebat: **{len(pirate['mürettebat'])}/{statlar['mürettebat_max']}**\n"
            f"{sefer_text}\n\n"
            f"**Yükseltmeler:**\n{yükseltme_text}\n"
            f"**Mürettebat:**\n{mürettebat_text}\n"
            f"**Nadir Eşyalar:**\n{envanter_text}"
        ),
        color=discord.Color.dark_blue(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(
        name="İstatistikler",
        value=(
            f"Toplam sefer: **{pirate.get('toplam_sefer', 0)}**\n"
            f"Toplam yağma: **{pirate.get('toplam_yağma', 0):,}** VisoCoin\n"
            f"Batırılan gemi: **{pirate.get('toplam_batırılan', 0)}**\n"
            f"PvP: **{pirate.get('pvp_galibiyet', 0)}G** / **{pirate.get('pvp_mağlubiyet', 0)}M**"
        ),
        inline=False
    )
    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="gemiler", aliases=["ships", "gemilistesi"])
async def gemiler(ctx):
    """Satın alınabilecek gemileri listele."""
    pirate = get_pirate(ctx.author.id)
    seviye = get_pirate_level(pirate["xp"])

    embed = discord.Embed(
        title="Gemi Mağazası",
        description="Gemi satın almak için: `!gemial <gemi>`",
        color=discord.Color.dark_blue(),
        timestamp=datetime.now(timezone.utc)
    )

    for gemi_id, gemi in GEMİLER.items():
        durum = "MEVCUT GEMİN" if pirate["gemi"] == gemi_id else (
            "Satın alabilirsin" if seviye >= gemi["seviye_gereksinim"] else
            f"Seviye {gemi['seviye_gereksinim']} gerekli"
        )
        fiyat_text = "Ücretsiz" if gemi["fiyat"] == 0 else f"{gemi['fiyat']:,} VisoCoin"

        embed.add_field(
            name=f"{gemi['emoji']} {gemi['isim']} (`{gemi_id}`)",
            value=(
                f"Fiyat: **{fiyat_text}**\n"
                f"HP: **{gemi['hp']}** | Saldırı: **{gemi['saldırı']}** | Zırh: **{gemi['zırh']}**\n"
                f"Hız: **{gemi['hız']}** | Kargo: **{gemi['kargo']}** | Mürettebat: **{gemi['mürettebat_max']}**\n"
                f"Gereksinim: Seviye **{gemi['seviye_gereksinim']}** | {durum}"
            ),
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name="gemial", aliases=["buyship", "gemisatınal"])
async def gemial(ctx, gemi_id: str = None):
    """Yeni gemi satın al."""
    user_id = ctx.author.id

    if gemi_id is None:
        embed = discord.Embed(
            description="Kullanım: `!gemial <gemi>`\nGemileri görmek için: `!gemiler`",
            color=discord.Color.blue()
        )
        return await ctx.send(embed=embed)

    gemi_id = gemi_id.lower().strip()

    if gemi_id not in GEMİLER:
        embed = discord.Embed(description="Böyle bir gemi yok! `!gemiler` ile listeye bak.", color=discord.Color.red())
        return await ctx.send(embed=embed)

    pirate = get_pirate(user_id)
    seviye = get_pirate_level(pirate["xp"])
    gemi = GEMİLER[gemi_id]

    if pirate["gemi"] == gemi_id:
        embed = discord.Embed(description="Zaten bu gemiye sahipsin!", color=discord.Color.orange())
        return await ctx.send(embed=embed)

    if seviye < gemi["seviye_gereksinim"]:
        embed = discord.Embed(
            description=f"Bu gemi için seviye **{gemi['seviye_gereksinim']}** gerekli! Seviyen: **{seviye}**",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if pirate.get("sefer"):
        now = time.time()
        if pirate["sefer"]["bitiş"] > now:
            embed = discord.Embed(description="Seferdeyken gemi alamazsın! Önce `!dön` ile geri dön.", color=discord.Color.red())
            return await ctx.send(embed=embed)

    user = get_user(user_id)
    if user["money"] < gemi["fiyat"]:
        embed = discord.Embed(
            description=f"Yetersiz bakiye! {gemi['isim']} için **{gemi['fiyat']:,}** VisoCoin gerekiyor.\nBakiyen: **{user['money']:,}** VisoCoin",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Eski gemiyi sat (yarı fiyatına)
    eski_gemi = GEMİLER[pirate["gemi"]]
    iade = eski_gemi["fiyat"] // 2

    user["money"] -= gemi["fiyat"]
    user["money"] += iade
    save_user(user)

    pirate["gemi"] = gemi_id
    pirate["gemi_hp"] = gemi["hp"]
    # Mürettebat fazlasını düşür
    if len(pirate["mürettebat"]) > gemi["mürettebat_max"]:
        pirate["mürettebat"] = pirate["mürettebat"][:gemi["mürettebat_max"]]
    save_pirate(pirate)

    embed = discord.Embed(
        title=f"{gemi['emoji']} Yeni Gemi Alındı!",
        description=(
            f"{ctx.author.mention}, **{gemi['isim']}** satın aldın!\n\n"
            f"Eski gemi ({eski_gemi['isim']}) iade: **+{iade:,}** VisoCoin\n"
            f"Maliyet: **{gemi['fiyat']:,}** VisoCoin\n"
            f"Bakiye: **{user['money']:,}** VisoCoin\n\n"
            f"HP: **{gemi['hp']}** | Saldırı: **{gemi['saldırı']}** | Zırh: **{gemi['zırh']}**"
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


@bot.command(name="harita", aliases=["regions"])
async def bölgeler(ctx):
    """Sefere çıkılabilecek bölgeleri listele."""
    pirate = get_pirate(ctx.author.id)
    seviye = get_pirate_level(pirate["xp"])

    embed = discord.Embed(
        title="Deniz Haritası",
        description="Sefere çıkmak için: `!sefer <bölge>`",
        color=discord.Color.dark_teal(),
        timestamp=datetime.now(timezone.utc)
    )

    for bölge_id, bölge in BÖLGELER.items():
        kilit = seviye < bölge["seviye_min"]
        dk = bölge["sefer_süresi"] // 60

        if kilit:
            durum = f"Seviye {bölge['seviye_min']} gerekli"
        else:
            durum = "Keşfedilebilir"

        embed.add_field(
            name=f"{bölge['emoji']} {bölge['isim']} (`{bölge_id}`)",
            value=(
                f"Süre: **{dk}** dakika | Tehlike: **%{bölge['tehlike']}**\n"
                f"Hazine: **{bölge['hazine_min']:,}-{bölge['hazine_max']:,}** VisoCoin\n"
                f"XP: **{bölge['xp_min']}-{bölge['xp_max']}** | Nadir eşya: **%{bölge['nadir_eşya_şansı']}**\n"
                f"Durum: {durum}"
            ),
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name="sefer", aliases=["sail", "yolculuk", "keşif"])
async def sefer(ctx, bölge_id: str = None):
    """Sefere çık."""
    user_id = ctx.author.id

    if bölge_id is None:
        embed = discord.Embed(
            description="Kullanım: `!sefer <bölge>`\nBölgeleri görmek için: `!denizler`",
            color=discord.Color.blue()
        )
        return await ctx.send(embed=embed)

    bölge_id = bölge_id.lower().strip()

    if bölge_id not in BÖLGELER:
        embed = discord.Embed(description="Böyle bir bölge yok! `!denizler` ile haritaya bak.", color=discord.Color.red())
        return await ctx.send(embed=embed)

    pirate = get_pirate(user_id)
    seviye = get_pirate_level(pirate["xp"])
    bölge = BÖLGELER[bölge_id]
    now = time.time()

    # Zaten seferde mi?
    if pirate.get("sefer"):
        if pirate["sefer"]["bitiş"] > now:
            kalan = int(pirate["sefer"]["bitiş"] - now)
            dk = kalan // 60
            sn = kalan % 60
            embed = discord.Embed(
                description=f"Zaten seferdesin! Kalan: **{dk}dk {sn}sn**\nGeri dönmek için: `!dön`",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

    # Seviye kontrolü
    if seviye < bölge["seviye_min"]:
        embed = discord.Embed(
            description=f"Bu bölge için seviye **{bölge['seviye_min']}** gerekli! Seviyen: **{seviye}**",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Gemi HP kontrolü
    if pirate["gemi_hp"] <= 0:
        embed = discord.Embed(
            description="Gemin hasarlı! Önce `!onar` ile tamir et.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    # Hız bonusu ile süre hesapla
    statlar = hesapla_gemi_statları(pirate)
    hız_çarpan = max(0.5, 1 - (statlar["hız"] - 3) * 0.05)  # Her hız puanı %5 azaltır, min %50
    gerçek_süre = int(bölge["sefer_süresi"] * hız_çarpan)

    # Seferi başlat
    pirate["sefer"] = {
        "bölge": bölge_id,
        "başlangıç": now,
        "bitiş": now + gerçek_süre,
    }
    save_pirate(pirate)

    dk = gerçek_süre // 60
    sn = gerçek_süre % 60

    embed = discord.Embed(
        title=f"{bölge['emoji']} Sefere Çıkıldı!",
        description=(
            f"{ctx.author.mention}, **{bölge['isim']}** bölgesine doğru yola çıktın!\n\n"
            f"Tahmini süre: **{dk}dk {sn}sn**\n"
            f"Tehlike seviyesi: **%{bölge['tehlike']}**\n"
            f"Nadir eşya şansı: **%{bölge['nadir_eşya_şansı']}**\n\n"
            f"Sefer bitince `!dön` ile sonuçları gör!"
        ),
        color=discord.Color.dark_teal(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="dön", aliases=["return", "geri", "dönüş"])
async def dön(ctx):
    """Seferden geri dön ve sonuçları gör."""
    user_id = ctx.author.id
    pirate = get_pirate(user_id)
    user = get_user(user_id)
    now = time.time()

    if not pirate.get("sefer"):
        embed = discord.Embed(
            description="Seferde değilsin! `!sefer <bölge>` ile yola çık.",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    sefer = pirate["sefer"]
    kalan = sefer["bitiş"] - now

    if kalan > 0:
        dk = int(kalan) // 60
        sn = int(kalan) % 60
        embed = discord.Embed(
            description=f"Sefer henüz bitmedi! Kalan: **{dk}dk {sn}sn**",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    # Sefer tamamlandı -- sonuçları hesapla
    bölge = BÖLGELER[sefer["bölge"]]
    statlar = hesapla_gemi_statları(pirate)
    xp_bonus = hesapla_xp_bonus(pirate)
    hazine_bonus = hesapla_hazine_bonus(pirate)

    olaylar_text = ""
    toplam_hazine = 0
    toplam_xp = 0
    toplam_hasar = 0
    bulunan_eşyalar = []

    # 2-4 rastgele olay
    olay_sayısı = random.randint(2, min(4, len(bölge["olaylar"])))
    seçilen_olaylar = random.sample(bölge["olaylar"], olay_sayısı)

    for olay in seçilen_olaylar:
        if olay["tip"] == "hazine":
            miktar = random.randint(olay["miktar_min"], olay["miktar_max"])
            if hazine_bonus > 0:
                miktar = int(miktar * (1 + hazine_bonus / 100))
            toplam_hazine += miktar
            olaylar_text += f"  {olay['isim']} **+{miktar:,}** VisoCoin\n"

        elif olay["tip"] == "xp":
            miktar = random.randint(olay["miktar_min"], olay["miktar_max"])
            if xp_bonus > 0:
                miktar = int(miktar * (1 + xp_bonus / 100))
            toplam_xp += miktar
            olaylar_text += f"  {olay['isim']} **+{miktar} XP**\n"

        elif olay["tip"] == "hasar":
            hasar = random.randint(olay["miktar_min"], olay["miktar_max"])
            # Zırh hasar azaltır
            hasar = max(1, hasar - statlar["zırh"] // 3)
            toplam_hasar += hasar
            olaylar_text += f"  {olay['isim']} **-{hasar} HP**\n"

        elif olay["tip"] == "savaş":
            düşman_güç = olay["düşman_güç"]
            savaş_gücü = statlar["saldırı"] + statlar["zırh"] // 2 + random.randint(-10, 10)

            if savaş_gücü >= düşman_güç:
                # Kazandık
                yağma = random.randint(bölge["hazine_min"], bölge["hazine_max"])
                if hazine_bonus > 0:
                    yağma = int(yağma * (1 + hazine_bonus / 100))
                toplam_hazine += yağma
                toplam_xp += random.randint(bölge["xp_min"], bölge["xp_max"])
                pirate["toplam_batırılan"] = pirate.get("toplam_batırılan", 0) + 1

                # Doktor varsa HP iyileştirme
                doktor_var = any(ü["tip"] == "doktor" for ü in pirate.get("mürettebat", []))
                iyileşme = 0
                if doktor_var:
                    iyileşme = int(statlar["hp"] * 0.15)

                olaylar_text += (
                    f"  {olay['isim']}\n"
                    f"    Savaş KAZANILDI! Yağma: **+{yağma:,}** VisoCoin"
                    f"{f', İyileşme: +{iyileşme} HP' if iyileşme > 0 else ''}\n"
                )
                if iyileşme > 0:
                    toplam_hasar -= iyileşme  # Negatif hasar = iyileşme
            else:
                # Kaybettik
                hasar = random.randint(20, 50)
                toplam_hasar += hasar
                olaylar_text += f"  {olay['isim']}\n    Savaş KAYBEDİLDİ! **-{hasar} HP**\n"

        elif olay["tip"] == "nadir_eşya":
            if random.randint(1, 100) <= bölge["nadir_eşya_şansı"]:
                mevcut_eşyalar = [e for e in NADİR_EŞYALAR if e not in pirate.get("envanter", [])]
                if mevcut_eşyalar:
                    yeni_eşya = random.choice(mevcut_eşyalar)
                    bulunan_eşyalar.append(yeni_eşya)
                    eşya = NADİR_EŞYALAR[yeni_eşya]
                    olaylar_text += f"  {olay['isim']}\n    NADİR EŞYA BULUNDU: {eşya['emoji']} **{eşya['isim']}**!\n"
                else:
                    olaylar_text += f"  {olay['isim']}\n    Ama zaten tüm eşyalara sahipsin.\n"
            else:
                # Eşya düşmedi ama XP versin
                xp_kazanç = random.randint(bölge["xp_min"], bölge["xp_max"])
                toplam_xp += xp_kazanç
                olaylar_text += f"  {olay['isim']}\n    Nadir eşya bulunamadı ama **+{xp_kazanç} XP** kazandın.\n"

    # Temel sefer ödülleri
    baz_hazine = random.randint(bölge["hazine_min"], bölge["hazine_max"])
    baz_xp = random.randint(bölge["xp_min"], bölge["xp_max"])
    if hazine_bonus > 0:
        baz_hazine = int(baz_hazine * (1 + hazine_bonus / 100))
    if xp_bonus > 0:
        baz_xp = int(baz_xp * (1 + xp_bonus / 100))
    toplam_hazine += baz_hazine
    toplam_xp += baz_xp

    # Sonuçları uygula
    user["money"] += toplam_hazine
    save_user(user)

    pirate["xp"] += toplam_xp
    pirate["gemi_hp"] = max(0, min(pirate["gemi_hp"] - toplam_hasar, statlar["hp"]))
    pirate["toplam_sefer"] = pirate.get("toplam_sefer", 0) + 1
    pirate["toplam_yağma"] = pirate.get("toplam_yağma", 0) + toplam_hazine
    pirate["sefer"] = None

    for eşya_id in bulunan_eşyalar:
        if eşya_id not in pirate["envanter"]:
            pirate["envanter"].append(eşya_id)

    eski_seviye = pirate.get("seviye", 1)
    yeni_seviye = get_pirate_level(pirate["xp"])
    pirate["seviye"] = yeni_seviye
    save_pirate(pirate)

    # Embed oluştur
    embed = discord.Embed(
        title=f"{bölge['emoji']} Sefer Tamamlandı -- {bölge['isim']}",
        description=(
            f"{ctx.author.mention}, seferden döndün!\n\n"
            f"**Olaylar:**\n{olaylar_text}\n"
            f"{'━' * 30}\n"
            f"**Sefer Özeti:**\n"
            f"Hazine: **+{toplam_hazine:,}** VisoCoin\n"
            f"XP: **+{toplam_xp}**\n"
            f"Gemi HP: **{pirate['gemi_hp']}/{statlar['hp']}**"
            f"{' (HASARLI!)' if pirate['gemi_hp'] < statlar['hp'] * 0.3 else ''}\n"
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

    # Seviye atlama
    if yeni_seviye > eski_seviye:
        yeni_rütbe = get_rütbe(yeni_seviye)
        level_embed = discord.Embed(
            title="Korsan Seviye Atladı!",
            description=(
                f"{ctx.author.mention}, seviyen **{yeni_seviye}** oldu!\n"
                f"Rütben: **{yeni_rütbe}**\n\n"
                f"Yeni gemiler ve bölgeler açılmış olabilir!"
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=level_embed)


@bot.command(name="onar", aliases=["repair", "tamir"])
async def onar(ctx):
    """Gemiyi onar."""
    user_id = ctx.author.id
    pirate = get_pirate(user_id)
    statlar = hesapla_gemi_statları(pirate)

    if pirate["gemi_hp"] >= statlar["hp"]:
        embed = discord.Embed(description="Gemin zaten tam HP'de!", color=discord.Color.green())
        return await ctx.send(embed=embed)

    # Seferdeyken onarılamaz
    now = time.time()
    if pirate.get("sefer") and pirate["sefer"]["bitiş"] > now:
        embed = discord.Embed(description="Seferdeyken onarım yapamazsın!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    eksik_hp = statlar["hp"] - pirate["gemi_hp"]
    onarım_maliyeti = eksik_hp * 3  # HP başına 3 VisoCoin

    # Onarım bonus kontrolü (deniz kızı gözyaşı)
    onarım_bonus = 0
    for eşya_id in pirate.get("envanter", []):
        eşya = NADİR_EŞYALAR.get(eşya_id)
        if eşya:
            onarım_bonus += eşya["bonus"].get("onarım_bonus", 0)
    if onarım_bonus > 0:
        onarım_maliyeti = int(onarım_maliyeti * (1 - onarım_bonus / 100))

    user = get_user(user_id)

    if user["money"] < onarım_maliyeti:
        embed = discord.Embed(
            description=f"Yetersiz bakiye! Onarım maliyeti: **{onarım_maliyeti:,}** VisoCoin\nBakiyen: **{user['money']:,}** VisoCoin",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= onarım_maliyeti
    save_user(user)

    pirate["gemi_hp"] = statlar["hp"]
    save_pirate(pirate)

    embed = discord.Embed(
        title="Gemi Onarıldı!",
        description=(
            f"{ctx.author.mention}, gemin tamamen onarıldı!\n\n"
            f"Onarım maliyeti: **{onarım_maliyeti:,}** VisoCoin"
            f"{f' (İndirim: %{onarım_bonus})' if onarım_bonus > 0 else ''}\n"
            f"HP: **{pirate['gemi_hp']}/{statlar['hp']}**\n"
            f"Bakiye: **{user['money']:,}** VisoCoin"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


@bot.command(name="yükselt", aliases=["upgrade", "geliştir"])
async def yükselt(ctx, yükseltme_id: str = None):
    """Gemi yükseltmesi yap."""
    user_id = ctx.author.id

    if yükseltme_id is None:
        embed = discord.Embed(
            title="Gemi Yükseltmeleri",
            description="Kullanım: `!yükselt <yükseltme>`\n\n",
            color=discord.Color.dark_blue(),
            timestamp=datetime.now(timezone.utc)
        )
        pirate = get_pirate(user_id)
        for yük_id, yük in GEMİ_YÜKSELTMELERİ.items():
            mevcut = pirate.get("yükseltmeler", {}).get(yük_id, 0)
            if mevcut >= yük["max_seviye"]:
                fiyat_text = "MAKSİMUM"
            else:
                fiyat = yük["fiyat_baz"] * (2 ** mevcut)
                fiyat_text = f"{fiyat:,} VisoCoin"

            bonus_text = ", ".join([f"{stat}: +{val}" for stat, val in yük["bonus_per_level"].items()])

            embed.add_field(
                name=f"{yük['emoji']} {yük['isim']} (`{yük_id}`) -- Lv.{mevcut}/{yük['max_seviye']}",
                value=f"Fiyat: **{fiyat_text}**\nSeviye başına: {bonus_text}",
                inline=False
            )
        return await ctx.send(embed=embed)

    yükseltme_id = yükseltme_id.lower().strip()

    if yükseltme_id not in GEMİ_YÜKSELTMELERİ:
        embed = discord.Embed(description="Böyle bir yükseltme yok! `!yükselt` ile listeye bak.", color=discord.Color.red())
        return await ctx.send(embed=embed)

    pirate = get_pirate(user_id)
    yükseltme = GEMİ_YÜKSELTMELERİ[yükseltme_id]
    mevcut = pirate.get("yükseltmeler", {}).get(yükseltme_id, 0)

    if mevcut >= yükseltme["max_seviye"]:
        embed = discord.Embed(description=f"{yükseltme['isim']} zaten maksimum seviyede!", color=discord.Color.orange())
        return await ctx.send(embed=embed)

    fiyat = yükseltme["fiyat_baz"] * (2 ** mevcut)
    user = get_user(user_id)

    if user["money"] < fiyat:
        embed = discord.Embed(
            description=f"Yetersiz bakiye! Yükseltme maliyeti: **{fiyat:,}** VisoCoin",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= fiyat
    save_user(user)

    pirate["yükseltmeler"][yükseltme_id] = mevcut + 1
    save_pirate(pirate)

    yeni_seviye = mevcut + 1
    bonus_text = ", ".join([f"{stat}: +{val * yeni_seviye}" for stat, val in yükseltme["bonus_per_level"].items()])

    embed = discord.Embed(
        title=f"{yükseltme['emoji']} Yükseltme Tamamlandı!",
        description=(
            f"{ctx.author.mention}, **{yükseltme['isim']}** Lv.**{yeni_seviye}** oldu!\n\n"
            f"Maliyet: **{fiyat:,}** VisoCoin\n"
            f"Toplam bonus: {bonus_text}\n"
            f"Bakiye: **{user['money']:,}** VisoCoin"
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


@bot.command(name="mürettebatal", aliases=["hirecrew", "tayfaal"])
async def mürettebatal(ctx, mürettebat_id: str = None):
    """Mürettebat kirala."""
    user_id = ctx.author.id

    if mürettebat_id is None:
        embed = discord.Embed(
            title="Mürettebat Kiralama",
            description="Kullanım: `!mürettebatal <tip>`\n\n",
            color=discord.Color.dark_blue(),
            timestamp=datetime.now(timezone.utc)
        )
        for m_id, m in MÜRETTEBAT.items():
            embed.add_field(
                name=f"{m['emoji']} {m['isim']} (`{m_id}`)",
                value=(
                    f"Fiyat: **{m['fiyat']:,}** VisoCoin\n"
                    f"Saldırı: **+{m['saldırı_bonus']}** | Savunma: **+{m['savunma_bonus']}**\n"
                    f"Özel: {m['özel'] or 'Yok'}"
                ),
                inline=True
            )
        return await ctx.send(embed=embed)

    mürettebat_id = mürettebat_id.lower().strip()

    if mürettebat_id not in MÜRETTEBAT:
        embed = discord.Embed(description="Böyle bir mürettebat tipi yok! `!mürettebatal` ile listeye bak.", color=discord.Color.red())
        return await ctx.send(embed=embed)

    pirate = get_pirate(user_id)
    statlar = hesapla_gemi_statları(pirate)
    mürettebat = MÜRETTEBAT[mürettebat_id]

    if len(pirate["mürettebat"]) >= statlar["mürettebat_max"]:
        embed = discord.Embed(
            description=f"Mürettebat kapasiten dolu! ({len(pirate['mürettebat'])}/{statlar['mürettebat_max']})\nDaha büyük gemi al veya `!mürettebatçıkar` ile birisini çıkar.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user = get_user(user_id)
    if user["money"] < mürettebat["fiyat"]:
        embed = discord.Embed(
            description=f"Yetersiz bakiye! Maliyet: **{mürettebat['fiyat']:,}** VisoCoin",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    user["money"] -= mürettebat["fiyat"]
    save_user(user)

    # Rastgele isim
    isimler = ["Ali", "Veli", "Hasan", "Mehmet", "Yusuf", "Ahmet", "Kara", "Fırtına", "Demir", "Bulut",
               "Rüzgar", "Deniz", "Dalga", "Yıldız", "Gökhan", "Bora", "Ozan", "Atlas", "Reis", "Kurt"]
    isim = random.choice(isimler)

    pirate["mürettebat"].append({"tip": mürettebat_id, "isim": isim})
    save_pirate(pirate)

    embed = discord.Embed(
        title=f"{mürettebat['emoji']} Yeni Mürettebat!",
        description=(
            f"{ctx.author.mention}, **{isim}** ({mürettebat['isim']}) gemiye katıldı!\n\n"
            f"Maliyet: **{mürettebat['fiyat']:,}** VisoCoin\n"
            f"Mürettebat: **{len(pirate['mürettebat'])}/{statlar['mürettebat_max']}**\n"
            f"Bakiye: **{user['money']:,}** VisoCoin"
        ),
        color=discord.Color.dark_blue(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


@bot.command(name="mürettebatçıkar", aliases=["firecrew", "tayfaçıkar"])
async def mürettebatçıkar(ctx, index: int = None):
    """Mürettebattan birini çıkar."""
    user_id = ctx.author.id
    pirate = get_pirate(user_id)

    if not pirate["mürettebat"]:
        embed = discord.Embed(description="Mürettebatın boş!", color=discord.Color.orange())
        return await ctx.send(embed=embed)

    if index is None:
        text = ""
        for i, üye in enumerate(pirate["mürettebat"], 1):
            m = MÜRETTEBAT[üye["tip"]]
            text += f"**{i}.** {m['emoji']} {üye['isim']} ({m['isim']})\n"
        embed = discord.Embed(
            title="Mürettebat Çıkarma",
            description=f"Kullanım: `!mürettebatçıkar <numara>`\n\n{text}",
            color=discord.Color.dark_blue()
        )
        return await ctx.send(embed=embed)

    if index < 1 or index > len(pirate["mürettebat"]):
        embed = discord.Embed(description=f"Geçersiz numara! 1-{len(pirate['mürettebat'])} arası gir.", color=discord.Color.red())
        return await ctx.send(embed=embed)

    çıkarılan = pirate["mürettebat"].pop(index - 1)
    save_pirate(pirate)

    m = MÜRETTEBAT[çıkarılan["tip"]]
    embed = discord.Embed(
        title="Mürettebat Çıkarıldı",
        description=f"**{çıkarılan['isim']}** ({m['isim']}) gemiden ayrıldı.",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


@bot.command(name="yağmala", aliases=["raid"])
async def yağmala(ctx, hedef: discord.Member = None):
    """Başka bir oyuncunun gemisine saldır (PvP)."""
    user_id = ctx.author.id

    if hedef is None:
        embed = discord.Embed(
            description="Kullanım: `!yağmala @kullanıcı`\nBaşka bir korsanın gemisine saldır!",
            color=discord.Color.blue()
        )
        return await ctx.send(embed=embed)

    if hedef.id == user_id:
        embed = discord.Embed(description="Kendi gemini yağmalayamazsın!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    if hedef.bot:
        embed = discord.Embed(description="Botlara saldıramazsın!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    saldıran = get_pirate(user_id)
    savunan = get_pirate(hedef.id)
    now = time.time()

    # Seferde mi kontrol
    if saldıran.get("sefer") and saldıran["sefer"]["bitiş"] > now:
        embed = discord.Embed(description="Seferdeyken saldıramazsın!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    if savunan.get("sefer") and savunan["sefer"]["bitiş"] > now:
        embed = discord.Embed(description="Hedef seferde, saldıramazsın!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    # HP kontrol
    if saldıran["gemi_hp"] <= 0:
        embed = discord.Embed(description="Gemin hasarlı! Önce `!onar` ile tamir et.", color=discord.Color.red())
        return await ctx.send(embed=embed)

    # PvP koruma kontrolü
    if savunan.get("koruma_süresi", 0) > now:
        kalan = int(savunan["koruma_süresi"] - now)
        dk = kalan // 60
        embed = discord.Embed(
            description=f"Hedef koruma altında! Kalan: **{dk}** dakika",
            color=discord.Color.orange()
        )
        return await ctx.send(embed=embed)

    # Savaş hesaplaması
    s_statlar = hesapla_gemi_statları(saldıran)
    d_statlar = hesapla_gemi_statları(savunan)

    # Topçu kritik vuruş
    topçu_var = any(ü["tip"] == "topçu" for ü in saldıran.get("mürettebat", []))
    kritik = topçu_var and random.randint(1, 100) <= 10

    s_güç = s_statlar["saldırı"] + s_statlar["hız"] * 2 + random.randint(-15, 15)
    d_güç = d_statlar["saldırı"] + d_statlar["zırh"] * 2 + random.randint(-15, 15)

    if kritik:
        s_güç = int(s_güç * 1.5)

    saldıran_user = get_user(user_id)
    savunan_user = get_user(hedef.id)

    if s_güç > d_güç:
        # Saldıran kazandı
        yağma_oran = random.uniform(0.05, 0.15)
        yağma = int(savunan_user["money"] * yağma_oran)
        yağma = max(yağma, 100)  # Min 100

        saldıran_user["money"] += yağma
        savunan_user["money"] = max(0, savunan_user["money"] - yağma)
        save_user(saldıran_user)
        save_user(savunan_user)

        s_hasar = random.randint(10, 25)
        d_hasar = random.randint(25, 50)
        saldıran["gemi_hp"] = max(0, saldıran["gemi_hp"] - s_hasar)
        savunan["gemi_hp"] = max(0, savunan["gemi_hp"] - d_hasar)
        saldıran["pvp_galibiyet"] = saldıran.get("pvp_galibiyet", 0) + 1
        savunan["pvp_mağlubiyet"] = savunan.get("pvp_mağlubiyet", 0) + 1
        saldıran["toplam_yağma"] = saldıran.get("toplam_yağma", 0) + yağma

        xp_kazanç = random.randint(30, 80)
        saldıran["xp"] += xp_kazanç

        # Kaybedene 10 dk koruma
        savunan["koruma_süresi"] = now + 600

        save_pirate(saldıran)
        save_pirate(savunan)

        embed = discord.Embed(
            title="Yağma Başarılı!",
            description=(
                f"{ctx.author.mention} vs {hedef.mention}\n\n"
                f"{'KRİTİK VURUŞ! ' if kritik else ''}"
                f"**{ctx.author.display_name}** savaşı kazandı!\n\n"
                f"Yağma: **+{yağma:,}** VisoCoin\n"
                f"XP: **+{xp_kazanç}**\n"
                f"Gemin aldığı hasar: **-{s_hasar} HP**\n"
                f"Düşman gemisi hasarı: **-{d_hasar} HP**"
            ),
            color=discord.Color.dark_gold(),
            timestamp=datetime.now(timezone.utc)
        )
    else:
        # Savunan kazandı
        s_hasar = random.randint(25, 50)
        d_hasar = random.randint(5, 15)
        saldıran["gemi_hp"] = max(0, saldıran["gemi_hp"] - s_hasar)
        savunan["gemi_hp"] = max(0, savunan["gemi_hp"] - d_hasar)
        saldıran["pvp_mağlubiyet"] = saldıran.get("pvp_mağlubiyet", 0) + 1
        savunan["pvp_galibiyet"] = savunan.get("pvp_galibiyet", 0) + 1

        # Saldırana 5 dk koruma
        saldıran["koruma_süresi"] = now + 300

        save_pirate(saldıran)
        save_pirate(savunan)

        embed = discord.Embed(
            title="Yağma Başarısız!",
            description=(
                f"{ctx.author.mention} vs {hedef.mention}\n\n"
                f"**{hedef.display_name}** savaşı kazandı!\n\n"
                f"Gemin aldığı hasar: **-{s_hasar} HP**\n"
                f"Saldırı geri püskürtüldü!"
            ),
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )

    await ctx.send(embed=embed)


@bot.command(name="korsaneşyasat", aliases=["piratesellitem"])
async def korsaneşyasat(ctx, eşya_id: str = None):
    """Nadir eşya sat."""
    user_id = ctx.author.id

    if eşya_id is None:
        pirate = get_pirate(user_id)
        if not pirate["envanter"]:
            embed = discord.Embed(description="Envanterin boş!", color=discord.Color.orange())
            return await ctx.send(embed=embed)

        text = ""
        for e_id in pirate["envanter"]:
            eşya = NADİR_EŞYALAR.get(e_id)
            if eşya:
                text += f"{eşya['emoji']} **{eşya['isim']}** (`{e_id}`) -- {eşya['satış_fiyat']:,} VisoCoin\n"

        embed = discord.Embed(
            title="Eşya Satışı",
            description=f"Kullanım: `!eşyasat <eşya_id>`\n\n{text}",
            color=discord.Color.dark_blue()
        )
        return await ctx.send(embed=embed)

    eşya_id = eşya_id.lower().strip()
    pirate = get_pirate(user_id)

    if eşya_id not in pirate["envanter"]:
        embed = discord.Embed(description="Bu eşya envaterinde yok!", color=discord.Color.red())
        return await ctx.send(embed=embed)

    eşya = NADİR_EŞYALAR[eşya_id]
    pirate["envanter"].remove(eşya_id)
    save_pirate(pirate)

    user = get_user(user_id)
    user["money"] += eşya["satış_fiyat"]
    save_user(user)

    embed = discord.Embed(
        title="Eşya Satıldı!",
        description=(
            f"{ctx.author.mention}, {eşya['emoji']} **{eşya['isim']}** satıldı!\n\n"
            f"Kazanç: **+{eşya['satış_fiyat']:,}** VisoCoin\n"
            f"Bakiye: **{user['money']:,}** VisoCoin"
        ),
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


@bot.command(name="korsansıralama", aliases=["pirateleaderboard", "korsantop"])
async def korsansıralama(ctx):
    """Korsan liderlik tablosu."""
    tüm_korsanlar = list(pirates_col.find().sort("xp", -1).limit(10))

    if not tüm_korsanlar:
        embed = discord.Embed(description="Henüz korsan yok!", color=discord.Color.dark_blue())
        return await ctx.send(embed=embed)

    sıralama_text = ""
    medals = ["🥇", "🥈", "🥉"]

    for i, p in enumerate(tüm_korsanlar):
        try:
            user = await bot.fetch_user(p["user_id"])
            isim = user.display_name
        except Exception:
            isim = f"Korsan #{p['user_id']}"

        seviye = get_pirate_level(p.get("xp", 0))
        rütbe = get_rütbe(seviye)
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        gemi_emoji = GEMİLER.get(p.get("gemi", "sandal"), GEMİLER["sandal"])["emoji"]

        sıralama_text += (
            f"{medal} {gemi_emoji} **{isim}** -- Lv.{seviye} {rütbe}\n"
            f"   XP: {p.get('xp', 0):,} | Yağma: {p.get('toplam_yağma', 0):,} | "
            f"PvP: {p.get('pvp_galibiyet', 0)}G/{p.get('pvp_mağlubiyet', 0)}M\n\n"
        )

    embed = discord.Embed(
        title="Korsan Sıralaması",
        description=sıralama_text,
        color=discord.Color.dark_gold(),
        timestamp=datetime.now(timezone.utc)
    )
    await ctx.send(embed=embed)


# ================= LONCA BOSSLARI =================

LONCA_BOSSLARI = {
    1: {"isim": "Lonca Trollü", "emoji": "🧌", "can": 2000, "saldırı": 35, "savunma": 20, "xp": 300, "altın": 2000, "gerekli_üye": 2},
    2: {"isim": "Karanlık Dev", "emoji": "👹", "can": 5000, "saldırı": 55, "savunma": 35, "xp": 600, "altın": 5000, "gerekli_üye": 3},
    3: {"isim": "Fırtına Tanrısı", "emoji": "⛈️", "can": 10000, "saldırı": 80, "savunma": 50, "xp": 1200, "altın": 12000, "gerekli_üye": 4},
    4: {"isim": "Kaos Lordu", "emoji": "🌀", "can": 20000, "saldırı": 120, "savunma": 70, "xp": 2500, "altın": 25000, "gerekli_üye": 5},
}

# ================= HAZİNE TİPLERİ =================

HAZINE_TIPLERI = {
    "altın_sandığı": {
        "isim": "Altın Sandığı",
        "emoji": "💰",
        "açıklama": "İçi altınla dolu bir sandık!",
        "altın_min": 200,
        "altın_max": 800,
        "şans": 40,
    },
    "efsanevi_sandık": {
        "isim": "Efsanevi Sandık",
        "emoji": "✨",
        "açıklama": "Nadir eşyalar içerebilir!",
        "altın_min": 100,
        "altın_max": 300,
        "eşya_şansı": 60,
        "şans": 25,
    },
    "tuzak_odası": {
        "isim": "Tuzak Odası",
        "emoji": "💀",
        "açıklama": "Dikkat! Tuzaklar var!",
        "hasar_min": 20,
        "hasar_max": 50,
        "altın_min": 50,
        "altın_max": 150,
        "şans": 20,
    },
    "bilmece_odası": {
        "isim": "Bilmece Odası",
        "emoji": "🧩",
        "açıklama": "Bilmeceyi çöz, hazineyi al!",
        "altın_min": 300,
        "altın_max": 1000,
        "xp_bonus": 50,
        "şans": 10,
    },
    "ejderha_hazinesi": {
        "isim": "Ejderha Hazinesi",
        "emoji": "🐲",
        "açıklama": "Ejderhanın gizli hazinesi!",
        "altın_min": 500,
        "altın_max": 2000,
        "eşya_şansı": 80,
        "şans": 5,
    },
}

BILMECELER = [
    {"soru": "Gündüz uyur, gece uyanır. Nedir?", "cevap": ["ay", "yıldız"]},
    {"soru": "Ne kadar koşarsan koş, onu geçemezsin. Nedir?", "cevap": ["gölge", "gölgen"]},
    {"soru": "Dili var konuşamaz, ayağı var yürüyemez. Nedir?", "cevap": ["ayakkabı", "terlik"]},
    {"soru": "İki kardeş birbirini hiç göremez. Nedir?", "cevap": ["göz", "gözler"]},
    {"soru": "Her gün doğar ama hiç büyümez. Nedir?", "cevap": ["güneş"]},
    {"soru": "Ağzı var yemez, gözü var görmez. Nedir?", "cevap": ["iğne"]},
    {"soru": "Herkes üstüne basar ama ses çıkarmaz. Nedir?", "cevap": ["yol", "toprak", "zemin"]},
    {"soru": "Kanatları var uçamaz, bacakları var yürüyemez. Nedir?", "cevap": ["masa", "sandalye"]},
]


# ================= LONCA FONKSIYONLARI =================

def get_lonca(lonca_id):
    """Lonca verisini getir."""
    return loncalar_col.find_one({"lonca_id": lonca_id})

def get_user_lonca(user_id):
    """Kullanıcının loncasını getir."""
    return loncalar_col.find_one({"üyeler": user_id})

def save_lonca(lonca):
    """Lonca verisini kaydet."""
    loncalar_col.update_one({"lonca_id": lonca["lonca_id"]}, {"$set": lonca}, upsert=True)


def roll_hazine_odası():
    """Hazine odası tipini belirle."""
    toplam = sum(h["şans"] for h in HAZINE_TIPLERI.values())
    zar = random.randint(1, toplam)
    birikmiş = 0
    for tip, hazine in HAZINE_TIPLERI.items():
        birikmiş += hazine["şans"]
        if zar <= birikmiş:
            return tip, hazine
    return None, None


# ================= PVP ARENA SİSTEMİ =================

@bot.command(name="pvp", aliases=["düello_zindan", "arena"])
async def pvp(ctx, hedef: discord.Member = None, bahis: int = 0):
    """Başka bir oyuncuyla PvP düellosu yap."""
    if hedef is None:
        embed = discord.Embed(
            title="PvP Arena",
            description=(
                "Kullanım: `!pvp @kullanıcı <bahis>`\n\n"
                "Örnek: `!pvp @Oyuncu 500`\n\n"
                "Kazanan bahisi alır, kaybeden kaybeder!\n"
                "Her iki tarafın da yeterli bakiyesi olmalı."
            ),
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    if hedef.id == ctx.author.id:
        return await ctx.send(embed=discord.Embed(description="Kendinle savaşamazsın!", color=discord.Color.red()))

    if hedef.bot:
        return await ctx.send(embed=discord.Embed(description="Botlarla savaşamazsın!", color=discord.Color.red()))

    # Zindan karakteri kontrolü
    saldıran_dungeon = get_dungeon(ctx.author.id)
    hedef_dungeon = get_dungeon(hedef.id)

    if saldıran_dungeon["sınıf"] is None:
        return await ctx.send(embed=discord.Embed(description="Önce bir zindan karakteri oluştur! `!sınıfseç`", color=discord.Color.red()))

    if hedef_dungeon["sınıf"] is None:
        return await ctx.send(embed=discord.Embed(description=f"{hedef.mention} henüz bir zindan karakteri oluşturmamış!", color=discord.Color.red()))

    # Aktif savaş kontrolü
    if saldıran_dungeon.get("aktif_savaş"):
        return await ctx.send(embed=discord.Embed(description="Zaten aktif bir savaşın var!", color=discord.Color.orange()))

    if hedef_dungeon.get("aktif_savaş"):
        return await ctx.send(embed=discord.Embed(description=f"{hedef.mention} şu anda başka bir savaşta!", color=discord.Color.orange()))

    # Bahis kontrolü
    bahis = max(0, bahis)
    if bahis > 0:
        saldıran_user = get_user(ctx.author.id)
        hedef_user = get_user(hedef.id)

        if saldıran_user["money"] < bahis:
            return await ctx.send(embed=discord.Embed(description=f"Yeterli bakiyen yok! Bakiyen: **{saldıran_user['money']}** VisoCoin", color=discord.Color.red()))

        if hedef_user["money"] < bahis:
            return await ctx.send(embed=discord.Embed(description=f"{hedef.mention} kullanıcısının yeterli bakiyesi yok!", color=discord.Color.red()))

    # PvP isteği gönder
    pvp_istekleri[hedef.id] = {
        "saldıran": ctx.author.id,
        "bahis": bahis,
        "zaman": time.time(),
        "kanal": ctx.channel.id,
    }

    saldıran_sınıf = SINIFLAR[saldıran_dungeon["sınıf"]]
    hedef_sınıf = SINIFLAR[hedef_dungeon["sınıf"]]
    saldıran_statlar = get_karakter_statları(saldıran_dungeon)
    hedef_statlar = get_karakter_statları(hedef_dungeon)

    embed = discord.Embed(
        title="PvP Arena - Düello İsteği!",
        description=(
            f"{ctx.author.mention} seni düelloya davet ediyor!\n\n"
            f"**{saldıran_sınıf['emoji']} {ctx.author.display_name}** vs **{hedef_sınıf['emoji']} {hedef.display_name}**\n\n"
            f"{'━' * 30}\n"
            f"**{ctx.author.display_name}** (Seviye {saldıran_dungeon['seviye']})\n"
            f"Can: {saldıran_statlar['can']} | Saldırı: {saldıran_statlar['saldırı']} | Savunma: {saldıran_statlar['savunma']}\n\n"
            f"**{hedef.display_name}** (Seviye {hedef_dungeon['seviye']})\n"
            f"Can: {hedef_statlar['can']} | Saldırı: {hedef_statlar['saldırı']} | Savunma: {hedef_statlar['savunma']}\n"
            f"{'━' * 30}\n\n"
            + (f"Bahis: **{bahis}** VisoCoin\n\n" if bahis > 0 else "") +
            f"{hedef.mention}, kabul etmek için `!pvpkabul` yaz!\n"
            f"60 saniye içinde yanıt vermelisin."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="PvP Arena")
    await ctx.send(embed=embed)


@bot.command(name="pvpkabul", aliases=["pvpaccept", "pvpkabulet"])
async def pvp_kabul(ctx):
    """PvP düello isteğini kabul et."""
    user_id = ctx.author.id

    if user_id not in pvp_istekleri:
        return await ctx.send(embed=discord.Embed(description="Bekleyen bir düello isteğin yok!", color=discord.Color.red()))

    istek = pvp_istekleri[user_id]

    # Süre kontrolü
    if time.time() - istek["zaman"] > PVP_ISTEK_SURESI:
        del pvp_istekleri[user_id]
        return await ctx.send(embed=discord.Embed(description="Düello isteği süresi doldu!", color=discord.Color.red()))

    saldıran_id = istek["saldıran"]
    bahis = istek["bahis"]
    del pvp_istekleri[user_id]

    # Savaşı başlat
    saldıran = await bot.fetch_user(saldıran_id)
    hedef = ctx.author

    saldıran_dungeon = get_dungeon(saldıran_id)
    hedef_dungeon = get_dungeon(user_id)

    saldıran_statlar = get_karakter_statları(saldıran_dungeon)
    hedef_statlar = get_karakter_statları(hedef_dungeon)

    # Canları ayarla
    saldıran_can = saldıran_statlar["can"]
    hedef_can = hedef_statlar["can"]

    saldıran_sınıf = SINIFLAR[saldıran_dungeon["sınıf"]]
    hedef_sınıf = SINIFLAR[hedef_dungeon["sınıf"]]

    savaş_logu = []
    tur = 0
    max_tur = 30

    # Savaş simülasyonu
    while saldıran_can > 0 and hedef_can > 0 and tur < max_tur:
        tur += 1

        # Saldıran vuruyor
        # Suikastçi kaçınma kontrolü (hedef)
        kaçındı = False
        if hedef_dungeon["sınıf"] == "suikastçi":
            kaçınma_şansı = SINIFLAR["suikastçi"].get("kaçınma", 10)
            if random.randint(1, 100) <= kaçınma_şansı:
                kaçındı = True
                savaş_logu.append(f"**Tur {tur}:** {saldıran_sınıf['emoji']} saldırdı ama {hedef_sınıf['emoji']} kaçındı!")

        if not kaçındı:
            hasar, kritik = hasar_hesapla(saldıran_statlar["saldırı"], hedef_statlar["savunma"], saldıran_statlar["şans"])
            hedef_can -= hasar
            kritik_text = " **KRİTİK!**" if kritik else ""
            savaş_logu.append(f"**Tur {tur}:** {saldıran_sınıf['emoji']} -> {hedef_sınıf['emoji']} **{hasar}** hasar{kritik_text}")

        if hedef_can <= 0:
            break

        # Hedef vuruyor
        # Suikastçi kaçınma kontrolü (saldıran)
        kaçındı = False
        if saldıran_dungeon["sınıf"] == "suikastçi":
            kaçınma_şansı = SINIFLAR["suikastçi"].get("kaçınma", 10)
            if random.randint(1, 100) <= kaçınma_şansı:
                kaçındı = True
                savaş_logu.append(f"**Tur {tur}:** {hedef_sınıf['emoji']} saldırdı ama {saldıran_sınıf['emoji']} kaçındı!")

        if not kaçındı:
            hasar, kritik = hasar_hesapla(hedef_statlar["saldırı"], saldıran_statlar["savunma"], hedef_statlar["şans"])
            saldıran_can -= hasar
            kritik_text = " **KRİTİK!**" if kritik else ""
            savaş_logu.append(f"**Tur {tur}:** {hedef_sınıf['emoji']} -> {saldıran_sınıf['emoji']} **{hasar}** hasar{kritik_text}")

        # Doktor pasif iyileşme (her 3 turda bir %10)
        if saldıran_dungeon["sınıf"] == "doktor" and tur % 3 == 0:
            iyileşme = int(saldıran_statlar["can"] * 0.10)
            saldıran_can = min(saldıran_can + iyileşme, saldıran_statlar["can"])
            savaş_logu.append(f"**Tur {tur}:** {saldıran_sınıf['emoji']} **+{iyileşme}** can iyileşti!")

        if hedef_dungeon["sınıf"] == "doktor" and tur % 3 == 0:
            iyileşme = int(hedef_statlar["can"] * 0.10)
            hedef_can = min(hedef_can + iyileşme, hedef_statlar["can"])
            savaş_logu.append(f"**Tur {tur}:** {hedef_sınıf['emoji']} **+{iyileşme}** can iyileşti!")

    # Sonuç
    if saldıran_can > hedef_can:
        kazanan = saldıran
        kazanan_id = saldıran_id
        kaybeden = hedef
        kaybeden_id = user_id
    elif hedef_can > saldıran_can:
        kazanan = hedef
        kazanan_id = user_id
        kaybeden = saldıran
        kaybeden_id = saldıran_id
    else:
        # Berabere
        embed = discord.Embed(
            title="PvP Arena - Berabere!",
            description=(
                f"**{saldıran.display_name}** vs **{hedef.display_name}**\n\n"
                f"Savaş berabere bitti! Bahisler iade edildi.\n\n"
                f"**Son Durum:**\n"
                f"{saldıran_sınıf['emoji']} {saldıran.display_name}: **{max(0, saldıran_can)}** can\n"
                f"{hedef_sınıf['emoji']} {hedef.display_name}: **{max(0, hedef_can)}** can"
            ),
            color=discord.Color.greyple()
        )
        return await ctx.send(embed=embed)

    # Bahis transferi
    if bahis > 0:
        kazanan_user = get_user(kazanan_id)
        kaybeden_user = get_user(kaybeden_id)
        kazanan_user["money"] += bahis
        kaybeden_user["money"] -= bahis
        save_user(kazanan_user)
        save_user(kaybeden_user)

    # XP ödülü
    kazanan_dungeon = get_dungeon(kazanan_id)
    xp_kazanç = 25 + tur * 2
    kazanan_dungeon["xp"] += xp_kazanç
    kazanan_dungeon["seviye"] = get_zindan_seviye(kazanan_dungeon["xp"])
    save_dungeon(kazanan_dungeon)

    # Savaş logu (son 10 tur)
    log_text = "\n".join(savaş_logu[-10:]) if len(savaş_logu) > 10 else "\n".join(savaş_logu)

    embed = discord.Embed(
        title="PvP Arena - Savaş Bitti!",
        description=(
            f"**Kazanan:** {kazanan.mention}\n\n"
            f"**Savaş Özeti ({tur} tur):**\n{log_text}\n\n"
            f"{'━' * 30}\n"
            f"**Son Durum:**\n"
            f"{saldıran_sınıf['emoji']} {saldıran.display_name}: **{max(0, saldıran_can)}** can\n"
            f"{hedef_sınıf['emoji']} {hedef.display_name}: **{max(0, hedef_can)}** can\n\n"
            + (f"**Bahis:** {kazanan.display_name} **+{bahis}** VisoCoin kazandı!\n" if bahis > 0 else "") +
            f"**XP:** {kazanan.display_name} **+{xp_kazanç}** XP kazandı!"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="PvP Arena")
    await ctx.send(embed=embed)


@bot.command(name="pvpreddet", aliases=["pvpreject", "pvpred"])
async def pvp_reddet(ctx):
    """PvP düello isteğini reddet."""
    if ctx.author.id in pvp_istekleri:
        del pvp_istekleri[ctx.author.id]
        await ctx.send(embed=discord.Embed(description="Düello isteği reddedildi.", color=discord.Color.red()))
    else:
        await ctx.send(embed=discord.Embed(description="Bekleyen bir düello isteğin yok!", color=discord.Color.red()))


# ================= LONCA SİSTEMİ =================

@bot.command(name="loncakur", aliases=["guildcreate", "loncaoluştur"])
async def lonca_kur(ctx, *, isim: str = None):
    """Yeni bir lonca kur."""
    if isim is None:
        embed = discord.Embed(
            description="Kullanım: `!loncakur <lonca adı>`\n\nKurma ücreti: **5000** VisoCoin",
            color=discord.Color.blue()
        )
        return await ctx.send(embed=embed)

    user_id = ctx.author.id

    # Zaten loncası var mı?
    mevcut = get_user_lonca(user_id)
    if mevcut:
        return await ctx.send(embed=discord.Embed(description=f"Zaten bir loncadasın: **{mevcut['isim']}**", color=discord.Color.red()))

    # Zindan karakteri var mı?
    dungeon = get_dungeon(user_id)
    if dungeon["sınıf"] is None:
        return await ctx.send(embed=discord.Embed(description="Önce zindan karakteri oluştur! `!sınıfseç`", color=discord.Color.red()))

    # Para kontrolü
    user = get_user(user_id)
    if user["money"] < LONCA_KURMA_UCRETI:
        return await ctx.send(embed=discord.Embed(description=f"Yeterli paran yok! Gereken: **{LONCA_KURMA_UCRETI}** VisoCoin", color=discord.Color.red()))

    # İsim kontrolü
    if len(isim) < 3 or len(isim) > 25:
        return await ctx.send(embed=discord.Embed(description="Lonca adı 3-25 karakter olmalı!", color=discord.Color.red()))

    # Aynı isimde lonca var mı?
    if loncalar_col.find_one({"isim": isim}):
        return await ctx.send(embed=discord.Embed(description="Bu isimde bir lonca zaten var!", color=discord.Color.red()))

    # Lonca oluştur
    lonca_id = str(uuid.uuid4())[:8]
    lonca = {
        "lonca_id": lonca_id,
        "isim": isim,
        "lider": user_id,
        "üyeler": [user_id],
        "seviye": 1,
        "xp": 0,
        "toplam_boss_öldürme": 0,
        "kasa": 0,
        "oluşturma_tarihi": datetime.now(timezone.utc).isoformat(),
        "son_boss_savaşı": 0,
    }
    loncalar_col.insert_one(lonca)

    # Para düş
    user["money"] -= LONCA_KURMA_UCRETI
    save_user(user)

    embed = discord.Embed(
        title="Lonca Kuruldu!",
        description=(
            f"**{isim}** loncası başarıyla kuruldu!\n\n"
            f"Lonca ID: `{lonca_id}`\n"
            f"Lider: {ctx.author.mention}\n\n"
            f"**Komutlar:**\n"
            f"`!lonca` - Lonca bilgisi\n"
            f"`!loncadavet @kullanıcı` - Üye davet et\n"
            f"`!loncaboss` - Lonca bossuna saldır\n"
            f"`!loncaçık` - Loncadan ayrıl"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Lonca Sistemi")
    await ctx.send(embed=embed)


@bot.command(name="lonca", aliases=["guild", "loncabilgi"])
async def lonca_bilgi(ctx):
    """Lonca bilgilerini göster."""
    user_id = ctx.author.id
    lonca = get_user_lonca(user_id)

    if not lonca:
        embed = discord.Embed(
            title="Lonca Sistemi",
            description=(
                "Bir loncaya üye değilsin!\n\n"
                "`!loncakur <isim>` - Yeni lonca kur (5000 VisoCoin)\n"
                "`!loncalar` - Mevcut loncaları gör"
            ),
            color=discord.Color.dark_grey()
        )
        return await ctx.send(embed=embed)

    # Lider bilgisi
    lider = await bot.fetch_user(lonca["lider"])

    # Üye listesi
    üye_text = ""
    for üye_id in lonca["üyeler"][:10]:  # İlk 10 üye
        try:
            üye = await bot.fetch_user(üye_id)
            dungeon = get_dungeon(üye_id)
            sınıf = SINIFLAR.get(dungeon["sınıf"], {}).get("emoji", "?")
            lider_badge = " (Lider)" if üye_id == lonca["lider"] else ""
            üye_text += f"{sınıf} {üye.display_name} (Sv.{dungeon.get('seviye', 1)}){lider_badge}\n"
        except:
            pass

    if len(lonca["üyeler"]) > 10:
        üye_text += f"... ve {len(lonca['üyeler']) - 10} kişi daha"

    # Lonca seviyesi
    lonca_xp = lonca.get("xp", 0)
    lonca_seviye = 1 + lonca_xp // 1000

    embed = discord.Embed(
        title=f"Lonca: {lonca['isim']}",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="Bilgiler",
        value=(
            f"Lonca ID: `{lonca['lonca_id']}`\n"
            f"Lider: {lider.display_name}\n"
            f"Seviye: **{lonca_seviye}** ({lonca_xp} XP)\n"
            f"Kasa: **{lonca.get('kasa', 0)}** VisoCoin\n"
            f"Boss Öldürme: **{lonca.get('toplam_boss_öldürme', 0)}**"
        ),
        inline=True
    )

    embed.add_field(
        name=f"Üyeler ({len(lonca['üyeler'])}/{LONCA_MAX_UYE})",
        value=üye_text or "Yok",
        inline=True
    )

    embed.set_footer(text="Lonca Sistemi")
    await ctx.send(embed=embed)


@bot.command(name="loncalar", aliases=["guilds", "loncalistesi"])
async def lonca_listesi(ctx):
    """Tüm loncaları listele."""
    tüm_loncalar = list(loncalar_col.find().sort("xp", -1).limit(10))

    if not tüm_loncalar:
        return await ctx.send(embed=discord.Embed(description="Henüz hiç lonca yok!", color=discord.Color.dark_grey()))

    embed = discord.Embed(
        title="Loncalar",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )

    for i, lonca in enumerate(tüm_loncalar, 1):
        seviye = 1 + lonca.get("xp", 0) // 1000
        embed.add_field(
            name=f"{i}. {lonca['isim']}",
            value=f"Seviye: {seviye} | Üye: {len(lonca['üyeler'])} | Boss: {lonca.get('toplam_boss_öldürme', 0)}",
            inline=False
        )

    embed.set_footer(text="!loncakur <isim> ile kendi loncanı kur!")
    await ctx.send(embed=embed)


@bot.command(name="loncadavet", aliases=["guildinvite"])
async def lonca_davet(ctx, hedef: discord.Member = None):
    """Bir kullanıcıyı loncaya davet et."""
    if hedef is None:
        return await ctx.send(embed=discord.Embed(description="Kullanım: `!loncadavet @kullanıcı`", color=discord.Color.blue()))

    user_id = ctx.author.id
    lonca = get_user_lonca(user_id)

    if not lonca:
        return await ctx.send(embed=discord.Embed(description="Bir loncada değilsin!", color=discord.Color.red()))

    if lonca["lider"] != user_id:
        return await ctx.send(embed=discord.Embed(description="Sadece lider davet gönderebilir!", color=discord.Color.red()))

    if len(lonca["üyeler"]) >= LONCA_MAX_UYE:
        return await ctx.send(embed=discord.Embed(description="Lonca dolu!", color=discord.Color.red()))

    if hedef.id in lonca["üyeler"]:
        return await ctx.send(embed=discord.Embed(description="Bu kişi zaten loncada!", color=discord.Color.red()))

    hedef_lonca = get_user_lonca(hedef.id)
    if hedef_lonca:
        return await ctx.send(embed=discord.Embed(description="Bu kişi zaten başka bir loncada!", color=discord.Color.red()))

    # Davet gönder
    lonca_davetleri[hedef.id] = {
        "lonca_id": lonca["lonca_id"],
        "davet_eden": user_id,
        "zaman": time.time(),
    }

    embed = discord.Embed(
        title="Lonca Daveti!",
        description=(
            f"{hedef.mention}, **{lonca['isim']}** loncasına davet edildin!\n\n"
            f"Kabul etmek için: `!loncakabulet`\n"
            f"Reddetmek için: `!loncareddet`\n\n"
            f"60 saniye içinde yanıt vermelisin."
        ),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


@bot.command(name="loncakabulet", aliases=["guildaccept"])
async def lonca_kabul_et(ctx):
    """Lonca davetini kabul et."""
    user_id = ctx.author.id

    if user_id not in lonca_davetleri:
        return await ctx.send(embed=discord.Embed(description="Bekleyen bir davet yok!", color=discord.Color.red()))

    davet = lonca_davetleri[user_id]

    if time.time() - davet["zaman"] > 60:
        del lonca_davetleri[user_id]
        return await ctx.send(embed=discord.Embed(description="Davet süresi doldu!", color=discord.Color.red()))

    lonca = get_lonca(davet["lonca_id"])
    if not lonca:
        del lonca_davetleri[user_id]
        return await ctx.send(embed=discord.Embed(description="Lonca artık mevcut değil!", color=discord.Color.red()))

    # Üye ekle
    lonca["üyeler"].append(user_id)
    save_lonca(lonca)
    del lonca_davetleri[user_id]

    embed = discord.Embed(
        title="Loncaya Katıldın!",
        description=f"**{lonca['isim']}** loncasına hoş geldin!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="loncareddet", aliases=["guildreject"])
async def lonca_reddet(ctx):
    """Lonca davetini reddet."""
    if ctx.author.id in lonca_davetleri:
        del lonca_davetleri[ctx.author.id]
        await ctx.send(embed=discord.Embed(description="Davet reddedildi.", color=discord.Color.red()))
    else:
        await ctx.send(embed=discord.Embed(description="Bekleyen bir davet yok!", color=discord.Color.red()))


@bot.command(name="loncaçık", aliases=["guildleave", "loncaayrıl"])
async def lonca_cik(ctx):
    """Loncadan ayrıl."""
    user_id = ctx.author.id
    lonca = get_user_lonca(user_id)

    if not lonca:
        return await ctx.send(embed=discord.Embed(description="Bir loncada değilsin!", color=discord.Color.red()))

    if lonca["lider"] == user_id:
        if len(lonca["üyeler"]) > 1:
            return await ctx.send(embed=discord.Embed(description="Lider loncayı terk edemez! Önce liderliği devret veya herkesi çıkar.", color=discord.Color.red()))
        else:
            # Loncayı sil
            loncalar_col.delete_one({"lonca_id": lonca["lonca_id"]})
            return await ctx.send(embed=discord.Embed(description=f"**{lonca['isim']}** loncası silindi.", color=discord.Color.red()))

    # Üyeyi çıkar
    lonca["üyeler"].remove(user_id)
    save_lonca(lonca)

    await ctx.send(embed=discord.Embed(description=f"**{lonca['isim']}** loncasından ayrıldın.", color=discord.Color.orange()))


@bot.command(name="loncaboss", aliases=["guildboss", "loncasavaş"])
async def lonca_boss(ctx):
    """Lonca bossu ile savaş (tüm üyeler katılır)."""
    user_id = ctx.author.id
    lonca = get_user_lonca(user_id)

    if not lonca:
        return await ctx.send(embed=discord.Embed(description="Bir loncada değilsin!", color=discord.Color.red()))

    # Cooldown kontrolü
    son_savaş = lonca.get("son_boss_savaşı", 0)
    if time.time() - son_savaş < LONCA_BOSS_COOLDOWN:
        kalan = int(LONCA_BOSS_COOLDOWN - (time.time() - son_savaş))
        dakika = kalan // 60
        saniye = kalan % 60
        return await ctx.send(embed=discord.Embed(description=f"Lonca boss savaşı için **{dakika}dk {saniye}sn** bekle!", color=discord.Color.orange()))

    # Boss seviyesi (lonca seviyesine göre)
    lonca_seviye = 1 + lonca.get("xp", 0) // 1000
    boss_seviye = min(lonca_seviye, 4)
    boss = LONCA_BOSSLARI[boss_seviye]

    # Yeterli üye kontrolü
    if len(lonca["üyeler"]) < boss["gerekli_üye"]:
        return await ctx.send(embed=discord.Embed(
            description=f"Bu boss için en az **{boss['gerekli_üye']}** üye gerekli! (Mevcut: {len(lonca['üyeler'])})",
            color=discord.Color.red()
        ))

    # Tüm üyelerin toplam hasarını hesapla
    toplam_hasar = 0
    katılımcılar = []
    boss_can = boss["can"]

    for üye_id in lonca["üyeler"]:
        dungeon = get_dungeon(üye_id)
        if dungeon["sınıf"]:
            statlar = get_karakter_statları(dungeon)
            # Her üye 5 tur saldırır
            üye_hasar = 0
            for _ in range(5):
                h, _ = hasar_hesapla(statlar["saldırı"], boss["savunma"], statlar["şans"])
                üye_hasar += h
            toplam_hasar += üye_hasar
            try:
                üye = await bot.fetch_user(üye_id)
                sınıf = SINIFLAR[dungeon["sınıf"]]
                katılımcılar.append(f"{sınıf['emoji']} {üye.display_name}: **{üye_hasar}** hasar")
            except:
                pass

    # Sonuç
    kazandı = toplam_hasar >= boss_can

    if kazandı:
        # Ödüller
        xp_ödül = boss["xp"]
        altın_ödül = boss["altın"]

        lonca["xp"] = lonca.get("xp", 0) + xp_ödül
        lonca["kasa"] = lonca.get("kasa", 0) + altın_ödül
        lonca["toplam_boss_öldürme"] = lonca.get("toplam_boss_öldürme", 0) + 1
        lonca["son_boss_savaşı"] = time.time()
        save_lonca(lonca)

        # Her üyeye XP
        for üye_id in lonca["üyeler"]:
            dungeon = get_dungeon(üye_id)
            if dungeon["sınıf"]:
                dungeon["xp"] += xp_ödül // len(lonca["üyeler"])
                dungeon["seviye"] = get_zindan_seviye(dungeon["xp"])
                save_dungeon(dungeon)

        embed = discord.Embed(
            title=f"Lonca Boss Savaşı - ZAFER!",
            description=(
                f"**{lonca['isim']}** loncası **{boss['emoji']} {boss['isim']}** bossunu yendi!\n\n"
                f"{'━' * 30}\n"
                f"**Katılımcılar:**\n" + "\n".join(katılımcılar[:10]) + "\n\n"
                f"**Toplam Hasar:** {toplam_hasar} / {boss_can}\n"
                f"{'━' * 30}\n\n"
                f"**Ödüller:**\n"
                f"Lonca XP: **+{xp_ödül}**\n"
                f"Lonca Kasası: **+{altın_ödül}** VisoCoin"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
    else:
        lonca["son_boss_savaşı"] = time.time()
        save_lonca(lonca)

        embed = discord.Embed(
            title=f"Lonca Boss Savaşı - YENİLGİ!",
            description=(
                f"**{lonca['isim']}** loncası **{boss['emoji']} {boss['isim']}** bossuna yenildi!\n\n"
                f"{'━' * 30}\n"
                f"**Katılımcılar:**\n" + "\n".join(katılımcılar[:10]) + "\n\n"
                f"**Toplam Hasar:** {toplam_hasar} / {boss_can}\n"
                f"{'━' * 30}\n\n"
                f"Daha güçlü olun ve tekrar deneyin!"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

    embed.set_footer(text="Lonca Sistemi")
    await ctx.send(embed=embed)


# ================= HAZİNE ODASI SİSTEMİ =================

async def hazine_odası_kontrol(ctx, dungeon, kat):
    """Katta hazine odası var mı kontrol et."""
    if random.randint(1, 100) <= HAZINE_ODASI_SANSI:
        tip, hazine = roll_hazine_odası()
        if not hazine:
            return False

        user_id = ctx.author.id
        user = get_user(user_id)

        if tip == "altın_sandığı":
            altın = random.randint(hazine["altın_min"], hazine["altın_max"])
            # Kat bonusu
            altın = int(altın * (1 + kat * 0.05))
            user["money"] += altın
            save_user(user)

            embed = discord.Embed(
                title=f"{hazine['emoji']} Hazine Odası!",
                description=(
                    f"**{hazine['isim']}** buldun!\n\n"
                    f"{hazine['açıklama']}\n\n"
                    f"**Ödül:** +**{altın}** VisoCoin!"
                ),
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return True

        elif tip == "efsanevi_sandık":
            altın = random.randint(hazine["altın_min"], hazine["altın_max"])
            user["money"] += altın
            save_user(user)

            eşya = None
            if random.randint(1, 100) <= hazine["eşya_şansı"]:
                eşya = roll_loot(kat + 10)  # Daha iyi eşya şansı
                if eşya and eşya in EKİPMANLAR:
                    eşya_id = str(uuid.uuid4())[:8]
                    dungeon["envanter"].append({"id": eşya_id, "eşya_tipi": eşya})
                    # Dogrudan veritabanina kaydet
                    dungeons_col.update_one(
                        {"user_id": user_id},
                        {"$push": {"envanter": {"id": eşya_id, "eşya_tipi": eşya}}}
                    )

            embed = discord.Embed(
                title=f"{hazine['emoji']} Hazine Odası!",
                description=(
                    f"**{hazine['isim']}** buldun!\n\n"
                    f"{hazine['açıklama']}\n\n"
                    f"**Ödüller:**\n"
                    f"+**{altın}** VisoCoin\n"
                    + (f"+**{EKİPMANLAR[eşya]['emoji']} {EKİPMANLAR[eşya]['isim']}**!" if eşya and eşya in EKİPMANLAR else "Eşya bulunamadı.")
                ),
                color=discord.Color.purple()
            )
            await ctx.send(embed=embed)
            return True

        elif tip == "tuzak_odası":
            hasar = random.randint(hazine["hasar_min"], hazine["hasar_max"])
            altın = random.randint(hazine["altın_min"], hazine["altın_max"])

            dungeon["can"] = max(1, dungeon["can"] - hasar)
            user["money"] += altın
            save_dungeon(dungeon)
            save_user(user)

            embed = discord.Embed(
                title=f"{hazine['emoji']} Tuzak Odası!",
                description=(
                    f"**{hazine['isim']}**'na düştün!\n\n"
                    f"Tuzaklar sana **{hasar}** hasar verdi!\n"
                    f"Ama yine de **{altın}** VisoCoin buldun.\n\n"
                    f"Kalan canın: **{dungeon['can']}**"
                ),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return True

        elif tip == "bilmece_odası":
            bilmece = random.choice(BILMECELER)
            altın = random.randint(hazine["altın_min"], hazine["altın_max"])
            altın = int(altın * (1 + kat * 0.05))

            aktif_bilmeceler[user_id] = {
                "bilmece": bilmece,
                "zaman": time.time(),
                "altın": altın,
                "xp": hazine["xp_bonus"],
            }

            embed = discord.Embed(
                title=f"{hazine['emoji']} Bilmece Odası!",
                description=(
                    f"**{hazine['isim']}** buldun!\n\n"
                    f"Bilmeceyi çöz ve hazineyi al!\n\n"
                    f"**Bilmece:** {bilmece['soru']}\n\n"
                    f"Cevaplamak için: `!cevap <cevabın>`\n"
                    f"30 saniye içinde cevap ver!"
                ),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return True

        elif tip == "ejderha_hazinesi":
            altın = random.randint(hazine["altın_min"], hazine["altın_max"])
            altın = int(altın * (1 + kat * 0.05))
            user["money"] += altın
            save_user(user)

            eşya = None
            if random.randint(1, 100) <= hazine["eşya_şansı"]:
                # Daha iyi loot
                eşya = roll_loot(max(kat, 50))
                if eşya and eşya in EKİPMANLAR:
                    eşya_id = str(uuid.uuid4())[:8]
                    dungeon["envanter"].append({"id": eşya_id, "eşya_tipi": eşya})
                    # Dogrudan veritabanina kaydet
                    dungeons_col.update_one(
                        {"user_id": user_id},
                        {"$push": {"envanter": {"id": eşya_id, "eşya_tipi": eşya}}}
                    )

            embed = discord.Embed(
                title=f"{hazine['emoji']} EJDERHA HAZİNESİ!",
                description=(
                    f"**{hazine['isim']}** buldun!\n\n"
                    f"Muhteşem bir hazine!\n\n"
                    f"**Ödüller:**\n"
                    f"+**{altın}** VisoCoin!\n"
                    + (f"+**{EKİPMANLAR[eşya]['emoji']} {EKİPMANLAR[eşya]['isim']}** ({EKİPMANLAR[eşya]['nadirlik']})!" if eşya and eşya in EKİPMANLAR else "")
                ),
                color=discord.Color.dark_gold()
            )
            await ctx.send(embed=embed)
            return True

    return False


@bot.command(name="cevap", aliases=["answer", "bilmececevap"])
async def bilmece_cevap(ctx, *, cevap: str = None):
    """Bilmece odasının cevabını ver."""
    user_id = ctx.author.id

    if user_id not in aktif_bilmeceler:
        return await ctx.send(embed=discord.Embed(description="Aktif bir bilmece sorun yok!", color=discord.Color.red()))

    bilmece_data = aktif_bilmeceler[user_id]

    # Süre kontrolü
    if time.time() - bilmece_data["zaman"] > 30:
        del aktif_bilmeceler[user_id]
        return await ctx.send(embed=discord.Embed(description="Süre doldu! Bilmece iptal edildi.", color=discord.Color.red()))

    if cevap is None:
        return await ctx.send(embed=discord.Embed(description="Kullanım: `!cevap <cevabın>`", color=discord.Color.blue()))

    cevap = cevap.lower().strip()
    doğru_cevaplar = bilmece_data["bilmece"]["cevap"]

    if cevap in doğru_cevaplar:
        # Doğru cevap!
        user = get_user(user_id)
        dungeon = get_dungeon(user_id)

        user["money"] += bilmece_data["altın"]
        dungeon["xp"] += bilmece_data["xp"]
        dungeon["seviye"] = get_zindan_seviye(dungeon["xp"])

        save_user(user)
        save_dungeon(dungeon)
        del aktif_bilmeceler[user_id]

        embed = discord.Embed(
            title="Doğru Cevap!",
            description=(
                f"Tebrikler! Bilmeceyi çözdün!\n\n"
                f"**Ödüller:**\n"
                f"+**{bilmece_data['altın']}** VisoCoin\n"
                f"+**{bilmece_data['xp']}** XP"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        del aktif_bilmeceler[user_id]
        embed = discord.Embed(
            title="Yanlış Cevap!",
            description=f"Maalesef yanlış. Doğru cevap: **{doğru_cevaplar[0]}**",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


# ================== RUN ==================

bot.run(TOKEN)

















