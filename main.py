import os
import asyncio
import datetime
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import yt_dlp

# --- [بياناتك الأساسية] ---
API_ID = 36550822
API_HASH = "28cda47fb7be63a735b66f101d34e60d"
BOT_TOKEN = "9269780285:AAGcVIGx5MMXT_6dR2-HiOQYoI7h-lptM9I"

app = Client(
    "video_bot_pro", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)

BLOCKED_KEYWORDS = ["porn", "xxx", "sex", "adult", "redtube", "pornhub", "xvideos", "xnxx", "brazzers", "nsfw", "camwhore", "ebony", "hentai"]

# قواميس مؤقتة لإدارة البيانات (يفضل استبدالها بـ Database لاحقاً على السيرفر)
pending_urls = {}
user_data = {}  # هيكل البيانات: {user_id: {"downloads": count, "last_date": date, "pro_expiry": datetime}}

DAILY_LIMIT = 3  # الحد الأقصى المجاني اليومي

async def run_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, func, *args)
    return result

def check_user_limit(user_id):
    today = datetime.date.today()
    if user_id not in user_data:
        user_data[user_id] = {"downloads": 0, "date": today, "pro_expiry": None}
    
    data = user_data[user_id]
    
    # تحقق من انتهاء اشتراك الـ Pro
    if data["pro_expiry"] and datetime.datetime.now() < data["pro_expiry"]:
        return True, "pro"  # مشترك Pro ومفعل
        
    # إعادة تعيين العداء اليومي إذا تغير اليوم
    if data["date"] != today:
        data["downloads"] = 0
        data["date"] = today
        
    if data["downloads"] >= DAILY_LIMIT:
        return False, "limit_exceeded"
        
    return True, "allowed"

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = message.from_user.id
    today = datetime.date.today()
    
    # تفعيل تجربة مجانية ليومين للـ Pro لأول مرة تلقائياً
    if user_id not in user_data:
        user_data[user_id] = {
            "downloads": 0, 
            "date": today, 
            "pro_expiry": datetime.datetime.now() + datetime.timedelta(days=2)
        }
        await message.reply_text("🎉 **مرحباً بك! تم منحك تجربة مجانية لباقة الـ Pro لمدة يومين بالكامل!**")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 تحميل فيديو / ميديا", callback_data="menu_download")],
        [InlineKeyboardButton("⭐ اشتراكات الـ Pro", callback_data="menu_pro"), InlineKeyboardButton("👤 حسابي", callback_data="menu_account")],
        [InlineKeyboardButton("ℹ️ مساعدة", callback_data="menu_help")]
    ])
    await message.reply_text(
        "🔥 **أهلاً بك في بوت التحميل الاحترافي!**\n\n"
        "أداتك السريعة لتحميل الفيديوهات بدون علامات مائية وبجودات عالية.",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("^menu_"))
async def main_menu_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "menu_download":
        await callback_query.answer()
        await callback_query.message.edit_text("🔗 **أرسل لي الآن رابط الفيديو أو الميديا** وسأقوم بمعالجته فوراً.")
    elif data == "menu_pro":
        await callback_query.answer()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 اشترك الآن (فودافون كاش / إنستاباي)", callback_data="buy_pro")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]
        ])
        await callback_query.message.edit_text(
            "⭐ **قسم مميزات وحزم الـ Pro:**\n\n"
            "- تحميل بلا حدود يومياً (بدون حد الـ 3 فيديوهات).\n"
            "- دعم تحميل الجودات الخارقة 4K.\n"
            "- سرعة أولوية في المعالجة.\n\n"
            "💰 *سعر الاشتراك: 50 جنيهاً شهرياً.*", 
            reply_markup=keyboard
        )
    elif data == "buy_pro":
        await callback_query.answer()
        await callback_query.message.reply_text("💳 للاشتراك في باقة Pro، برجاء تحويل المبلغ على وعبدالعزيز فودافون كاش أو إنستاباي على الرقم: `01012345678` وإرسال صورة الإيصل هنا للمشرف @Admin.")
    elif data == "menu_account":
        await callback_query.answer()
        user_info = user_data.get(user_id, {"downloads": 0, "pro_expiry": None})
        is_pro = user_info["pro_expiry"] and datetime.datetime.now() < user_info["pro_expiry"]
        pro_status = f"مفعل حتى {user_info['pro_expiry'].strftime('%Y-%m-%d')}" if is_pro else "غير مشترك (حساب عادي)"
        rem_downloads = "غير محدود (Pro)" if is_pro else max(0, DAILY_LIMIT - user_info["downloads"])
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]])
        user = callback_query.from_user
        await callback_query.message.edit_text(
            f"👤 **معلومات حسابك:**\n\n"
            f"- الاسم: {user.first_name}\n"
            f"- الحالة: {pro_status}\n"
            f"- التحميلات المتبقية اليوم: {rem_downloads}", 
            reply_markup=keyboard
        )
    elif data == "menu_help":
        await callback_query.answer()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]])
        await callback_query.message.edit_text("ℹ️ **مساعدة:**\nكل ما عليك هو إرسال رابط الفيديو وسيتكفل البوت بالباقي.", reply_markup=keyboard)
    elif data == "menu_back":
        await callback_query.answer()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 تحميل فيديو / ميديا", callback_data="menu_download")],
            [InlineKeyboardButton("⭐ اشتراكات الـ Pro", callback_data="menu_pro"), InlineKeyboardButton("👤 حسابي", callback_data="menu_account")],
            [InlineKeyboardButton("ℹ️ مساعدة", callback_data="menu_help")]
        ])
        await callback_query.message.edit_text("🔥 **القائمة الرئيسية:**", reply_markup=keyboard)

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_url_request(client, message: Message):
    user_id = message.from_user.id
    
    # فحص الحصص والاشتراك
    allowed, status = check_user_limit(user_id)
    if not allowed:
        await message.reply_text("⚠️ **لقد استنفذت الحد اليومي المجاني (3 فيديوهات).**\n\nللاستمتاع بتحميلات غير محدودة، قم ترقية حسابك إلى باقة الـ ⭐ **Pro** من القائمة الرئيسية!")
        return

    url = message.text.strip()
    if not url.startswith("http"):
        await message.reply_text("⚠️ يرجى إرسال رابط صحيح.")
        return

    for bad_word in BLOCKED_KEYWORDS:
        if bad_word in url.lower():
            await message.reply_text("🚫 محتوى محظور.")
            return

    pending_urls[message.id] = url
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 أعلى جودة", callback_data=f"dl_best_{message.id}")],
        [InlineKeyboardButton("🎬 جودة متوسطة", callback_data=f"dl_medium_{message.id}")],
        [InlineKeyboardButton("🎵 صوت فقط (MP3)", callback_data=f"dl_audio_{message.id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_{message.id}")]
    ])
    await message.reply_text("🔗 **تم استلام الرابط بنجاح!** اختر الجودة:", reply_markup=keyboard)

@app.on_callback_query(~filters.regex("^menu_"))
async def callback_query_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    try:
        parts = data.split('_')
        option = parts[1]
        message_id = int(parts[2])
    except:
        return

    url = pending_urls.get(message_id)
    if option == "cancel":
        await callback_query.answer("تم الإلغاء")
        await callback_query.edit_message_text("❌ تم الإلغاء.")
        pending_urls.pop(message_id, None)
        return

    if not url:
        await callback_query.answer("⚠️ انتهت صلاحية الرابط.", show_alert=True)
        return

    # خصم محاولة من رصيد المستخدم اليومي لو مش Pro
    allowed, status = check_user_limit(user_id)
    if status != "pro":
        user_data[user_id]["downloads"] += 1

    await callback_query.answer("جاري التحميل...")
    await callback_query.edit_message_text("☕ ثواني، يتم جلب الفيديو...")

    # إعدادات yt_dlp للتحميل
    ydl_opts = {'quiet': True, 'no_warnings': True}
    if option == "audio":
        filename = f"audio_{message_id}.mp3"
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': filename.replace('.mp3', '.%(ext)s'),
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        })
    elif option == "medium":
        filename = f"video_med_{message_id}.mp4"
        ydl_opts.update({'format': 'best[height<=360]/best[height<=480]/best', 'outtmpl': filename})
    else:
        filename = f"video_{message_id}.mp4"
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'outtmpl': filename})

    downloaded_file = None
    try:
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if option == "audio":
                    base_fn = filename.replace('.mp3', '')
                    for f in os.listdir('.'):
                        if f.startswith(base_fn) and f.endswith('.mp3'):
                            return f
                    return filename
                return ydl.prepare_filename(info)

        downloaded_file = await run_in_executor(download)

        if downloaded_file and os.path.exists(downloaded_file):
            await callback_query.message.reply_text("📤 جاري الإرسال...")
            if option == "audio":
                await callback_query.message.reply_audio(audio=downloaded_file, caption="✅ تم استخراج الصوت بنجاح.")
            else:
                await callback_query.message.reply_video(video=downloaded_file, supports_streaming=True, caption="✅ تم تحميل الفيديو بنجاح.")
            try:
                await callback_query.message.delete()
            except:
                pass
        else:
            await callback_query.message.reply_text("❌ لم نتمكن من جلب الملف.")
    except Exception as e:
        await callback_query.message.reply_text(f"❌ حدث خطأ:\n`{str(e)}`")
    finally:
        pending_urls.pop(message_id, None)
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except:
                pass

if __name__ == "__main__":
    print("البوت الاحترافي يعمل الآن...")
    app.run()
