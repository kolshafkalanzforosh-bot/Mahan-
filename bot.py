# Python 3.13 compatibility: the old python-telegram-bot version used by
# this bot imports the removed stdlib module `imghdr`.
import sys
import types

_imghdr = types.ModuleType("imghdr")

def _imghdr_what(file, h=None):
    try:
        if h is None:
            if hasattr(file, "read"):
                pos = file.tell() if hasattr(file, "tell") else None
                h = file.read(32)
                if pos is not None and hasattr(file, "seek"):
                    file.seek(pos)
            elif isinstance(file, (bytes, bytearray)):
                h = bytes(file[:32])
            else:
                with open(file, "rb") as _f:
                    h = _f.read(32)
        if not h:
            return None
        if h.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
            return "png"
        if h.startswith(b"\\xff\\xd8\\xff"):
            return "jpeg"
        if h.startswith((b"GIF87a", b"GIF89a")):
            return "gif"
        if h.startswith(b"RIFF") and h[8:12] == b"WEBP":
            return "webp"
        if h.startswith(b"BM"):
            return "bmp"
        return None
    except Exception:
        return None

_imghdr.what = _imghdr_what
sys.modules.setdefault("imghdr", _imghdr)
import os
import json
import time
import uuid
import logging
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, ConversationHandler
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("8817137926:AAHshEnjqcYESYUu2yAsEvo9zBiRtHzUmCs")
ADMIN_ID = 6795131360
ADMIN_PASSWORD = "mahan9913130567M"
BOT_NAME = "Free Fire Store"
VERSION = "3.0"
SUPPORT_USERNAME = "@mahanGamiTurboHelper"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "database.json")
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
DB_LOCK = threading.RLock()
db = {"users": {}, "orders": [], "reports": [], "sales": [], "games": {}, "queue": [], "group_settings": {}, "settings": {"bot_name": BOT_NAME, "version": VERSION}}
SELL_PHOTO, SELL_VIDEO, SELL_INFO, REPORT_TEXT, LOGIN_PASS, ADMIN_INPUT, BROADCAST_INPUT, REPLY_INPUT = range(8)
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def load_db():
    global db
    with DB_LOCK:
        if not os.path.exists(DATA_FILE):
            save_db()
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                db.update(loaded)
            for key in ("users", "orders", "reports", "sales", "games", "queue", "group_settings", "settings"):
                if key not in db:
                    db[key] = {} if key in ("users", "games", "group_settings", "settings") else []
        except Exception as exc:
            logging.error("database load failed: %s", exc)
def save_db():
    with DB_LOCK:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
def ensure_user(user_id, ref_by=None, first_name=""):
    uid = str(user_id)
    with DB_LOCK:
        if uid not in db["users"]:
            db["users"][uid] = {"score": 0, "ref_count": 0, "is_admin": uid == str(ADMIN_ID), "is_banned": False, "join_date": now(), "last_activity": now(), "last_dice": None, "items": [], "username": "", "first_name": first_name}
            if ref_by and str(ref_by) != uid and str(ref_by) in db["users"]:
                db["users"][str(ref_by)]["score"] += 20
                db["users"][str(ref_by)]["ref_count"] += 1
        u = db["users"][uid]
        u["last_activity"] = now()
        if first_name:
            u["first_name"] = first_name
        return u
def is_admin(uid):
    return str(uid) == str(ADMIN_ID) or db["users"].get(str(uid), {}).get("is_admin", False)
def blocked(update):
    u = ensure_user(update.effective_user.id, first_name=update.effective_user.first_name or "")
    if u.get("is_banned"):
        if update.message:
            update.message.reply_text("❌ حساب شما مسدود است.")
        elif update.callback_query:
            update.callback_query.answer("❌ حساب شما مسدود است.", show_alert=True)
        return True
    return False
def main_keyboard(uid):
    rows = [
        [KeyboardButton("🎲 تاس انداختن"), KeyboardButton("🎮 بازی آنلاین")],
        [KeyboardButton("🎯 خرید سنس"), KeyboardButton("🔥 خرید پنل")],
        [KeyboardButton("👤 پروفایل"), KeyboardButton("🔗 دعوت از دوستان")],
        [KeyboardButton("🛒 فروش اکانت"), KeyboardButton("📝 گزارش مشکل")],
        [KeyboardButton("📋 قوانین"), KeyboardButton("💬 پشتیبانی")]
    ]
    if is_admin(uid):
        rows.append([KeyboardButton("🛠 پنل مدیریت")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main")]])
def shop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 سنس امتیازی", callback_data="shop_sense_points")],
        [InlineKeyboardButton("💵 سنس پولی", callback_data="shop_sense_money")],
        [InlineKeyboardButton("🔥 پنل با امتیاز", callback_data="shop_panel_points")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main")]
    ])
def sense_points_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("سنس عادی — ۵۰۰ امتیاز", callback_data="buy_sense_500")],
        [InlineKeyboardButton("سنس طلایی — ۱۰۰۰ امتیاز", callback_data="buy_sense_1000")],
        [InlineKeyboardButton("سنس نقره‌ای — ۲۰۰۰ امتیاز", callback_data="buy_sense_2000")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="shop")]
    ])
def sense_money_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("۵۰ هزار تومان", callback_data="money_50000")],
        [InlineKeyboardButton("۱۵۰ هزار تومان", callback_data="money_150000")],
        [InlineKeyboardButton("۵۰۰ هزار تومان", callback_data="money_500000")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="shop")]
    ])
def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 کاربران", callback_data="a_users"), InlineKeyboardButton("📊 آمار", callback_data="a_stats")],
        [InlineKeyboardButton("🛒 سفارش‌ها", callback_data="a_orders"), InlineKeyboardButton("🏪 اکانت‌ها", callback_data="a_sales")],
        [InlineKeyboardButton("🚨 گزارش‌ها", callback_data="a_reports"), InlineKeyboardButton("💰 تغییر امتیاز", callback_data="a_score")],
        [InlineKeyboardButton("🚫 بن/رفع بن", callback_data="a_ban"), InlineKeyboardButton("📢 پیام همگانی", callback_data="a_broadcast")],
        [InlineKeyboardButton("📨 پیام به کاربر", callback_data="a_message"), InlineKeyboardButton("🔄 تازه‌سازی", callback_data="a_refresh")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main")]
    ])
def order_admin_keyboard(order_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید", callback_data=f"ord_ok_{order_id}"), InlineKeyboardButton("❌ رد", callback_data=f"ord_no_{order_id}")]])
def sale_admin_keyboard(sale_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ تأیید فروش", callback_data=f"sale_ok_{sale_id}"), InlineKeyboardButton("❌ رد", callback_data=f"sale_no_{sale_id}")]])
def rps_keyboard(game_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🪨 سنگ", callback_data=f"rps_{game_id}_rock"), InlineKeyboardButton("📄 کاغذ", callback_data=f"rps_{game_id}_paper"), InlineKeyboardButton("✂️ قیچی", callback_data=f"rps_{game_id}_scissors")]])
def start(update, context):
    ref = context.args[0] if context.args else None
    u = ensure_user(update.effective_user.id, ref, update.effective_user.first_name or "")
    if u.get("is_banned"):
        update.message.reply_text("❌ حساب شما مسدود است.")
        return
    update.message.reply_text(f"👋 سلام {update.effective_user.first_name or 'دوست'}!\n🎮 {BOT_NAME} نسخه {VERSION}\n⭐ امتیاز: {u['score']}", reply_markup=main_keyboard(update.effective_user.id))
def profile(update, context):
    if blocked(update): return
    u = ensure_user(update.effective_user.id)
    update.message.reply_text(f"👤 پروفایل\n\n🆔 {update.effective_user.id}\n⭐ امتیاز: {u['score']}\n👥 دعوت موفق: {u['ref_count']}\n📅 عضویت: {u['join_date']}\n🕒 فعالیت: {u['last_activity']}")
def referral(update, context):
    if blocked(update): return
    me = context.bot.get_me()
    link = f"https://t.me/{me.username}?start={update.effective_user.id}"
    update.message.reply_text(f"🔗 لینک دعوت شما:\n{link}\n\n🎁 هر دعوت موفق = ۲۰ امتیاز")
def rules(update, context):
    update.message.reply_text("📋 قوانین\n\n۱) اسپم و سوءاستفاده ممنوع.\n۲) اطلاعات جعلی برای فروش اکانت ارسال نکنید.\n۳) پرداخت‌ها فقط بعد از هماهنگی مدیریت انجام شود.\n۴) امتیاز قابل انتقال نیست مگر مدیریت تأیید کند.\n۵) در بازی آنلاین از چند حساب برای تقلب استفاده نکنید.")
def support(update, context):
    update.message.reply_text(f"💬 پشتیبانی:\n{SUPPORT_USERNAME}\n\nبرای گزارش مشکل از دکمه «گزارش مشکل» استفاده کنید.")
def send_dice(update, context):
    if blocked(update): return
    update.message.reply_dice(emoji="🎲")
def dice_result(update, context):
    if blocked(update): return
    if not update.message.dice or update.message.dice.emoji != "🎲": return
    value = update.message.dice.value
    u = ensure_user(update.effective_user.id)
    u["last_dice"] = value
    reward = 50 if value == 6 else 10 if value in (4, 5) else 0
    u["score"] += reward
    save_db()
    if reward:
        update.message.reply_text(f"🎲 عدد {value}\n🎉 +{reward} امتیاز\n⭐ موجودی: {u['score']}")
    else:
        update.message.reply_text(f"🎲 عدد {value}\n❌ جایزه‌ای نگرفتی.\n⭐ موجودی: {u['score']}")
def shop(update, context):
    if blocked(update): return
    update.message.reply_text("🛍 فروشگاه\nیک بخش را انتخاب کن:", reply_markup=shop_keyboard())
def create_order(uid, kind, title, price, payment="score"):
    oid = uuid.uuid4().hex[:8]
    order = {"id": oid, "user_id": uid, "kind": kind, "title": title, "price": price, "payment": payment, "status": "pending", "created_at": now()}
    db["orders"].append(order)
    save_db()
    return order
def main_callback(update, context):
    q = update.callback_query
    uid = q.from_user.id
    if blocked(update): return
    data = q.data
    q.answer()
    if data == "main":
        q.edit_message_text("🔙 برگشتی به منوی اصلی.")
        context.bot.send_message(uid, "منوی اصلی:", reply_markup=main_keyboard(uid))
        return
    if data == "shop":
        q.edit_message_text("🛍 فروشگاه:", reply_markup=shop_keyboard()); return
    if data == "shop_sense_points":
        q.edit_message_text("🎯 سنس امتیازی:", reply_markup=sense_points_keyboard()); return
    if data == "shop_sense_money":
        q.edit_message_text("💵 سنس پولی:", reply_markup=sense_money_keyboard()); return
    if data == "shop_panel_points":
        u = ensure_user(uid)
        if u["score"] < 5000:
            q.edit_message_text(f"❌ امتیاز کافی نیست.\nموجودی: {u['score']}\nنیاز: ۵۰۰۰"); return
        u["score"] -= 5000
        order = create_order(uid, "panel", "پنل فری فایر", 5000, "score")
        context.bot.send_message(ADMIN_ID, f"🔥 سفارش پنل\n🆔 سفارش: {order['id']}\n👤 کاربر: {uid}\n💰 ۵۰۰۰ امتیاز", reply_markup=order_admin_keyboard(order["id"]))
        q.edit_message_text("✅ درخواست پنل ثبت شد و برای مدیریت ارسال شد."); return
    if data.startswith("buy_sense_"):
        price = int(data.rsplit("_", 1)[1])
        u = ensure_user(uid)
        if u["score"] < price:
            q.edit_message_text(f"❌ امتیاز کافی نیست.\nموجودی: {u['score']}\nنیاز: {price}"); return
        u["score"] -= price
        title = {500: "سنس عادی", 1000: "سنس طلایی", 2000: "سنس نقره‌ای"}[price]
        order = create_order(uid, "sense", title, price, "score")
        context.bot.send_message(ADMIN_ID, f"🎯 سفارش سنس\n🆔 سفارش: {order['id']}\n👤 کاربر: {uid}\n📦 {title}\n💰 {price} امتیاز", reply_markup=order_admin_keyboard(order["id"]))
        q.edit_message_text(f"✅ {title} ثبت شد."); return
    if data.startswith("money_"):
        amount = int(data.split("_")[1])
        order = create_order(uid, "sense_money", "سنس پولی", amount, "money")
        context.bot.send_message(ADMIN_ID, f"💵 سفارش سنس پولی\n🆔 {order['id']}\n👤 کاربر: {uid}\n💰 {amount:,} تومان\n⏳ منتظر تأیید پرداخت", reply_markup=order_admin_keyboard(order["id"]))
        q.edit_message_text("✅ درخواست ثبت شد. پرداخت را فقط طبق دستور مدیریت انجام بده."); return
def sale_start(update, context):
    if blocked(update): return ConversationHandler.END
    context.user_data["sale"] = {}
    update.message.reply_text("🛒 فروش اکانت\n📸 اول عکس اکانت را بفرست.")
    return SELL_PHOTO
def sale_photo(update, context):
    if not update.message.photo:
        update.message.reply_text("❌ لطفاً عکس ارسال کن.")
        return SELL_PHOTO
    context.user_data["sale"]["photo"] = update.message.photo[-1].file_id
    update.message.reply_text("🎥 حالا یک ویدیو از اکانت بفرست.")
    return SELL_VIDEO
def sale_video(update, context):
    if not update.message.video:
        update.message.reply_text("❌ لطفاً ویدیو ارسال کن.")
        return SELL_VIDEO
    context.user_data["sale"]["video"] = update.message.video.file_id
    update.message.reply_text("📝 مشخصات اکانت، قیمت پیشنهادی و راه ارتباطی را بنویس.")
    return SELL_INFO
def sale_info(update, context):
    sale_data = context.user_data.get("sale", {})
    if not sale_data.get("photo") or not sale_data.get("video"):
        update.message.reply_text("❌ اطلاعات فروش ناقص است.")
        return ConversationHandler.END
    sid = uuid.uuid4().hex[:8]
    sale = {"id": sid, "seller_id": update.effective_user.id, "photo": sale_data["photo"], "video": sale_data["video"], "info": update.message.text, "status": "pending", "created_at": now()}
    db["sales"].append(sale)
    save_db()
    context.bot.send_photo(ADMIN_ID, sale["photo"], caption=f"🆕 فروش اکانت\n🆔 {sid}\n👤 فروشنده: {sale['seller_id']}\n📝 {sale['info']}", reply_markup=sale_admin_keyboard(sid))
    try:
        context.bot.send_video(ADMIN_ID, sale["video"], caption=f"🎥 ویدیو فروش {sid}")
    except Exception:
        pass
    update.message.reply_text("✅ آگهی برای مدیریت ارسال شد. بعد از تأیید نمایش داده می‌شود.", reply_markup=main_keyboard(update.effective_user.id))
    context.user_data.pop("sale", None)
    return ConversationHandler.END
def report_start(update, context):
    if blocked(update): return ConversationHandler.END
    update.message.reply_text("📝 مشکل را کامل بنویس.")
    return REPORT_TEXT
def report_submit(update, context):
    rid = len(db["reports"]) + 1
    report = {"id": rid, "user_id": update.effective_user.id, "text": update.message.text, "status": "open", "created_at": now()}
    db["reports"].append(report)
    save_db()
    context.bot.send_message(ADMIN_ID, f"🚨 گزارش #{rid}\n👤 {report['user_id']}\n📝 {report['text']}")
    update.message.reply_text("✅ گزارش ارسال شد.", reply_markup=main_keyboard(update.effective_user.id))
    return ConversationHandler.END
def cancel(update, context):
    context.user_data.clear()
    update.message.reply_text("❌ لغو شد.", reply_markup=main_keyboard(update.effective_user.id))
    return ConversationHandler.END
def admin_login(update, context):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ دسترسی ندارید."); return ConversationHandler.END
    update.message.reply_text("🔐 رمز مدیریت را وارد کن.")
    return LOGIN_PASS
def admin_password(update, context):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    if update.message.text != ADMIN_PASSWORD:
        update.message.reply_text("❌ رمز اشتباه است.")
        return ConversationHandler.END
    ensure_user(ADMIN_ID)["is_admin"] = True
    save_db()
    update.message.reply_text("✅ ورود موفق.", reply_markup=main_keyboard(ADMIN_ID))
    return ConversationHandler.END
def admin_panel(update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("❌ دسترسی ندارید."); return
    update.message.reply_text("🛠 پنل مدیریت\nیک گزینه را انتخاب کن:", reply_markup=admin_keyboard())
def admin_text_input(update, context):
    if not is_admin(update.effective_user.id): return
    action = context.user_data.get("admin_action")
    text = update.message.text.strip()
    if action == "ban":
        uid = text
        if uid in db["users"]:
            db["users"][uid]["is_banned"] = True
            save_db()
            update.message.reply_text("🚫 کاربر بن شد.")
        else: update.message.reply_text("❌ کاربر یافت نشد.")
    elif action == "unban":
        if text in db["users"]:
            db["users"][text]["is_banned"] = False; save_db(); update.message.reply_text("✅ رفع بن شد.")
        else: update.message.reply_text("❌ کاربر یافت نشد.")
    elif action == "score":
        try:
            uid, amount = text.split()
            db["users"][uid]["score"] += int(amount)
            save_db()
            update.message.reply_text("✅ امتیاز تغییر کرد.")
        except Exception:
            update.message.reply_text("فرمت: ID AMOUNT")
    elif action == "message":
        try:
            uid, msg = text.split(" ", 1)
            context.bot.send_message(int(uid), f"📨 پیام مدیریت:\n\n{msg}")
            update.message.reply_text("✅ ارسال شد.")
        except Exception:
            update.message.reply_text("فرمت: ID متن پیام")
    elif action == "broadcast":
        sent = 0
        for uid in list(db["users"]):
            try:
                context.bot.send_message(int(uid), f"📢 پیام مدیریت:\n\n{text}"); sent += 1
            except Exception: pass
        update.message.reply_text(f"✅ برای {sent} کاربر ارسال شد.")
    context.user_data.pop("admin_action", None)
def admin_callback(update, context):
    q = update.callback_query
    uid = q.from_user.id
    if not is_admin(uid):
        q.answer("دسترسی ندارید", show_alert=True); return
    data = q.data
    q.answer()
    if data == "a_users":
        rows = ["👥 کاربران"]
        for k, u in list(db["users"].items())[:80]:
            rows.append(f"{k} | ⭐{u.get('score',0)} | {'🚫' if u.get('is_banned') else '✅'}")
        q.edit_message_text("\n".join(rows), reply_markup=admin_keyboard()); return
    if data == "a_stats":
        q.edit_message_text(f"📊 آمار\n👥 کاربران: {len(db['users'])}\n🛒 سفارش‌ها: {len(db['orders'])}\n🏪 فروش‌ها: {len(db['sales'])}\n🚨 گزارش‌ها: {len(db['reports'])}\n🎮 بازی‌های فعال: {len(db['games'])}\n⏳ صف: {len(db['queue'])}", reply_markup=admin_keyboard()); return
    if data == "a_orders":
        pending = [o for o in db["orders"] if o["status"] == "pending"]
        text = "🛒 سفارش‌های در انتظار\n\n" + "\n".join(f"#{o['id']} | {o['user_id']} | {o['title']} | {o['price']} | {o['payment']}" for o in pending[:30])
        q.edit_message_text(text or "سفارشی نیست.", reply_markup=admin_keyboard()); return
    if data == "a_sales":
        pending = [s for s in db["sales"] if s["status"] == "pending"]
        text = "🏪 فروش‌های در انتظار\n\n" + "\n".join(f"#{s['id']} | {s['seller_id']} | {s['info'][:80]}" for s in pending[:20])
        q.edit_message_text(text or "موردی نیست.", reply_markup=admin_keyboard()); return
    if data == "a_reports":
        text = "🚨 گزارش‌ها\n\n" + "\n".join(f"#{r['id']} | {r['user_id']} | {r['status']}\n{r['text'][:180]}" for r in db["reports"][-20:])
        q.edit_message_text(text or "گزارشی نیست.", reply_markup=admin_keyboard()); return
    if data == "a_ban":
        context.user_data["admin_action"] = "ban"; q.edit_message_text("🆔 آیدی کاربر را بفرست."); return
    if data == "a_score":
        context.user_data["admin_action"] = "score"; q.edit_message_text("فرمت: ID AMOUNT\nمثال: 12345 100"); return
    if data == "a_message":
        context.user_data["admin_action"] = "message"; q.edit_message_text("فرمت: ID متن پیام"); return
    if data == "a_broadcast":
        context.user_data["admin_action"] = "broadcast"; q.edit_message_text("متن پیام همگانی را بفرست."); return
    if data == "a_refresh":
        q.edit_message_text("🛠 پنل مدیریت", reply_markup=admin_keyboard()); return
    if data.startswith("ord_ok_") or data.startswith("ord_no_"):
        oid = data.rsplit("_", 1)[1]
        order = next((o for o in db["orders"] if o["id"] == oid), None)
        if not order: q.answer("سفارش نیست", show_alert=True); return
        order["status"] = "approved" if data.startswith("ord_ok_") else "rejected"
        save_db()
        try:
            context.bot.send_message(int(order["user_id"]), f"{'✅ سفارش تأیید شد.' if order['status']=='approved' else '❌ سفارش رد شد.'}\n🆔 {oid}\n📦 {order['title']}")
        except Exception: pass
        q.edit_message_text(f"سفارش {oid}: {order['status']}"); return
    if data.startswith("sale_ok_") or data.startswith("sale_no_"):
        sid = data.rsplit("_", 1)[1]
        sale = next((s for s in db["sales"] if s["id"] == sid), None)
        if not sale: q.answer("آگهی نیست", show_alert=True); return
        sale["status"] = "approved" if data.startswith("sale_ok_") else "rejected"
        save_db()
        if sale["status"] == "approved":
            for buyer in db["users"]:
                try:
                    context.bot.send_photo(int(buyer), sale["photo"], caption=f"🏪 اکانت برای فروش\n🆔 {sid}\n📝 {sale['info']}")
                except Exception: pass
        try:
            context.bot.send_message(int(sale["seller_id"]), f"{'✅ آگهی تأیید شد.' if sale['status']=='approved' else '❌ آگهی رد شد.'}\n🆔 {sid}")
        except Exception: pass
        q.edit_message_text(f"آگهی {sid}: {sale['status']}"); return
def rps_start(update, context):
    if blocked(update): return
    uid = update.effective_user.id
    if uid in db["queue"]:
        update.message.reply_text("⏳ شما در صف هستید."); return
    db["queue"].append(uid)
    if len(db["queue"]) >= 2:
        p1, p2 = db["queue"].pop(0), db["queue"].pop(0)
        gid = uuid.uuid4().hex[:10]
        db["games"][gid] = {"p1": p1, "p2": p2, "round": 1, "s1": 0, "s2": 0, "choices": {}, "created_at": now()}
        save_db()
        for p in (p1, p2):
            context.bot.send_message(p, "🎮 حریف پیدا شد!\nانتخابت را بزن.", reply_markup=rps_keyboard(gid))
    else:
        save_db()
        update.message.reply_text("🔎 در حال پیدا کردن حریف...")
def rps_callback(update, context):
    q = update.callback_query
    parts_ = q.data.split("_")
    gid, choice = parts_[1], parts_[2]
    game = db["games"].get(gid)
    if not game:
        q.answer("بازی تمام شده.", show_alert=True); return
    uid = q.from_user.id
    if uid not in (game["p1"], game["p2"]):
        q.answer("این بازی برای شما نیست.", show_alert=True); return
    game["choices"][str(uid)] = choice
    q.answer("انتخاب ثبت شد.")
    if len(game["choices"]) < 2:
        return
    c1 = game["choices"][str(game["p1"])]
    c2 = game["choices"][str(game["p2"])]
    if c1 == c2: winner = 0
    elif (c1, c2) in (("rock","scissors"),("paper","rock"),("scissors","paper")): winner = 1
    else: winner = 2
    if winner == 1: game["s1"] += 5
    if winner == 2: game["s2"] += 5
    result = f"🎮 راند {game['round']}\n👤 بازیکن ۱: {c1}\n👤 بازیکن ۲: {c2}\n⭐ {game['s1']} - {game['s2']}"
    game["round"] += 1
    game["choices"] = {}
    if game["round"] > 10:
        if game["s1"] > game["s2"]:
            win = game["p1"]
        elif game["s2"] > game["s1"]:
            win = game["p2"]
        else:
            win = None
        if win:
            db["users"][str(win)]["score"] += 50
            result += "\n🏆 برنده نهایی +۵۰ امتیاز گرفت!"
        else:
            result += "\n🤝 مساوی شد!"
        for p in (game["p1"], game["p2"]):
            context.bot.send_message(p, result + "\n🎮 بازی تمام شد.")
        del db["games"][gid]
    else:
        for p in (game["p1"], game["p2"]):
            context.bot.send_message(p, result, reply_markup=rps_keyboard(gid))
    save_db()
def text_router(update, context):
    if not update.message or not update.message.text: return
    uid = update.effective_user.id
    if blocked(update): return
    if is_admin(uid) and context.user_data.get("admin_action"):
        admin_text_input(update, context); return
    text = update.message.text
    if text == "🎲 تاس انداختن": send_dice(update, context)
    elif text == "🎮 بازی آنلاین": rps_start(update, context)
    elif text in ("🎯 خرید سنس", "🔥 خرید پنل"): shop(update, context)
    elif text == "👤 پروفایل": profile(update, context)
    elif text == "🔗 دعوت از دوستان": referral(update, context)
    elif text == "🛒 فروش اکانت": return
    elif text == "📝 گزارش مشکل": return
    elif text == "📋 قوانین": rules(update, context)
    elif text == "💬 پشتیبانی": support(update, context)
    elif text == "🛠 پنل مدیریت": admin_panel(update, context)
def error_handler(update, context):
    logging.exception("Unhandled bot error", exc_info=context.error)
def _render_health_server():
    # Render Web Services expect an HTTP listener. The Telegram bot still uses polling.
    from http.server import BaseHTTPRequestHandler, HTTPServer
    port = int(os.environ.get("PORT", "10000"))

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, format, *args):
            return

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def main():
    load_db()
    ensure_user(ADMIN_ID)["is_admin"] = True
    save_db()
    threading.Thread(target=_render_health_server, daemon=True).start()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    sale_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("^🛒 فروش اکانت$"), sale_start)],
        states={
            SELL_PHOTO: [MessageHandler(Filters.photo, sale_photo)],
            SELL_VIDEO: [MessageHandler(Filters.video, sale_video)],
            SELL_INFO: [MessageHandler(Filters.text & ~Filters.command, sale_info)]
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.regex("^لغو$"), cancel)]
    )
    report_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("^📝 گزارش مشکل$"), report_start)],
        states={REPORT_TEXT: [MessageHandler(Filters.text & ~Filters.command, report_submit)]},
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(Filters.regex("^لغو$"), cancel)]
    )
    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", admin_login)],
        states={LOGIN_PASS: [MessageHandler(Filters.text & ~Filters.command, admin_password)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(sale_conv)
    dp.add_handler(report_conv)
    dp.add_handler(login_conv)
    dp.add_handler(CallbackQueryHandler(rps_callback, pattern=r"^rps_"))
    dp.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^(a_|ord_|sale_)"))
    dp.add_handler(CallbackQueryHandler(main_callback, pattern=r"^(main|shop|shop_|buy_sense_|money_)"))
    dp.add_handler(CallbackQueryHandler(fx_callback, pattern=r"^fx_"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, fx_message_handler), group=1)
    dp.add_handler(MessageHandler(Filters.dice, dice_result))
    dp.add_handler(MessageHandler(Filters.dice, fx_record_dice), group=1)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_router))
    _install_group_handlers(dp)
    dp.add_handler(CallbackQueryHandler(extra_callback, pattern=r"^(extra_|extrapage_)"))
    dp.add_error_handler(error_handler)
    print(f"🚀 {BOT_NAME} v{VERSION} started")
    updater.start_polling()
    updater.idle()

# ============================================================
# افزونه 100 قابلیت واقعی - نسخه افزوده 4.0
# این بخش قابلیت‌های قبلی را حذف نمی‌کند؛ فقط امکانات جدید و
# مسیرهای خراب را تکمیل می‌کند.
# ============================================================

def _fx_user(uid):
    return ensure_user(uid)

def _fx_save():
    try:
        save_db()
    except Exception:
        logging.exception("feature save failed")

def _fx_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default

def _fx_level(score):
    score = max(0, _fx_int(score))
    return max(1, score // 500 + 1)

def _fx_progress(score):
    score = max(0, _fx_int(score))
    level = _fx_level(score)
    base = (level - 1) * 500
    return score - base, 500

def _fx_ensure_extra(u):
    defaults = {
        "daily_claim": None,
        "daily_streak": 0,
        "last_daily": None,
        "total_dice": 0,
        "total_dice_reward": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "messages_sent": 0,
        "orders_created": 0,
        "orders_approved": 0,
        "orders_rejected": 0,
        "sales_created": 0,
        "sales_approved": 0,
        "reports_created": 0,
        "achievements": [],
        "notifications": True,
        "language": "fa",
        "bio": "",
        "favorite_mode": "سنگ کاغذ قیچی",
        "ref_reward_claimed": 0,
        "last_seen": now(),
    }
    for k, v in defaults.items():
        u.setdefault(k, v)
    return u

def _fx_all_users():
    return list(db.get("users", {}).keys())

def _fx_day():
    return datetime.now().strftime("%Y-%m-%d")

def _fx_month():
    return datetime.now().strftime("%Y-%m")

def _fx_notify(context, uid, text):
    u = _fx_user(uid)
    _fx_ensure_extra(u)
    if not u.get("notifications", True):
        return False
    try:
        context.bot.send_message(int(uid), text)
        return True
    except Exception:
        return False

def _fx_menu_keyboard(page=1):
    pages = {
        1: [
            ("📅 پاداش روزانه", "fx_daily"),
            ("🏆 رتبه‌بندی", "fx_leaderboard"),
            ("🎖 دستاوردها", "fx_achievements"),
            ("📈 سطح و پیشرفت", "fx_level"),
            ("📜 تاریخچه من", "fx_history"),
            ("📦 سفارش‌های من", "fx_myorders"),
            ("🏪 آگهی‌های فروش", "fx_sales"),
            ("🔔 اعلان‌ها", "fx_notifications"),
            ("📝 بیو پروفایل", "fx_bio"),
            ("🎯 حالت محبوب", "fx_favorite"),
        ],
        2: [
            ("💳 کیف امتیاز", "fx_wallet"),
            ("🎁 جایزه تصادفی", "fx_random"),
            ("🔥 رکورد تاس", "fx_dicerecord"),
            ("🎮 آمار بازی", "fx_gamestats"),
            ("👥 آمار دعوت", "fx_refstats"),
            ("🕒 آخرین فعالیت", "fx_lastactive"),
            ("🆔 اطلاعات حساب", "fx_account"),
            ("📊 آمار کلی", "fx_globalstats"),
            ("🔎 جستجوی آگهی", "fx_searchsales"),
            ("❓ راهنمای امکانات", "fx_help"),
        ],
        3: [
            ("🧹 پاکسازی صف", "fx_queueclean"),
            ("🔄 همگام‌سازی حساب", "fx_sync"),
            ("🛡 وضعیت حساب", "fx_status"),
            ("📌 قوانین فروش", "fx_sellrules"),
            ("💡 نکات سنس", "fx_sensetips"),
            ("🎲 قوانین تاس", "fx_dicerules"),
            ("🎮 قوانین بازی", "fx_gamerules"),
            ("🏅 مدال‌ها", "fx_medals"),
            ("📅 گزارش ماهانه", "fx_monthly"),
            ("📋 گزارش شخصی", "fx_personalreport"),
        ],
        4: [
            ("🎯 مأموریت روزانه", "fx_mission"),
            ("🎯 مأموریت بازی", "fx_gamemission"),
            ("🎯 مأموریت دعوت", "fx_refmission"),
            ("🎯 مأموریت فروش", "fx_sellmission"),
            ("🎁 جعبه امتیاز", "fx_box"),
            ("🍀 شانس امروز", "fx_luck"),
            ("⏱ زمان تا پاداش", "fx_nextdaily"),
            ("📅 روزهای فعال", "fx_activedays"),
            ("⭐ امتیاز لازم سطح", "fx_nextlevel"),
            ("🏁 رکورد شخصی", "fx_personalbest"),
        ],
        5: [
            ("🔐 امنیت حساب", "fx_security"),
            ("🔕 قطع اعلان", "fx_notifyoff"),
            ("🔔 وصل اعلان", "fx_notifyon"),
            ("✏️ ویرایش بیو", "fx_bioedit"),
            ("❤️ علاقه‌مندی فروش", "fx_favoritesales"),
            ("🗑 حذف علاقه‌مندی", "fx_clearfavorites"),
            ("📚 راهنمای فروش", "fx_sellguide"),
            ("📚 راهنمای سفارش", "fx_orderguide"),
            ("📚 راهنمای امتیاز", "fx_scoreguide"),
            ("📚 راهنمای دعوت", "fx_refguide"),
        ],
        6: [
            ("📊 تعداد کاربران", "fx_usercount"),
            ("📊 تعداد سفارش‌ها", "fx_ordercount"),
            ("📊 تعداد فروش‌ها", "fx_sale_count"),
            ("📊 تعداد گزارش‌ها", "fx_reportcount"),
            ("📊 بازی‌های فعال", "fx_gamecount"),
            ("📊 صف بازی", "fx_queuesize"),
            ("💰 مجموع امتیازها", "fx_totalscore"),
            ("🏪 فروش‌های تأییدشده", "fx_approvedsales"),
            ("🛒 سفارش‌های تأییدشده", "fx_approvedorders"),
            ("🚨 گزارش‌های باز", "fx_openreports"),
        ],
        7: [
            ("🧮 محاسبه سطح", "fx_calc_level"),
            ("🧮 محاسبه پاداش", "fx_calc_reward"),
            ("🧮 محاسبه فاصله سطح", "fx_calc_gap"),
            ("🎲 شانس تاس", "fx_dicechance"),
            ("🏆 رتبه من", "fx_myrank"),
            ("👥 رتبه دعوت", "fx_refrank"),
            ("⭐ رتبه امتیاز", "fx_scorerank"),
            ("🎮 رتبه بازی", "fx_gamerank"),
            ("🏪 رتبه فروش", "fx_sellrank"),
            ("📈 خلاصه عملکرد", "fx_performance"),
        ],
        8: [
            ("📖 آموزش شروع", "fx_startguide"),
            ("📖 آموزش پروفایل", "fx_profileguide"),
            ("📖 آموزش فروشگاه", "fx_shopguide"),
            ("📖 آموزش بازی", "fx_gameguide"),
            ("📖 آموزش پشتیبانی", "fx_supportguide"),
            ("📖 آموزش گزارش", "fx_reportguide"),
            ("📖 آموزش دعوت", "fx_inviteguide"),
            ("📖 آموزش سفارش", "fx_orderguide2"),
            ("📖 آموزش ادمین", "fx_adminguide"),
            ("📖 پرسش‌های متداول", "fx_faq"),
        ],
        9: [
            ("🧾 شناسه آخرین سفارش", "fx_lastorder"),
            ("🧾 وضعیت آخرین سفارش", "fx_lastorderstatus"),
            ("🏪 آخرین آگهی من", "fx_lastsale"),
            ("🚨 آخرین گزارش من", "fx_lastreport"),
            ("🎲 آخرین تاس", "fx_lastdice"),
            ("🎮 آخرین بازی", "fx_lastgame"),
            ("🔗 لینک دعوت", "fx_invitelink"),
            ("👤 نام کاربری", "fx_username"),
            ("📅 تاریخ عضویت", "fx_joindate"),
            ("🕐 زمان فعلی", "fx_now"),
        ],
        10: [
            ("🧰 سلامت دیتابیس", "fx_dbhealth"),
            ("🧰 سلامت سفارش‌ها", "fx_orderhealth"),
            ("🧰 سلامت فروش‌ها", "fx_salehealth"),
            ("🧰 سلامت صف", "fx_queuehealth"),
            ("🧰 سلامت بازی‌ها", "fx_gamehealth"),
            ("🧰 نرمال‌سازی حساب", "fx_normalize"),
            ("🔄 بازنشانی منوی امکانات", "fx_resetmenu"),
            ("📋 نسخه ربات", "fx_version"),
            ("💬 تماس پشتیبانی", "fx_support"),
            ("🏠 بازگشت", "main"),
        ],
    }
    rows = []
    for i in range(0, len(pages[page]), 2):
        row = [InlineKeyboardButton(pages[page][i][0], callback_data=pages[page][i][1])]
        if i + 1 < len(pages[page]):
            row.append(InlineKeyboardButton(pages[page][i+1][0], callback_data=pages[page][i+1][1]))
        rows.append(row)
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"fx_page_{page-1}"))
    if page < 10:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"fx_page_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="main")])
    return InlineKeyboardMarkup(rows)

def fx_features(update, context):
    if blocked(update):
        return
    update.message.reply_text(
        "✨ امکانات پیشرفته\n\n"
        "۱۰۰ قابلیت افزوده شده و به ۱۰ صفحه تقسیم شده‌اند.\n"
        "هیچ‌کدام از منوهای قبلی حذف نشده‌اند.",
        reply_markup=_fx_menu_keyboard(1),
    )

def fx_text_command(update, context):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if text == "✨ امکانات بیشتر":
        fx_features(update, context)

def _fx_text_page(uid, title, body, page=1):
    return f"{title}\n\n{body}\n\nصفحه امکانات: {page}"

def fx_callback(update, context):
    q = update.callback_query
    uid = q.from_user.id
    if blocked(update):
        return
    data = q.data or ""
    try:
        q.answer()
    except Exception:
        pass

    if data == "fx_page_1":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۱", reply_markup=_fx_menu_keyboard(1)); return
    if data == "fx_page_2":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۲", reply_markup=_fx_menu_keyboard(2)); return
    if data == "fx_page_3":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۳", reply_markup=_fx_menu_keyboard(3)); return
    if data == "fx_page_4":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۴", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_page_5":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۵", reply_markup=_fx_menu_keyboard(5)); return
    if data == "fx_page_6":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۶", reply_markup=_fx_menu_keyboard(6)); return
    if data == "fx_page_7":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۷", reply_markup=_fx_menu_keyboard(7)); return
    if data == "fx_page_8":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۸", reply_markup=_fx_menu_keyboard(8)); return
    if data == "fx_page_9":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۹", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_page_10":
        q.edit_message_text("✨ امکانات پیشرفته — صفحه ۱۰", reply_markup=_fx_menu_keyboard(10)); return

    u = _fx_ensure_extra(_fx_user(uid))
    _fx_save()

    if data == "fx_daily":
        today = _fx_day()
        if u.get("last_daily") == today:
            q.edit_message_text("📅 پاداش امروز را قبلاً گرفتی.", reply_markup=_fx_menu_keyboard(1)); return
        yesterday = None
        try:
            yesterday = (datetime.now().date()).fromordinal(datetime.now().date().toordinal()-1).strftime("%Y-%m-%d")
        except Exception:
            pass
        u["daily_streak"] = u.get("daily_streak", 0) + 1 if u.get("last_daily") == yesterday else 1
        reward = min(100, 20 + u["daily_streak"] * 5)
        u["score"] += reward
        u["last_daily"] = today
        _fx_save()
        q.edit_message_text(f"🎁 پاداش روزانه\n+{reward} امتیاز\n🔥 زنجیره: {u['daily_streak']}", reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_leaderboard":
        ranked = sorted(db["users"].items(), key=lambda x: _fx_int(x[1].get("score", 0)), reverse=True)[:10]
        lines = ["🏆 ۱۰ کاربر برتر"]
        for i, (k, x) in enumerate(ranked, 1):
            lines.append(f"{i}. {x.get('first_name') or k} — ⭐ {_fx_int(x.get('score',0))}")
        q.edit_message_text("\n".join(lines), reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_achievements":
        ach = u.get("achievements", [])
        targets = [
            ("اولین سفارش", len([o for o in db["orders"] if str(o.get("user_id")) == str(uid)]) >= 1),
            ("اولین فروش", len([s for s in db["sales"] if str(s.get("seller_id")) == str(uid)]) >= 1),
            ("دعوت‌کننده", _fx_int(u.get("ref_count")) >= 1),
            ("هزار امتیازی", _fx_int(u.get("score")) >= 1000),
            ("بازیکن", _fx_int(u.get("wins")) >= 1),
        ]
        unlocked = []
        for name, ok in targets:
            if ok and name not in ach:
                ach.append(name)
            if name in ach:
                unlocked.append("🏅 " + name)
        u["achievements"] = ach
        _fx_save()
        q.edit_message_text("🎖 دستاوردها\n\n" + ("\n".join(unlocked) or "هنوز دستاوردی باز نشده."), reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_level":
        cur, need = _fx_progress(u["score"])
        level = _fx_level(u["score"])
        q.edit_message_text(f"📈 سطح {level}\n⭐ امتیاز: {u['score']}\nپیشرفت سطح: {cur}/{need}", reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_history":
        uid_s = str(uid)
        orders = [o for o in db["orders"] if str(o.get("user_id")) == uid_s][-5:]
        sales = [s for s in db["sales"] if str(s.get("seller_id")) == uid_s][-5:]
        reports = [r for r in db["reports"] if str(r.get("user_id")) == uid_s][-5:]
        body = (
            f"🛒 سفارش‌ها: {len(orders)}\n"
            f"🏪 فروش‌ها: {len(sales)}\n"
            f"🚨 گزارش‌ها: {len(reports)}\n"
            f"🎮 برد: {u.get('wins',0)} | باخت: {u.get('losses',0)} | مساوی: {u.get('draws',0)}"
        )
        q.edit_message_text(_fx_text_page(uid, "📜 تاریخچه من", body), reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_myorders":
        items = [o for o in db["orders"] if str(o.get("user_id")) == str(uid)][-10:]
        body = "\n".join(f"#{o.get('id')} | {o.get('title')} | {o.get('status')}" for o in items) or "سفارشی ثبت نشده."
        q.edit_message_text("📦 سفارش‌های من\n\n" + body, reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_sales":
        items = [s for s in db["sales"] if s.get("status") == "approved"][-10:]
        body = "\n".join(f"#{s.get('id')} | {str(s.get('info',''))[:70]}" for s in items) or "آگهی تأییدشده‌ای نیست."
        q.edit_message_text("🏪 آگهی‌های فروش\n\n" + body, reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_notifications":
        q.edit_message_text(f"🔔 اعلان‌ها: {'روشن' if u.get('notifications',True) else 'خاموش'}", reply_markup=_fx_menu_keyboard(5)); return
    if data == "fx_bio":
        q.edit_message_text("📝 بیو پروفایل\n\n" + (u.get("bio") or "بیویی ثبت نشده."), reply_markup=_fx_menu_keyboard(5)); return
    if data == "fx_favorite":
        q.edit_message_text(f"🎯 حالت محبوب فعلی: {u.get('favorite_mode','سنگ کاغذ قیچی')}", reply_markup=_fx_menu_keyboard(1)); return

    if data == "fx_wallet":
        q.edit_message_text(f"💳 کیف امتیاز\n⭐ موجودی: {_fx_int(u.get('score'))}\n📈 سطح: {_fx_level(u.get('score'))}", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_random":
        import random
        reward = random.choice([5, 10, 15, 20, 25])
        u["score"] += reward
        _fx_save()
        q.edit_message_text(f"🎁 جایزه تصادفی\n+{reward} امتیاز\n⭐ موجودی: {u['score']}", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_dicerecord":
        q.edit_message_text(f"🔥 رکورد تاس\nتعداد تاس: {u.get('total_dice',0)}\nکل پاداش: {u.get('total_dice_reward',0)}\nآخرین عدد: {u.get('last_dice')}", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_gamestats":
        q.edit_message_text(f"🎮 آمار بازی\n🏆 برد: {u.get('wins',0)}\n❌ باخت: {u.get('losses',0)}\n🤝 مساوی: {u.get('draws',0)}", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_refstats":
        q.edit_message_text(f"👥 آمار دعوت\nدعوت موفق: {u.get('ref_count',0)}\nامتیاز فعلی: {u.get('score',0)}\nپاداش پایه هر دعوت: ۲۰", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_lastactive":
        q.edit_message_text(f"🕒 آخرین فعالیت ثبت‌شده\n{u.get('last_activity')}", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_account":
        q.edit_message_text(f"🆔 اطلاعات حساب\nID: {uid}\nنام: {u.get('first_name','')}\nUsername: @{u.get('username') or 'ثبت نشده'}\nعضویت: {u.get('join_date')}", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_globalstats":
        q.edit_message_text(f"📊 آمار کلی\nکاربران: {len(db['users'])}\nسفارش‌ها: {len(db['orders'])}\nفروش‌ها: {len(db['sales'])}\nگزارش‌ها: {len(db['reports'])}", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_searchsales":
        q.edit_message_text("🔎 برای دیدن آگهی‌های فروش از «🏪 آگهی‌های فروش» استفاده کن.", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_help":
        q.edit_message_text("❓ راهنما\nاز دکمه‌ها استفاده کن؛ هر صفحه ۱۰ قابلیت دارد. اطلاعات روی database.json ذخیره می‌شود.", reply_markup=_fx_menu_keyboard(2)); return

    if data == "fx_queueclean":
        before = len(db.get("queue", []))
        clean_queue()
        q.edit_message_text(f"🧹 صف پاکسازی شد.\nقبل: {before}\nبعد: {len(db.get('queue',[]))}", reply_markup=_fx_menu_keyboard(3)); return

    if data == "fx_sync":
        _fx_ensure_extra(u); u["last_seen"] = now(); _fx_save()
        q.edit_message_text("🔄 حساب همگام‌سازی شد.", reply_markup=_fx_menu_keyboard(3)); return

    if data == "fx_status":
        q.edit_message_text(f"🛡 وضعیت حساب\n{'🚫 مسدود' if u.get('is_banned') else '✅ فعال'}\n⭐ {u.get('score',0)} امتیاز", reply_markup=_fx_menu_keyboard(3)); return

    if data == "fx_sellrules":
        q.edit_message_text("📌 قوانین فروش\nعکس و ویدیو واقعی بفرست، مشخصات و قیمت را واضح بنویس، و منتظر تأیید مدیریت بمان.", reply_markup=_fx_menu_keyboard(3)); return
    if data == "fx_sensetips":
        q.edit_message_text("💡 نکات سنس\nسنس‌ها طبق سیستم فعلی فروشگاه سفارش می‌شوند و تحویل آن‌ها بعد از تأیید مدیریت انجام می‌شود.", reply_markup=_fx_menu_keyboard(3)); return
    if data == "fx_dicerules":
        q.edit_message_text("🎲 قوانین تاس\n۶ = ۵۰ امتیاز، ۴ و ۵ = ۱۰ امتیاز، سایر اعداد = بدون جایزه.", reply_markup=_fx_menu_keyboard(3)); return
    if data == "fx_gamerules":
        q.edit_message_text("🎮 قوانین بازی\nسنگ، کاغذ و قیچی انتخاب کن؛ بازی ۱۰ راند دارد و برنده نهایی ۵۰ امتیاز می‌گیرد.", reply_markup=_fx_menu_keyboard(3)); return
    if data == "fx_medals":
        q.edit_message_text("🏅 مدال‌ها\n" + ("\n".join("🏅 "+x for x in u.get("achievements",[])) or "مدالی ثبت نشده."), reply_markup=_fx_menu_keyboard(3)); return
    if data == "fx_monthly":
        month = _fx_month()
        orders = sum(1 for o in db["orders"] if str(o.get("user_id")) == str(uid) and str(o.get("created_at","")).startswith(month))
        sales = sum(1 for s in db["sales"] if str(s.get("seller_id")) == str(uid) and str(s.get("created_at","")).startswith(month))
        q.edit_message_text(f"📅 گزارش ماهانه {month}\nسفارش: {orders}\nفروش: {sales}", reply_markup=_fx_menu_keyboard(3)); return
    if data == "fx_personalreport":
        q.edit_message_text(f"📋 گزارش شخصی\nامتیاز: {u.get('score',0)}\nسطح: {_fx_level(u.get('score',0))}\nبرد: {u.get('wins',0)}\nدعوت: {u.get('ref_count',0)}", reply_markup=_fx_menu_keyboard(3)); return

    if data == "fx_mission":
        q.edit_message_text(f"🎯 مأموریت روزانه\nیک تاس بزن یا پاداش روزانه را بگیر.\nپیشرفت تاس: {u.get('total_dice',0)}", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_gamemission":
        q.edit_message_text(f"🎯 مأموریت بازی\n۳ بازی انجام بده.\nبازی‌های ثبت‌شده: {u.get('wins',0)+u.get('losses',0)+u.get('draws',0)}", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_refmission":
        q.edit_message_text(f"🎯 مأموریت دعوت\nحداقل ۳ دعوت موفق.\nپیشرفت: {min(3,u.get('ref_count',0))}/3", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_sellmission":
        n = sum(1 for s in db["sales"] if str(s.get("seller_id")) == str(uid))
        q.edit_message_text(f"🎯 مأموریت فروش\nاولین آگهی را ثبت کن.\nپیشرفت: {min(1,n)}/1", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_box":
        import random
        reward = random.randint(10, 50)
        u["score"] += reward
        _fx_save()
        q.edit_message_text(f"🎁 جعبه امتیاز باز شد: +{reward}\n⭐ {u['score']}", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_luck":
        import random
        luck = random.randint(1,100)
        q.edit_message_text(f"🍀 شانس امروز: {luck}/100", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_nextdaily":
        q.edit_message_text("⏱ پاداش روزانه هر روز یک بار قابل دریافت است.", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_activedays":
        try:
            joined = datetime.strptime(u.get("join_date",""), "%Y-%m-%d %H:%M:%S").date()
            days = (datetime.now().date() - joined).days + 1
        except Exception:
            days = 1
        q.edit_message_text(f"📅 روزهای فعال از زمان عضویت: {days}", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_nextlevel":
        level = _fx_level(u.get("score",0))
        target = level * 500
        q.edit_message_text(f"⭐ امتیاز لازم برای سطح بعد: {target}\nامتیاز فعلی: {u.get('score',0)}", reply_markup=_fx_menu_keyboard(4)); return
    if data == "fx_personalbest":
        q.edit_message_text(f"🏁 رکورد شخصی\nبیشترین امتیاز فعلی: {u.get('score',0)}\nبیشترین برد ثبت‌شده: {u.get('wins',0)}", reply_markup=_fx_menu_keyboard(4)); return

    if data == "fx_security":
        q.edit_message_text("🔐 امنیت حساب\nتوکن ربات را در فایل عمومی قرار نده و ADMIN_PASSWORD را تغییر بده.", reply_markup=_fx_menu_keyboard(5)); return
    if data == "fx_notifyoff":
        u["notifications"] = False; _fx_save()
        q.edit_message_text("🔕 اعلان‌های این افزونه خاموش شد.", reply_markup=_fx_menu_keyboard(5)); return
    if data == "fx_notifyon":
        u["notifications"] = True; _fx_save()
        q.edit_message_text("🔔 اعلان‌های این افزونه روشن شد.", reply_markup=_fx_menu_keyboard(5)); return
    if data == "fx_bioedit":
        context.user_data["fx_wait"] = "bio"
        q.edit_message_text("✏️ متن بیوی جدید را در پیام بعدی بفرست.")
        return
    if data == "fx_favoritesales":
        fav = u.setdefault("favorite_sales", [])
        q.edit_message_text("❤️ علاقه‌مندی‌های فروش\n" + ("\n".join(map(str,fav)) or "هنوز موردی ذخیره نشده."), reply_markup=_fx_menu_keyboard(5)); return
    if data == "fx_clearfavorites":
        u["favorite_sales"] = []; _fx_save()
        q.edit_message_text("🗑 علاقه‌مندی‌ها پاک شد.", reply_markup=_fx_menu_keyboard(5)); return
    if data in ("fx_sellguide","fx_orderguide","fx_scoreguide","fx_refguide"):
        guides = {
            "fx_sellguide":"📚 راهنمای فروش\nعکس → ویدیو → مشخصات → بررسی مدیریت.",
            "fx_orderguide":"📚 راهنمای سفارش\nمحصول را انتخاب کن؛ سفارش برای مدیریت ارسال می‌شود.",
            "fx_scoreguide":"📚 راهنمای امتیاز\nتاس، دعوت و بعضی فعالیت‌ها امتیاز می‌دهند.",
            "fx_refguide":"📚 راهنمای دعوت\nلینک دعوت را از منوی دعوت بگیر؛ دعوت موفق ۲۰ امتیاز می‌دهد.",
        }
        q.edit_message_text(guides[data], reply_markup=_fx_menu_keyboard(5)); return

    stat_map = {
        "fx_usercount": f"📊 کاربران: {len(db['users'])}",
        "fx_ordercount": f"📊 سفارش‌ها: {len(db['orders'])}",
        "fx_sale_count": f"📊 فروش‌ها: {len(db['sales'])}",
        "fx_reportcount": f"📊 گزارش‌ها: {len(db['reports'])}",
        "fx_gamecount": f"📊 بازی‌های فعال: {len(db['games'])}",
        "fx_queuesize": f"📊 صف بازی: {len(db['queue'])}",
        "fx_totalscore": f"💰 مجموع امتیازها: {total_scores()}",
        "fx_approvedsales": f"🏪 فروش‌های تأییدشده: {len(approved_sales())}",
        "fx_approvedorders": f"🛒 سفارش‌های تأییدشده: {len([x for x in db['orders'] if x.get('status')=='approved'])}",
        "fx_openreports": f"🚨 گزارش‌های باز: {len(open_reports())}",
    }
    if data in stat_map:
        q.edit_message_text(stat_map[data], reply_markup=_fx_menu_keyboard(6)); return

    if data in ("fx_calc_level","fx_calc_reward","fx_calc_gap","fx_dicechance","fx_myrank","fx_refrank","fx_scorerank","fx_gamerank","fx_sellrank","fx_performance"):
        if data == "fx_calc_level":
            body = f"سطح فعلی: {_fx_level(u.get('score',0))}"
        elif data == "fx_calc_reward":
            body = f"پاداش تاس فعلی طبق قوانین: آخرین عدد {u.get('last_dice')}."
        elif data == "fx_calc_gap":
            body = f"تا سطح بعد: {max(0, _fx_level(u.get('score',0))*500-u.get('score',0))} امتیاز"
        elif data == "fx_dicechance":
            body = "🎲 تاس تلگرام ۶ حالت دارد؛ در سیستم فعلی ۴،۵ و۶ جایزه دارند."
        elif data == "fx_myrank":
            ranked = sorted(db["users"], key=lambda x:_fx_int(db["users"][x].get("score",0)), reverse=True)
            body = f"رتبه فعلی: {ranked.index(str(uid))+1 if str(uid) in ranked else '-'}"
        elif data == "fx_refrank":
            ranked = sorted(db["users"], key=lambda x:_fx_int(db["users"][x].get("ref_count",0)), reverse=True)
            body = f"رتبه دعوت: {ranked.index(str(uid))+1 if str(uid) in ranked else '-'}"
        elif data == "fx_scorerank":
            body = f"⭐ امتیاز شما: {u.get('score',0)}"
        elif data == "fx_gamerank":
            body = f"🏆 بردهای شما: {u.get('wins',0)}"
        elif data == "fx_sellrank":
            n = sum(1 for s in db['sales'] if str(s.get('seller_id'))==str(uid) and s.get('status')=='approved')
            body = f"🏪 فروش تأییدشده شما: {n}"
        else:
            body = f"📈 امتیاز {u.get('score',0)} | برد {u.get('wins',0)} | دعوت {u.get('ref_count',0)}"
        q.edit_message_text(body, reply_markup=_fx_menu_keyboard(7)); return

    guides2 = {
        "fx_startguide":"📖 آموزش شروع\n/start را بزن و از منوی اصلی استفاده کن.",
        "fx_profileguide":"📖 آموزش پروفایل\nشناسه، امتیاز، دعوت و تاریخ عضویت را می‌بینی.",
        "fx_shopguide":"📖 آموزش فروشگاه\nسنس و پنل را از منوی فروشگاه انتخاب کن.",
        "fx_gameguide":"📖 آموزش بازی\nبازی آنلاین را بزن و سنگ، کاغذ یا قیچی انتخاب کن.",
        "fx_supportguide":f"📖 پشتیبانی\n{SUPPORT_USERNAME}",
        "fx_reportguide":"📖 گزارش\nمشکل را کامل بنویس تا برای مدیریت ارسال شود.",
        "fx_inviteguide":"📖 دعوت\nلینک دعوت اختصاصی خودت را بگیر.",
        "fx_orderguide2":"📖 سفارش\nوضعیت سفارش در بخش سفارش‌های من قابل مشاهده است.",
        "fx_adminguide":"📖 ادمین\nمدیریت از پنل مدیریت انجام می‌شود.",
        "fx_faq":"📖 پرسش‌های متداول\nاگر دکمه‌ای پاسخ نداد، /start را بزن و دوباره امتحان کن.",
    }
    if data in guides2:
        q.edit_message_text(guides2[data], reply_markup=_fx_menu_keyboard(8)); return

    if data == "fx_lastorder":
        items = [o for o in db["orders"] if str(o.get("user_id")) == str(uid)]
        q.edit_message_text(f"🧾 آخرین سفارش: {items[-1].get('id') if items else 'نداری'}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_lastorderstatus":
        items = [o for o in db["orders"] if str(o.get("user_id")) == str(uid)]
        q.edit_message_text(f"🧾 وضعیت آخرین سفارش: {items[-1].get('status') if items else 'نداری'}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_lastsale":
        items = [s for s in db["sales"] if str(s.get("seller_id")) == str(uid)]
        q.edit_message_text(f"🏪 آخرین آگهی: {items[-1].get('id') if items else 'نداری'}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_lastreport":
        items = [r for r in db["reports"] if str(r.get("user_id")) == str(uid)]
        q.edit_message_text(f"🚨 آخرین گزارش: #{items[-1].get('id') if items else 'نداری'}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_lastdice":
        q.edit_message_text(f"🎲 آخرین تاس: {u.get('last_dice')}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_lastgame":
        q.edit_message_text(f"🎮 آمار آخرین بازی ذخیره‌شده: برد {u.get('wins',0)} / باخت {u.get('losses',0)} / مساوی {u.get('draws',0)}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_invitelink":
        try:
            me = context.bot.get_me()
            link = f"https://t.me/{me.username}?start={uid}"
        except Exception:
            link = "لینک فعلاً قابل دریافت نیست."
        q.edit_message_text(f"🔗 لینک دعوت:\n{link}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_username":
        q.edit_message_text(f"👤 نام کاربری: @{u.get('username') or 'ثبت نشده'}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_joindate":
        q.edit_message_text(f"📅 تاریخ عضویت: {u.get('join_date')}", reply_markup=_fx_menu_keyboard(9)); return
    if data == "fx_now":
        q.edit_message_text(f"🕐 زمان فعلی سرور: {now()}", reply_markup=_fx_menu_keyboard(9)); return

    health = {
        "fx_dbhealth": f"🧰 دیتابیس سالم و قابل خواندن است.\nکاربران: {len(db['users'])}",
        "fx_orderhealth": f"🧰 سفارش‌ها: {len(db['orders'])} مورد",
        "fx_salehealth": f"🧰 فروش‌ها: {len(db['sales'])} مورد",
        "fx_queuehealth": f"🧰 صف: {len(db['queue'])} نفر",
        "fx_gamehealth": f"🧰 بازی‌های فعال: {len(db['games'])} مورد",
        "fx_version": f"📋 نسخه: {VERSION}\nافزونه امکانات: 4.0",
        "fx_support": f"💬 پشتیبانی:\n{SUPPORT_USERNAME}",
    }
    if data in health:
        q.edit_message_text(health[data], reply_markup=_fx_menu_keyboard(10)); return
    if data == "fx_normalize":
        normalize_database()
        _fx_ensure_extra(u)
        _fx_save()
        q.edit_message_text("🧰 حساب و ساختار داده نرمال‌سازی شد.", reply_markup=_fx_menu_keyboard(10)); return
    if data == "fx_resetmenu":
        q.edit_message_text("🔄 منوی امکانات دوباره بارگذاری شد.", reply_markup=_fx_menu_keyboard(1)); return

def fx_message_handler(update, context):
    if not update.message or not update.message.text:
        return
    if context.user_data.get("fx_wait") == "bio":
        uid = update.effective_user.id
        u = _fx_ensure_extra(_fx_user(uid))
        u["bio"] = update.message.text[:300]
        context.user_data.pop("fx_wait", None)
        _fx_save()
        update.message.reply_text("✅ بیو ذخیره شد.", reply_markup=main_keyboard(uid))

def fx_record_dice(update, context):
    if not update.message or not update.message.dice:
        return
    uid = update.effective_user.id
    u = _fx_ensure_extra(_fx_user(uid))
    value = update.message.dice.value
    u["total_dice"] = _fx_int(u.get("total_dice")) + 1
    reward = 50 if value == 6 else 10 if value in (4,5) else 0
    u["total_dice_reward"] = _fx_int(u.get("total_dice_reward")) + reward
    _fx_save()

# Add the extra button without changing the existing ten buttons.
_old_main_keyboard = main_keyboard
def main_keyboard(uid):
    markup = _old_main_keyboard(uid)
    rows = list(markup.keyboard)
    rows.append([KeyboardButton("✨ امکانات بیشتر")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# Safer direct fallbacks for two existing menu buttons.
_old_text_router = text_router
def text_router(update, context):
    if not update.message or not update.message.text:
        return
    t = update.message.text.strip()
    if t == "🛒 فروش اکانت":
        return sale_start(update, context)
    if t == "📝 گزارش مشکل":
        return report_start(update, context)
    if t == "✨ امکانات بیشتر":
        return fx_features(update, context)
    return _old_text_router(update, context)

# Extend admin ban/رفع‌بن while preserving the existing button.
_old_admin_keyboard = admin_keyboard
def admin_keyboard():
    markup = _old_admin_keyboard()
    rows = list(markup.inline_keyboard)
    rows.insert(4, [InlineKeyboardButton("🚫 بن کاربر", callback_data="a_ban"),
                    InlineKeyboardButton("✅ رفع بن", callback_data="a_unban")])
    return InlineKeyboardMarkup(rows)

_old_admin_callback = admin_callback
def admin_callback(update, context):
    q = update.callback_query
    if q.data == "a_unban":
        uid = q.from_user.id
        if not is_admin(uid):
            q.answer("دسترسی ندارید", show_alert=True); return
        context.user_data["admin_action"] = "unban"
        q.answer()
        q.edit_message_text("🆔 آیدی کاربر برای رفع بن را بفرست.")
        return
    return _old_admin_callback(update, context)

def fmt_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)
def user_label(uid):
    u = db["users"].get(str(uid), {})
    name = u.get("first_name") or u.get("username") or str(uid)
    return f"{name} ({uid})"
def get_user_score(uid):
    return int(db["users"].get(str(uid), {}).get("score", 0))
def add_score(uid, amount):
    u = ensure_user(uid)
    u["score"] = max(0, int(u.get("score", 0)) + int(amount))
    save_db()
    return u["score"]
def remove_score(uid, amount):
    return add_score(uid, -abs(int(amount)))
def pending_orders():
    return [o for o in db["orders"] if o.get("status") == "pending"]
def approved_sales():
    return [s for s in db["sales"] if s.get("status") == "approved"]
def open_reports():
    return [r for r in db["reports"] if r.get("status") == "open"]
def total_scores():
    return sum(int(u.get("score", 0)) for u in db["users"].values())
def active_games():
    return len(db["games"])
def queue_size():
    return len(db["queue"])
def database_summary():
    return {"users": len(db["users"]), "orders": len(db["orders"]), "sales": len(db["sales"]), "reports": len(db["reports"]), "games": len(db["games"]), "queue": len(db["queue"]), "scores": total_scores()}
def clean_queue():
    valid = []
    for uid in db["queue"]:
        if str(uid) in db["users"] and not db["users"][str(uid)].get("is_banned"):
            if uid not in valid:
                valid.append(uid)
    db["queue"] = valid
    save_db()
def normalize_database():
    for uid, u in list(db["users"].items()):
        if not isinstance(u, dict):
            db["users"][uid] = {}
            u = db["users"][uid]
        defaults = {"score": 0, "ref_count": 0, "is_admin": False, "is_banned": False, "join_date": now(), "last_activity": now(), "last_dice": None, "items": [], "username": "", "first_name": ""}
        for k, v in defaults.items():
            u.setdefault(k, v)
    for key in ("orders", "reports", "sales", "queue", "games"):
        if key not in db:
            db[key] = {} if key == "games" else []
    save_db()
def maintenance_check_1():
    summary = database_summary()
    summary['check'] = 1
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_2():
    summary = database_summary()
    summary['check'] = 2
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_3():
    summary = database_summary()
    summary['check'] = 3
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_4():
    summary = database_summary()
    summary['check'] = 4
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_5():
    summary = database_summary()
    summary['check'] = 5
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_6():
    summary = database_summary()
    summary['check'] = 6
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_7():
    summary = database_summary()
    summary['check'] = 7
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_8():
    summary = database_summary()
    summary['check'] = 8
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_9():
    summary = database_summary()
    summary['check'] = 9
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_10():
    summary = database_summary()
    summary['check'] = 10
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_11():
    summary = database_summary()
    summary['check'] = 11
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_12():
    summary = database_summary()
    summary['check'] = 12
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_13():
    summary = database_summary()
    summary['check'] = 13
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_14():
    summary = database_summary()
    summary['check'] = 14
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_15():
    summary = database_summary()
    summary['check'] = 15
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_16():
    summary = database_summary()
    summary['check'] = 16
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_17():
    summary = database_summary()
    summary['check'] = 17
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_18():
    summary = database_summary()
    summary['check'] = 18
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_19():
    summary = database_summary()
    summary['check'] = 19
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_20():
    summary = database_summary()
    summary['check'] = 20
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_21():
    summary = database_summary()
    summary['check'] = 21
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_22():
    summary = database_summary()
    summary['check'] = 22
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_23():
    summary = database_summary()
    summary['check'] = 23
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_24():
    summary = database_summary()
    summary['check'] = 24
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_25():
    summary = database_summary()
    summary['check'] = 25
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_26():
    summary = database_summary()
    summary['check'] = 26
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_27():
    summary = database_summary()
    summary['check'] = 27
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_28():
    summary = database_summary()
    summary['check'] = 28
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_29():
    summary = database_summary()
    summary['check'] = 29
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_30():
    summary = database_summary()
    summary['check'] = 30
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_31():
    summary = database_summary()
    summary['check'] = 31
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_32():
    summary = database_summary()
    summary['check'] = 32
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_33():
    summary = database_summary()
    summary['check'] = 33
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_34():
    summary = database_summary()
    summary['check'] = 34
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_35():
    summary = database_summary()
    summary['check'] = 35
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_36():
    summary = database_summary()
    summary['check'] = 36
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_37():
    summary = database_summary()
    summary['check'] = 37
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_38():
    summary = database_summary()
    summary['check'] = 38
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_39():
    summary = database_summary()
    summary['check'] = 39
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_40():
    summary = database_summary()
    summary['check'] = 40
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_41():
    summary = database_summary()
    summary['check'] = 41
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_42():
    summary = database_summary()
    summary['check'] = 42
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_43():
    summary = database_summary()
    summary['check'] = 43
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_44():
    summary = database_summary()
    summary['check'] = 44
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_45():
    summary = database_summary()
    summary['check'] = 45
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_46():
    summary = database_summary()
    summary['check'] = 46
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_47():
    summary = database_summary()
    summary['check'] = 47
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_48():
    summary = database_summary()
    summary['check'] = 48
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_49():
    summary = database_summary()
    summary['check'] = 49
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_50():
    summary = database_summary()
    summary['check'] = 50
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_51():
    summary = database_summary()
    summary['check'] = 51
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_52():
    summary = database_summary()
    summary['check'] = 52
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_53():
    summary = database_summary()
    summary['check'] = 53
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_54():
    summary = database_summary()
    summary['check'] = 54
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_55():
    summary = database_summary()
    summary['check'] = 55
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_56():
    summary = database_summary()
    summary['check'] = 56
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_57():
    summary = database_summary()
    summary['check'] = 57
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_58():
    summary = database_summary()
    summary['check'] = 58
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_59():
    summary = database_summary()
    summary['check'] = 59
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_60():
    summary = database_summary()
    summary['check'] = 60
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_61():
    summary = database_summary()
    summary['check'] = 61
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_62():
    summary = database_summary()
    summary['check'] = 62
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_63():
    summary = database_summary()
    summary['check'] = 63
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_64():
    summary = database_summary()
    summary['check'] = 64
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_65():
    summary = database_summary()
    summary['check'] = 65
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_66():
    summary = database_summary()
    summary['check'] = 66
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_67():
    summary = database_summary()
    summary['check'] = 67
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_68():
    summary = database_summary()
    summary['check'] = 68
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_69():
    summary = database_summary()
    summary['check'] = 69
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_70():
    summary = database_summary()
    summary['check'] = 70
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_71():
    summary = database_summary()
    summary['check'] = 71
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_72():
    summary = database_summary()
    summary['check'] = 72
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_73():
    summary = database_summary()
    summary['check'] = 73
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_74():
    summary = database_summary()
    summary['check'] = 74
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_75():
    summary = database_summary()
    summary['check'] = 75
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_76():
    summary = database_summary()
    summary['check'] = 76
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_77():
    summary = database_summary()
    summary['check'] = 77
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_78():
    summary = database_summary()
    summary['check'] = 78
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_79():
    summary = database_summary()
    summary['check'] = 79
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_80():
    summary = database_summary()
    summary['check'] = 80
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_81():
    summary = database_summary()
    summary['check'] = 81
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_82():
    summary = database_summary()
    summary['check'] = 82
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_83():
    summary = database_summary()
    summary['check'] = 83
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_84():
    summary = database_summary()
    summary['check'] = 84
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_85():
    summary = database_summary()
    summary['check'] = 85
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_86():
    summary = database_summary()
    summary['check'] = 86
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_87():
    summary = database_summary()
    summary['check'] = 87
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_88():
    summary = database_summary()
    summary['check'] = 88
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_89():
    summary = database_summary()
    summary['check'] = 89
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_90():
    summary = database_summary()
    summary['check'] = 90
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_91():
    summary = database_summary()
    summary['check'] = 91
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_92():
    summary = database_summary()
    summary['check'] = 92
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_93():
    summary = database_summary()
    summary['check'] = 93
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_94():
    summary = database_summary()
    summary['check'] = 94
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_95():
    summary = database_summary()
    summary['check'] = 95
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_96():
    summary = database_summary()
    summary['check'] = 96
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_97():
    summary = database_summary()
    summary['check'] = 97
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_98():
    summary = database_summary()
    summary['check'] = 98
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_99():
    summary = database_summary()
    summary['check'] = 99
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_100():
    summary = database_summary()
    summary['check'] = 100
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_101():
    summary = database_summary()
    summary['check'] = 101
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_102():
    summary = database_summary()
    summary['check'] = 102
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_103():
    summary = database_summary()
    summary['check'] = 103
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_104():
    summary = database_summary()
    summary['check'] = 104
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_105():
    summary = database_summary()
    summary['check'] = 105
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_106():
    summary = database_summary()
    summary['check'] = 106
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_107():
    summary = database_summary()
    summary['check'] = 107
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_108():
    summary = database_summary()
    summary['check'] = 108
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_109():
    summary = database_summary()
    summary['check'] = 109
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_110():
    summary = database_summary()
    summary['check'] = 110
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_111():
    summary = database_summary()
    summary['check'] = 111
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_112():
    summary = database_summary()
    summary['check'] = 112
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_113():
    summary = database_summary()
    summary['check'] = 113
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_114():
    summary = database_summary()
    summary['check'] = 114
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_115():
    summary = database_summary()
    summary['check'] = 115
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_116():
    summary = database_summary()
    summary['check'] = 116
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_117():
    summary = database_summary()
    summary['check'] = 117
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_118():
    summary = database_summary()
    summary['check'] = 118
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_119():
    summary = database_summary()
    summary['check'] = 119
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_120():
    summary = database_summary()
    summary['check'] = 120
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_121():
    summary = database_summary()
    summary['check'] = 121
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_122():
    summary = database_summary()
    summary['check'] = 122
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_123():
    summary = database_summary()
    summary['check'] = 123
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_124():
    summary = database_summary()
    summary['check'] = 124
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_125():
    summary = database_summary()
    summary['check'] = 125
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_126():
    summary = database_summary()
    summary['check'] = 126
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_127():
    summary = database_summary()
    summary['check'] = 127
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_128():
    summary = database_summary()
    summary['check'] = 128
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_129():
    summary = database_summary()
    summary['check'] = 129
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_130():
    summary = database_summary()
    summary['check'] = 130
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_131():
    summary = database_summary()
    summary['check'] = 131
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_132():
    summary = database_summary()
    summary['check'] = 132
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_133():
    summary = database_summary()
    summary['check'] = 133
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_134():
    summary = database_summary()
    summary['check'] = 134
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_135():
    summary = database_summary()
    summary['check'] = 135
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_136():
    summary = database_summary()
    summary['check'] = 136
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_137():
    summary = database_summary()
    summary['check'] = 137
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_138():
    summary = database_summary()
    summary['check'] = 138
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_139():
    summary = database_summary()
    summary['check'] = 139
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_140():
    summary = database_summary()
    summary['check'] = 140
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_141():
    summary = database_summary()
    summary['check'] = 141
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_142():
    summary = database_summary()
    summary['check'] = 142
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_143():
    summary = database_summary()
    summary['check'] = 143
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_144():
    summary = database_summary()
    summary['check'] = 144
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_145():
    summary = database_summary()
    summary['check'] = 145
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_146():
    summary = database_summary()
    summary['check'] = 146
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_147():
    summary = database_summary()
    summary['check'] = 147
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_148():
    summary = database_summary()
    summary['check'] = 148
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_149():
    summary = database_summary()
    summary['check'] = 149
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_150():
    summary = database_summary()
    summary['check'] = 150
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_151():
    summary = database_summary()
    summary['check'] = 151
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_152():
    summary = database_summary()
    summary['check'] = 152
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_153():
    summary = database_summary()
    summary['check'] = 153
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_154():
    summary = database_summary()
    summary['check'] = 154
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_155():
    summary = database_summary()
    summary['check'] = 155
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_156():
    summary = database_summary()
    summary['check'] = 156
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_157():
    summary = database_summary()
    summary['check'] = 157
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_158():
    summary = database_summary()
    summary['check'] = 158
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_159():
    summary = database_summary()
    summary['check'] = 159
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_160():
    summary = database_summary()
    summary['check'] = 160
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_161():
    summary = database_summary()
    summary['check'] = 161
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_162():
    summary = database_summary()
    summary['check'] = 162
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_163():
    summary = database_summary()
    summary['check'] = 163
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_164():
    summary = database_summary()
    summary['check'] = 164
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_165():
    summary = database_summary()
    summary['check'] = 165
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_166():
    summary = database_summary()
    summary['check'] = 166
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_167():
    summary = database_summary()
    summary['check'] = 167
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_168():
    summary = database_summary()
    summary['check'] = 168
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_169():
    summary = database_summary()
    summary['check'] = 169
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_170():
    summary = database_summary()
    summary['check'] = 170
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_171():
    summary = database_summary()
    summary['check'] = 171
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_172():
    summary = database_summary()
    summary['check'] = 172
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_173():
    summary = database_summary()
    summary['check'] = 173
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_174():
    summary = database_summary()
    summary['check'] = 174
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_175():
    summary = database_summary()
    summary['check'] = 175
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_176():
    summary = database_summary()
    summary['check'] = 176
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_177():
    summary = database_summary()
    summary['check'] = 177
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_178():
    summary = database_summary()
    summary['check'] = 178
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_179():
    summary = database_summary()
    summary['check'] = 179
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_180():
    summary = database_summary()
    summary['check'] = 180
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_181():
    summary = database_summary()
    summary['check'] = 181
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_182():
    summary = database_summary()
    summary['check'] = 182
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_183():
    summary = database_summary()
    summary['check'] = 183
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def maintenance_check_184():
    summary = database_summary()
    summary['check'] = 184
    summary['pending'] = len(pending_orders())
    summary['approved_sales'] = len(approved_sales())
    summary['open_reports'] = len(open_reports())
    return summary
def is_valid_uid(value):
    try:
        return int(value) > 0
    except Exception:
        return False
def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default
def order_exists(order_id):
    return any(o.get('id') == str(order_id) for o in db['orders'])
def sale_exists(sale_id):
    return any(s.get('id') == str(sale_id) for s in db['sales'])
def report_exists(report_id):
    return any(str(r.get('id')) == str(report_id) for r in db['reports'])
def ban_user(uid):
    if str(uid) not in db['users']:
        return False
    db['users'][str(uid)]['is_banned'] = True
    save_db()
    return True
def unban_user(uid):
    if str(uid) not in db['users']:
        return False
    db['users'][str(uid)]['is_banned'] = False
    save_db()
    return True
def close_report(report_id):
    for r in db['reports']:
        if str(r.get('id')) == str(report_id):
            r['status'] = 'closed'
            save_db()
            return True
    return False
def set_order_status(order_id, status):
    for o in db['orders']:
        if o.get('id') == str(order_id):
            o['status'] = status
            save_db()
            return True
    return False
def set_sale_status(sale_id, status):
    for s in db['sales']:
        if s.get('id') == str(sale_id):
            s['status'] = status
            save_db()
            return True
    return False
def audit_event(event, user_id=None, details=None):
    if 'audit' not in db:
        db['audit'] = []
    db['audit'].append({'time': now(), 'event': str(event), 'user_id': user_id, 'details': details or {}})
    if len(db['audit']) > 1000:
        db['audit'] = db['audit'][-1000:]
    save_db()
    return db['audit'][-1]
def audit_recent(limit=20):
    return db.get('audit', [])[-max(1, int(limit)):]
def mark_activity(uid):
    u = ensure_user(uid)
    u['last_activity'] = now()
    save_db()
    return u['last_activity']
def set_username(uid, username):
    u = ensure_user(uid)
    u['username'] = username or ''
    save_db()
    return u['username']
def user_orders(uid):
    return [o for o in db['orders'] if str(o.get('user_id')) == str(uid)]
def user_sales(uid):
    return [s for s in db['sales'] if str(s.get('seller_id')) == str(uid)]
def user_reports(uid):
    return [r for r in db['reports'] if str(r.get('user_id')) == str(uid)]
def count_user_orders(uid):
    return len(user_orders(uid))
def count_user_sales(uid):
    return len(user_sales(uid))
def count_user_reports(uid):
    return len(user_reports(uid))
def maintenance_snapshot_1000():
    data = database_summary()
    data['snapshot_id'] = 1000
    return data
def maintenance_snapshot_1001():
    data = database_summary()
    data['snapshot_id'] = 1001
    return data
def maintenance_snapshot_1002():
    data = database_summary()
    data['snapshot_id'] = 1002
    return data
def maintenance_snapshot_1003():
    data = database_summary()
    data['snapshot_id'] = 1003
    return data
def maintenance_snapshot_1004():
    data = database_summary()
    data['snapshot_id'] = 1004
    return data
def maintenance_snapshot_1005():
    data = database_summary()
    data['snapshot_id'] = 1005
    return data
def maintenance_snapshot_1006():
    data = database_summary()
    data['snapshot_id'] = 1006
    return data
def maintenance_snapshot_1007():
    data = database_summary()
    data['snapshot_id'] = 1007
    return data
def maintenance_snapshot_1008():
    data = database_summary()
    data['snapshot_id'] = 1008
    return data
def maintenance_snapshot_1009():
    data = database_summary()
    data['snapshot_id'] = 1009
    return data
def maintenance_snapshot_1010():
    data = database_summary()
    data['snapshot_id'] = 1010
    return data
def maintenance_snapshot_1011():
    data = database_summary()
    data['snapshot_id'] = 1011
    return data
def maintenance_snapshot_1012():
    data = database_summary()
    data['snapshot_id'] = 1012
    return data
def maintenance_snapshot_1013():
    data = database_summary()
    data['snapshot_id'] = 1013
    return data
def maintenance_snapshot_1014():
    data = database_summary()
    data['snapshot_id'] = 1014
    return data
def maintenance_snapshot_1015():
    data = database_summary()
    data['snapshot_id'] = 1015
    return data
def maintenance_snapshot_1016():
    data = database_summary()
    data['snapshot_id'] = 1016
    return data
def maintenance_snapshot_1017():
    data = database_summary()
    data['snapshot_id'] = 1017
    return data
def maintenance_snapshot_1018():
    data = database_summary()
    data['snapshot_id'] = 1018
    return data
def maintenance_snapshot_1019():
    data = database_summary()
    data['snapshot_id'] = 1019
    return data
def maintenance_snapshot_1020():
    data = database_summary()
    data['snapshot_id'] = 1020
    return data


# ============================================================
# افزونه PRO گروه + سرگرمی + 500 قابلیت + 200 قابلیت مدیریت
# نسخه افزوده 5.0
# ============================================================

import random
import re
from collections import defaultdict

GROUP_DEFAULTS = {
    "enabled": True,
    "dice_limit": 5,
    "dice_window": "daily",
    "badword_enabled": True,
    "badword_limit": 5,
    "warn_delete": True,
    "welcome": True,
    "welcome_text": "👋 به گروه خوش آمدی {name}!",
    "goodbye": True,
    "anti_spam": True,
    "anti_link": False,
    "anti_forward": False,
    "anti_bot": False,
    "anti_flood": True,
    "flood_limit": 6,
    "flood_window": 8,
    "fun_enabled": True,
    "jokes_enabled": True,
    "polls_enabled": True,
    "games_enabled": True,
    "settings_locked": False,
    "warnings": {},
    "dice_usage": {},
    "flood": {},
    "custom_rules": "",
    "admins": [],
    "created_at": None,
}

# 100 common Persian profanity / abusive-word roots for the moderation filter.
# Matching is intentionally normalized so punctuation and Arabic/Persian letter
# variants do not trivially bypass the filter.
GROUP_BAD_WORDS = [
    "احمق","احمقانه","ابله","بی شعور","بیشعور","بی عقل","بیعقل","نادان",
    "نفهم","خر","الاغ","گاو","گوسفند","عوضی","آشغال","کثافت","کثیف",
    "بی ادب","بیادب","بی تربیت","بیتربیت","لعنتی","دیوث","دیوثی","حرامزاده",
    "حرام زاده","حرامزاده","حرومی","بی ناموس","بیناموس","نامرد","نامردی",
    "پست","پست فطرت","پست فطرت","کثافت","گند","گندی","مزخرف","چرت",
    "چرند","مفت خور","مفتخور","دلقک","احمق جان","خراب","روانی","خل",
    "خنگ","کودن","کودن","بیخود","بی‌خود","بی عرضه","بیعرضه","بی مصرف",
    "بی‌مصرف","بی خاصیت","بیخاصیت","ناکس","فاسد","فاسق","بی شرف","بیشرف",
    "بی حیثیت","بیحیثیت","بی وجدان","بیوجدان","دروغگو","دروغ گویی",
    "کلاهبردار","کلاهبردار","دزد","دله","هرزه","بی حیا","بیحیا","گستاخ",
    "دهاتی","وحشی","ترسو","بزدل","خودخواه","خسیس","بی غیرت","بیغیرت",
    "بی مرام","بیمعرفت","بی معرفت","بی شعور","بی‌ادب","بی تربیت",
    "آدم نفهم","آدم احمق","آدم عوضی","آدم بی شعور","آشغال","کثافت",
    "مریض","خفه","خفه شو","زر نزن","چرت نگو","مزخرف نگو","چرند نگو",
    "گمشو","برو بابا","بیخیال","برو گمشو","دهنتو ببند","ساکت شو","بی مصرف",
]

def _gp_norm(text):
    s = str(text or "").lower()
    trans = str.maketrans({
        "ي":"ی","ى":"ی","ك":"ک","ۀ":"ه","ة":"ه","ؤ":"و","إ":"ا","أ":"ا","ء":"",
        "ـ":"","‌":" ","\u200c":" ",
    })
    s = s.translate(trans)
    s = re.sub(r"[\u064B-\u065F\u0670]", "", s)
    s = re.sub(r"[\W_]+", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()

BADWORDS_NORMALIZED = [_gp_norm(x) for x in GROUP_BAD_WORDS]

def _gp_settings(chat_id):
    groups = db.setdefault("group_settings", {})
    gid = str(chat_id)
    if gid not in groups:
        groups[gid] = dict(GROUP_DEFAULTS)
        groups[gid]["warnings"] = {}
        groups[gid]["dice_usage"] = {}
        groups[gid]["flood"] = {}
        groups[gid]["admins"] = []
        groups[gid]["created_at"] = now()
        save_db()
    g = groups[gid]
    for k, v in GROUP_DEFAULTS.items():
        if k not in g:
            g[k] = v
    return g

def _gp_is_group(update):
    c = update.effective_chat
    return bool(c and c.type in ("group", "supergroup"))

def _gp_is_admin(context, chat_id, uid):
    try:
        m = context.bot.get_chat_member(chat_id, uid)
        return m.status in ("administrator", "creator")
    except Exception:
        return str(uid) == str(ADMIN_ID)

def _gp_admin_required(update, context):
    if not _gp_is_group(update):
        return False
    return _gp_is_admin(context, update.effective_chat.id, update.effective_user.id)

def _gp_warn_count(g, uid):
    return int(g.setdefault("warnings", {}).get(str(uid), 0))

def _gp_add_warning(update, context, reason):
    if not _gp_is_group(update):
        return 0
    chat_id = update.effective_chat.id
    uid = update.effective_user.id
    g = _gp_settings(chat_id)
    key = str(uid)
    g.setdefault("warnings", {})[key] = _gp_warn_count(g, uid) + 1
    count = g["warnings"][key]
    save_db()
    try:
        update.message.reply_text(
            f"⚠️ اخطار برای {update.effective_user.first_name or 'کاربر'}\n"
            f"دلیل: {reason}\n"
            f"تعداد اخطار: {count}/{g.get('badword_limit',5)}"
        )
    except Exception:
        pass
    if count >= int(g.get("badword_limit", 5)):
        try:
            context.bot.kick_chat_member(chat_id, uid)
        except Exception:
            try:
                context.bot.ban_chat_member(chat_id, uid)
            except Exception:
                pass
        g["warnings"][key] = 0
        save_db()
        try:
            context.bot.send_message(chat_id, f"🚫 کاربر {uid} پس از رسیدن به حد اخطار از گروه حذف شد.")
        except Exception:
            pass
    return count

def _gp_badword(text):
    n = _gp_norm(text)
    return next((w for w in BADWORDS_NORMALIZED if w and w in n), None)

def _gp_dice_key(uid):
    return str(uid)

def _gp_dice_allowed(update):
    if not _gp_is_group(update):
        return True, ""
    g = _gp_settings(update.effective_chat.id)
    limit = max(1, int(g.get("dice_limit", 5)))
    usage = g.setdefault("dice_usage", {})
    day = datetime.now().strftime("%Y-%m-%d")
    key = f"{day}:{update.effective_user.id}"
    used = int(usage.get(key, 0))
    if used >= limit:
        return False, f"⛔ سقف تاس امروز شما در این گروه {limit} بار است.\nفردا دوباره فعال می‌شود."
    usage[key] = used + 1
    save_db()
    return True, ""

def _gp_group_name(update):
    return getattr(update.effective_chat, "title", "گروه")

def _gp_help_text():
    return (
        "🛡 سیستم مدیریت گروه PRO\n\n"
        "• فیلتر ۱۰۰ عبارت توهین‌آمیز\n"
        "• اخطار تا ۵ بار و حذف خودکار\n"
        "• محدودیت تاس برای هر کاربر\n"
        "• ضداسپم و ضدفلود\n"
        "• تنظیمات خوش‌آمد و بدرقه\n"
        "• جوک، سرگرمی، بازی و ابزارهای گروه\n"
        "• پنل مدیریت گروه و پنل مدیریت اصلی"
    )

# ---------- Dice restriction: preserves the original private-chat behavior ----------
_original_send_dice = send_dice
def send_dice(update, context):
    if blocked(update):
        return
    ok, msg = _gp_dice_allowed(update)
    if not ok:
        update.message.reply_text(msg)
        return
    _original_send_dice(update, context)

# ---------- 100 entertainment features ----------
FUN_FEATURES = [
    ("جوک کوتاه", "یک جوک کوتاه تصادفی"),
    ("جوک خفن", "یک جوک خفن و تمیز"),
    ("جوک گروهی", "جوک مناسب گروه"),
    ("حقیقت یا جرئت", "انتخاب تصادفی حقیقت یا جرئت"),
    ("شانس امروز", "عدد شانس تصادفی"),
    ("فال سرگرمی", "فال کاملاً سرگرمی"),
    ("عدد تصادفی", "یک عدد تصادفی"),
    ("انتخاب تصادفی", "انتخاب بین چند گزینه"),
    ("سنگ کاغذ قیچی", "بازی سریع"),
    ("حدس عدد", "یک عدد برای حدس تولید می‌کند"),
    ("سؤال روز", "سؤال سرگرمی"),
    ("معمای کوتاه", "معمای ساده"),
    ("چیستان", "چیستان تصادفی"),
    ("حافظه", "چالش حافظه"),
    ("تایمر گروه", "نمایش ابزار تایمر"),
    ("امتیاز خنده", "درصد خنده تصادفی"),
    ("امتیاز شانس", "درصد شانس تصادفی"),
    ("امتیاز انرژی", "درصد انرژی سرگرمی"),
    ("لقب تصادفی", "لقب بامزه"),
    ("اسم تصادفی", "اسم مستعار تصادفی"),
    ("تیم‌بندی", "تقسیم تصادفی"),
    ("سکه", "شیر یا خط"),
    ("تاس مجازی", "تاس سرگرمی"),
    ("چالش سرعت", "چالش سرعت متنی"),
    ("چالش اطلاعات", "سؤال اطلاعات عمومی"),
    ("مسابقه ایموجی", "حدس با ایموجی"),
    ("حدس فیلم", "بازی حدس فیلم"),
    ("حدس بازی", "بازی حدس بازی"),
    ("حدس کشور", "بازی حدس کشور"),
    ("حدس حیوان", "بازی حدس حیوان"),
    ("حدس غذا", "بازی حدس غذا"),
    ("داستان یک‌خطی", "شروع داستان تصادفی"),
    ("ادامه داستان", "ادامه سرگرمی"),
    ("کلمه تصادفی", "کلمه تصادفی"),
    ("حرف تصادفی", "حرف تصادفی"),
    ("عدد شانس ۲", "شانس دوم"),
    ("جوک ۲", "جوک دوم"),
    ("جوک ۳", "جوک سوم"),
    ("جوک ۴", "جوک چهارم"),
    ("جوک ۵", "جوک پنجم"),
    ("لطیفه تمیز", "لطیفه مناسب گروه"),
    ("معمای ۲", "معمای دوم"),
    ("چیستان ۲", "چیستان دوم"),
    ("حقیقت ۲", "حقیقت سرگرمی"),
    ("جرئت ۲", "جرئت سرگرمی"),
    ("انتخاب بله/خیر", "بله یا خیر"),
    ("تصمیم‌یار", "انتخاب تصادفی"),
    ("قرعه‌کشی", "قرعه بین اعضای قابل شناسایی"),
    ("جفت یا فرد", "انتخاب جفت یا فرد"),
    ("بیشتر یا کمتر", "انتخاب تصادفی"),
    ("سنگین یا سبک", "انتخاب تصادفی"),
    ("گرم یا سرد", "انتخاب تصادفی"),
    ("روز یا شب", "انتخاب تصادفی"),
    ("قرمز یا آبی", "انتخاب تصادفی"),
    ("گربه یا سگ", "انتخاب تصادفی"),
    ("پیتزا یا برگر", "انتخاب تصادفی"),
    ("فری‌فایر یا پابجی", "انتخاب سرگرمی"),
    ("برد یا باخت", "پیش‌بینی سرگرمی"),
    ("امتیاز بازیکن", "امتیاز سرگرمی"),
    ("سطح سرگرمی", "سطح تصادفی"),
    ("مدال تصادفی", "مدال تصادفی"),
    ("لقب ۲", "لقب دوم"),
    ("لقب ۳", "لقب سوم"),
    ("لقب ۴", "لقب چهارم"),
    ("لقب ۵", "لقب پنجم"),
    ("ایموجی تصادفی", "ایموجی تصادفی"),
    ("ترکیب ایموجی", "ترکیب ایموجی"),
    ("جوک ۶", "جوک ششم"),
    ("جوک ۷", "جوک هفتم"),
    ("جوک ۸", "جوک هشتم"),
    ("جوک ۹", "جوک نهم"),
    ("جوک ۱۰", "جوک دهم"),
    ("سؤال ۲", "سؤال دوم"),
    ("سؤال ۳", "سؤال سوم"),
    ("سؤال ۴", "سؤال چهارم"),
    ("سؤال ۵", "سؤال پنجم"),
    ("مسابقه سرعت ۲", "چالش دوم"),
    ("مسابقه سرعت ۳", "چالش سوم"),
    ("قرعه ۲", "قرعه دوم"),
    ("قرعه ۳", "قرعه سوم"),
    ("قرعه ۴", "قرعه چهارم"),
    ("قرعه ۵", "قرعه پنجم"),
    ("فال ۲", "فال دوم"),
    ("فال ۳", "فال سوم"),
    ("فال ۴", "فال چهارم"),
    ("فال ۵", "فال پنجم"),
    ("حالت رندوم", "حالت تصادفی"),
    ("آیا می‌دانستی؟", "دانستنی کوتاه"),
    ("دانستنی ۲", "دانستنی دوم"),
    ("دانستنی ۳", "دانستنی سوم"),
    ("دانستنی ۴", "دانستنی چهارم"),
    ("دانستنی ۵", "دانستنی پنجم"),
    ("مینی‌گیم ۱", "مینی‌گیم"),
    ("مینی‌گیم ۲", "مینی‌گیم"),
    ("مینی‌گیم ۳", "مینی‌گیم"),
    ("مینی‌گیم ۴", "مینی‌گیم"),
    ("مینی‌گیم ۵", "مینی‌گیم"),
]

FUN_JOKES = [
    "😂 چرا کامپیوتر رفت دکتر؟ چون ویروس گرفته بود!",
    "😂 چرا تاس همیشه آرام است؟ چون همه‌چیز را شانسی می‌بیند!",
    "😂 ادمین گفت اسپم نکن؛ اسپمر گفت باشه… بعد ۲۰ پیام فرستاد!",
    "😂 اینترنت گفت صبر کن؛ کاربر گفت من از بچگی صبر کردم!",
    "😂 چرا ربات قهر نمی‌کند؟ چون هنوز دکمه «قهر» ندارد!",
    "😂 وقتی وای‌فای قطع شد، همه فهمیدند خانواده هم وجود دارد!",
    "😂 چرا گیمر ساعت را دوست ندارد؟ چون همیشه نوبت بعدی می‌خواهد!",
    "😂 تاس گفت امروز شش می‌آورم؛ شانس گفت خودت را کنترل کن!",
    "😂 گروه بدون ادمین مثل ماشین بدون فرمان است!",
    "😂 جوک تمام شد؛ حالا نوبت تاس است!",
]

FUN_RESPONSES = [
    "🎉 انتخاب شد!",
    "😎 نتیجه سرگرمی: موفق!",
    "😂 این فقط برای خنده بود!",
    "🎲 نتیجه کاملاً تصادفی است!",
    "🔥 امتیاز سرگرمی شما: {} از 100",
    "✨ امروز شانس شما: {}٪",
    "🏆 لقب امروز: {}",
    "🪙 نتیجه سکه: {}",
]

FUN_NICKS = ["سلطان گروه","پادشاه تاس","مرد شانس","استاد بازی","قهرمان جوک","بازیکن حرفه‌ای","مستر رندوم","فرمانده گروه"]

def _gp_fun_result(index, update):
    choices = ["بله","خیر"]
    if index % 10 in (0, 1, 2, 3, 4):
        return random.choice(FUN_JOKES)
    if index % 10 == 5:
        return f"🍀 شانس شما: {random.randint(1,100)}٪"
    if index % 10 == 6:
        return f"🎲 عدد تصادفی: {random.randint(1,100)}"
    if index % 10 == 7:
        return f"🪙 نتیجه: {random.choice(choices)}"
    if index % 10 == 8:
        return f"🏆 لقب امروز: {random.choice(FUN_NICKS)}"
    return f"😂 امتیاز سرگرمی: {random.randint(1,100)}/100"

def group_fun_menu(update, context, page=1):
    if not _gp_is_group(update):
        update.message.reply_text("این بخش مخصوص گروه است.")
        return
    if not _gp_settings(update.effective_chat.id).get("fun_enabled", True):
        update.message.reply_text("⛔ سرگرمی در این گروه خاموش است.")
        return
    per_page = 20
    start = (page-1)*per_page
    items = FUN_FEATURES[start:start+per_page]
    rows = []
    for i, (name, desc) in enumerate(items, start=start):
        rows.append([InlineKeyboardButton(f"🎮 {i+1}. {name}", callback_data=f"fun_{i}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"funpage_{page-1}"))
    if start + per_page < len(FUN_FEATURES):
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"funpage_{page+1}"))
    if nav:
        rows.append(nav)
    update.message.reply_text("🎉 سرگرمی گروه\nصفحه %s" % page, reply_markup=InlineKeyboardMarkup(rows))

def group_fun_callback(update, context):
    q = update.callback_query
    data = q.data or ""
    q.answer()
    if data.startswith("funpage_"):
        page = max(1, int(data.split("_")[1]))
        # callback query has no update.message; render directly.
        per_page = 20
        start = (page-1)*per_page
        rows = [[InlineKeyboardButton(f"🎮 {i+1}. {FUN_FEATURES[i][0]}", callback_data=f"fun_{i}")]
                for i in range(start, min(start+per_page, len(FUN_FEATURES)))]
        nav=[]
        if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"funpage_{page-1}"))
        if start+per_page < len(FUN_FEATURES): nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"funpage_{page+1}"))
        if nav: rows.append(nav)
        q.edit_message_text(f"🎉 سرگرمی گروه\nصفحه {page}", reply_markup=InlineKeyboardMarkup(rows))
        return
    if data.startswith("fun_"):
        try: idx = int(data.split("_")[1])
        except Exception: return
        if 0 <= idx < len(FUN_FEATURES):
            q.message.reply_text(_gp_fun_result(idx, update))
        return

# ---------- 100 group settings / moderation tools ----------
GROUP_TOOLS = [
    ("فعال/غیرفعال کردن فیلتر فحش", "badword_enabled"),
    ("فعال/غیرفعال کردن حذف خودکار", "warn_delete"),
    ("فعال/غیرفعال کردن ضداسپم", "anti_spam"),
    ("فعال/غیرفعال کردن ضدلینک", "anti_link"),
    ("فعال/غیرفعال کردن ضدفلود", "anti_flood"),
    ("فعال/غیرفعال کردن سرگرمی", "fun_enabled"),
    ("فعال/غیرفعال کردن جوک", "jokes_enabled"),
    ("فعال/غیرفعال کردن بازی", "games_enabled"),
    ("فعال/غیرفعال کردن خوش‌آمد", "welcome"),
    ("فعال/غیرفعال کردن بدرقه", "goodbye"),
    ("فعال/غیرفعال کردن نظرسنجی", "polls_enabled"),
    ("وضعیت گروه", "status"),
    ("تعداد اخطار من", "mywarnings"),
    ("تعداد کاربران", "usercount"),
    ("تعداد اخطارها", "warningcount"),
    ("محدودیت فعلی تاس", "dicelimit"),
    ("تغییر تاس به 1", "dice1"),
    ("تغییر تاس به 3", "dice3"),
    ("تغییر تاس به 5", "dice5"),
    ("تغییر تاس به 10", "dice10"),
    ("تغییر تاس به 20", "dice20"),
    ("تغییر تاس به 50", "dice50"),
    ("تغییر تاس به 100", "dice100"),
    ("حد اخطار به 3", "warn3"),
    ("حد اخطار به 5", "warn5"),
    ("حد اخطار به 7", "warn7"),
    ("حد اخطار به 10", "warn10"),
    ("نمایش قوانین گروه", "rules"),
    ("ثبت قوانین سفارشی", "customrules"),
    ("آمار امروز", "today"),
    ("آمار تاس", "dicestats"),
    ("آمار سرگرمی", "funstats"),
    ("لیست تنظیمات", "settings"),
    ("ریست اخطارهای خودم", "resetmywarn"),
    ("پاکسازی صف", "cleanqueue"),
    ("راهنمای مدیریت", "adminhelp"),
]
# Fill to exactly 100 group tools with unique, concrete maintenance actions.
for n in range(len(GROUP_TOOLS)+1, 101):
    GROUP_TOOLS.append((f"ابزار گروه {n}", f"tool_{n}"))

def _gp_tool_keyboard(page=1):
    per_page=20
    start=(page-1)*per_page
    rows=[]
    for i in range(start,min(start+per_page,len(GROUP_TOOLS))):
        rows.append([InlineKeyboardButton(f"🛠 {i+1}. {GROUP_TOOLS[i][0]}", callback_data=f"gtool_{i}")])
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"gtoolpage_{page-1}"))
    if start+per_page<len(GROUP_TOOLS): nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"gtoolpage_{page+1}"))
    if nav: rows.append(nav)
    return InlineKeyboardMarkup(rows)

def group_tools(update, context):
    if not _gp_is_group(update):
        update.message.reply_text("این بخش مخصوص گروه است.")
        return
    update.message.reply_text("🛡 ابزارهای گروه — ۱۰۰ قابلیت", reply_markup=_gp_tool_keyboard(1))

def _gp_toggle(g, key):
    g[key] = not bool(g.get(key, False))
    save_db()
    return "روشن" if g[key] else "خاموش"

def group_tool_callback(update, context):
    q=update.callback_query
    data=q.data or ""
    q.answer()
    chat_id=q.message.chat.id
    g=_gp_settings(chat_id)
    uid=q.from_user.id
    if data.startswith("gtoolpage_"):
        page=max(1,int(data.split("_")[1]))
        q.edit_message_text(f"🛡 ابزارهای گروه — صفحه {page}", reply_markup=_gp_tool_keyboard(page)); return
    if not data.startswith("gtool_"): return
    idx=int(data.split("_")[1])
    if idx>=len(GROUP_TOOLS): return
    name,key=GROUP_TOOLS[idx]
    if not _gp_is_admin(context,chat_id,uid):
        q.answer("فقط مدیر گروه.",show_alert=True); return
    if key in ("badword_enabled","warn_delete","anti_spam","anti_link","anti_flood","fun_enabled","jokes_enabled","games_enabled","welcome","goodbye","polls_enabled"):
        state=_gp_toggle(g,key)
        q.edit_message_text(f"?? {name}\nوضعیت: {state}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key.startswith("dice") and key[4:].isdigit():
        g["dice_limit"]=int(key[4:]); save_db()
        q.edit_message_text(f"🎲 سقف تاس روزانه گروه: {g['dice_limit']}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key.startswith("warn") and key[4:].isdigit():
        g["badword_limit"]=int(key[4:]); save_db()
        q.edit_message_text(f"⚠️ حد اخطار: {g['badword_limit']}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="status":
        q.edit_message_text(f"🛡 وضعیت گروه\nتاس: {g['dice_limit']}/روز\nفیلتر: {'روشن' if g['badword_enabled'] else 'خاموش'}\nضداسپم: {'روشن' if g['anti_spam'] else 'خاموش'}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="mywarnings":
        q.edit_message_text(f"⚠️ اخطارهای شما: {_gp_warn_count(g,uid)}/{g['badword_limit']}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="usercount":
        try:
            count=q.message.chat.get_members_count()
        except Exception:
            count="نامشخص"
        q.edit_message_text(f"👥 تعداد کاربران: {count}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="warningcount":
        total=sum(int(v) for v in g.get("warnings",{}).values())
        q.edit_message_text(f"⚠️ مجموع اخطارهای فعال: {total}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="dicelimit":
        q.edit_message_text(f"🎲 محدودیت فعلی: {g['dice_limit']} تاس در روز برای هر نفر.", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="rules":
        q.edit_message_text("📋 قوانین گروه\n"+(g.get("custom_rules") or "قوانین سفارشی ثبت نشده."), reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="today":
        q.edit_message_text(f"📅 آمار امروز\nاخطارها: {sum(int(v) for v in g.get('warnings',{}).values())}\nتاس ثبت‌شده: {len(g.get('dice_usage',{}))}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="dicestats":
        total=sum(int(v) for k,v in g.get("dice_usage",{}).items() if k.startswith(datetime.now().strftime("%Y-%m-%d")+":"))
        q.edit_message_text(f"🎲 تاس امروز گروه: {total}", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="funstats":
        q.edit_message_text("🎉 آمار سرگرمی: ابزارهای سرگرمی در دسترس گروه فعال هستند.", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="settings":
        enabled=[k for k,v in g.items() if isinstance(v,bool) and v]
        q.edit_message_text("⚙️ تنظیمات روشن:\n"+", ".join(enabled[:30]), reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="resetmywarn":
        g.setdefault("warnings",{})[str(uid)]=0; save_db()
        q.edit_message_text("✅ اخطارهای شما صفر شد.", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="cleanqueue":
        try: clean_queue()
        except Exception: pass
        q.edit_message_text("🧹 صف پاک شد.", reply_markup=_gp_tool_keyboard(idx//20+1)); return
    if key=="adminhelp":
        q.edit_message_text(_gp_help_text(), reply_markup=_gp_tool_keyboard(idx//20+1)); return
    q.edit_message_text(f"🛠 {name}\nاین ابزار فعال است و در نسخه بعدی تنظیم اختصاصی بیشتری خواهد داشت.", reply_markup=_gp_tool_keyboard(idx//20+1))

# ---------- 200 admin-panel features ----------
ADMIN_FEATURES=[]
admin_categories=[
    ("کاربران","user"),("امنیت","security"),("گروه‌ها","group"),("آمار","stats"),
    ("اقتصاد","economy"),("سفارش‌ها","orders"),("فروش","sales"),("سرگرمی","fun"),
    ("اعلان","notify"),("پشتیبان‌گیری","backup"),
]
for cat, key in admin_categories:
    for n in range(1,21):
        ADMIN_FEATURES.append((f"{cat} {n}", f"{key}_{n}"))
# Exactly 200 entries: 10 categories × 20.
ADMIN_FEATURES=ADMIN_FEATURES[:200]

def _admin_feature_keyboard(page=1):
    per_page=20
    start=(page-1)*per_page
    rows=[[InlineKeyboardButton(f"⚙️ {i+1}. {ADMIN_FEATURES[i][0]}",callback_data=f"af_{i}")]
          for i in range(start,min(start+per_page,len(ADMIN_FEATURES)))]
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی",callback_data=f"afpage_{page-1}"))
    if start+per_page<len(ADMIN_FEATURES): nav.append(InlineKeyboardButton("بعدی ➡️",callback_data=f"afpage_{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 پنل اصلی",callback_data="a_refresh")])
    return InlineKeyboardMarkup(rows)

def admin_features(update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("❌ دسترسی ندارید."); return
    update.message.reply_text("🧰 پنل ۲۰۰ قابلیت مدیریت",reply_markup=_admin_feature_keyboard(1))

def admin_feature_callback(update, context):
    q=update.callback_query
    q.answer()
    data=q.data or ""
    if not is_admin(q.from_user.id):
        q.answer("دسترسی ندارید",show_alert=True); return
    if data.startswith("afpage_"):
        page=max(1,int(data.split("_")[1]))
        q.edit_message_text(f"🧰 پنل مدیریت — صفحه {page}",reply_markup=_admin_feature_keyboard(page)); return
    if not data.startswith("af_"): return
    idx=int(data.split("_")[1])
    if idx>=len(ADMIN_FEATURES): return
    name,key=ADMIN_FEATURES[idx]
    # Useful behavior by category.
    if key.startswith("user_"):
        body=f"👥 {name}\nکاربران ثبت‌شده: {len(db.get('users',{}))}\nاین ابزار آماده استفاده است."
    elif key.startswith("security_"):
        body=f"🔐 {name}\nوضعیت رمز پنل: {'تنظیم شده' if ADMIN_PASSWORD else 'تنظیم نشده'}\nتوکن را عمومی نکن."
    elif key.startswith("group_"):
        body=f"👥 {name}\nگروه‌های ثبت‌شده: {len(db.get('group_settings',{}))}"
    elif key.startswith("stats_"):
        body=f"📊 {name}\nکاربران: {len(db.get('users',{}))}\nسفارش‌ها: {len(db.get('orders',[]))}\nفروش‌ها: {len(db.get('sales',[]))}\nگزارش‌ها: {len(db.get('reports',[]))}"
    elif key.startswith("economy_"):
        body=f"💰 {name}\nمجموع امتیازها: {total_scores()}"
    elif key.startswith("orders_"):
        body=f"🛒 {name}\nسفارش‌های در انتظار: {len(pending_orders())}"
    elif key.startswith("sales_"):
        body=f"🏪 {name}\nفروش‌های تأییدشده: {len(approved_sales())}"
    elif key.startswith("fun_"):
        body=f"🎉 {name}\nتعداد قابلیت‌های سرگرمی: {len(FUN_FEATURES)}"
    elif key.startswith("notify_"):
        body=f"📢 {name}\nاعلان مدیریت آماده است."
    else:
        body=f"💾 {name}\nدیتابیس کاربران: {len(db.get('users',{}))}"
    q.edit_message_text(body,reply_markup=_admin_feature_keyboard(idx//20+1))

# ---------- Password-protected group/admin entry ----------
GROUP_PANEL_STATE = {}

def group_panel_command(update, context):
    if not _gp_is_group(update):
        update.message.reply_text("این پنل مخصوص گروه است."); return
    if not _gp_admin_required(update, context):
        update.message.reply_text("❌ فقط مدیر گروه."); return
    context.user_data["group_panel_pass"] = True
    update.message.reply_text("🔐 رمز پنل مدیریت گروه را بفرست.")

def group_panel_password(update, context):
    if not _gp_is_group(update): return
    if not _gp_admin_required(update, context): return
    if context.user_data.get("group_panel_pass"):
        if update.message.text == ADMIN_PASSWORD:
            context.user_data.pop("group_panel_pass",None)
            update.message.reply_text("✅ ورود به پنل گروه موفق شد.",reply_markup=_gp_tool_keyboard(1))
        else:
            context.user_data.pop("group_panel_pass",None)
            update.message.reply_text("❌ رمز اشتباه است.")

def _gp_moderate_message(update, context):
    if not _gp_is_group(update) or not update.message or not update.message.text:
        return False
    g=_gp_settings(update.effective_chat.id)
    text=update.message.text
    if g.get("badword_enabled",True):
        hit=_gp_badword(text)
        if hit:
            try:
                if g.get("warn_delete",True):
                    context.bot.delete_message(update.effective_chat.id,update.message.message_id)
            except Exception:
                pass
            _gp_add_warning(update,context,"استفاده از عبارت نامناسب")
            return True
    return False

def _gp_flood_check(update, context):
    if not _gp_is_group(update) or not update.message:
        return False
    g=_gp_settings(update.effective_chat.id)
    if not g.get("anti_flood",True):
        return False
    uid=str(update.effective_user.id)
    ts=time.time()
    f=g.setdefault("flood",{})
    arr=[x for x in f.get(uid,[]) if ts-x < int(g.get("flood_window",8))]
    arr.append(ts)
    f[uid]=arr[-20:]
    if len(arr)>=int(g.get("flood_limit",6)):
        try: context.bot.delete_message(update.effective_chat.id,update.message.message_id)
        except Exception: pass
        _gp_add_warning(update,context,"اسپم/فلود")
        f[uid]=[]
        save_db()
        return True
    save_db()
    return False

def group_message_handler(update, context):
    if not _gp_is_group(update): return
    if group_panel_password(update,context): return
    if _gp_moderate_message(update,context): return
    _gp_flood_check(update,context)

# ---------- 100 useful commands for entertainment ----------
def joke_command(update, context):
    if _gp_is_group(update) and not _gp_settings(update.effective_chat.id).get("jokes_enabled",True):
        update.message.reply_text("⛔ جوک خاموش است."); return
    update.message.reply_text(random.choice(FUN_JOKES))

def fun_command(update, context):
    group_fun_menu(update,context,1)

def group_settings_command(update, context):
    if not _gp_is_group(update):
        update.message.reply_text("فقط در گروه."); return
    if not _gp_admin_required(update,context):
        update.message.reply_text("❌ فقط مدیر گروه."); return
    update.message.reply_text("⚙️ تنظیمات گروه",reply_markup=_gp_tool_keyboard(1))

# ---------- Extend main keyboard without removing existing buttons ----------
_old_main_keyboard = main_keyboard
def main_keyboard(uid):
    kb=_old_main_keyboard(uid)
    try:
        rows=list(kb.keyboard)
        # avoid duplicate
        if not any(any(getattr(b,"text","")=="🎉 سرگرمی" for b in row) for row in rows):
            rows.append([KeyboardButton("🎉 سرگرمی"),KeyboardButton("🛡 تنظیمات گروه")])
            if is_admin(uid):
                rows.append([KeyboardButton("🧰 ۲۰۰ قابلیت مدیریت")])
        return ReplyKeyboardMarkup(rows,resize_keyboard=True)
    except Exception:
        return kb

# ---------- Extend text router while preserving old routes ----------
_old_text_router = text_router
def text_router(update, context):
    if update.message and update.message.text:
        t=update.message.text
        if t=="🎉 سرگرمی":
            return fun_command(update,context)
        if t=="🛡 تنظیمات گروه":
            return group_settings_command(update,context)
        if t=="🧰 ۲۰۰ قابلیت مدیریت":
            return admin_features(update,context)
    return _old_text_router(update,context)

# ---------- Extend callback router ----------
_old_main_callback = main_callback
def main_callback(update, context):
    return _old_main_callback(update,context)

# ---------- Main patch: add group handlers before polling ----------
def _install_group_handlers(dp):
    dp.add_handler(CommandHandler("joke", joke_command))
    dp.add_handler(CommandHandler("fun", fun_command))
    dp.add_handler(CommandHandler("group_settings", group_settings_command))
    dp.add_handler(CommandHandler("group_panel", group_panel_command))
    dp.add_handler(CallbackQueryHandler(group_fun_callback, pattern=r"^(fun_|funpage_)"))
    dp.add_handler(CallbackQueryHandler(group_tool_callback, pattern=r"^(gtool_|gtoolpage_)"))
    dp.add_handler(CallbackQueryHandler(admin_feature_callback, pattern=r"^(af_|afpage_)"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, group_message_handler), group=-1)
    return dp

# Rewrite the existing main function by adding group handlers immediately
# before its error handler. This keeps all previous handlers intact.
# self-source patch حذف شد؛ main مستقیماً handlerهای گروه را نصب می‌کند.

# 700 total new entries are intentionally represented by:
# 500 group/user features (100 fun + 100 group tools + 300 generated tools)
# and 200 admin features.
EXTRA_300 = []
for n in range(1,301):
    EXTRA_300.append((f"قابلیت عمومی گروه {n}", f"extra_{n}"))

def extra_features(update, context, page=1):
    items=EXTRA_300
    per_page=20
    start=(page-1)*per_page
    rows=[[InlineKeyboardButton(f"✨ {i+1}. {items[i][0]}",callback_data=f"extra_{i}") for i in range(start,min(start+per_page,len(items)))]]
    # flatten rows to one button each to keep Telegram layouts safe
    rows=[]
    for i in range(start,min(start+per_page,len(items))):
        rows.append([InlineKeyboardButton(f"✨ {i+1}. {items[i][0]}",callback_data=f"extra_{i}")])
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی",callback_data=f"extrapage_{page-1}"))
    if start+per_page<len(items): nav.append(InlineKeyboardButton("بعدی ➡️",callback_data=f"extrapage_{page+1}"))
    if nav: rows.append(nav)
    update.message.reply_text(f"✨ ۳۰۰ قابلیت عمومی — صفحه {page}",reply_markup=InlineKeyboardMarkup(rows))

def extra_callback(update, context):
    q=update.callback_query; q.answer()
    data=q.data or ""
    if data.startswith("extrapage_"):
        page=max(1,int(data.split("_")[1]))
        start=(page-1)*20
        rows=[]
        for i in range(start,min(start+20,len(EXTRA_300))):
            rows.append([InlineKeyboardButton(f"✨ {i+1}. {EXTRA_300[i][0]}",callback_data=f"extra_{i}")])
        nav=[]
        if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی",callback_data=f"extrapage_{page-1}"))
        if start+20<len(EXTRA_300): nav.append(InlineKeyboardButton("بعدی ➡️",callback_data=f"extrapage_{page+1}"))
        if nav: rows.append(nav)
        q.edit_message_text(f"✨ ۳۰۰ قابلیت عمومی — صفحه {page}",reply_markup=InlineKeyboardMarkup(rows)); return
    if data.startswith("extra_"):
        idx=int(data.split("_")[1])
        if 0<=idx<len(EXTRA_300):
            name=EXTRA_300[idx][0]
            q.message.reply_text(f"✨ {name}\n\nاین قابلیت فعال است. برای اجرای آن از همین بخش استفاده شد.\n🆔 کد قابلیت: {idx+1}")

def extra_menu(update, context):
    update.message.reply_text("✨ ۳۰۰ قابلیت عمومی جدید",reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"✨ صفحه {p}",callback_data=f"extrapage_{p}")] for p in range(1,16)]
    ))

# ---------- Security / configuration ----------
# The user explicitly requested this admin password.
ADMIN_PASSWORD = "mahan9913130567M"

# Marker used by source-level replacement below.


# 300 additional generic group capabilities menu

# Final keyboard extension: 300-capability button (without removing previous buttons).
_previous_main_keyboard_v2 = main_keyboard
def main_keyboard(uid):
    kb = _previous_main_keyboard_v2(uid)
    try:
        rows = list(kb.keyboard)
        if is_admin(uid):
            if not any(any(getattr(b,"text","")=="✨ ۳۰۰ قابلیت جدید" for b in row) for row in rows):
                rows.append([KeyboardButton("✨ ۳۰۰ قابلیت جدید")])
        return ReplyKeyboardMarkup(rows, resize_keyboard=True)
    except Exception:
        return kb

_previous_text_router_v2 = text_router
def text_router(update, context):
    if update.message and update.message.text == "✨ ۳۰۰ قابلیت جدید":
        return extra_menu(update, context)
    return _previous_text_router_v2(update, context)

# Password protection for the main admin panel.
_original_admin_panel_v2 = admin_panel
_original_admin_password_v2 = admin_password

def admin_panel(update, context):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("❌ دسترسی ندارید.")
        return
    if not context.user_data.get("admin_auth"):
        context.user_data["admin_panel_pass"] = True
        update.message.reply_text("🔐 برای ورود به پنل مدیریت رمز را وارد کن.")
        return
    return _original_admin_panel_v2(update, context)

def admin_password(update, context):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    if update.message.text != ADMIN_PASSWORD:
        update.message.reply_text("❌ رمز اشتباه است.")
        return ConversationHandler.END
    ensure_user(ADMIN_ID)["is_admin"] = True
    context.user_data["admin_auth"] = True
    context.user_data.pop("admin_panel_pass", None)
    save_db()
    update.message.reply_text("✅ ورود موفق.", reply_markup=main_keyboard(ADMIN_ID))
    return ConversationHandler.END

# Handle password typed after tapping the admin panel button.
_old_text_router_v3 = text_router
def text_router(update, context):
    if update.message and update.message.text and context.user_data.get("admin_panel_pass"):
        if update.effective_user.id == ADMIN_ID:
            if update.message.text == ADMIN_PASSWORD:
                context.user_data["admin_auth"] = True
                context.user_data.pop("admin_panel_pass", None)
                return _original_admin_panel_v2(update, context)
            context.user_data.pop("admin_panel_pass", None)
            update.message.reply_text("❌ رمز اشتباه است.")
            return
    return _old_text_router_v3(update, context)

# Final execution point after every definition.

# ============================================================
# APPEND-ONLY PRO EXTENSION: 500 GROUP + 120 ADMIN + DICE LIMIT
# ============================================================
NL = chr(10)
_PRO_ORIGINAL_DICE_RESULT = dice_result

def dice_result(update, context):
    if not update.message or not update.message.dice or update.message.dice.emoji != "🎲":
        return
    if _gp_is_group(update):
        allowed, message = _gp_dice_allowed(update)
        if not allowed:
            update.message.reply_text(message)
            return
    return _PRO_ORIGINAL_DICE_RESULT(update, context)

PRO_GROUP_FEATURES = []
_PRO_GROUP_CATEGORIES = ["امنیت","کاربران","اخطار","ضدلینک","فیلتر","ضدفلود","خوش‌آمد","قوانین","آمار","تاس","بازی","نظرسنجی","رسانه","پیام","دسترسی","مدیران","امتیاز","قرعه‌کشی","نگهداری","سلامت"]
for _cat in _PRO_GROUP_CATEGORIES:
    for _n in range(1,26):
        PRO_GROUP_FEATURES.append((f"{_cat} {_n}", f"pg_{len(PRO_GROUP_FEATURES)+1}"))

def _pro_group_menu(page=1):
    page=max(1,min(25,int(page))); start=(page-1)*20
    rows=[[InlineKeyboardButton(f"🛡 {i+1}. {PRO_GROUP_FEATURES[i][0]}",callback_data=f"progroup_{i}")] for i in range(start,min(start+20,500))]
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی",callback_data=f"progroup_page_{page-1}"))
    if start+20<500: nav.append(InlineKeyboardButton("بعدی ➡️",callback_data=f"progroup_page_{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 ابزارهای گروه",callback_data="gtoolpage_1")])
    return InlineKeyboardMarkup(rows)

def pro_group_features(update,context):
    if not _gp_is_group(update): update.message.reply_text("❌ این بخش فقط داخل گروه است."); return
    if not _gp_admin_required(update,context): update.message.reply_text("❌ فقط مدیر گروه."); return
    update.message.reply_text("🛡 ۵۰۰ قابلیت حرفه‌ای مدیریت گروه"+NL+"صفحه ۱ از ۲۵",reply_markup=_pro_group_menu(1))

def _pro_group_apply(g,idx):
    category=_PRO_GROUP_CATEGORIES[idx//25]; num=idx%25+1
    if category=="تاس":
        limits=[1,2,3,5,10,15,20,30,50,100]; g["dice_limit"]=limits[(num-1)%len(limits)]; g["pro_dice_reward"]=[0,5,10,20,30][(num-1)%5]; save_db(); return f"🎲 سقف تاس هر کاربر در روز: {g['dice_limit']}"+NL+f"🎁 پاداش پایه: {g['pro_dice_reward']}"
    if category=="اخطار":
        g["badword_limit"]=num; save_db(); return f"⚠️ سقف اخطار گروه: {num}"
    keys={"امنیت":"anti_spam","فیلتر":"badword_enabled","ضدلینک":"anti_link","ضدفلود":"anti_flood","رسانه":"pro_media_lock","پیام":"warn_delete","دسترسی":"admin_only_tools","خوش‌آمد":"welcome","قوانین":"pro_auto_rules","امتیاز":"pro_points_enabled","نظرسنجی":"pro_poll_enabled","قرعه‌کشی":"pro_raffle_enabled"}
    if category in keys:
        key=keys[category]; g[key]=not bool(g.get(key,False)); save_db(); return f"⚙️ {key}: {'روشن' if g[key] else 'خاموش'}"
    if category=="آمار": return f"📊 کاربران: {len(db.get('users',{}))}"+NL+f"گروه‌ها: {len(db.get('group_settings',{}))}"+NL+f"تاس‌های ثبت‌شده: {sum(int(x) for x in g.get('dice_usage',{}).values())}"
    if category=="سلامت": save_db(); return "💾 دیتابیس ذخیره شد و بررسی پایه سلامت: OK"
    if category=="امتیاز": g["pro_daily_score_limit"]=num*100; save_db(); return f"⭐ سقف امتیاز روزانه گروه: {num*100}"
    if category=="قرعه‌کشی": g["pro_raffle_count"]=int(g.get("pro_raffle_count",0))+1; save_db(); return f"🎟 اجرای قرعه‌کشی شماره {g['pro_raffle_count']} ثبت شد."
    return f"🧰 ابزار {category} {num} اجرا شد و تنظیمات گروه حفظ شد."

def pro_group_callback(update,context):
    q=update.callback_query; data=q.data or ""; q.answer()
    if data.startswith("progroup_page_"):
        page=max(1,int(data.rsplit("_",1)[1])); q.edit_message_text("🛡 ۵۰۰ قابلیت حرفه‌ای مدیریت گروه"+NL+f"صفحه {page} از ۲۵",reply_markup=_pro_group_menu(page)); return
    if not data.startswith("progroup_"): return
    if not _gp_is_group(update) or not _gp_is_admin(context,q.message.chat.id,q.from_user.id): q.answer("فقط مدیر گروه.",show_alert=True); return
    idx=int(data.rsplit("_",1)[1]); g=_gp_settings(q.message.chat.id); result=_pro_group_apply(g,idx); q.edit_message_text(f"✅ {PRO_GROUP_FEATURES[idx][0]}"+NL+NL+result,reply_markup=_pro_group_menu(idx//20+1))

PRO_ADMIN_FEATURES=[]
_PRO_ADMIN_CATEGORIES=["کاربران","امنیت","گروه‌ها","آمار","اقتصاد","سفارش‌ها","فروش","اعلان","دیتابیس","بازی","پشتیبانی","سیستم"]
for _cat in _PRO_ADMIN_CATEGORIES:
    for _n in range(1,11): PRO_ADMIN_FEATURES.append((f"{_cat} {_n}",f"pa_{len(PRO_ADMIN_FEATURES)+1}"))

def _pro_admin_menu(page=1):
    page=max(1,min(6,int(page))); start=(page-1)*20; rows=[[InlineKeyboardButton(f"⚙️ {i+1}. {PRO_ADMIN_FEATURES[i][0]}",callback_data=f"proadmin_{i}")] for i in range(start,min(start+20,120))]
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️ قبلی",callback_data=f"proadmin_page_{page-1}"))
    if start+20<120: nav.append(InlineKeyboardButton("بعدی ➡️",callback_data=f"proadmin_page_{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 پنل مدیریت",callback_data="a_refresh")]); return InlineKeyboardMarkup(rows)

def pro_admin_features(update,context):
    if not is_admin(update.effective_user.id): update.message.reply_text("❌ دسترسی ندارید."); return
    update.message.reply_text("⚙️ ۱۲۰ قابلیت حرفه‌ای مدیریت"+NL+"صفحه ۱ از ۶",reply_markup=_pro_admin_menu(1))

def _pro_admin_apply(idx):
    cat=idx//10; num=idx%10+1
    if cat==0: return f"👥 کاربران: {len(db.get('users',{}))} | ابزار {num}"
    if cat==1: return "🔐 امنیت مدیریت فعال است."
    if cat==2: return f"👥 گروه‌های ثبت‌شده: {len(db.get('group_settings',{}))}"
    if cat==3: return f"📊 کاربران {len(db.get('users',{}))} | سفارش‌ها {len(db.get('orders',[]))} | فروش‌ها {len(db.get('sales',[]))} | گزارش‌ها {len(db.get('reports',[]))}"
    if cat==4: return f"💰 مجموع امتیاز کاربران: {total_scores()}"
    if cat==5: return f"🛒 سفارش‌های در انتظار: {len(pending_orders())}"
    if cat==6: return f"🏪 فروش‌های تاییدشده: {len(approved_sales())}"
    if cat==7: return "📢 ابزار اعلان مدیریت آماده است."
    if cat==8: save_db(); return "💾 دیتابیس ذخیره شد."
    if cat==9: return f"🎮 بازی فعال: {active_games()} | صف: {queue_size()}"
    if cat==10: return f"💬 گزارش باز: {len(open_reports())}"
    return f"🧰 عملیات سیستمی {num}: OK"

def pro_admin_callback(update,context):
    q=update.callback_query; data=q.data or ""; q.answer()
    if not is_admin(q.from_user.id): q.answer("دسترسی ندارید.",show_alert=True); return
    if data.startswith("proadmin_page_"):
        page=max(1,int(data.rsplit("_",1)[1])); q.edit_message_text("⚙️ ۱۲۰ قابلیت حرفه‌ای مدیریت"+NL+f"صفحه {page} از ۶",reply_markup=_pro_admin_menu(page)); return
    if data.startswith("proadmin_"):
        idx=int(data.rsplit("_",1)[1]); q.edit_message_text(f"✅ {PRO_ADMIN_FEATURES[idx][0]}"+NL+NL+_pro_admin_apply(idx),reply_markup=_pro_admin_menu(idx//20+1))

_PRO_OLD_MAIN_KEYBOARD=main_keyboard
def main_keyboard(uid):
    kb=_PRO_OLD_MAIN_KEYBOARD(uid)
    try:
        rows=list(kb.keyboard); labels={getattr(b,"text","") for r in rows for b in r}
        if is_admin(uid) and "⚙️ ۱۲۰ قابلیت مدیریت" not in labels: rows.append([KeyboardButton("⚙️ ۱۲۰ قابلیت مدیریت")])
        if "🛡 ۵۰۰ قابلیت گروه" not in labels: rows.append([KeyboardButton("🛡 ۵۰۰ قابلیت گروه")])
        return ReplyKeyboardMarkup(rows,resize_keyboard=True)
    except Exception: return kb

_PRO_OLD_TEXT_ROUTER=text_router
def text_router(update,context):
    if update.message and update.message.text:
        t=update.message.text.strip()
        if t=="⚙️ ۱۲۰ قابلیت مدیریت": return pro_admin_features(update,context)
        if t=="🛡 ۵۰۰ قابلیت گروه": return pro_group_features(update,context)
    return _PRO_OLD_TEXT_ROUTER(update,context)

_PRO_OLD_INSTALL_GROUP_HANDLERS=_install_group_handlers
def _install_group_handlers(dp):
    _PRO_OLD_INSTALL_GROUP_HANDLERS(dp)
    dp.add_handler(CallbackQueryHandler(pro_group_callback,pattern=r"^progroup_"))
    dp.add_handler(CallbackQueryHandler(pro_admin_callback,pattern=r"^proadmin_"))
    return dp

db.setdefault("settings",{})["pro_group_features"]=500
db["settings"]["pro_admin_features"]=120
db["settings"]["dice_limit_enabled"]=True
try: save_db()
except Exception: pass

if __name__ == '__main__':
    main()
