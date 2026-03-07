import telebot
from telebot import types
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from keep_alive import keep_alive

TOKEN = '8580639697:AAFPv5TYWiWFXFxaMYQWPN7JzCwMUMYkVIQ'
ADMIN_ID = 7985206085
SOURCE_CHANNEL = -1002182432143
DESTINATION_GROUP = -1003664534861

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler()
user_state = {}

CONFIG_FILE = 'bot_config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'ad_text': '', 'ad_interval_minutes': 5, 'is_ad_active': False}

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

config = load_config()

# ---- REKLAMA ----
def send_ad():
    c = load_config()
    if c.get('is_ad_active') and c.get('ad_text'):
        try:
            bot.send_message(SOURCE_CHANNEL, c['ad_text'])
        except Exception as e:
            print(f"Ad error: {e}")

def reschedule_ad():
    scheduler.remove_all_jobs()
    if config.get('is_ad_active') and config.get('ad_interval_minutes', 0) > 0:
        scheduler.add_job(send_ad, 'interval', minutes=config['ad_interval_minutes'], id='ad_job')

scheduler.start()
reschedule_ad()

# ---- KANALDAN GURUHGA FORWARD ----
@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'])
def forward_channel(message):
    print(f"[CHANNEL POST] chat_id={message.chat.id}")
    if message.chat.id == SOURCE_CHANNEL:
        try:
            bot.copy_message(DESTINATION_GROUP, message.chat.id, message.message_id)
            bot.delete_message(message.chat.id, message.message_id)
            print("[OK] Forwarded and deleted")
        except Exception as e:
            print(f"[ERROR] Forward failed: {e}")

# ---- ADMIN PANEL ----
@bot.message_handler(commands=['admin'], func=lambda m: m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📝 Reklama matnini yozish", callback_data="ad_text"),
        types.InlineKeyboardButton("⏱ Vaqt belgilash (minut)", callback_data="ad_time"),
        types.InlineKeyboardButton(
            f"{'🟢 Reklama YOQILGAN' if config.get('is_ad_active') else '🔴 Reklama O`CHIRILGAN'}",
            callback_data="ad_toggle"
        )
    )
    txt = (f"🛠 *Admin Panel*\n\n"
           f"📢 Reklama: {'Yoqilgan' if config.get('is_ad_active') else 'O`chirilgan'}\n"
           f"⏱ Interval: {config.get('ad_interval_minutes', 5)} minut\n"
           f"📝 Matn:\n{config.get('ad_text', '(bo`sh)')}")
    bot.send_message(message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.from_user.id == ADMIN_ID)
def admin_cb(call):
    cid = call.message.chat.id
    if call.data == "ad_text":
        user_state[cid] = 'set_ad_text'
        bot.send_message(cid, "Reklama matnini yuboring:")
    elif call.data == "ad_time":
        user_state[cid] = 'set_ad_time'
        bot.send_message(cid, "Necha minutda bir chiqsin? (faqat raqam):")
    elif call.data == "ad_toggle":
        config['is_ad_active'] = not config.get('is_ad_active', False)
        save_config(config)
        reschedule_ad()
        bot.answer_callback_query(call.id, "O'zgartirildi!")
        admin_panel(call.message)

# ---- /start ----
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🚕 Taksi chaqirish"), types.KeyboardButton("📦 Pochta jo'natish"))
    bot.send_message(message.chat.id,
        f"Assalomu alaykum, {message.from_user.first_name}!\nTugmalardan birini tanlang:",
        reply_markup=markup)

# ---- TEXT HANDLER ----
@bot.message_handler(content_types=['text'], func=lambda m: m.chat.type == 'private')
def handle_text(message):
    cid = message.chat.id
    text = message.text

    # Admin text inputs
    if cid == ADMIN_ID and cid in user_state:
        if user_state[cid] == 'set_ad_text':
            config['ad_text'] = text
            save_config(config)
            del user_state[cid]
            bot.send_message(cid, "✅ Reklama matni saqlandi!")
            return
        elif user_state[cid] == 'set_ad_time':
            try:
                config['ad_interval_minutes'] = int(text)
                save_config(config)
                reschedule_ad()
                bot.send_message(cid, f"✅ Interval {text} minut qilib belgilandi!")
            except:
                bot.send_message(cid, "Faqat raqam yozing!")
                return
            del user_state[cid]
            return

    # Cancel
    if text == "🚫 Bekor qilish":
        if cid in user_state: del user_state[cid]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton("🚕 Taksi chaqirish"), types.KeyboardButton("📦 Pochta jo'natish"))
        bot.send_message(cid, "Bekor qilindi.", reply_markup=markup)
        return

    # Start order
    if text in ("🚕 Taksi chaqirish", "📦 Pochta jo'natish"):
        user_state[cid] = {'step': 'name', 'type': 'Taksi' if 'Taksi' in text else 'Pochta'}
        cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_markup.add(types.KeyboardButton("🚫 Bekor qilish"))
        bot.send_message(cid, "Ismingizni yozing:", reply_markup=cancel_markup)
        return

    # Order steps
    if cid in user_state and isinstance(user_state[cid], dict):
        s = user_state[cid]
        step = s['step']
        if step == 'name':
            s['name'] = text
            s['step'] = 'phone'
            mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
            mk.add(types.KeyboardButton("🚫 Bekor qilish"))
            bot.send_message(cid, "Telefon raqamingizni yuboring:", reply_markup=mk)
        elif step == 'from':
            s['from_loc'] = text
            s['step'] = 'to'
            bot.send_message(cid, "Qayerga borasiz (yoki jo'natasiz)?")
        elif step == 'to':
            s['to_loc'] = text
            s['step'] = 'location'
            mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.add(types.KeyboardButton("📍 Lokatsiyani yuborish", request_location=True))
            mk.add(types.KeyboardButton("🚫 Bekor qilish"))
            bot.send_message(cid, "Hozirgi lokatsiyangizni yuboring:", reply_markup=mk)

# ---- CONTACT ----
@bot.message_handler(content_types=['contact'], func=lambda m: m.chat.type == 'private')
def handle_contact(message):
    cid = message.chat.id
    if cid in user_state and isinstance(user_state[cid], dict) and user_state[cid]['step'] == 'phone':
        user_state[cid]['phone'] = message.contact.phone_number
        user_state[cid]['step'] = 'from'
        mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
        mk.add(types.KeyboardButton("🚫 Bekor qilish"))
        bot.send_message(cid, "Qayerdan ketasiz (yoki jo'natasiz)?", reply_markup=mk)

# ---- LOCATION ----
@bot.message_handler(content_types=['location'], func=lambda m: m.chat.type == 'private')
def handle_location(message):
    cid = message.chat.id
    if cid in user_state and isinstance(user_state[cid], dict) and user_state[cid]['step'] == 'location':
        s = user_state[cid]
        uid = message.from_user.id
        profile = f"<a href='tg://user?id={uid}'>{s['name']}</a>"
        title = "🚕 YANGI TAKSI BUYURTMA" if s['type'] == 'Taksi' else "📦 YANGI POCHTA BUYURTMA"
        txt = (f"<b>{title}</b>\n\n"
               f"👤 <b>Mijoz:</b> {profile}\n"
               f"📞 <b>Tel:</b> +{s['phone'].lstrip('+')}\n"
               f"📍 <b>Qayerdan:</b> {s['from_loc']}\n"
               f"🏁 <b>Qayerga:</b> {s['to_loc']}\n")
        try:
            msg = bot.send_message(DESTINATION_GROUP, txt, parse_mode="HTML")
            bot.send_location(DESTINATION_GROUP, message.location.latitude, message.location.longitude, reply_to_message_id=msg.message_id)
            bot.send_message(cid, "✅ Buyurtmangiz qabul qilindi!")
        except Exception as e:
            bot.send_message(cid, "Xatolik yuz berdi, keyinroq urinib ko'ring.")
            print(f"Order error: {e}")
        del user_state[cid]
        mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
        mk.row(types.KeyboardButton("🚕 Taksi chaqirish"), types.KeyboardButton("📦 Pochta jo'natish"))
        bot.send_message(cid, "Yana xizmat kerakmi?", reply_markup=mk)

if __name__ == '__main__':
    keep_alive()
    print("Bot ishga tushdi!")
    bot.infinity_polling(allowed_updates=["message", "callback_query", "channel_post"])
