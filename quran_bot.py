import asyncio
import random
import logging
import json
import os
import re
from datetime import datetime
import requests
from pypdf import PdfReader
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
# 🔧 تنظیمات - اینجا رو پر کن
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MY_CHANNEL = "@telavat1403"
CHANNEL_MIN_ID = 1
CHANNEL_MAX_ID = 1179
PDF_FOLDER = "books"
USERS_FILE = "users.json"
TIMEZONE = "Asia/Tehran"

# ============================================================
# 💾 مدیریت کاربران
# ============================================================
def load_users() -> set:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users: set):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

subscribers = load_users()

# ============================================================
# 📖 منبع ۱ - آیه قرآن از API
# ============================================================
def get_random_quran_verse() -> str:
    try:
        surah = random.randint(1, 114)
        info = requests.get(f"https://api.alquran.cloud/v1/surah/{surah}", timeout=10).json()
        total_ayahs = info["data"]["numberOfAyahs"]
        ayah = random.randint(1, total_ayahs)

        arabic_resp = requests.get(
            f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar.alafasy",
            timeout=10
        ).json()
        arabic_text = arabic_resp["data"]["text"]
        surah_name = arabic_resp["data"]["surah"]["name"]

        persian_resp = requests.get(
            f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/fa.ansarian",
            timeout=10
        ).json()
        persian_text = persian_resp["data"]["text"]

        return (
            f"📖 *آیه قرآن*\n\n"
            f"🔸 {arabic_text}\n\n"
            f"💬 _{persian_text}_\n\n"
            f"📌 سوره {surah_name}، آیه {ayah}"
        )
    except:
        return get_fallback_verse()

def get_fallback_verse() -> str:
    verses = [
        ("إِنَّ مَعَ الْعُسْرِ يُسْرًا", "به درستی که با سختی، آسانی است.", "انشراح، ۶"),
        ("وَمَن يَتَوَكَّلْ عَلَى اللَّهِ فَهُوَ حَسْبُهُ", "هر کس بر خدا توکل کند، خدا او را کافی است.", "طلاق، ۳"),
        ("إِنَّ اللَّهَ مَعَ الصَّابِرِينَ", "خداوند با صبرکنندگان است.", "بقره، ۱۵۳"),
        ("وَإِذَا سَأَلَكَ عِبَادِي عَنِّي فَإِنِّي قَرِيبٌ", "بندگانم بدانند که من نزدیکم.", "بقره، ۱۸۶"),
        ("حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ", "خدا ما را کافی است و چه خوب وکیلی است.", "آل عمران، ۱۷۳"),
    ]
    v = random.choice(verses)
    return f"📖 *آیه قرآن*\n\n🔸 {v[0]}\n\n💬 _{v[1]}_\n\n📌 سوره {v[2]}"

# ============================================================
# 🤲 منبع ۲ - اذکار روزانه
# ============================================================
DAILY_DHIKR = [
    ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ الْعَظِيمِ", "خداوند منزه است و ستایش از آن اوست؛ خداوند بزرگ منزه است.", "محبوب‌ترین کلمات نزد خداوند - متفق علیه"),
    ("لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ", "هیچ معبودی جز خدای یگانه نیست، ملک از اوست، ستایش از اوست.", "بهترین ذکر - متفق علیه"),
    ("أَسْتَغْفِرُ اللَّهَ وَأَتُوبُ إِلَيْهِ", "از خداوند آمرزش می‌خواهم و به سوی او بازمی‌گردم.", "پیامبر ﷺ روزی ۱۰۰ بار - مسلم"),
    ("لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ", "هیچ توان و قدرتی جز از خداوند نیست.", "کنزی از کنوز بهشت - متفق علیه"),
    ("سُبْحَانَ اللَّهِ وَالْحَمْدُ لِلَّهِ وَلَا إِلَهَ إِلَّا اللَّهُ وَاللَّهُ أَكْبَرُ", "خداوند منزه است، ستایش از آن اوست، معبودی جز او نیست و خداوند بزرگ است.", "محبوب‌ترین سخن نزد خداوند - مسلم"),
    ("اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ", "خداوندا بر محمد و آل محمد درود فرست.", "هر صلواتی ده حسنه دارد - مسلم"),
    ("رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ", "پروردگارا! در دنیا و آخرت به ما نیکی عطا کن و از عذاب آتش نگاهمان دار.", "جامع‌ترین دعا - متفق علیه"),
    ("يَا حَيُّ يَا قَيُّومُ بِرَحْمَتِكَ أَسْتَغِيثُ", "ای زنده، ای پاینده! به رحمتت پناه می‌برم.", "دعای پیامبر ﷺ در سختی‌ها - ترمذی"),
    ("حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ", "خداوند مرا کافی است، معبودی جز او نیست، بر او توکل کردم.", "هر کس صبح و شب بگوید خداوند کارش را کفایت می‌کند - ابوداود"),
]

def get_random_dhikr() -> str:
    d = random.choice(DAILY_DHIKR)
    return (
        f"🤲 *ذکر روزانه*\n\n"
        f"🔹 {d[0]}\n\n"
        f"💬 _{d[1]}_\n\n"
        f"✨ {d[2]}"
    )

# ============================================================
# 📚 منبع ۳ - از PDF کتاب
# ============================================================
def load_pdf_paragraphs() -> list:
    paragraphs = []
    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER)
        return paragraphs

    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith(".pdf"):
            try:
                reader = PdfReader(os.path.join(PDF_FOLDER, filename))
                book_name = filename.replace(".pdf", "")
                full_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

                raw_paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 80]
                for p in raw_paragraphs:
                    clean = re.sub(r'\s+', ' ', p).strip()
                    if 80 < len(clean) < 600:
                        paragraphs.append({"text": clean, "book": book_name})
            except Exception as e:
                print(f"❌ خطا در خواندن {filename}: {e}")

    return paragraphs

PDF_PARAGRAPHS = load_pdf_paragraphs()

def get_random_book_paragraph() -> str:
    if not PDF_PARAGRAPHS:
        return None
    p = random.choice(PDF_PARAGRAPHS)
    return (
        f"📚 *از کتاب: {p['book']}*\n\n"
        f"{p['text']}"
    )

# ============================================================
# 🌅 اذکار صبح
# ============================================================
MORNING_ADHKAR = """🌅 *اذکار صبح*
_بسم الله الرحمن الرحیم_

━━━━━━━━━━━━━━━━━

*۱. ذکر صبح (۳ بار):*
أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ
_صبح کردیم و ملک از آنِ خداست و ستایش از آن خداست._

━━━━━━━━━━━━━━━━━

*۲. آیة الکرسی (۱ بار):*
اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ...
_هر کس صبح این آیه را بخواند تا شب از جن و شیطان محفوظ است._

━━━━━━━━━━━━━━━━━

*۳. سوره اخلاص، فلق، ناس (۳ بار):*
_قُلْ هُوَ اللَّهُ أَحَدٌ..._
_قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ..._
_قُلْ أَعُوذُ بِرَبِّ النَّاسِ..._

━━━━━━━━━━━━━━━━━

*۴. دعای عافیت (۳ بار):*
اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ فِي الدُّنْيَا وَالْآخِرَةِ
_خداوندا! از تو عفو و عافیت در دنیا و آخرت می‌خواهم._

━━━━━━━━━━━━━━━━━

*۵. سیدالاستغفار (۱ بار):*
اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ...
_هر کس این دعا را با یقین صبح بگوید و همان روز بمیرد از اهل بهشت است._

━━━━━━━━━━━━━━━━━

*۶. ذکر حفاظت (۷ بار):*
حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ

━━━━━━━━━━━━━━━━━
صبح بخیر 🌸 روزت پر از برکت باشد"""

# ============================================================
# 🌙 اذکار شب
# ============================================================
NIGHT_ADHKAR = """🌙 *اذکار قبل از خواب*
_بسم الله الرحمن الرحیم_

━━━━━━━━━━━━━━━━━

*۱. آیة الکرسی (۱ بار):*
اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ...
_هر کس شب این آیه را بخواند، شیطان نزدیکش نمی‌شود._

━━━━━━━━━━━━━━━━━

*۲. سوره اخلاص، فلق، ناس (۳ بار):*
_قُلْ هُوَ اللَّهُ أَحَدٌ..._

━━━━━━━━━━━━━━━━━

*۳. تسبیح فاطمه:*
سُبْحَانَ اللَّهِ ×۳۳
الْحَمْدُ لِلَّهِ ×۳۳
اللَّهُ أَكْبَرُ ×۳۴

━━━━━━━━━━━━━━━━━

*۴. دعای خواب:*
اللَّهُمَّ بِاسْمِكَ أَمُوتُ وَأَحْيَا
_خداوندا! به نام تو می‌میرم و زنده می‌شوم._

━━━━━━━━━━━━━━━━━

*۵. دعای پناه بردن (۳ بار):*
أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ
_به کلمات کامل خداوند از شرّ آنچه آفریده پناه می‌برم._

━━━━━━━━━━━━━━━━━
شب بخیر 🌙 خوابی آرام داشته باشی"""

# ============================================================
# 📬 ارسال به همه کاربران
# ============================================================
async def send_text_to_all(bot: Bot, content: str):
    failed = set()
    for user_id in subscribers.copy():
        try:
            await bot.send_message(chat_id=user_id, text=content, parse_mode="Markdown")
            await asyncio.sleep(0.05)
        except Exception as e:
            if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                failed.add(user_id)

    if failed:
        subscribers.difference_update(failed)
        save_users(subscribers)

async def forward_to_all(bot: Bot, message_id: int):
    failed = set()
    for user_id in subscribers.copy():
        try:
            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=MY_CHANNEL,
                message_id=message_id
            )
            await asyncio.sleep(0.05)
        except Exception as e:
            if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                failed.add(user_id)

    if failed:
        subscribers.difference_update(failed)
        save_users(subscribers)

# ============================================================
# ⏰ جاب‌های زمان‌بندی شده
# ============================================================
CONTENT_TYPES = ["quran", "dhikr", "book", "channel"]
last_type_index = [0]

async def job_every_4_hours(bot: Bot):
    content_type = CONTENT_TYPES[last_type_index[0] % 4]
    last_type_index[0] += 1

    print(f"📤 ارسال نوع: {content_type} | {datetime.now().strftime('%H:%M')}")

    if content_type == "quran":
        content = get_random_quran_verse()
        await send_text_to_all(bot, content)

    elif content_type == "dhikr":
        content = get_random_dhikr()
        await send_text_to_all(bot, content)

    elif content_type == "book":
        content = get_random_book_paragraph()
        if content:
            await send_text_to_all(bot, content)
        else:
            await send_text_to_all(bot, get_random_dhikr())

    elif content_type == "channel":
        # تلاش برای فوروارد از کانال
        success = False
        for _ in range(5):  # ۵ بار تلاش با آیدی رندوم
            random_id = random.randint(CHANNEL_MIN_ID, CHANNEL_MAX_ID)
            try:
                await forward_to_all(bot, random_id)
                success = True
                break
            except:
                continue
        if not success:
            await send_text_to_all(bot, get_random_dhikr())

    print(f"✅ ارسال شد | {len(subscribers)} مشترک")

async def job_morning_adhkar(bot: Bot):
    await send_text_to_all(bot, MORNING_ADHKAR)
    print(f"🌅 اذکار صبح ارسال شد | {datetime.now().strftime('%H:%M')}")

async def job_night_adhkar(bot: Bot):
    await send_text_to_all(bot, NIGHT_ADHKAR)
    print(f"🌙 اذکار شب ارسال شد | {datetime.now().strftime('%H:%M')}")

# ============================================================
# ⌨️ دستورات ربات
# ============================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if user_id not in subscribers:
        subscribers.add(user_id)
        save_users(subscribers)
        await update.message.reply_text(
            f"سلام {name}! 🌙\n\n"
            "✅ با موفقیت عضو شدی!\n\n"
            "📅 برنامه ارسال:\n"
            "🌅 ساعت ۷ صبح ← اذکار صبح\n"
            "🔄 هر ۴ ساعت ← آیه / ذکر / کتاب / کانال\n"
            "🌙 ساعت ۱۲ شب ← اذکار قبل از خواب\n\n"
            "دستورات:\n"
            "/now ← همین الان یه پیام بده\n"
            "/morning ← اذکار صبح\n"
            "/night ← اذکار شب\n"
            "/stop ← لغو عضویت"
        )
        content = get_random_quran_verse()
        await update.message.reply_text(content, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"سلام {name}! 😊\nقبلاً عضو شدی.\n\n"
            "/now ← همین الان پیام\n"
            "/morning ← اذکار صبح\n"
            "/night ← اذکار شب\n"
            "/stop ← لغو عضویت"
        )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in subscribers:
        subscribers.discard(user_id)
        save_users(subscribers)
        await update.message.reply_text("❌ عضویتت لغو شد.\nهر وقت خواستی دوباره /start بزن 🌙")
    else:
        await update.message.reply_text("تو عضو نبودی! /start بزن.")

async def now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content_type = CONTENT_TYPES[last_type_index[0] % 4]
    last_type_index[0] += 1

    if content_type == "quran":
        await update.message.reply_text(get_random_quran_verse(), parse_mode="Markdown")
    elif content_type == "dhikr":
        await update.message.reply_text(get_random_dhikr(), parse_mode="Markdown")
    elif content_type == "book":
        content = get_random_book_paragraph()
        if content:
            await update.message.reply_text(content, parse_mode="Markdown")
        else:
            await update.message.reply_text(get_random_dhikr(), parse_mode="Markdown")
    elif content_type == "channel":
        success = False
        for _ in range(5):
            random_id = random.randint(CHANNEL_MIN_ID, CHANNEL_MAX_ID)
            try:
                await context.bot.forward_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=MY_CHANNEL,
                    message_id=random_id
                )
                success = True
                break
            except:
                continue
        if not success:
            await update.message.reply_text(get_random_dhikr(), parse_mode="Markdown")

async def morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MORNING_ADHKAR, parse_mode="Markdown")

async def night_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(NIGHT_ADHKAR, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 آمار ربات:\n\n"
        f"👥 مشترکین: {len(subscribers)} نفر\n"
        f"📚 پاراگراف‌های کتاب: {len(PDF_PARAGRAPHS)}"
    )

# ============================================================
# 🚀 اجرا
# ============================================================
async def main():
    print("🚀 ربات در حال راه‌اندازی...")
    os.makedirs(PDF_FOLDER, exist_ok=True)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("now", now_command))
    app.add_handler(CommandHandler("morning", morning_command))
    app.add_handler(CommandHandler("night", night_command))
    app.add_handler(CommandHandler("stats", stats_command))

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(job_every_4_hours, "interval", hours=4, kwargs={"bot": app.bot})
    scheduler.add_job(job_morning_adhkar, "cron", hour=7, minute=0, kwargs={"bot": app.bot})
    scheduler.add_job(job_night_adhkar, "cron", hour=0, minute=0, kwargs={"bot": app.bot})
    scheduler.start()

    print(f"✅ ربات آماده! {len(subscribers)} مشترک | {len(PDF_PARAGRAPHS)} پاراگراف از کتاب")
    await app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
