import telebot
from telebot import types
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
import time

# Options & Setup
TOKEN = '8580639697:AAFPv5TYWiWFXFxaMYQWPN7JzCwMUMYkVIQ'
ADMIN_ID = 7985206085

# Initial configuration if config.json doesn't exist
CONFIG_FILE = 'bot_config.json'
default_config = {
    'source_channel': 0, # Int ID needed, or we can catch it dynamically
    'destination_group': 0,
    'ad_text': "Sizning reklamangiz shu yerda bo'lishi mumkin!",
    'ad_interval_minutes': 5,
    'is_ad_active': False,
    'is_forwarding_active': True 
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default_config.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

config = load_config()
bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler()

# State management
user_state = {}

KEYS = {
    'TAXI': '🚕 Taksi chaqirish',
    'MAIL': '📦 Pochta jo\'natish',
    'CANCEL': '🚫 Bekor qilish'
}

# -----------------
# BACKGROUND JOBS
# -----------------
def send_advertisement():
    config = load_config() # reload to get latest
    if not config['is_ad_active'] or not config['source_channel'] or not config['ad_text']:
        return

    try:
        bot.send_message(config['source_channel'], config['ad_text'])
    except Exception as e:
        print(f"Failed to send ad to source channel: {e}")

# We schedule it initially
def reschedule_ad():
    scheduler.remove_all_jobs()
    if config['is_ad_active'] and config['ad_interval_minutes'] > 0:
        scheduler.add_job(send_advertisement, 'interval', minutes=config['ad_interval_minutes'])

scheduler.start()
reschedule_ad()

# -----------------
# ADMIN PANEL
# -----------------
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Kechirasiz, siz admin emassiz.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Buttons for config
    btn_text = types.InlineKeyboardButton("📝 Reklama matnini o'zgartirish", callback_data="admin_ad_text")
    btn_time = types.InlineKeyboardButton("⏱ Vaqtni belgilash (minut)", callback_data="admin_ad_time")
    
    ad_status = "🟢 YOZISH YOQILGAN" if config['is_ad_active'] else "🔴 YOZISH O'CHIRILGAN"
    btn_toggle = types.InlineKeyboardButton(f"Reklama yoqish/o'chirish: {ad_status}", callback_data="admin_toggle_ad")

    fwd_status = "🟢 FORWARD YOQILGAN" if config['is_forwarding_active'] else "🔴 FORWARD O'CHIRILGAN"
    btn_fwd_toggle = types.InlineKeyboardButton(f"Kanal forward: {fwd_status}", callback_data="admin_toggle_fwd")
    
    btn_channels = types.InlineKeyboardButton("⚙️ Kanal/Guruh IDlarini sozlash", callback_data="admin_setup_ids")

    markup.add(btn_text, btn_time, btn_toggle, btn_fwd_toggle, btn_channels)
    
    text = (f"🛠 **Admin Panel**\n\n"
            f"**Kanal:** {config['source_channel']}\n"
            f"**Guruh:** {config['destination_group']}\n"
            f"**Reklama intervali:** {config['ad_interval_minutes']} minut\n"
            f"**Joriy reklama matni:**\n{config['ad_text']}")
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    chat_id = call.message.chat.id
    
    if call.data == "admin_ad_text":
        user_state[chat_id] = {'step': 'admin_set_ad_text'}
        bot.send_message(chat_id, "Yangi reklama matnini yuboring:")
        
    elif call.data == "admin_ad_time":
        user_state[chat_id] = {'step': 'admin_set_ad_time'}
        bot.send_message(chat_id, "Yangi intervalni (minutda) yuboring, faqat raqam:")

    elif call.data == "admin_toggle_ad":
        config['is_ad_active'] = not config['is_ad_active']
        save_config(config)
        reschedule_ad()
        bot.answer_callback_query(call.id, "Reklama holati o'zgardi!")
        admin_panel(call.message) # refresh panel
        
    elif call.data == "admin_toggle_fwd":
        config['is_forwarding_active'] = not config['is_forwarding_active']
        save_config(config)
        bot.answer_callback_query(call.id, "Kanal forward holati o'zgardi!")
        admin_panel(call.message) # refresh panel
        
    elif call.data == "admin_setup_ids":
        user_state[chat_id] = {'step': 'admin_set_source_chan'}
        bot.send_message(chat_id, "Avval qaysi kanaldan xabarlar olinganini yubormoqchisiz?\nMen shu kanalga admin qilingan bo'lishim shart.\n\nIltimos, o'sha kanaldagi biror postni menga Foward qiling (uzating):")


# -----------------
# CHANNEL FORWARDING LOGIC
# -----------------
@bot.channel_post_handler(func=lambda message: True)
def handle_channel_posts(message):
    global config
    # If config IDs are 0, we can auto-capture them if admin hasn't set them yet
    if config['source_channel'] == 0:
         config['source_channel'] = message.chat.id
         save_config(config)
         bot.send_message(ADMIN_ID, f"Avtomatik sozlandim! Source Channel ID: {message.chat.id}")

    # Forwarding logic
    if config['is_forwarding_active'] and message.chat.id == config['source_channel']:
        if config['destination_group'] != 0:
            try:
                # Copy message guarantees exact duplicate, forwards show 'Forwarded from'
                bot.copy_message(config['destination_group'], message.chat.id, message.message_id)
                # Then delete original
                bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                bot.send_message(ADMIN_ID, f"Xatolik: Kanal xabarini o'chirish/ko'chirishda muammo: {e}")

# We also need a way to auto-capture destination group if missing
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'], func=lambda message: message.chat.type in ['group', 'supergroup'])
def group_messages(message):
    global config
    if config['destination_group'] == 0:
        config['destination_group'] = message.chat.id
        save_config(config)
        try:
             bot.send_message(ADMIN_ID, f"Avtomatik sozlandim! Destination Group ID: {message.chat.id}")
        except:
             pass

# -----------------
# GENERAL USER LOGIC
# -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton(KEYS['TAXI']), types.KeyboardButton(KEYS['MAIL']))
    
    bot.reply_to(message, 
                 f"Assalomu alaykum, {message.from_user.first_name}!\n\nBizning xizmatdan foydalanish uchun tugmalardan birini tanlang:", 
                 reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text

    # Default logic for users canceling
    if text == KEYS['CANCEL']:
        if chat_id in user_state:
            del user_state[chat_id]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton(KEYS['TAXI']), types.KeyboardButton(KEYS['MAIL']))
        bot.send_message(chat_id, "Tizim bekor qilindi. Bosh menyu:", reply_markup=markup)
        return

    # Admin step handlers via text
    if chat_id in user_state and chat_id == ADMIN_ID and user_state[chat_id]['step'].startswith('admin_'):
        step = user_state[chat_id]['step']
        
        if step == 'admin_set_ad_text':
            config['ad_text'] = text
            save_config(config)
            bot.send_message(chat_id, "✅ Reklama matni saqlandi.")
            del user_state[chat_id]
            admin_panel(message)
            return
            
        elif step == 'admin_set_ad_time':
            try:
                mins = int(text)
                config['ad_interval_minutes'] = mins
                save_config(config)
                reschedule_ad()
                bot.send_message(chat_id, f"✅ Interval {mins} minut etib belgilandi.")
            except ValueError:
                bot.send_message(chat_id, "Iltimos, faqat raqam kiriting (masalan, 5)")
                return
            del user_state[chat_id]
            admin_panel(message)
            return
        
        elif step == 'admin_set_source_chan':
             # Admin is supposed to forward a message from the channel here
             # We actually handle forwarded messages below, so if it's pure text we can check if it's an ID
             try:
                 channel_id = int(text)
                 config['source_channel'] = channel_id
                 save_config(config)
                 bot.send_message(chat_id, "✅ Kanal ID saqlandi. Endi Group menda nimadir yozsa, ID ni olib qolaman.")
                 del user_state[chat_id]
                 admin_panel(message)
             except:
                 bot.send_message(chat_id, "Iltimos ID raqam yozing yoki menga kanaldan post FORWARD qiling.")
             return
            

    # Users clicking buttons
    if text == KEYS['TAXI'] or text == KEYS['MAIL']:
         order_type = "Taksi" if text == KEYS['TAXI'] else "Pochta"
         
         # Initialize state
         user_state[chat_id] = {
             'step': 'name',
             'type': order_type
         }
         
         markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
         markup.row(types.KeyboardButton(KEYS['CANCEL']))
         
         bot.send_message(chat_id, "Ism-sharifingizni kiriting:", reply_markup=markup)
         return

    # User multi-step flow
    if chat_id in user_state and not user_state[chat_id]['step'].startswith('admin_'):
         step = user_state[chat_id]['step']
         state = user_state[chat_id]
         
         if step == 'name':
              state['name'] = text
              state['step'] = 'phone'
              
              markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
              markup.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
              markup.add(types.KeyboardButton(KEYS['CANCEL']))
              bot.send_message(chat_id, "Telefon raqamingizni jo'nating:", reply_markup=markup)
              
         elif step == 'from':
              state['from_loc'] = text
              state['step'] = 'to'
              bot.send_message(chat_id, "Qayerga (masalan: Toshkentga) borasiz (yoki narsa jo'natasiz)?")
              
         elif step == 'to':
              state['to_loc'] = text
              state['step'] = 'location'
              
              markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
              markup.add(types.KeyboardButton("📍 Lokatsiyani yuborish", request_location=True))
              markup.add(types.KeyboardButton(KEYS['CANCEL']))
              
              bot.send_message(chat_id, "Ayni vaqtda turgan lokatsiyangizni yuboring:", reply_markup=markup)

# Specialized handler for admin forwarding a message from channel to get its ID
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'], func=lambda msg: msg.forward_from_chat is not None)
def handle_forwarded_from_channel(message):
    chat_id = message.chat.id
    if chat_id == ADMIN_ID and chat_id in user_state and user_state[chat_id]['step'] == 'admin_set_source_chan':
         source_chat = message.forward_from_chat
         if source_chat.type == 'channel':
              config['source_channel'] = source_chat.id
              save_config(config)
              bot.send_message(chat_id, f"✅ Kanal ID ({source_chat.id}) saqlandi!\n\nEndi botni o'sha guruhga (https://t.me/Uski_ku) qo'shing va o'sha guruhga biror narsa yozing. Bot o'zi avtomatik Group ID-ni ushlab qoladi.")
              del user_state[chat_id]
              admin_panel(message)
         else:
              bot.send_message(chat_id, "Bu kanaldan yuborilgan xabar emas.")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    if chat_id in user_state and user_state[chat_id]['step'] == 'phone':
         user_state[chat_id]['phone'] = message.contact.phone_number
         user_state[chat_id]['step'] = 'from'
         
         markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
         markup.add(types.KeyboardButton(KEYS['CANCEL']))
         bot.send_message(chat_id, "Qayerdan (masalan: Angrendan) ketasiz (yoki narsa jo'natasiz)?", reply_markup=markup)


@bot.message_handler(content_types=['location'])
def handle_location(message):
    chat_id = message.chat.id
    
    if chat_id in user_state and user_state[chat_id]['step'] == 'location':
         state = user_state[chat_id]
         loc = message.location
         state['lat'] = loc.latitude
         state['lon'] = loc.longitude
         
         # Time to format and send everything to group
         group_id = config['destination_group']
         
         order_title = "🚕 YANGI TAKSI BUYURTMA" if state['type'] == "Taksi" else "📦 YANGI POCHTA BUYURTMA"
         user_id = message.from_user.id
         profile_link = f"<a href='tg://user?id={user_id}'>{state['name']}</a>"
         
         text = (f"<b>{order_title}</b>\n\n"
                 f"👤 <b>Mijoz:</b> {profile_link}\n"
                 f"📞 <b>Tel:</b> +{state['phone'].lstrip('+')}\n"
                 f"📍 <b>Qayerdan:</b> {state['from_loc']}\n"
                 f"🏁 <b>Qayerga:</b> {state['to_loc']}\n"
                 f"📱 <b>Profil:</b> {profile_link}\n")
         
         # Send to group
         try:
             if group_id == 0:
                  bot.send_message(chat_id, "Kechirasiz, admin hali guruhni sozlamagan. Buyurtma qabul qilinmadi.")
             else:
                  # Send Location marker first or Data first? Let's send Data then Location.
                  # Note: Telegram can't combine Location format with long text.
                  msg1 = bot.send_message(group_id, text, parse_mode="HTML")
                  bot.send_location(group_id, state['lat'], state['lon'], reply_to_message_id=msg1.message_id)
                  
                  bot.send_message(chat_id, "✅ Sizning buyurtmangiz guruhga yuborildi! Tez orada shofyorlar siz bilan bog'lanishadi.")
         except Exception as e:
             bot.send_message(chat_id, "Tizimda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring yoki adminga murojaat qiling.")
             print(f"Error sending order to group: {e}")
             
         # Cleanup
         del user_state[chat_id]
         
         # Back to main menu
         markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
         markup.row(types.KeyboardButton(KEYS['TAXI']), types.KeyboardButton(KEYS['MAIL']))
         bot.send_message(chat_id, "Yana xizmat kerakmi?", reply_markup=markup)

from keep_alive import keep_alive

if __name__ == '__main__':
    keep_alive()
    print("Bot starting with Ad & Forward features...")
    bot.infinity_polling()
