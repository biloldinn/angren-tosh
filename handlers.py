from bot_instance import bot
from config import config, save_config, ADMIN_ID
from logger import logger
from telebot import types
import html
import ads
import forwarder

user_states = {}

def register_handlers():
    
    @bot.message_handler(commands=['start'])
    def start(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton("🚕 Taksi chaqirish"), types.KeyboardButton("📦 Pochta jo'natish"))
        bot.send_message(message.chat.id, 
            f"🌟 *Assalomu alaykum, {message.from_user.first_name}!*\n\n"
            "Sizga qanday xizmat kerak? Quyidagi tugmalardan birini tanlang:", 
            reply_markup=markup, parse_mode="Markdown")

    @bot.message_handler(commands=['status'])
    def status(message):
        s = config.get('source_group', 'Sozlanmagan')
        d = config.get('destination_group', 'Sozlanmagan')
        ad_g = config.get('ad_target_group', s)
        
        status_text = (
            f"📊 *Bot holati*\n\n"
            f"📤 Manba: `{s}`\n"
            f"📥 Qabul qiluvchi: `{d}`\n"
            f"📢 Reklama guruhi: `{ad_g}`\n"
            f"🔄 Forward: {'🟢' if config.get('is_forwarding_active') else '🔴'}\n"
            f"📢 Reklama: {'🟢' if config.get('is_ad_active') else '🔴'}\n"
            f"⏱ Interval: {config.get('ad_interval_minutes')} min"
        )
        bot.send_message(message.chat.id, status_text, parse_mode="Markdown")

    @bot.message_handler(commands=['setgroups'], func=lambda m: m.from_user.id == ADMIN_ID)
    def set_groups(message):
        bot.send_message(message.chat.id, 
            "Guruhlarni quyidagi formatda yuboring:\n`Manba_ID Qabul_qiluvchi_ID`\n\n"
            "Masalan: `-100123 -100456`", parse_mode="Markdown")
        user_states[message.chat.id] = 'waiting_for_groups'

    @bot.message_handler(commands=['admin'], func=lambda m: m.from_user.id == ADMIN_ID)
    def admin_panel(message):
        status_ad = "🟢 YOQILGAN" if config.get('is_ad_active') else "🔴 O'CHIRILGAN"
        status_fwd = "🟢 YOQILGAN" if config.get('is_forwarding_active') else "🔴 O'CHIRILGAN"
        
        ad_text_preview = (config.get('ad_text')[:40] + "...") if config.get('ad_text') else "Mavjud emas"
        
        panel_text = (
            f"🛠 *Admin Panel*\n\n"
            f"📢 *Reklama holati:* {status_ad}\n"
            f"⏱ *Interval:* {config.get('ad_interval_minutes')} min\n"
            f"📝 *Matn:* _{ad_text_preview}_\n"
            f"🔄 *Forward:* {status_fwd}"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📝 Matn", callback_data="admin_ad_text"),
            types.InlineKeyboardButton("📸 Rasm", callback_data="admin_ad_photo")
        )
        markup.add(
            types.InlineKeyboardButton("⏱ Interval", callback_data="admin_ad_time"),
            types.InlineKeyboardButton("🎯 Guruh ID", callback_data="admin_ad_target")
        )
        markup.add(
            types.InlineKeyboardButton("🚀 Reklamani hozir yuborish", callback_data="admin_ad_now")
        )
        markup.add(
            types.InlineKeyboardButton(f"{'🔴 Reklamani o`chirish' if config.get('is_ad_active') else '🟢 Reklamani yoqish'}", callback_data="admin_ad_toggle"),
            types.InlineKeyboardButton(f"{'🔴 Forwardni o`chirish' if config.get('is_forwarding_active') else '🟢 Forwardni yoqish'}", callback_data="admin_fwd_toggle")
        )
        bot.send_message(message.chat.id, panel_text, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: c.data.startswith('admin_'))
    def admin_callbacks(call):
        cid = call.message.chat.id
        if call.data == "admin_ad_text":
            bot.send_message(cid, "Yangi reklama matnini yuboring:")
            user_states[cid] = 'setting_ad_text'
        elif call.data == "admin_ad_photo":
            bot.send_message(cid, "Reklama uchun rasm yuboring (yoki 'yo'q' deb yozing):")
            user_states[cid] = 'setting_ad_photo'
        elif call.data == "admin_ad_time":
            bot.send_message(cid, "Intervalni minutlarda yuboring:")
            user_states[cid] = 'setting_ad_time'
        elif call.data == "admin_ad_target":
            bot.send_message(cid, "Reklama yuborilishi kerak bo'lgan guruh ID sini yuboring:")
            user_states[cid] = 'setting_ad_target'
        elif call.data == "admin_ad_now":
            ads.send_ad()
            bot.answer_callback_query(call.id, "Reklama guruhga yuborildi!")
        elif call.data == "admin_ad_toggle":
            config['is_ad_active'] = not config['is_ad_active']
            save_config(config)
            ads.reschedule_ads()
            bot.answer_callback_query(call.id, "O'zgartirildi")
            admin_panel(call.message)
        elif call.data == "admin_fwd_toggle":
            config['is_forwarding_active'] = not config['is_forwarding_active']
            save_config(config)
            bot.answer_callback_query(call.id, "O'zgartirildi")
            admin_panel(call.message)

    # Order flow handlers (Simplified for @ANGREN_TOSHKENT_TAKSI_POCHTA)
    @bot.message_handler(func=lambda m: m.text in ["🚕 Taksi chaqirish", "📦 Pochta jo'natish"])
    def start_order(message):
        cid = message.chat.id
        user_states[cid] = {'type': 'Taksi' if "Taksi" in message.text else 'Pochta', 'step': 'name'}
        
        cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_markup.add(types.KeyboardButton("❌ Bekor qilish"))
        
        bot.send_message(cid, "📝 *Ismingizni yozing:*", reply_markup=cancel_markup, parse_mode="Markdown")

    @bot.message_handler(func=lambda m: m.chat.id in user_states and isinstance(user_states[m.chat.id], dict))
    def order_steps(message):
        cid = message.chat.id
        state = user_states[cid]
        step = state['step']
        
        if step == 'name':
            state['name'] = message.text
            state['step'] = 'phone'
            mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            mk.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
            bot.send_message(cid, "📞 *Telefon raqamingizni yuboring:*", reply_markup=mk, parse_mode="Markdown")
        elif step == 'phone':
            # This is for manual text entry of phone if they don't use the button
            state['phone'] = message.text
            state['step'] = 'from'
            bot.send_message(cid, "📍 *Qayerdan:*", parse_mode="Markdown")
        elif step == 'from':
            state['from'] = message.text
            state['step'] = 'to'
            bot.send_message(cid, "🏁 *Qayerga:*", parse_mode="Markdown")
        elif step == 'to':
            state['to'] = message.text
            state['step'] = 'location'
            mk = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            mk.add(types.KeyboardButton("📍 Lokatsiyani yuborish", request_location=True))
            mk.add(types.KeyboardButton("❌ Bekor qilish"))
            bot.send_message(cid, "🗺 *Lokatsiyangizni yuboring:*", reply_markup=mk, parse_mode="Markdown")

    @bot.message_handler(content_types=['contact'])
    def handle_contact(message):
        cid = message.chat.id
        if cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('step') == 'phone':
            user_states[cid]['phone'] = message.contact.phone_number
            user_states[cid]['step'] = 'from'
            bot.send_message(cid, "Qayerdan?")

    @bot.message_handler(content_types=['location'])
    def handle_location(message):
        cid = message.chat.id
        if cid in user_states and isinstance(user_states[cid], dict) and user_states[cid].get('step') == 'location':
            state = user_states[cid]
            state['lat'] = message.location.latitude
            state['lon'] = message.location.longitude
            
            # Finalize order to destinaton group
            target = config.get('destination_group')
            if target:
                title = "🚕 #YANGI_TAKSI" if state['type'] == 'Taksi' else "📦 #YANGI_POCHTA"
                esc_name = html.escape(state['name'])
                profile = f"<a href='tg://user?id={cid}'>{esc_name}</a>"
                # Time formatting (UTC+5 for Uzbekistan)
                from datetime import datetime, timedelta
                uz_time = (datetime.fromtimestamp(message.date) + timedelta(hours=5)).strftime('%H:%M:%S')
                
                esc_from = html.escape(state['from'])
                esc_to = html.escape(state['to'])
                
                text = (f"📥 <b>{title}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"👤 <b>Mijoz:</b> {profile}\n"
                        f"📞 <b>Tel:</b> <code>+{state['phone']}</code>\n"
                        f"📍 <b>Qayerdan:</b> <code>{esc_from}</code>\n"
                        f"🏁 <b>Qayerga:</b> <code>{esc_to}</code>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"🕒 <b>Vaqt:</b> <code>{uz_time}</code>")
                
                # Buttons for Group
                mk_group = types.InlineKeyboardMarkup()
                mk_group.add(
                    types.InlineKeyboardButton("✅ Qabul qilish", callback_data=f"order_accept_{cid}"),
                    types.InlineKeyboardButton("❌ Rad etish", callback_data=f"order_reject_{cid}")
                )

                m = bot.send_message(target, text, parse_mode="HTML", reply_markup=mk_group)
                bot.send_location(target, state['lat'], state['lon'], reply_to_message_id=m.message_id)
                bot.send_message(cid, "✅ *Buyurtmangiz yuborildi!* Adminlar qabul qilishi bilan xabar beramiz.", parse_mode="Markdown")
            else:
                bot.send_message(cid, "❌ Xatolik: Guruh sozlanmagan.")
            
            del user_states[cid]
            start(message)

    # General text inputs for admin settings
    @bot.message_handler(func=lambda m: m.chat.id in user_states and isinstance(user_states[m.chat.id], str))
    def handle_admin_inputs(message):
        cid = message.chat.id
        state = user_states[cid]
        
        if state == 'waiting_for_groups':
            try:
                parts = message.text.split()
                config['source_group'] = parts[0]
                config['destination_group'] = parts[1]
                save_config(config)
                bot.send_message(cid, f"✅ Sozlandi!\nManba: {parts[0]}\nQabul: {parts[1]}")
            except:
                bot.send_message(cid, "Xato format! `Manba_ID Qabul_ID` shaklida yuboring.")
        elif state == 'setting_ad_text':
            config['ad_text'] = message.text
            save_config(config)
            bot.send_message(cid, "✅ Reklama matni saqlandi.")
        elif state == 'setting_ad_time':
            try:
                config['ad_interval_minutes'] = int(message.text)
                save_config(config)
                ads.reschedule_ads()
                bot.send_message(cid, f"✅ Interval {message.text} minutga sozlandi.")
            except:
                bot.send_message(cid, "Faqat raqam yuboring.")
        elif state == 'setting_ad_target':
            config['ad_target_group'] = message.text
            save_config(config)
            bot.send_message(cid, "✅ Reklama guruhi saqlandi.")
        
        elif message.text == "❌ Bekor qilish":
            bot.send_message(cid, "Amal bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
            start(message)
            return

        if cid in user_states: del user_states[cid]

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        cid = message.chat.id
        if cid in user_states and user_states[cid] == 'setting_ad_photo':
            config['ad_photo'] = message.photo[-1].file_id
            save_config(config)
            bot.send_message(cid, "✅ Reklama rasmi saqlandi.")
            del user_states[cid]

    @bot.callback_query_handler(func=lambda c: c.data.startswith('order_'))
    def order_callbacks(call):
        cid = call.message.chat.id
        data = call.data.split('_')
        action = data[1]
        customer_id = data[2]
        
        # Get original text
        text = call.message.text
        
        if action == "accept":
            # Update message in group
            new_text = f"✅ <b>QABUL QILINDI</b>\n━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━\n👤 Admin: <a href='tg://user?id={call.from_user.id}'>{call.from_user.first_name}</a>"
            bot.edit_message_text(new_text, cid, call.message.message_id, parse_mode="HTML", reply_markup=None)
            
            # Notify customer
            try:
                bot.send_message(customer_id, "✅ <b>Buyurtmangiz qabul qilindi!</b>\nHozir haydovchi siz bilan bog'lanadi.", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Could not notify customer {customer_id}: {e}")
            
            bot.answer_callback_query(call.id, "Buyurtma qabul qilindi!")
            
        elif action == "reject":
            # Update message in group
            new_text = f"❌ <b>RAD ETILDI</b>\n━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━\n👤 Admin: <a href='tg://user?id={call.from_user.id}'>{call.from_user.first_name}</a>"
            bot.edit_message_text(new_text, cid, call.message.message_id, parse_mode="HTML", reply_markup=None)
            
            bot.answer_callback_query(call.id, "Buyurtma rad etildi!")

    # Forwarding handler
    @bot.message_handler(func=lambda m: True)
    @bot.channel_post_handler(func=lambda m: True)
    def catch_all(message):
        forwarder.handle_forwarding(message)

register_handlers()
