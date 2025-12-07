import telebot
import sqlite3
from telebot import types

TOKEN = "8347295633:AAHvvAvyHwQTT0f3-xDS-m35klBUWgZRxaA"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Каналы, которые нужно проверять — оставляем только один
CHANNELS = {
    "@pizik_lab": -1002738738306
}

# Instagram — НЕ ПРОВЕРЯЕТСЯ
INSTAGRAM_LINK = "https://www.instagram.com/pizik_lab?utm_source=ig_web_button_share_sheet&igsh=ZDNlZDc0MzIxNw=="

ADMINS = [6986318573, 1091967814, 7646563258]

conn = sqlite3.connect("videos.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    file_id TEXT,
    full_name TEXT,
    age INTEGER,
    school TEXT,
    region TEXT
)
""")
conn.commit()


# Проверка подписки
def check_sub(user_id):
    try:
        link = "@pizik_lab"
        channel_id = CHANNELS[link]
        member = bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# Этапы заполнения информации
user_state = {}
user_data = {}


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id

    # Кнопки-ссылки
    markup = types.InlineKeyboardMarkup()
    for link in CHANNELS.keys():
        markup.add(types.InlineKeyboardButton(text=f"📌 {link}", url=f"https://t.me/{link[1:]}"))
    markup.add(types.InlineKeyboardButton("📸 Instagram", url=INSTAGRAM_LINK))
    markup.add(types.InlineKeyboardButton("🔄 Obunani tekshirish", callback_data="check_sub"))

    bot.send_message(
        chat_id,
        "Davom ettirish uchun pastdagi kanallarga obuna bo'ling! 👇\nObuna bo'lganingizdan so'ng «Obunani tekshirish» tugmasini bosing.",
        reply_markup=markup
    )


# Нажата кнопка "Проверить"
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check(call):
    user_id = call.from_user.id

    if check_sub(user_id):
        user_state[user_id] = "ask_name"
        user_data[user_id] = {}
        bot.send_message(call.message.chat.id, "🎉 Ajoyib! Siz obuna bo'ldingiz!\n\n<b>Ism va familiyangizni</b> kiriting:")
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali kanallarga obuna bo'lmagansiz!")


@bot.message_handler(func=lambda m: m.from_user.id in user_state)
def registration_steps(message):
    user_id = message.from_user.id
    state = user_state.get(user_id)

    if state == "ask_name":
        user_data[user_id]["full_name"] = message.text
        user_state[user_id] = "ask_age"
        bot.send_message(message.chat.id, "📅 Yoshingiz nechida?")
        return

    if state == "ask_age":
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "Yoshingizni raqamlar bilan kiriting!")
            return
        user_data[user_id]["age"] = int(message.text)
        user_state[user_id] = "ask_school"
        bot.send_message(message.chat.id, "🏫 Qaysi maktabda o'qiysiz?")
        return

    if state == "ask_school":
        user_data[user_id]["school"] = message.text
        user_state[user_id] = "ask_region"
        bot.send_message(message.chat.id, "🌍 Qaysi viloyatdansiz?")
        return

    if state == "ask_region":
        user_data[user_id]["region"] = message.text
        user_state[user_id] = "wait_video"
        bot.send_message(message.chat.id, "🎥 Endi videoni jo'nating:")
        return


# Получение видео
@bot.message_handler(content_types=['video'])
def receive_video(message):
    user_id = message.from_user.id

    # 🔥 Проверяем: участник уже отправлял видео?
    cursor.execute("SELECT id FROM videos WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "⚠️ Siz allaqachon tanlovda ishtirok etgansiz! Qayta video yubora olmaysiz.")
        return

    # Проверка подписки
    if not check_sub(user_id):
        bot.send_message(message.chat.id, "❌ Avval kanallarga obuna bo'ling!")
        return

    # Проверяем, завершил ли регистрацию
    if user_id not in user_state or user_state[user_id] != "wait_video":
        bot.send_message(message.chat.id, "📌 Avval ma'lumotlaringizni kiriting! /start")
        return

    file_id = message.video.file_id
    username = message.from_user.username or "No username"

    # Сохраняем данные
    cursor.execute("""
        INSERT INTO videos (user_id, username, file_id, full_name, age, school, region)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        file_id,
        user_data[user_id]["full_name"],
        user_data[user_id]["age"],
        user_data[user_id]["school"],
        user_data[user_id]["region"]
    ))
    conn.commit()

    # Чистим состояния
    user_state.pop(user_id, None)
    user_data.pop(user_id, None)

    bot.send_message(message.chat.id, "🎉 Video yuborildi! Omad tilaymiz!")


# Админ панель
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMINS:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📄 Videolar ro'yhati")
    bot.send_message(message.chat.id, "Admin-panel", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "📄 Videolar ro'yhati")
def list_videos(message):
    if message.from_user.id not in ADMINS:
        return

    cursor.execute("SELECT id, username, full_name FROM videos")
    videos = cursor.fetchall()

    if not videos:
        bot.send_message(message.chat.id, "Hozircha videolar yo'q")
        return

    text = "📄 <b>Jo'natilgan videolar ro'yhati</b>:\n\n"
    for vid in videos:
        username_display = vid[1] if vid[1] else "No username"
        text += f"ID: {vid[0]} — {username_display} — {vid[2]}\n"

    text += "\nBarcha ma'lumotlarni olish uchun video ID raqamini yuboring:"
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text.isdigit() and m.from_user.id in ADMINS)
def get_video(message):
    vid = int(message.text)

    cursor.execute("""
        SELECT username, full_name, age, school, region, file_id
        FROM videos WHERE id = ?
    """, (vid,))
    row = cursor.fetchone()

    if not row:
        bot.send_message(message.chat.id, "Video topilmadi")
        return

    username, full_name, age, school, region, file_id = row

    username_display = username if username else "No username"

    text = (
        f"📌 <b>Ishtirokchi ma'lumotlari</b>\n\n"
        f"👤 Ism Familiya: {full_name}\n"
        f"🎂 Yoshi: {age}\n"
        f"🏫 Maktab: {school}\n"
        f"🌍 Viloyat: {region}\n"
        f"🔗 Username: {username_display}\n"
    )

    bot.send_message(message.chat.id, text)
    bot.send_video(message.chat.id, file_id)


# Запуск бота
bot.polling(none_stop=True)
