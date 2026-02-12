import telebot
from telebot import types

# Token
TOKEN = '8580639697:AAFPv5TYWiWFXFxaMYQWPN7JzCwMUMYkVIQ'
bot = telebot.TeleBot(TOKEN)

# State
user_state = {}

# Keywords
KEYS = {
    'TAXI': '🚕 Taksi kerak',
    'CLIENT': '🙋‍♂️ Yo\'lovchiman',
    'DRIVER': '🚖 Haydovchiman',
    'MAIL': '📦 Pochta yuborish',
    'CANCEL': '🚫 Bekor qilish'
}

# Start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton(KEYS['CLIENT']), types.KeyboardButton(KEYS['DRIVER']))
    markup.row(types.KeyboardButton(KEYS['MAIL']))
    bot.reply_to(message, f"Assalomu alaykum, {message.from_user.first_name}!\n\nBizning xizmatdan foydalanish uchun tanlang:", reply_markup=markup)

# Handle Content/Text
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text

    if text == KEYS['CANCEL']:
        if chat_id in user_state:
            del user_state[chat_id]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton(KEYS['CLIENT']), types.KeyboardButton(KEYS['DRIVER']))
        markup.row(types.KeyboardButton(KEYS['MAIL']))
        bot.send_message(chat_id, "Bekor qilindi. Bosh menyu:", reply_markup=markup)
        return

    if text == KEYS['CLIENT']:
        user_state[chat_id] = {'step': 'from'}
        bot.send_message(chat_id, "Qayerdan ketasiz? (Tuman/Shahar)", reply_markup=types.ReplyKeyboardRemove())
    
    elif text == KEYS['DRIVER']:
        user_state[chat_id] = {'step': 'driver_start'}
        bot.send_message(chat_id, "Mashinangiz modeli va rangi?", reply_markup=types.ReplyKeyboardRemove())
    
    elif text == KEYS['MAIL']:
        user_state[chat_id] = {'step': 'mail_content'}
        bot.send_message(chat_id, "Pochta nima? (Masalan: Hujjat, Sumka...)", reply_markup=types.ReplyKeyboardRemove())

    elif chat_id in user_state:
        step = user_state[chat_id]['step']
        state = user_state[chat_id]

        if step == 'from':
            state['from_loc'] = text
            state['step'] = 'to'
            bot.send_message(chat_id, "Qayerga borasiz?")
        
        elif step == 'to':
            state['to_loc'] = text
            state['step'] = 'phone'
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
            bot.send_message(chat_id, "Telefon raqamingizni yuboring:", reply_markup=markup)
        
        elif step == 'driver_start':
            state['car'] = text
            state['step'] = 'driver_route'
            bot.send_message(chat_id, "Yo'nalishingiz? (Masalan: Angren -> Toshkent)")
        
        elif step == 'driver_route':
            state['route'] = text
            state['step'] = 'phone'
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
            bot.send_message(chat_id, "Telefon raqamingizni yuboring:", reply_markup=markup)
        
        elif step == 'mail_content':
            state['content'] = text
            state['step'] = 'driver_route' 
            # Reusing 'driver_route' step logic as it asks for route then phone
            bot.send_message(chat_id, "Qayerdan - Qayerga?")

# Handle Contact
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    contact = message.contact

    if chat_id in user_state and user_state[chat_id]['step'] == 'phone':
        state = user_state[chat_id]
        phone = contact.phone_number
        
        summary = ""
        if 'car' in state:
            summary = f"🚖 #Haydovchi\n🚗 Mashina: {state['car']}\n🛣 Yo'nalish: {state['route']}\n📞 Tel: {phone}"
        elif 'content' in state:
            # Note: For mail, we used 'driver_route' logic, so 'route' is stored there? 
            # Wait, in mail logic: step='driver_route', so previous text input became state['route']?
            # actually above:
            # elif step == 'mail_content': ... state['step'] = 'driver_route'
            # then user types route -> handler catches 'driver_route' -> state['route'] = text -> asks phone
            # So yes, 'route' is populated.
             summary = f"📦 #Pochta\n📄 Narsa: {state['content']}\n🛣 Yo'nalish: {state.get('route', '?')}\n📞 Tel: {phone}"
        else:
             summary = f"🙋‍♂️ #Yo_lovchi\n📍 Qayerdan: {state.get('from_loc', '?')}\n🏁 Qayerga: {state.get('to_loc', '?')}\n📞 Tel: {phone}"

        bot.send_message(chat_id, f"✅ E'lon qabul qilindi!\n\n{summary}\n\nTez orada kanalga chiqariladi.")

        # Clear state
        del user_state[chat_id]

        # Back to menu
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton(KEYS['CLIENT']), types.KeyboardButton(KEYS['DRIVER']))
        markup.row(types.KeyboardButton(KEYS['MAIL']))
        bot.send_message(chat_id, "Yana xizmat kerakmi?", reply_markup=markup)

if __name__ == '__main__':
    print("Bot starting...")
    bot.infinity_polling()
