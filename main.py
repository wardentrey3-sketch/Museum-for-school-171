import telebot
import json
import os
from telebot import types

TOKEN = 'Token'
ADMIN_ID = 1846110852
bot = telebot.TeleBot(TOKEN)

DB_MSG = 'last_messages.json'
DB_EXHIBITS = 'exhibits.json'
DB_QUIZ = 'quiz.json'

admin_state = {}

main_sms_text = (
    "<b>Добро пожаловать в виртуальный Музей боевой славы школы №171!</b>\n\n"
    "Наш музей был торжественно открыт 29 апреля 2025 года в преддверии <b>80-летия Великой Победы</b>. "
    "Это место силы и памяти, где хранятся истории о тех, кто самоотверженно защищал нашу Родину.\n\n"
    "<b>Экспозиция посвящена:</b>\n"
    "• Героям Великой Отечественной войны;\n"
    "• Воинам-интернационалистам Афганской войны;\n"
    "• Участникам Специальной военной операции.\n\n"
    "Особое внимание в музее уделено жизни и творчеству <u>Шагинура Ахметсафовича Мустафина</u> — "
    "писателя и поисковика, который вернул имена сотням неизвестных героев фронта. ✍️\n\n"
    "Используйте меню ниже, чтобы прикоснуться к истории, увидеть уникальные артефакты и архивные документы."
)

with open('main_photo.json', 'r') as f:
    main_photo = json.load(f)[0]

def load_json(path, default):
    if not os.path.exists(path): return default
    with open(path, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_last_id(chat_id):
    return load_json(DB_MSG, {}).get(str(chat_id))

def set_last_id(chat_id, msg_id):
    data = load_json(DB_MSG, {})
    data[str(chat_id)] = msg_id
    save_json(DB_MSG, data)

def send_clean(chat_id, text, photo=None, markup=None):
    last_id = get_last_id(chat_id)
    try:
        if photo:
            img = photo if isinstance(photo, list) and photo else photo
            new_msg = bot.send_photo(chat_id, img, caption=text, reply_markup=markup, parse_mode='HTML')
        else:
            new_msg = bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
    except Exception as e: print(f"Ошибка: {e}")
    if last_id:
        try: bot.delete_message(chat_id, last_id)
        except: pass
    set_last_id(chat_id, new_msg.message_id)



@bot.message_handler(commands=['start', 'menu'])
def start_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏛️ Список экспонатов", callback_data="list"))
    markup.add(types.InlineKeyboardButton("📝 Пройти тест", callback_data="quiz_0_0"))
    if message.from_user.id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("Админ-панель", callback_data="admin_main"))

    send_clean(message.chat.id, main_sms_text, main_photo,markup=markup)
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

@bot.message_handler(commands=['help'])
def help(message):
    send_clean(message.from_user.id, 'По всем вопросам обращаться к @Yii_t\n\n<blockquote>made by ABCtv</blockquote>')  
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass


@bot.message_handler(content_types=['photo'])
def process_admin_photo(message):
    chat_id = message.chat.id
    if chat_id in admin_state:
        if admin_state[chat_id].get('type') == 'exhibit':
            admin_state[chat_id]['photos'].append(message.photo[-1].file_id)
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Завершить", callback_data="admin_save_ex"))
            send_clean(chat_id, f"📸 Фото получено ({len(admin_state[chat_id]['photos'])}).", markup=markup)
            try: bot.delete_message(chat_id, message.message_id)
            except: pass
    else:
        if chat_id == ADMIN_ID:
            global main_photo
            main_photo = message.photo[-1].file_id
            with open('main_photo.json', 'w') as file:
                json.dump([main_photo], file)
            bot.send_message(ADMIN_ID, 'Установлено')

@bot.message_handler(func=lambda m: m.chat.id in admin_state)
def process_admin_text(message):
    chat_id = message.chat.id
    state = admin_state[chat_id]

    if state['type'] == 'exhibit' and 'name' not in state:
        try:
            name, desc = message.text.split('|')
            state.update({'name': name.strip(), 'desc': desc.strip()})
            send_clean(chat_id, f"<b>{name.strip()}</b> принят. Теперь отправляйте фото по очереди:")
        except: bot.send_message(chat_id, "❌ Формат: Название | Описание")
    elif state['type'] == 'quiz':
        try:
            q, opts, corr = message.text.split('|')
            options = [o.strip() for o in opts.split(',')]
            q_db = load_json(DB_QUIZ, [])
            q_db.append({"question": q.strip(), "options": options, "correct": int(corr)})
            save_json(DB_QUIZ, q_db)
            admin_state.pop(chat_id)
            send_clean(chat_id, "✅ Вопрос добавлен!", markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Админ-панель", callback_data="admin_main")))
        except: bot.send_message(chat_id, "❌ Ошибка формата!")
    try: bot.delete_message(chat_id, message.message_id)
    except: pass


@bot.callback_query_handler(func=lambda call: True)
def handle_queries(call):
    chat_id = call.message.chat.id
    db = load_json(DB_EXHIBITS, {})
    quiz = load_json(DB_QUIZ, [])


    if call.data == "admin_main" and call.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Добавить экспонат", callback_data="admin_add_ex"))
        markup.add(types.InlineKeyboardButton("Добавить вопрос", callback_data="admin_add_q"))
        markup.add(types.InlineKeyboardButton("Удалить экспонат", callback_data="admin_del_ex_list"))
        markup.add(types.InlineKeyboardButton("Удалить вопрос", callback_data="admin_del_q_list"))
        markup.add(types.InlineKeyboardButton("В меню", callback_data="main_menu"))
        send_clean(chat_id, "<b>Админ-панель</b>", markup=markup)


    elif call.data == "admin_add_ex":
        admin_state[chat_id] = {'type': 'exhibit', 'photos': []}
        send_clean(chat_id, "Введите: <code>Название | Описание</code>")
    elif call.data == "admin_add_q":
        admin_state[chat_id] = {'type': 'quiz'}
        send_clean(chat_id, "Введите: <code>Вопрос | Отв1, Отв2 | индекс прав. ответа</code>")
    elif call.data == "admin_save_ex":
        data = admin_state.pop(chat_id, None)
        if data and data.get('photos'):
            db[f"ex_{int(call.message.date)}"] = {"name": data['name'], "description": data['desc'], "photos": data['photos']}
            save_json(DB_EXHIBITS, db)
            send_clean(chat_id, f"✅ Экспонат сохранен!", markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Админ-панель", callback_data="admin_main")))

    elif call.data == "admin_del_ex_list":
        if not db:
            return bot.answer_callback_query(call.id, "Список экспонатов пуст")
        
        markup = types.InlineKeyboardMarkup()
        for k, v in db.items():
            markup.add(types.InlineKeyboardButton(f"❌ {v['name']}", callback_data=f"admin_rem_ex_{k}"))
        markup.add(types.InlineKeyboardButton("⬅️ Назад в админ-панель", callback_data="admin_main"))
        send_clean(chat_id, "<b>Нажмите на экспонат для удаления:</b>", markup=markup)
    
    elif call.data.startswith("admin_rem_ex_"):
        key = call.data.replace("admin_rem_ex_", "")
        if key in db:
            name = db[key]['name']
            del db[key]
            save_json(DB_EXHIBITS, db)
            bot.answer_callback_query(call.id, f"Удалено: {name}")
            

            if not db:
                markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_main"))
                bot.edit_message_text("Все экспонаты удалены.", chat_id, call.message.message_id, reply_markup=markup)
            else:
                markup = types.InlineKeyboardMarkup()
                for k, v in db.items():
                    markup.add(types.InlineKeyboardButton(f"❌ {v['name']}", callback_data=f"admin_rem_ex_{k}"))
                markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_main"))
                bot.edit_message_text("<b>Выберите следующий для удаления:</b>", chat_id, call.message.message_id, reply_markup=markup, parse_mode='HTML')

    elif call.data == "admin_del_q_list":
        if not quiz:
            return bot.answer_callback_query(call.id, "Список вопросов пуст")
            
        markup = types.InlineKeyboardMarkup()
        for i, q in enumerate(quiz):
            markup.add(types.InlineKeyboardButton(f"❌ {q['question'][:30]}...", callback_data=f"admin_rem_q_{i}"))
        markup.add(types.InlineKeyboardButton("⬅️ Назад в админ-панель", callback_data="admin_main"))
        send_clean(chat_id, "<b>Выберите вопрос для удаления:</b>", markup=markup)

    elif call.data.startswith("admin_rem_q_"):
        idx = int(call.data.replace("admin_rem_q_", ""))
        if 0 <= idx < len(quiz):
            quiz.pop(idx)
            save_json(DB_QUIZ, quiz)
            bot.answer_callback_query(call.id, "Вопрос удален")
            
            if not quiz:
                markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_main"))
                bot.edit_message_text("Все вопросы удалены.", chat_id, call.message.message_id, reply_markup=markup)
            else:
                markup = types.InlineKeyboardMarkup()
                for i, q in enumerate(quiz):
                    markup.add(types.InlineKeyboardButton(f"❌ {q['question'][:30]}...", callback_data=f"admin_rem_q_{i}"))
                markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_main"))
                bot.edit_message_text("🗑 <b>Выберите следующий для удаления:</b>", chat_id, call.message.message_id, reply_markup=markup, parse_mode='HTML')



    elif call.data == "list":
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = []
        for k, v in db.items():
            buttons.append(types.InlineKeyboardButton(v['name'], callback_data=f"view_{k}_0"))

        markup.add(*buttons)
        
        markup.row(types.InlineKeyboardButton("Назад", callback_data="main_menu"))
        
        send_clean(chat_id, "<b>Экспонаты музея Боевой Славы школы №171:</b>", markup=markup)

    elif call.data.startswith("view_"):
        parts = call.data.split("_")
        idx, ex_key = int(parts[-1]), "_".join(parts[1:-1])
        ex = db.get(ex_key)
        if ex:
            photos = ex['photos']
            text = f"<b>{ex['name']}</b>\n\n{ex['description']}\n<i>Фото {idx+1}/{len(photos)}</i>"
            markup = types.InlineKeyboardMarkup()
            if len(photos) > 1:
                markup.row(types.InlineKeyboardButton("⬅️ Пред. фото", callback_data=f"view_{ex_key}_{(idx-1)%len(photos)}"),
                           types.InlineKeyboardButton("➡️ След. фото", callback_data=f"view_{ex_key}_{(idx+1)%len(photos)}"))
            markup.add(types.InlineKeyboardButton("⬅️ К списку", callback_data="list"))
            if call.message.content_type == 'photo':
                bot.edit_message_media(types.InputMediaPhoto(photos[idx], caption=text, parse_mode='HTML'), chat_id, call.message.message_id, reply_markup=markup)
            else: send_clean(chat_id, text, photo=photos[idx], markup=markup)

    elif call.data.startswith("quiz_"):
        _, q_idx, score = call.data.split("_")
        q_idx, score = int(q_idx), int(score)
        if q_idx < len(quiz):
            q = quiz[q_idx]
            markup = types.InlineKeyboardMarkup()
            for i, opt in enumerate(q['options']):
                markup.add(types.InlineKeyboardButton(opt, callback_data=f"quiz_{q_idx+1}_{score + (1 if i == q['correct'] else 0)}"))
            send_clean(chat_id, f"❓ <b>Вопрос {q_idx+1} из {len(quiz)}:</b>\n\n{q['question']}", markup=markup)
        else:
            send_clean(chat_id, f"<b>Конец!</b>\nВаш результат: {score}/{len(quiz)}", markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("В меню", callback_data="main_menu")))

    elif call.data == "main_menu":
        start_menu(call.message)

bot.send_message(ADMIN_ID, 'Bot start')
bot.infinity_polling()
