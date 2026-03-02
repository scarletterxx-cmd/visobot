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
    print(f"MongoDB baglanti hatasi: {e}")

users_col = db["users"]
warnings_col = db["warnings"]
daily_col = db["daily"]
quests_col = db["quests"]

app = Flask("")

@app.route("/")
def home():
    return "BOT AYAKTA KARDES"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

Thread(target=run).start()

WARNINGS_FILE = "warnings.json"
LOG_CHANNEL_ID = 1435663818528129117
DAILY_MESSAGE_USER_ID = 594917441054834698
DAILY_MESSAGE_FILE = "daily_message.json"

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

DATA_FILE = "data.json"

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
    {"id": "rulet_3", "name": "🎱 Rulet Ustası", "desc": "3 rulet oyna", "type": "rulet", "goal": 3, "reward": 250},
    {"id": "duello_2", "name": "Düellocu", "desc": "2 düello yap", "type": "duello", "goal": 2, "reward": 350},
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
                embed.set_footer(text="Sohbet et, sansini dene!")
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
        return await ctx.send(f"Bekleme süresindesin: <t:{bitis}:R>")

    if choice is None or miktar is None:
        return await ctx.send("Kullanım: `!coinflip tura/tura miktar`")

    choice = choice.lower()

    if choice not in ["yazı", "tura"]:
        return await ctx.send("Seçenek olarak `yazı` veya `tura` girebilirsin.")

    if miktar <= 0:
        return await ctx.send("Gecerli bir miktar gir.")

    user = get_user(user_id)

    if user["money"] < miktar:
        return await ctx.send("Yetersiz bakiye.")

    user["money"] -= miktar
    save_user(user)

    msg = await ctx.send("Hazırlanıyor...")

    frames = [
        "🎡 Dönüyor...",
        "🎲 Zar atılıyor...",
        "🍃 Havada süzülüyor...",
        "👁 Sonuç geliyor..."
    ]

    for frame in frames:
        await asyncio.sleep(0.7)
        await msg.edit(content=frame)

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
        await msg.edit(content=f"**{result.upper()}** geldi! +{kazanc} VisoCoin kazandın.")
    else:
        save_user(user)
        await msg.edit(content=f"**{result.upper()}** geldi! {miktar} VisoCoin'ler kayboldu...")


# ======================================================================
#                        BLACKJACK
# ======================================================================

def draw_card():
    """Rastgele bir kart çek (sadece sayılar)."""
    cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
    return random.choice(cards)

def hand_value(hand):
    """Eldeki kartların toplam değerini hesapla (11 için akıllı hesaplama)."""
    total = sum(hand)
    aces = hand.count(11)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def format_hand(hand):
    """Eli gösterim formatına çevir."""
    return " | ".join([f"`{c}`" for c in hand])

def bj_embed(author, miktar, player_hand, dealer_hand, durum="oyun", sonuc_text=""):
    """Blackjack embed oluştur."""
    p_val = hand_value(player_hand)
    d_val = hand_value(dealer_hand)

    # Ust bar
    bar = f"Bahis: **{miktar:,}** VisoCoin"

    if durum == "oyun":
        # Oyun devam ediyor - krupiyenin 2. karti gizli
        desc = (
            f"{bar}\n"
            f"{'━' * 25}\n\n"
            f"**Senin Elin:** ({p_val})\n"
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
            f"**Senin Elin:** ({p_val})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot** ({d_val})\n"
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
            f"**Senin Elin:** ({p_val})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot:** ({d_val})\n"
            f"{format_hand(dealer_hand)}\n\n"
            f"{'━' * 25}\n"
            f"{sonuc_text}"
        )
        renk = discord.Color.green()
        baslik = "🃏 Kazandin!"

    elif durum == "kaybet":
        desc = (
            f"{bar}\n"
            f"{'━' * 25}\n\n"
            f"**Senin Elin:** ({p_val})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot:** ({d_val})\n"
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
            f"**Senin Elin:** ({p_val})\n"
            f"{format_hand(player_hand)}\n\n"
            f"**VisoBot:** ({d_val})\n"
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

        p_val = hand_value(self.player_hand)

        # Krupiye 17'ye kadar cekmeli
        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(draw_card())

        d_val = hand_value(self.dealer_hand)

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
                             durum="berabere", sonuc_text=f"Bahsin geri verildi: **{self.miktar:,} VisoCoin**")
        else:
            save_user(user)
            embed = bj_embed(self.ctx.author, self.miktar, self.player_hand, self.dealer_hand,
                             durum="kaybet", sonuc_text=f"**{self.miktar:,} VisoCoin** kaybettin.")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Kart Çek", style=discord.ButtonStyle.primary, emoji=None, custom_id="bj_cek")
    async def cek_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kart çek butonu"""
        self.player_hand.append(draw_card())
        p_val = hand_value(self.player_hand)

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
        p_val = hand_value(self.player_hand)

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

    p_val = hand_value(player_hand)

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
        return await ctx.send(f"Bekleme süresindesin: <t:{bitis}:R>")

    if miktar is None:
        return await ctx.send("Kullanım: `!slot <miktar>`")

    if miktar <= 0:
        return await ctx.send("Geçerli bir miktar gir.")

    user = get_user(user_id)
    if user["money"] < miktar:
        return await ctx.send("Yetersiz bakiye.")

    user["money"] -= miktar
    save_user(user)

    slot_cd[user_id] = now + SLOT_COOLDOWN
    update_quest_progress(user_id, "slot", 1)
    update_quest_progress(user_id, "harca", miktar)

    # Animasyon
    msg = await ctx.send("Slot çevriliyor...")

    for _ in range(3):
        r1, r2, r3 = random.choice(SLOT_SYMBOLS), random.choice(SLOT_SYMBOLS), random.choice(SLOT_SYMBOLS)
        await asyncio.sleep(0.6)
        await msg.edit(content=f"[ {r1} | {r2} | {r3} ]")

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
            title="🎰 SLOT - JACKPOT!",
            description=(
                f"[ **{reel1}** | **{reel2}** | **{reel3}** ]\n\n"
                f"{ctx.author.mention}, 3x **{reel1}**! ({carpan}x carpan)\n"
                f"**+{kazanc} VisoCoin** kazandın!\n"
                f"Bakiye: **{user['money']}** VisoCoin"
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
            title="🎰 SLOT - İkili Eşleşme!",
            description=(
                f"[ **{reel1}** | **{reel2}** | **{reel3}** ]\n\n"
                f"{ctx.author.mention}, ikili eslesme!\n"
                f"**+{kazanc} VisoCoin** kazandın!\n"
                f"Bakiye: **{user['money']}** VisoCoin"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )

    # Hic eslesmedi
    else:
        save_user(user)

        embed = discord.Embed(
            title="🎰 SLOT - Kaybettin!",
            description=(
                f"[ **{reel1}** | **{reel2}** | **{reel3}** ]\n\n"
                f"{ctx.author.mention}, eşleşme yok.\n"
                f"**{miktar} VisoCoin** kaybettin.\n"
                f"Bakiye: **{user['money']}** VisoCoin"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

    await msg.edit(content=None, embed=embed)


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
        return await ctx.send(f"{member.mention} bu düello icin yeterli VisoCoin'e sahip degil.")

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
        return await ctx.send("Düello daveti zamanaşımına uğradı.")

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
            f"{winner_member.mention} düelloyu kazandı!\n\n"
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

@bot.command(name="sıralama", aliases=["leaderboard", "lb", "top", "zenginler"])
async def siralama(ctx):
    # MongoDB'den en zengin 10 kullaniciyi cek
    top_users = list(users_col.find().sort("money", -1).limit(10))

    if not top_users:
        return await ctx.send("Henuz kimsenin parasi yok!")

    medal_emojis = {0: "1.", 1: "2.", 2: "3."}
    desc = ""

    for i, u in enumerate(top_users):
        uid = u["user_id"]
        money = u.get("money", 0)
        level = u.get("level", 1)
        prefix = medal_emojis.get(i, f"{i + 1}.")

        member = ctx.guild.get_member(uid)
        name = member.display_name if member else f"Bilinmeyen ({uid})"

        desc += f"**{prefix}** {name} - **{money:,}** VisoCoin (Sv. {level})\n"

    # Komutu kullananin sirasi
    caller = get_user(ctx.author.id)
    all_users = list(users_col.find().sort("money", -1))
    caller_rank = next((i + 1 for i, u in enumerate(all_users) if u["user_id"] == ctx.author.id), "?")

    embed = discord.Embed(
        title="💎 VisoCoin Sıralaması",
        description=desc,
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Senin sıran: #{caller_rank} | {caller['money']:,} VisoCoin")
    await ctx.send(embed=embed)


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
        "price": 25000,
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
            status = "[HAZIR!]"
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
            status = "[✅ TOPLANDI]"
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
            "`!rulet <seçim> <miktar>` - 🎱 Rulet oyna\n"
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

    await ctx.send(embed=embed)


# ================== RUN ==================

bot.run(TOKEN)






