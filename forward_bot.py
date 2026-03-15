import telebot
from telebot import types
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 7985206085))

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler()
user_state = {}

CONFIG_FILE = 'bot_config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'ad_text': '', 'ad_interval_minutes': 5, 'is_ad_active': False, 'is_forwarding_active': True}

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

config = load_config()

# ---- REKLAMA ----
def send_ad():
    c = load_config()
    source_id = c.get('source_channel')
    if c.get('is_ad_active') and c.get('ad_text') and source_id:
        try:
            bot.send_message(source_id, c['ad_text'])
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
    print(f"[LOG] Channel post received from chat_id={message.chat.id}")
    cfg = load_config()
    
    # Auto-learn the source channel for ads
    if cfg.get('source_channel') != message.chat.id:
        cfg['source_channel'] = message.chat.id
        save_config(cfg)
        print(f"[LOG] Updated source_channel to {message.chat.id}")

    dest_id = cfg.get('destination_group')
    if not dest_id:
        print(f"[LOG] No destination group configured. Use /setgroup in a group to set one.")
        return

    if not cfg.get('is_forwarding_active', False):
        print(f"[LOG] Forwarding is disabled in config.")
        return

    print(f"[LOG] Forwarding message {message.message_id} to {dest_id}")
    try:
        bot.copy_message(dest_id, message.chat.id, message.message_id)
        print(f"[OK] Copied {message.message_id} to {dest_id}")
        
        try:
            bot.delete_message(message.chat.id, message.message_id)
            print(f"[OK] Deleted {message.message_id} from channel")
        except Exception as e:
            print(f"[WARN] Delete failed: {e}")
    except Exception as e:
        print(f"[ERROR] Copy failed: {e}. Check if bot is admin in BOTH channel and group.")
        
# ---- SET GROUP ID ----
@bot.message_handler(commands=['setgroup'], func=lambda m: m.from_user.id == ADMIN_ID)
def set_destination_group(message):
    if message.chat.type in ['group', 'supergroup']:
        config['destination_group'] = message.chat.id
        save_config(config)
        bot.reply_to(message, f"✅ Bu guruh ({message.chat.id}) qabul qilish guruhi etib belgilandi!")
    else:
        bot.reply_to(message, "Bu buyruqni faqat guruhda yozish orqali guruhni ro'yxatdan o'tkazasiz.")

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
        ),
        types.InlineKeyboardButton(
            f"{'🟢 Forward YOQILGAN' if config.get('is_forwarding_active', True) else '🔴 Forward O`CHIRILGAN'}",
            callback_data="fwd_toggle"
        )
    )
    txt = (f"🛠 *Admin Panel*\n\n"
           f"📢 Reklama: {'Yoqilgan' if config.get('is_ad_active') else 'O`chirilgan'}\n"
           f"⏱ Interval: {config.get('ad_interval_minutes', 5)} minut\n"
           f"🔄 Forward: {'Yoqilgan' if config.get('is_forwarding_active', True) else 'O`chirilgan'}\n"
           f"📝 Matn:\n{config.get('ad_text', '(bo`sh)')}")
    bot.send_message(message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    cid = call.message.chat.id
    mid = call.message.message_id
    
    # Admin actions
    if call.from_user.id == ADMIN_ID and call.data.startswith('ad_') or call.data.startswith('fwd_'):
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
        elif call.data == "fwd_toggle":
            config['is_forwarding_active'] = not config.get('is_forwarding_active', True)
            save_config(config)
            bot.answer_callback_query(call.id, "Forward holati o'zgartirildi!")
            admin_panel(call.message)
        return

    # User actions (Order confirmation)
    if cid in user_state and isinstance(user_state[cid], dict):
        s = user_state[cid]
        if call.data == "confirm_order":
            cfg = load_config()
            dest_id = cfg.get('destination_group')
            
            if not dest_id:
                bot.send_message(cid, "❌ Xatolik: Guruh hali sozlanmagan. Admin /setgroup buyrug'ini ishlatishi kerak.")
                return

            try:
                uid = call.from_user.id
                profile = f"<a href='tg://user?id={uid}'>{s['name']}</a>"
                title = "🚕 YANGI TAKSI BUYURTMA" if s['type'] == 'Taksi' else "📦 YANGI POCHTA BUYURTMA"
                txt = (f"<b>{title}</b>\n\n"
                       f"👤 <b>Mijoz:</b> {profile}\n"
                       f"📞 <b>Tel:</b> +{s['phone'].lstrip('+')}\n"
                       f"📍 <b>Qayerdan:</b> {s['from_loc']}\n"
                       f"🏁 <b>Qayerga:</b> {s['to_loc']}\n")
                
                msg = bot.send_message(dest_id, txt, parse_mode="HTML")
                if 'lat' in s and 'lon' in s:
                    bot.send_location(dest_id, s['lat'], s['lon'], reply_to_message_id=msg.message_id)
                
                bot.edit_message_text("✅ Hurmatli mijoz, siz bilan tez orada bog'lanishadi. Buyurtmangiz qabul qilindi.", cid, mid)
            except Exception as e:
                bot.send_message(cid, "❌ Xatolik yuz berdi, iltimos qaytadan urinib ko'ring.")
                print(f"[ERROR] Finalizing order: {e}")
            
            del user_state[cid]
            # Main menu
            mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.row(types.KeyboardButton("🚕 Taksi chaqirish"), types.KeyboardButton("📦 Pochta jo'natish"))
            bot.send_message(cid, "Yana xizmat kerakmi?", reply_markup=mk)
            
        elif call.data == "cancel_order":
            del user_state[cid]
            bot.edit_message_text("🚫 Buyurtma bekor qilindi.", cid, mid)
            mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.row(types.KeyboardButton("🚕 Taksi chaqirish"), types.KeyboardButton("📦 Pochta jo'natish"))
            bot.send_message(cid, "Bosh menyu:", reply_markup=mk)

# ---- /start ----
@bot.message_handler(commands=['start'])
def start(message):
    print(f"[LOG] Start command received from {message.from_user.id}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🚕 Taksi chaqirish"), types.KeyboardButton("📦 Pochta jo'natish"))
    try:
        bot.send_message(message.chat.id,
            f"Assalomu alaykum, {message.from_user.first_name}!\nTugmalardan birini tanlang:",
            reply_markup=markup)
        print(f"[LOG] Start message sent successfully")
    except Exception as e:
        print(f"[ERROR] Failed to send start message: {e}")

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
                minutes = int(text)
                if minutes <= 0:
                    bot.send_message(cid, "Musbat raqam yozing!")
                    return
                config['ad_interval_minutes'] = minutes
                save_config(config)
                reschedule_ad()
                bot.send_message(cid, f"✅ Interval {text} minut qilib belgilandi!")
            except ValueError:
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
        s['lat'] = message.location.latitude
        s['lon'] = message.location.longitude
        
        # Confirmation keyboard
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Tasdiqlash (Yuborish)", callback_data="confirm_order"),
            types.InlineKeyboardButton("❌ Rad etish", callback_data="cancel_order")
        )
        
        summary = (f"📋 <b>Buyurtma ma'lumotlari:</b>\n\n"
                  f"👤 Ism: {s['name']}\n"
                  f"📞 Tel: +{s['phone'].lstrip('+')}\n"
                  f"📍 Qayerdan: {s['from_loc']}\n"
                  f"🏁 Qayerga: {s['to_loc']}\n\n"
                  f"Ma'lumotlar to'g'rimi?")
        
        bot.send_message(cid, summary, reply_markup=markup, parse_mode="HTML")

if __name__ == '__main__':
    print("Bot ishga tushdi!")
    bot.infinity_polling(allowed_updates=["message", "callback_query", "channel_post"])
