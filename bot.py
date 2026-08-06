import asyncio
import logging
import os
import zipfile
import re
import time
import requests
import cloudscraper
from PIL import Image
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile

TOKEN = "8804041104:AAGXQzLoXuHqA-ExUUKt7pPAhXyzhu4-WMM"
ADMIN_CHAT_ID = 7369573507

bot = Bot(token=TOKEN)
dp = Dispatcher()

# دوال ومحركات سحب MangaDex
class SimpleScraper:
    def get(self, url, timeout=20, retries=3):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://mangadex.org/'
        }
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    return response
            except Exception:
                if attempt == retries - 1:
                    raise
                asyncio.sleep(1)
        return requests.get(url, headers=headers, timeout=timeout)

scraper = SimpleScraper()

# أدوات ومحركات سحب EZManga
EZ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7',
}

def create_ez_scraper():
    scr = cloudscraper.create_scraper(
        browser={'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    scr.headers.update(EZ_HEADERS)
    return scr

ez_scraper = create_ez_scraper()

# أدوات ومحركات سحب King of Shojo
KOS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://kingofshojo.com/",
}

def create_kos_session():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    session.headers.update(KOS_HEADERS)
    return session

kos_session = create_kos_session()

# أدوات ومحركات سحب Webtoons (مع الكوكيز المدمجة)[cite: 5, 6]
WEBTOON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7',
}

def create_webtoon_session():
    session = requests.Session()
    session.cookies.set('NEO_CHK', 'PZTO+AJBfWvbsLj1CVg9stEuAEb2mHpv1L1WKh7VDC1E4Rpi2zgTVinI/8+6h7B2h2NAy8p9Wtq6PLXhjSNgo3eHjsr8hccXwooIUYlZJQLJpo2WUD9BhF3Ngno4SiEwUjQquhFO5Pas81l9K1HYrQ==', domain='.webtoons.com', path='/')
    session.cookies.set('NEO_SES', '29X8mo/G9oxT+vsFbtwiAaEaV+0IfRUkfVNdVJSUOQ9LDlTkucJGdkIWFUWVGuB4V+7+jL1UKd8V9T2Hnl3ork041WzvSDZRhMuBkVw2uZdETnoRddC8KXEHzW6AQUBmBcM7tzo/ntAVJFkNofeKLDpswWg0bwetsuERWyJnF5QtVrSTziBBJIzQnPRDYx5vv5z+uBLd8qfyiLoEGEBJvI7PsjYJdXR8HIoGcgfy4dFrOS6NupV36eO5ZPNx/Ka3Iz2IN+5hbnwkMkiVdeCovgo2FDOXUPN6gUDrMVmqrcnNlVXB14i2HG+hMuD6vNeCappjTZN2wi0NVEmNZjzTjPR5eoCYLs8y8iNae3r0YtiINMaGxTGwHFe54lnHhxsGHV6k4Okykq8DAcQvtVBnQ7cNqA8nPJuUiHmEYd6DLAw8RgUxgku9oKlN9jiFvZgZ', domain='.webtoons.com', path='/')
    session.headers.update(WEBTOON_HEADERS)
    return session

webtoon_session = create_webtoon_session()

user_sessions = {}
user_favorites = {}
approved_users = set()
pending_registration = {}
user_applications = {}
active_downloads = {}

LANG_FLAGS = {
    "en": "🇬🇧", "es": "🇪🇸", "ar": "🇸🇦", "fr": "🇫🇷",
    "ja": "🇯🇵", "ko": "🇰🇷", "zh": "🇨🇳", "pt": "🇵🇹",
    "it": "🇮🇹", "de": "🇩🇪", "ru": "🇷🇺", "uk": "🇺🇦", "tr": "🇹🇷"
}

@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    if user_id == ADMIN_CHAT_ID or user_id in approved_users:
        await show_sources_menu(message, is_edit=False)
        return

    pending_registration[user_id] = True
    await message.answer(
        "🔒 **نظام حماية البوت:**\n\n"
        "عذراً، يجب عليك التسجيل أولاً.\n"
        "أرسل معلوماتك بالشكل التالي في رسالة واحدة:\n"
        "📌 **التخصص، الرتبة، الفريق**\n\n"
        "*(مثال: مبرمج، قائد فريق، Team Name)*"
    )

async def show_sources_menu(event, is_edit=False):
    source_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 MangaDex", callback_data="set_source_mangadex")],
        [InlineKeyboardButton(text="🟣 EZManga", callback_data="set_source_ezmanga")],
        [InlineKeyboardButton(text="🟠 King of Shojo", callback_data="set_source_kos")],
        [InlineKeyboardButton(text="🔵 Webtoons", callback_data="set_source_webtoon")]
    ])
    
    welcome_text = (
        "🚀 **بوت سحب المانجا والويبتون**\n\n"
        "🌐 **اختر المصدر للبدء:**\n"
        "• **🟢 MangaDex:** بحث مباشر أو سحب نطاق فصول.\n"
        "• **🟣 EZManga:** سحب نطاق فصول برابط العينة.\n"
        "• **🟠 King of Shojo:** سحب نطاق فصول برابط العينة.\n"
        "• **🔵 Webtoons:** دمج وسحب الفصول بملفات مضغوطة.\n\n"
        "💬 **للتواصل:**[cite: 7]@slash7209"
    )
    
    if is_edit:
        await event.message.edit_text(welcome_text, reply_markup=source_keyboard)
    else:
        await event.answer(welcome_text, reply_markup=source_keyboard)

@dp.callback_query(F.data == "set_source_mangadex")
async def set_source_mangadex(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["source"] = "mangadex"
    user_sessions[user_id]["mode"] = "choice"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 بحث عادي واختيار فصل", callback_data="md_mode_search")],
        [InlineKeyboardButton(text="📦 سحب نطاق فصول", callback_data="md_mode_range")],
        [InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_sources")]
    ])
    await callback.message.edit_text("🟢 **MangaDex:**\nاختر طريقة السحب المطلوبة:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "md_mode_search")
async def md_mode_search(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_sessions[user_id]["mangadex_submode"] = "search"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 العودة", callback_data="set_source_mangadex")]
    ])
    await callback.message.edit_text("🟢 **بحث MangaDex:**\nأرسل اسم العمل للبحث عنه:", reply_markup=back_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "md_mode_range")
async def md_mode_range(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_sessions[user_id]["mangadex_submode"] = "range"
    user_sessions[user_id]["step"] = "waiting_url"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 العودة", callback_data="set_source_mangadex")]
    ])
    await callback.message.edit_text("📦 **سحب نطاق من MangaDex:**\nأرسل **رابط عينة فصل** أو آيدي العمل:", reply_markup=back_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "set_source_ezmanga")
async def set_source_ezmanga(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_sessions[user_id] = {"source": "ezmanga", "step": "waiting_url"}
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_sources")]])
    await callback.message.edit_text("🟣 **EZManga:**\nأرسل **رابط عينة لفصل**:", reply_markup=back_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "set_source_kos")
async def set_source_kos(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_sessions[user_id] = {"source": "kos", "step": "waiting_url"}
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_sources")]])
    await callback.message.edit_text("🟠 **King of Shojo:**\nأرسل **رابط عينة لفصل**:", reply_markup=back_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "set_source_webtoon")
async def set_source_webtoon(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_sessions[user_id] = {"source": "webtoon", "step": "waiting_url"}
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_sources")]])
    await callback.message.edit_text("🔵 **Webtoons:**\nأرسل **رابط أي فصل** من الموقع:", reply_markup=back_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "back_to_sources")
async def back_to_sources_callback(callback: CallbackQuery):
    await show_sources_menu(callback, is_edit=True)
    await callback.answer()

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text_messages(message: Message):
    user_id = message.from_user.id
    if pending_registration.get(user_id):
        info_text = message.text.strip()
        user_applications[user_id] = info_text
        pending_registration[user_id] = False
        
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ موافقة", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_{user_id}")
            ]
        ])
        
        user_name = message.from_user.full_name
        username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
        
        admin_msg = (
            "🔔 **طلب انضمام جديد:**\n\n"
            f"👤 الاسم: {user_name} ({username})\n"
            f"🆔 الآيدي: `{user_id}`\n"
            f"📋 المعلومات: {info_text}"
        )
        
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_msg, reply_markup=admin_keyboard)
            await message.answer("⏳ تم إرسال طلبك بنجاح. ينتظر مراجعة المشرف.")
        except Exception:
            await message.answer("❌ حدث خطأ أثناء إرسال الطلب.")
        return

    if user_id != ADMIN_CHAT_ID and user_id not in approved_users:
        await message.answer("🔒 يرجى التسجيل أولاً عبر إرسال `/start`.")
        return

    if user_id not in user_sessions:
        user_sessions[user_id] = {"source": "mangadex", "mangadex_submode": "search"}

    session = user_sessions[user_id]
    source_type = session.get("source", "mangadex")
    text_input = message.text.strip()

    is_range_mode = (source_type in ["ezmanga", "kos", "webtoon"]) or (source_type == "mangadex" and session.get("mangadex_submode") == "range")

    if is_range_mode:
        step = session.get("step", "waiting_url")

        if step == "waiting_url":
            if not text_input.startswith("http"):
                await message.answer("❌ أرسل رابطاً صحيحاً يبدأ بـ http/https.")
                return
            session["sample_url"] = text_input
            session["step"] = "waiting_start_ep"
            await message.answer("▶️ **أدخل رقم الفصل الأول:**")
            return

        elif step == "waiting_start_ep":
            try:
                session["start_ep"] = int(text_input)
                session["step"] = "waiting_end_ep"
                await message.answer("⏹️ **أدخل رقم الفصل الأخير:**")
            except ValueError:
                await message.answer("❌ أرسل رقماً صحيحاً للفصل.")
            return

        elif step == "waiting_end_ep":
            try:
                session["end_ep"] = int(text_input)
            except ValueError:
                await message.answer("❌ أرسل رقماً صحيحاً للفصل الأخير.")
                return

            start_ep = session["start_ep"]
            end_ep = session["end_ep"]
            sample_url = session["sample_url"]

            if start_ep > end_ep:
                await message.answer("❌ رقم البداية أكبر من النهاية. أعد المحاولة.")
                session["step"] = "waiting_url"
                return

            finish_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 سحب آخر", callback_data=f"set_source_{source_type}" if source_type!="mangadex" else "set_source_mangadex")],
                [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_to_sources")]
            ])

            if source_type == "webtoon":
                status_msg = await message.answer("⏳ **جاري تحضير فصول Webtoons...**\n▰▰▰▰▰▰▰▰▰▰ `0%`")
                try:
                    url = sample_url.replace("www.webtoons.com", "m.webtoons.com")
                    if '?' not in url:
                        await status_msg.edit_text("❌ الرابط غير صالح.")
                        session["step"] = "waiting_url"
                        return
                    base, query = url.split('?', 1)
                    params = {}
                    for part in query.split('&'):
                        if '=' in part:
                            k, v = part.split('=', 1)
                            params[k] = v

                    if 'title_no' not in params:
                        await status_msg.edit_text("❌ الرابط لا يحتوي على رقم العمل (title_no).")
                        session["step"] = "waiting_url"
                        return

                    total_chapters = end_ep - start_ep + 1
                    current_processed = 0

                    for ep in range(start_ep, end_ep + 1):
                        current_processed += 1
                        percent = int((current_processed / total_chapters) * 100)
                        filled = percent // 10
                        bar = "▰" * filled + "▱" * (10 - filled)
                        
                        try:
                            await status_msg.edit_text(
                                f"⏳ **سحب Webtoons (فصل {ep})**\n"
                                f"{bar} `{percent}%`"
                            )
                        except:
                            pass

                        new_params = params.copy()
                        new_params['episode_no'] = str(ep)
                        query_str = '&'.join(f"{k}={v}" for k, v in new_params.items())
                        ep_url = f"{base}?{query_str}"

                        try:
                            resp = webtoon_session.get(ep_url, timeout=30)
                            if resp.status_code != 200:
                                continue
                            match = re.search(r'var\s+imageList\s*=\s*(\[.*?\])\s*;', resp.text, re.DOTALL)
                            if not match:
                                continue
                            urls = re.findall(r'url\s*:\s*"([^"]+)"', match.group(1))
                            img_urls = ['https:' + u if u.startswith('//') else u for u in urls]
                            if not img_urls:
                                continue

                            ep_folder = f"webtoon_ch_{ep}_{int(time.time())}"
                            os.makedirs(ep_folder, exist_ok=True)
                            img_headers = WEBTOON_HEADERS.copy()
                            img_headers['Referer'] = ep_url

                            saved_files = []
                            for idx, img_u in enumerate(img_urls, start=1):
                                try:
                                    r = webtoon_session.get(img_u, headers=img_headers, timeout=20)
                                    if r.status_code == 200 and len(r.content) > 500:
                                        fpath = os.path.join(ep_folder, f"{idx:03d}.jpg")
                                        with open(fpath, 'wb') as f:
                                            f.write(r.content)
                                        saved_files.append(fpath)
                                except:
                                    pass

                            if not saved_files:
                                continue

                            batches = [saved_files[i:i+10] for i in range(0, len(saved_files), 10)]
                            if len(batches) > 1 and len(batches[-1]) < 5:
                                batches[-2].extend(batches[-1])
                                batches.pop()

                            merged_folder = f"webtoon_merged_{ep}"
                            os.makedirs(merged_folder, exist_ok=True)
                            for b_idx, batch in enumerate(batches, start=1):
                                images = [Image.open(f).convert('RGB') for f in batch]
                                max_w = max(im.width for im in images)
                                total_h = sum(im.height for im in images)
                                merged = Image.new('RGB', (max_w, total_h), color='white')
                                y_off = 0
                                for im in images:
                                    x_off = (max_w - im.width) // 2
                                    merged.paste(im, (x_off, y_off))
                                    y_off += im.height
                                merged.save(os.path.join(merged_folder, f"P_{b_idx:03d}.jpg"), 'JPEG', quality=95)

                            zip_filename = f"Webtoon_Chapter_{ep}.zip"
                            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                                for root, dirs, files in os.walk(merged_folder):
                                    for file in files:
                                        zipf.write(os.path.join(root, file), arcname=file)

                            if os.path.exists(zip_filename) and os.path.getsize(zip_filename) > 0:
                                with open(zip_filename, "rb") as f:
                                    zip_bytes = f.read()
                                input_file = BufferedInputFile(zip_bytes, filename=zip_filename)
                                await message.answer_document(
                                    document=input_file,
                                    caption=f"📦 **فصل Webtoons ({ep})**"
                                )
                                os.remove(zip_filename)

                            for f in saved_files:
                                if os.path.exists(f): os.remove(f)
                            for root, dirs, files in os.walk(merged_folder, topdown=False):
                                for name in files: os.remove(os.path.join(root, name))
                                for name in dirs: os.rmdir(os.path.join(root, name))
                            if os.path.exists(merged_folder): os.rmdir(merged_folder)
                            if os.path.exists(ep_folder): os.rmdir(ep_folder)

                        except Exception:
                            continue

                    await status_msg.edit_text("✅ **تم الانتهاء من سحب وإرسال فصول Webtoons بنجاح!**", reply_markup=finish_keyboard)
                except Exception as e:
                    await status_msg.edit_text(f"❌ حدث خطأ: {str(e)}")
                
                session["step"] = "waiting_url"
                return

            if source_type in ["ezmanga", "kos"]:
                scraper_obj = ez_scraper if source_type == "ezmanga" else kos_session
                site_label = "EZManga" if source_type == "ezmanga" else "King of Shojo"
                status_msg = await message.answer(f"⏳ **جاري تحضير فصول {site_label}...**\n▰▰▰▰▰▰▰▰▰▰ `0%`")

                try:
                    total_chapters = end_ep - start_ep + 1
                    current_processed = 0

                    for ep in range(start_ep, end_ep + 1):
                        current_processed += 1
                        percent = int((current_processed / total_chapters) * 100)
                        filled = percent // 10
                        bar = "▰" * filled + "▱" * (10 - filled)
                        
                        try:
                            await status_msg.edit_text(
                                f"⏳ **سحب {site_label} (فصل {ep})**\n"
                                f"{bar} `{percent}%`"
                            )
                        except:
                            pass

                        ep_url = re.sub(r'chapter-\d+', f'chapter-{ep}', sample_url)
                        try:
                            resp = scraper_obj.get(ep_url, timeout=30)
                            if resp.status_code != 200:
                                continue

                            if source_type == "ezmanga":
                                img_urls = re.findall(r'<img[^>]+src="(https?://media\.ezmanga\.org/[^"]+\.webp)"', resp.text)
                            else:
                                reader_match = re.search(r'<div[^>]+id="readerarea"[^>]*>(.*?)</div>', resp.text, re.DOTALL)
                                if not reader_match:
                                    continue
                                raw_urls = re.findall(r'<img[^>]+src="([^"]+)"', reader_match.group(1), re.IGNORECASE)
                                img_urls = ['https:' + u if u.startswith('//') else u for u in raw_urls if 'wp-content' in u or 'jpg' in u or 'png' in u]

                            if not img_urls:
                                continue

                            ep_folder = f"{source_type}_ch_{ep}_{int(time.time())}"
                            os.makedirs(ep_folder, exist_ok=True)

                            for i, img_u in enumerate(img_urls, start=1):
                                img_resp = scraper_obj.get(img_u, headers={'Referer': ep_url}, timeout=20)
                                if img_resp.status_code == 200 and len(img_resp.content) > 500:
                                    path_jpg = os.path.join(ep_folder, f"{i:03d}.jpg")
                                    path_webp = os.path.join(ep_folder, f"{i:03d}.webp")
                                    with open(path_webp, 'wb') as f:
                                        f.write(img_resp.content)
                                    im = Image.open(path_webp).convert('RGB')
                                    im.save(path_jpg, 'JPEG', quality=95)
                                    if os.path.exists(path_webp):
                                        os.remove(path_webp)

                            zip_filename = f"{site_label}_Chapter_{ep}.zip"
                            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                                for root, dirs, files in os.walk(ep_folder):
                                    for file in files:
                                        zipf.write(os.path.join(root, file), arcname=file)

                            if os.path.exists(zip_filename) and os.path.getsize(zip_filename) > 0:
                                with open(zip_filename, "rb") as f:
                                    zip_bytes = f.read()
                                input_file = BufferedInputFile(zip_bytes, filename=zip_filename)
                                await message.answer_document(
                                    document=input_file,
                                    caption=f"📦 **فصل {site_label} ({ep})**"
                                )
                                os.remove(zip_filename)

                            for root, dirs, files in os.walk(ep_folder, topdown=False):
                                for name in files: os.remove(os.path.join(root, name))
                                for name in dirs: os.rmdir(os.path.join(root, name))
                            os.rmdir(ep_folder)

                        except:
                            continue

                    await status_msg.edit_text(f"✅ **تم الانتهاء من فصول {site_label} بنجاح!**", reply_markup=finish_keyboard)
                except Exception as e:
                    await status_msg.edit_text(f"❌ حدث خطأ: {str(e)}")

                session["step"] = "waiting_url"
                return

            if source_type == "mangadex" and session.get("mangadex_submode") == "range":
                status_msg = await message.answer("⏳ **جاري جلب فصول MangaDex...**\n▰▰▰▰▰▰▰▰▰▰ `0%`")
                try:
                    manga_id = None
                    if "mangadex.org/title/" in sample_url:
                        parts = sample_url.split("/title/")[-1].split("/")
                        manga_id = parts[0]
                    else:
                        s_resp = scraper.get(f"https://api.mangadex.org/manga?title={sample_url}&limit=1", timeout=20).json()
                        if s_resp.get("data"):
                            manga_id = s_resp["data"][0]["id"]

                    if not manga_id:
                        await status_msg.edit_text("❌ لم يتم العثور على العمل.")
                        session["step"] = "waiting_url"
                        return

                    ch_url = f"https://api.mangadex.org/manga/{manga_id}/feed?translatedLanguage[]=en&translatedLanguage[]=es&translatedLanguage[]=ar&order[chapter]=asc&limit=500"
                    ch_data = scraper.get(ch_url, timeout=20).json()
                    raw_ch = ch_data.get("data", [])
                    if not raw_ch:
                        ch_url = f"https://api.mangadex.org/manga/{manga_id}/feed?order[chapter]=asc&limit=500"
                        raw_ch = scraper.get(ch_url, timeout=20).json().get("data", [])

                    target_chapters = []
                    for ch in raw_ch:
                        ch_num_str = ch["attributes"].get("chapter", "0")
                        try:
                            ch_num_val = float(ch_num_str)
                            if start_ep <= ch_num_val <= end_ep:
                                target_chapters.append(ch)
                        except:
                            pass

                    if not target_chapters:
                        await status_msg.edit_text("❌ لم يتم العثور على فصول ضمن هذا النطاق.")
                        session["step"] = "waiting_url"
                        return

                    total_chapters = len(target_chapters)
                    current_processed = 0

                    for ch in target_chapters:
                        current_processed += 1
                        percent = int((current_processed / total_chapters) * 100)
                        filled = percent // 10
                        bar = "▰" * filled + "▱" * (10 - filled)
                        ch_num = ch["attributes"].get("chapter", "0")

                        try:
                            await status_msg.edit_text(
                                f"⏳ **سحب MangaDex (فصل {ch_num})**\n"
                                f"{bar} `{percent}%`"
                            )
                        except:
                            pass

                        ch_id = ch["id"]
                        at_home = scraper.get(f"https://api.mangadex.org/at-home/server/{ch_id}", timeout=20).json()
                        base_url = at_home.get("baseUrl")
                        ch_hash = at_home["chapter"]["hash"]
                        img_files = at_home["chapter"]["data"]

                        if not base_url or not img_files:
                            continue

                        ep_folder = f"md_ch_{ch_num}_{int(time.time())}"
                        os.makedirs(ep_folder, exist_ok=True)

                        for sub_i, filename in enumerate(img_files, start=1):
                            img_u = f"{base_url}/data/{ch_hash}/{filename}"
                            try:
                                img_data = scraper.get(img_u, timeout=15).content
                                with open(os.path.join(ep_folder, f"{sub_i:03d}.jpg"), 'wb') as f:
                                    f.write(img_data)
                            except:
                                pass

                        zip_filename = f"MangaDex_Chapter_{ch_num}.zip"
                        with zipfile.ZipFile(zip_filename, 'w') as zipf:
                            for root, dirs, files in os.walk(ep_folder):
                                for file in files:
                                    zipf.write(os.path.join(root, file), arcname=file)

                        if os.path.exists(zip_filename) and os.path.getsize(zip_filename) > 0:
                            with open(zip_filename, "rb") as f:
                                zip_bytes = f.read()
                            input_file = BufferedInputFile(zip_bytes, filename=zip_filename)
                            await message.answer_document(
                                document=input_file,
                                caption=f"📦 **فصل MangaDex ({ch_num})**"
                            )
                            os.remove(zip_filename)

                        for root, dirs, files in os.walk(ep_folder, topdown=False):
                            for name in files: os.remove(os.path.join(root, name))
                            for name in dirs: os.rmdir(os.path.join(root, name))
                        os.rmdir(ep_folder)

                    await status_msg.edit_text("✅ **تم الانتهاء من إرسال جميع الفصول بنجاح!**", reply_markup=finish_keyboard)
                except Exception as e:
                    await status_msg.edit_text(f"❌ حدث خطأ: `{str(e)}`")

                session["step"] = "waiting_url"
                return

    if source_type == "mangadex" and session.get("mangadex_submode", "search") == "search":
        query = text_input
        await message.answer(f"🔍 جاري البحث...")
        
        try:
            search_url = f"https://api.mangadex.org/manga?title={query}&limit=1"
            response = scraper.get(search_url, timeout=20)
            data = response.json()
            
            if not data.get("data"):
                await message.answer("❌ لم يتم العثور على نتائج.")
                return
                
            manga_id = data["data"][0]["id"]
            manga_title = data["data"][0]["attributes"]["title"].get("en") or list(data["data"][0]["attributes"]["title"].values())[0]
            
            chapters_url = f"https://api.mangadex.org/manga/{manga_id}/feed?translatedLanguage[]=en&translatedLanguage[]=es&translatedLanguage[]=ar&order[chapter]=asc&limit=500"
            ch_response = scraper.get(chapters_url, timeout=20)
            ch_data = ch_response.json()
            
            raw_chapters = ch_data.get("data", [])
            if not raw_chapters:
                fallback_url = f"https://api.mangadex.org/manga/{manga_id}/feed?order[chapter]=asc&limit=500"
                ch_response = scraper.get(fallback_url, timeout=20)
                ch_data = ch_response.json()
                raw_chapters = ch_data.get("data", [])
                
            if not raw_chapters:
                await message.answer("❌ لا توجد فصول متاحة.")
                return
                
            chapters = []
            for ch in raw_chapters:
                attr = ch["attributes"]
                ch_num = attr.get("chapter", "0")
                ch_lang = attr.get("translatedLanguage", "en").lower()
                flag = LANG_FLAGS.get(ch_lang, "🌐")
                chapters.append({"title": f"فصل {ch_num} {flag}", "id": ch["id"]})
                
            session["manga_id"] = manga_id
            session["chapters"] = chapters
            session["title"] = manga_title
            session["page"] = 0
            
            await send_chapters_page(message, user_id, edit=False)
                
        except Exception as e:
            await message.answer(f"❌ حدث خطأ: `{str(e)}`")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: CallbackQuery):
    target_user_id = int(callback.data.replace("approve_", ""))
    approved_users.add(target_user_id)
    await callback.message.edit_text(callback.message.text + "\n\n✅ **[تمت الموافقة]**")
    try:
        await bot.send_message(target_user_id, "🎉 تمت الموافقة على طلبك.\nاضغط على `/start` لبدء الاستخدام.")
    except Exception:
        pass
    await callback.answer("تمت الموافقة بنجاح!")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_user(callback: CallbackQuery):
    target_user_id = int(callback.data.replace("reject_", ""))
    await callback.message.edit_text(callback.message.text + "\n\n❌ **[تم الرفض]**")
    try:
        await bot.send_message(target_user_id, "❌ نأسف، لم يتم قبول طلبك.")
    except Exception:
        pass
    await callback.answer("تم الرفض.")

@dp.message(Command("favorites"))
async def show_favorites_command(message: Message):
    await render_favorites(message, user_id=message.from_user.id, is_edit=False)

async def render_favorites(event, user_id, is_edit=True):
    favs = user_favorites.get(user_id, {})
    keyboard_buttons = []
    for manga_id, manga_title in favs.items():
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"📖 {manga_title}", callback_data=f"fav_select_{manga_id}"),
            InlineKeyboardButton(text="❌ حذف", callback_data=f"fav_del_{manga_id}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="➕ إضافة أعمال أخرى", callback_data="back_to_sources")
    ])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    text = "⭐ **المفضلة لديك:**" if favs else "⭐ قائمة المفضلة فارغة."
    
    if is_edit:
        await event.message.edit_text(text, reply_markup=keyboard)
    else:
        await event.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "show_favorites_menu")
async def show_favorites_callback(callback: CallbackQuery):
    await render_favorites(callback, user_id=callback.from_user.id, is_edit=True)
    await callback.answer()

async def send_chapters_page(event, user_id, edit=True):
    session = user_sessions.get(user_id)
    if not session:
        return
        
    chapters = session["chapters"]
    manga_title = session["title"]
    manga_id = session["manga_id"]
    page = session["page"]
    
    per_page = 20
    total_pages = (len(chapters) + per_page - 1) // per_page
    start_idx = page * per_page
    current_chapters = chapters[start_idx:start_idx + per_page]
    
    keyboard_buttons = []
    row = []
    
    for idx, ch in enumerate(current_chapters):
        actual_idx = start_idx + idx
        row.append(InlineKeyboardButton(text=ch["title"], callback_data=f"get_manga_ch_{actual_idx}"))
        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []
    if row:
        keyboard_buttons.append(row)
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data="nav_prev"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data="nav_next"))
    keyboard_buttons.append(nav_row)
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="⭐ حفظ", callback_data=f"save_fav_{manga_id}"),
        InlineKeyboardButton(text="⭐ المفضلة", callback_data="show_favorites_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    text = f"📖 **العمل:** {manga_title}\n📌 الفصول: {len(chapters)}\nاختر الفصل للتحميل:"
    
    if edit:
        await event.message.edit_text(text, reply_markup=keyboard)
    else:
        await event.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("save_fav_"))
async def save_to_favorites(callback: CallbackQuery):
    user_id = callback.from_user.id
    manga_id = callback.data.replace("save_fav_", "")
    session = user_sessions.get(user_id)
    
    if not session or session.get("manga_id") != manga_id:
        await callback.answer("❌ حدث خطأ، ابحث مجدداً.", show_alert=True)
        return
        
    if user_id not in user_favorites:
        user_favorites[user_id] = {}
        
    user_favorites[user_id][manga_id] = session["title"]
    await callback.answer("⭐ تم الحفظ في المفضلة!", show_alert=True)

@dp.callback_query(F.data.startswith("fav_select_"))
async def select_favorite_manga(callback: CallbackQuery):
    user_id = callback.from_user.id
    manga_id = callback.data.replace("fav_select_", "")
    favs = user_favorites.get(user_id, {})
    
    if manga_id not in favs:
        await callback.answer("❌ غير موجود بالمفضلة.", show_alert=True)
        return
        
    manga_title = favs[manga_id]
    await callback.message.edit_text(f"⏳ جاري جلب الفصول ({manga_title})...")
    
    try:
        chapters_url = f"https://api.mangadex.org/manga/{manga_id}/feed?translatedLanguage[]=en&translatedLanguage[]=es&translatedLanguage[]=ar&order[chapter]=asc&limit=500"
        ch_response = scraper.get(chapters_url, timeout=20)
        ch_data = ch_response.json()
        
        raw_chapters = ch_data.get("data", [])
        chapters = []
        for ch in raw_chapters:
            attr = ch["attributes"]
            ch_num = attr.get("chapter", "0")
            ch_lang = attr.get("translatedLanguage", "en").lower()
            flag = LANG_FLAGS.get(ch_lang, "🌐")
            chapters.append({"title": f"فصل {ch_num} {flag}", "id": ch["id"]})
            
        user_sessions[user_id] = {"manga_id": manga_id, "chapters": chapters, "title": manga_title, "page": 0, "source": "mangadex", "mangadex_submode": "search"}
        await send_chapters_page(callback, user_id, edit=True)
    except Exception as e:
        await callback.message.answer(f"❌ حدث خطأ: `{str(e)}`")

@dp.callback_query(F.data.startswith("fav_del_"))
async def delete_favorite_manga(callback: CallbackQuery):
    user_id = callback.from_user.id
    manga_id = callback.data.replace("fav_del_", "")
    
    if user_id in user_favorites and manga_id in user_favorites[user_id]:
        del user_favorites[user_id][manga_id]
        await callback.answer("🗑️ تم الحذف.", show_alert=True)
        await render_favorites(callback, user_id, is_edit=True)
    else:
        await callback.answer("❌ غير موجود.", show_alert=True)

@dp.callback_query(F.data.in_({"nav_prev", "nav_next"}))
async def handle_pagination(callback: CallbackQuery):
    user_id = callback.from_user.id
    session = user_sessions.get(user_id)
    if not session:
        await callback.answer("❌ انتهت الجلسة.", show_alert=True)
        return
        
    per_page = 20
    total_pages = (len(session["chapters"]) + per_page - 1) // per_page
    
    if callback.data == "nav_next" and session["page"] < total_pages - 1:
        session["page"] += 1
    elif callback.data == "nav_prev" and session["page"] > 0:
        session["page"] -= 1
        
    await send_chapters_page(callback, user_id, edit=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("get_manga_ch_"))
async def confirm_chapter_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    ch_idx = int(callback.data.replace("get_manga_ch_", ""))
    session = user_sessions.get(user_id)
    
    if not session or "chapters" not in session:
        await callback.message.edit_text("❌ انتهت الجلسة.")
        return
        
    chapter_info = session["chapters"][ch_idx]
    ch_title = chapter_info["title"]
    
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 نعم", callback_data=f"do_dl_{ch_idx}"),
            InlineKeyboardButton(text="🔴 لا", callback_data=f"cancel_dl_{ch_idx}")
        ],
        [InlineKeyboardButton(text="🔄 اختيار آخر", callback_data="back_to_chapters_list")]
    ])
    
    await callback.message.edit_text(
        f"❓ **تأكيد تحميل:**\n📌 **{ch_title}**",
        reply_markup=confirm_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_chapters_list")
async def back_to_chapters_list_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await send_chapters_page(callback, user_id, edit=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("cancel_dl_"))
async def cancel_dl_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await send_chapters_page(callback, user_id, edit=True)
    await callback.answer("تم الإلغاء.")

@dp.callback_query(F.data == "cancel_download")
async def cancel_download_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_downloads[user_id] = False
    await callback.answer("⏹️ جاري إيقاف السحب...", show_alert=True)

@dp.callback_query(F.data.startswith("do_dl_"))
async def handle_chapter_download(callback: CallbackQuery):
    user_id = callback.from_user.id
    ch_idx = int(callback.data.replace("do_dl_", ""))
    
    session = user_sessions.get(user_id)
    if not session or "chapters" not in session:
        await callback.message.edit_text("❌ انتهت الجلسة.")
        return
        
    chapter_info = session["chapters"][ch_idx]
    ch_id = chapter_info["id"]
    ch_title = chapter_info["title"]
    active_downloads[user_id] = True
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹️ إيقاف", callback_data="cancel_download")]
    ])
    
    status_msg = await callback.message.edit_text(
        f"⏳ **جاري تحضير ({ch_title})...**\n\n"
        f"▰▰▰▰▰▰▰▰▰▰ `0%`", 
        reply_markup=cancel_keyboard
    )
    
    try:
        at_home_url = f"https://api.mangadex.org/at-home/server/{ch_id}"
        resp = scraper.get(at_home_url, timeout=20).json()
        
        base_url = resp.get("baseUrl")
        chapter_hash = resp["chapter"]["hash"]
        image_filenames = resp["chapter"]["data"]
        
        if not base_url or not image_filenames:
            await status_msg.edit_text("❌ تعذر جلب مسارات الصور.")
            return
            
        safe_title_name = "".join([c if c.isalnum() else "_" for c in ch_title])
        total_images = len(image_filenames)
        chunk_size = 10
        total_chunks = (total_images + chunk_size - 1) // chunk_size
        part_num = 1
        
        for i in range(0, total_images, chunk_size):
            if not active_downloads.get(user_id, True):
                await status_msg.edit_text("⏹️ **تم إيقاف السحب بنجاح.**")
                return

            current_chunk_idx = (i // chunk_size) + 1
            percent = int((current_chunk_idx / total_chunks) * 100)
            filled_blocks = int(percent / 10)
            empty_blocks = 10 - filled_blocks
            bar_str = "▰" * filled_blocks + "▱" * empty_blocks

            try:
                await status_msg.edit_text(
                    f"⏳ **جاري السحب ({ch_title}) - جزء {current_chunk_idx}/{total_chunks}**\n\n"
                    f"{bar_str} `{percent}%`",
                    reply_markup=cancel_keyboard
                )
            except:
                pass

            chunk = image_filenames[i:i + chunk_size]
            zip_filename = f"Manga_{safe_title_name}_Part{part_num}.zip"
            
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for sub_idx, filename in enumerate(chunk, 1):
                    img_url = f"{base_url}/data/{chapter_hash}/{filename}"
                    try:
                        img_data = scraper.get(img_url, timeout=15, retries=3).content
                        zipf.writestr(f"page_{sub_idx:02d}.jpg", img_data)
                    except Exception:
                        continue
                        
            if not os.path.exists(zip_filename) or os.path.getsize(zip_filename) == 0:
                continue

            with open(zip_filename, "rb") as f:
                zip_bytes = f.read()
                
            input_file = BufferedInputFile(zip_bytes, filename=zip_filename)
            
            sent_successfully = False
            for attempt in range(5):
                try:
                    await callback.message.answer_document(
                        document=input_file,
                        caption=f"📦 **{ch_title} - الجزء {part_num}**"
                    )
                    sent_successfully = True
                    break
                except Exception:
                    await asyncio.sleep(3)

            if not sent_successfully:
                await callback.message.answer(f"⚠️ تعذر إرسال الجزء {part_num}.")
            
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
                
            part_num += 1
            await asyncio.sleep(0.5)
            
        finish_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 سحب آخر", callback_data="set_source_mangadex")],
            [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_to_sources")]
        ])
        await status_msg.edit_text(f"✅ **تم إرسال كافة أجزاء ({ch_title}) بنجاح!**", reply_markup=finish_keyboard)
    except Exception as e:
        try:
            await status_msg.edit_text(f"❌ حدث خطأ: {str(e)}")
        except:
            pass

async def main():
    print("البوت يعمل الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
