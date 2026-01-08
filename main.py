import telebot
from telebot.types import *
import sqlite3
import requests

BOT_TOKEN = "8487056282:AAGj3HtURmLZ9VNckkbI4HSjtwAZH1L2nng"
ADMIN_ID = 7126212094

bot = telebot.TeleBot(BOT_TOKEN)

API_CODE_URL = "https://jasurcoder.alwaysdata.net/web/v1/auth/code"
user_phone = {}

# Ixtiyoriy (majburiy emas) kanallar
OPTIONAL_LINKS = [
    ("▶️ YouTube", "https://www.youtube.com/@OMAD_TDM"),
    ("📸 Instagram 1", "https://www.instagram.com/omad_sale"),
    ("📸 Instagram 2", "https://www.instagram.com/omad.tdm")
]


# ===========================
# 📌 DATABASE
# ===========================
db = sqlite3.connect("database.db", check_same_thread=False)
sql = db.cursor()

# Users table
sql.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    status TEXT
)
""")

# Channels table
sql.execute("""
CREATE TABLE IF NOT EXISTS mandatory_channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT
)
""")
db.commit()


# ===========================
# 📌 USER FUNCTIONS
# ===========================
def register_user(user_id):
    sql.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if sql.fetchone() is None:
        sql.execute("INSERT INTO users(user_id, status) VALUES(?, ?)", (user_id, "active"))
        db.commit()


def get_user_status(user_id):
    sql.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
    row = sql.fetchone()
    if row:
        return row[0]
    return "active"


# ===========================
# 📌 ADMIN PANEL
# ===========================
def admin_panel(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📋 Majburiy kanallar", callback_data="admin_channels"))
    kb.add(InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"))
    kb.add(InlineKeyboardButton("📨 Habar yuborish", callback_data="admin_broadcast"))
    bot.send_message(chat_id, "🔧 Admin panel:", reply_markup=kb)


# START
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    # Agar user bo‘lsa — ro‘yxatga olish
    register_user(user_id)

    # Agar block bo‘lsa — ishlamaydi
    if get_user_status(user_id) == "blocked":
        bot.send_message(user_id, "🚫 Siz blocklangansiz!")
        return

    # Admin bo‘lsa — faqat admin panel
    if user_id == ADMIN_ID:
        admin_panel(user_id)
        return

    send_registration_menu(message.chat.id)


# ===========================
# 📌 REGISTRATION MENU
# ===========================
def send_registration_menu(chat_id):
    required_channels = get_channels()

    markup = InlineKeyboardMarkup()

    # 🔴 Majburiy kanallar (title bilan)
    for username in required_channels:
        try:
            chat_info = bot.get_chat(username)
            title = chat_info.title
        except:
            title = username  # fallback
        markup.add(InlineKeyboardButton(f"🔔 {title}", url=f"https://t.me/{username.replace('@', '')}"))

    # 🟡 Majburiy emas — oddiy kanallar
    for name, link in OPTIONAL_LINKS:
        markup.add(InlineKeyboardButton(name, url=link))

    # Tekshirish tugmasi
    markup.add(InlineKeyboardButton("📢 Obunani tekshirish", callback_data="check_sub"))

    bot.send_message(
        chat_id,
        "🔔 <b>Ro‘yxatdan o‘tish uchun majburiy kanallarga obuna bo‘ling:</b>",
        parse_mode="HTML",
        reply_markup=markup
    )



# ===========================
# 📌 CHANNEL DB FUNCS
# ===========================
def get_channels():
    sql.execute("SELECT channel FROM mandatory_channels")
    return [row[0] for row in sql.fetchall()]


def add_channel_db(c):
    sql.execute("INSERT INTO mandatory_channels(channel) VALUES(?)", (c,))
    db.commit()


def delete_channel_db(c):
    sql.execute("DELETE FROM mandatory_channels WHERE channel=?", (c,))
    db.commit()


# ===========================
# 📌 ADMIN → CHANNEL SETTINGS
# ===========================
@bot.callback_query_handler(func=lambda c: c.data == "admin_channels")
def admin_channels(call):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Qo‘shish", callback_data="add_channel"),
        InlineKeyboardButton("➖ O‘chirish", callback_data="remove_channel")
    )
    kb.add(InlineKeyboardButton("📄 Ro‘yxat", callback_data="list_channels"))
    bot.edit_message_text("⚙️ Majburiy kanallar:", call.message.chat.id, call.message.message_id, reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "add_channel")
def add_channel_handler(call):
    msg = bot.send_message(call.message.chat.id, "➕ Kanalni @ bilan kiriting:")
    bot.register_next_step_handler(msg, finish_add_channel)


def finish_add_channel(message):
    text = message.text.strip()
    if not text.startswith("@"):
        bot.send_message(message.chat.id, "❌ @ bilan kiriting!")
        return
    add_channel_db(text)
    bot.send_message(message.chat.id, "✅ Qo‘shildi!")


@bot.callback_query_handler(func=lambda c: c.data == "remove_channel")
def remove_channel_handler(call):
    channels = get_channels()
    if not channels:
        bot.send_message(call.message.chat.id, "Kanal yo‘q.")
        return

    kb = InlineKeyboardMarkup()
    for c in channels:
        kb.add(InlineKeyboardButton(f"❌ {c}", callback_data=f"del_{c}"))
    bot.send_message(call.message.chat.id, "O‘chirish uchun tanlang:", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def finish_delete_channel(call):
    ch = call.data.replace("del_", "")
    delete_channel_db(ch)
    bot.send_message(call.message.chat.id, f"{ch} o‘chirildi.")

@bot.callback_query_handler(func=lambda c: c.data == "list_channels")
def list_channels(call):
    channels = get_channels()
    if not channels:
        bot.send_message(call.message.chat.id, "📋 Majburiy kanallar yo‘q")
        return

    text = "📋 <b>Majburiy kanallar ro‘yxati:</b>\n\n"

    for username in channels:
        try:
            chat_info = bot.get_chat(username)
            title = chat_info.title
        except:
            title = username
        text += f"• {title}  ({username})\n"

    bot.send_message(call.message.chat.id, text, parse_mode="HTML")



# ===========================
# 📌 CHECK SUBSCRIPTION
# ===========================
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    user_id = call.from_user.id

    for channel in get_channels():
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ["member", "creator", "administrator"]:
                bot.answer_callback_query(call.id, "❌ Obuna yo‘q")
                return
        except:
            bot.answer_callback_query(call.id, "❌ Bot kanalni ko‘ra olmaydi")
            return

    bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True))
    bot.send_message(call.message.chat.id, "📱 Raqam yuboring:\n\nWeb saytda kiritilgan telefon nomer bolishi shart !", reply_markup=kb)


# ===========================
# 📌 CONTACT HANDLER
# ===========================
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    user_phone[message.chat.id] = phone

    wait = bot.send_message(message.chat.id, "⏳ Kod olinmoqda...")

    code = get_code(phone)

    if code == "NO_CODE":
        bot.edit_message_text("❗ Bu raqam uchun kod yaratilmagan!\n\nWeb saytda kiritilgan raqam bilan telegramdagi raqam bir xil bolishi kere !", message.chat.id, wait.message_id)
    elif code == "API_ERROR":
        bot.edit_message_text("❌ API xatosi!", message.chat.id, wait.message_id)
    else:
        bot.delete_message(message.chat.id, wait.message_id)
        send_code(message.chat.id, code)


# API
def get_code(phone):
    try:
        r = requests.get(f"{API_CODE_URL}/{phone}")
        data = r.json()

        if not data.get("success"):
            if "No active verification code" in data.get("message", ""):
                return "NO_CODE"
            return "API_ERROR"

        return data["data"]["code"]

    except:
        return "API_ERROR"


def send_code(chat_id, code):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangi kod", callback_data="new_code"))

    bot.send_message(chat_id,
                     f"🔐 <b>Kod:</b>\n\n<code>{code}</code>",
                     parse_mode="HTML",
                     reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "new_code")
def new_code(call):
    phone = user_phone.get(call.message.chat.id)
    if not phone:
        bot.answer_callback_query(call.id, "❌ Avval raqam yuboring!")
        return

    code = get_code(phone)

    if code in ["NO_CODE", "API_ERROR"]:
        bot.answer_callback_query(call.id, "❗ Kod mavjud emas!")
    else:
        send_code(call.message.chat.id, code)
        bot.answer_callback_query(call.id, "✅ Yangi kod yuborildi!")


# ===========================
# 📌 ADMIN → STATISTICS
# ===========================
@bot.callback_query_handler(func=lambda c: c.data == "admin_stats")
def admin_stats(call):
    sql.execute("SELECT COUNT(*) FROM users")
    all_users = sql.fetchone()[0]

    sql.execute("SELECT COUNT(*) FROM users WHERE status='active'")
    active_users = sql.fetchone()[0]

    sql.execute("SELECT COUNT(*) FROM users WHERE status='blocked'")
    blocked_users = sql.fetchone()[0]

    msg = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Umumiy: <b>{all_users}</b>\n"
        f"🟢 Aktiv: <b>{active_users}</b>\n"
        f"🔴 Blocklangan: <b>{blocked_users}</b>"
    )
    bot.send_message(call.message.chat.id, msg, parse_mode="HTML")


# ===========================
# 📌 ADMIN → BROADCAST
# ===========================
broadcast_mode = False
broadcast_caption = None


@bot.callback_query_handler(func=lambda c: c.data == "admin_broadcast")
def admin_broadcast(call):
    global broadcast_mode, broadcast_caption
    broadcast_mode = True
    broadcast_caption = None
    bot.send_message(call.message.chat.id, "📨 Yubormoqchi bo‘lgan xabaringizni jo‘nating:")
    

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def handle_broadcast(message):
    global broadcast_mode

    if not broadcast_mode:
        return

    # Get all users
    sql.execute("SELECT user_id FROM users WHERE status='active'")
    users = [row[0] for row in sql.fetchall()]

    sent = 0

    for uid in users:
        try:
            if message.content_type == "text":
                bot.send_message(uid, message.text)

            elif message.content_type == "photo":
                bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)

            elif message.content_type == "video":
                bot.send_video(uid, message.video.file_id, caption=message.caption)

            elif message.content_type == "voice":
                bot.send_voice(uid, message.voice.file_id)

            elif message.content_type == "video_note":
                bot.send_video_note(uid, message.video_note.file_id)

            elif message.content_type == "document":
                bot.send_document(uid, message.document.file_id, caption=message.caption)

            sent += 1
        except:
            pass

    broadcast_mode = False
    bot.send_message(ADMIN_ID, f"📨 Yuborildi: {sent} ta foydalanuvchiga")


# ===========================
# 📌 START BOT
# ===========================
bot.infinity_polling()

