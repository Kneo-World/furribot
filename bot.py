import logging
import asyncio
import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

import config
from database import (
    init_db, init_territories, create_user, get_user, get_user_by_username,
    get_profile, update_profile, get_fursona, update_fursona,
    find_users_by_tags, create_group, join_group,
    add_like, check_mutual_like, add_match, get_random_profile,
    get_territories, update_territory_owner, get_group_settings, update_group_settings
)
from ai import generate_reply, compatibility_analysis
from game import (
    add_xp, get_level_info, daily_reward, battle,
    territory_status, attack_territory, assign_random_quest,
    get_inventory, add_item
)
from image import generate_image
from voice import transcribe_audio, text_to_speech
from utils import random_mood, format_profile, cooldown_check

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище настроений пользователей
user_moods = {}

# ---------- Экранирование Markdown ----------
def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2"""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

# ---------- Глобальный обработчик ошибок ----------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("😿 Что-то пошло не так. Попробуй позже.")

# ---------- Команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await create_user(user.id, user.username or user.first_name)
    await update.message.reply_text(
        f"Ррр! Привет, {user.first_name}!\n"
        "Я Пушистик – твой дерзкий фурри-друг. Напиши /menu, чтобы начать."
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🐾 Профиль"), KeyboardButton("🔍 Найти фурри")],
        [KeyboardButton("🐺 Группы"), KeyboardButton("🎮 Игры")],
        [KeyboardButton("🤖 AI чат")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выбери действие:", reply_markup=reply_markup)

async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🐾 Профиль":
        await profile(update, context)
    elif text == "🔍 Найти фурри":
        await find_menu(update, context)
    elif text == "🐺 Группы":
        await groups_menu(update, context)
    elif text == "🎮 Игры":
        await games_menu(update, context)
    elif text == "🤖 AI чат":
        await ai_chat(update, context)

# ---------- Меню (отсутствующие функции) ----------
async def find_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = escape_markdown(
        "🔍 **Поиск фурри**\n"
        "• /find <тег> – найти по тегу\n"
        "• /match – случайный фурри (Tinder)\n"
        "• /compatibility @user – проверить совместимость"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

async def groups_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = escape_markdown(
        "🐺 **Группы и стаи**\n"
        "• /create_group – создать группу\n"
        "• /join_group <id> – вступить\n"
        "• /settings – настройки бота в группе"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = escape_markdown(
        "🎮 **Игры**\n"
        "• /level – твой уровень\n"
        "• /quest – новый квест\n"
        "• /battle @user – битва\n"
        "• /territory – карта территорий"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = escape_markdown(
        "🤖 **AI чат**\n"
        "Просто напиши мне что-нибудь – я отвечу как фурри-персонаж!\n"
        "Моё настроение может меняться 😼"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

# ---------- Профиль и фурсона ----------
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    profile_data = await get_profile(user_id)
    fursona_data = await get_fursona(user_id)
    # format_profile уже использует экранирование внутри
    await update.message.reply_text(
        format_profile(user_data, profile_data, fursona_data),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def fursona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🐺 Волк", callback_data="fursona_wolf"),
         InlineKeyboardButton("🦊 Лис", callback_data="fursona_fox")],
        [InlineKeyboardButton("🐱 Кошка", callback_data="fursona_cat"),
         InlineKeyboardButton("🐉 Дракон", callback_data="fursona_dragon")],
        [InlineKeyboardButton("🐻 Медведь", callback_data="fursona_bear"),
         InlineKeyboardButton("🐧 Пингвин", callback_data="fursona_penguin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери вид твоей фурсоны:", reply_markup=reply_markup)

async def fursona_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("fursona_"):
        species = data.split('_')[1]
        await update_fursona(user_id, species=species)
        await query.edit_message_text(f"Отлично! Ты выбрал {species}. Теперь напиши цвет (например: рыжий, серый).")
        context.user_data["fursona_step"] = "color"

# ---------- Поиск и Tinder ----------
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи тег. Например: /find art")
        return
    tag = " ".join(context.args)
    results = await find_users_by_tags(tag)
    if not results:
        await update.message.reply_text("Никого не найдено.")
        return
    text = "Найденные фурри:\n" + "\n".join([f"@{r[1]} – {r[2]}" for r in results])
    await update.message.reply_text(escape_markdown(text), parse_mode=ParseMode.MARKDOWN_V2)

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    candidate = await get_random_profile(user_id)
    if not candidate:
        await update.message.reply_text("Пока нет других фурри для знакомства.")
        return
    uid, username, species, color, personality, interests = candidate
    text = f"🐾 **{username}**\nВид: {species}\nЦвет: {color}\nХарактер: {personality}\nИнтересы: {interests}"
    keyboard = [
        [InlineKeyboardButton("❤️", callback_data=f"like_{uid}"),
         InlineKeyboardButton("❌", callback_data=f"pass_{uid}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(escape_markdown(text), reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def match_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    action, other_id = data.split('_')
    other_id = int(other_id)
    if action == "like":
        if await check_mutual_like(user_id, other_id):
            await query.edit_message_text("Это взаимно! Вы теперь друзья.")
            await add_match(user_id, other_id)
        else:
            await query.edit_message_text("Лайк отправлен!")
            await add_like(user_id, other_id)
    else:
        await query.edit_message_text("Пропущено.")

# ---------- Совместимость ----------
async def compatibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи пользователя: /compatibility @username")
        return
    target = context.args[0]
    if not target.startswith('@'):
        await update.message.reply_text("Упоминание должно начинаться с @")
        return
    username = target[1:]
    user2 = await get_user_by_username(username)
    if not user2:
        await update.message.reply_text("Пользователь не найден.")
        return
    user1_id = update.effective_user.id
    user2_id = user2[0]

    fursona1 = await get_fursona(user1_id)
    fursona2 = await get_fursona(user2_id)
    if not fursona1 or not fursona2:
        await update.message.reply_text("У одного из вас не заполнена фурсона.")
        return

    analysis = await compatibility_analysis(user1_id, user2_id, fursona1, fursona2)
    await update.message.reply_text(escape_markdown(analysis), parse_mode=ParseMode.MARKDOWN_V2)

# ---------- Группы ----------
async def create_group_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args).split(";")
    if len(args) < 5:
        await update.message.reply_text("Использование: /create_group Имя;Описание;теги;уровень;цена")
        return
    name, desc, tags, req_lvl, price = [a.strip() for a in args]
    try:
        req_lvl = int(req_lvl)
        price = int(price)
    except:
        await update.message.reply_text("Уровень и цена должны быть числами.")
        return
    ok, msg = await create_group(name, desc, tags, req_lvl, price, update.effective_user.id)
    await update.message.reply_text(msg)

async def join_group_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи ID группы. Например: /join_group 1")
        return
    try:
        gid = int(context.args[0])
    except:
        await update.message.reply_text("ID группы должен быть числом.")
        return
    ok, msg = await join_group(gid, update.effective_user.id)
    await update.message.reply_text(msg)

# ---------- Игры ----------
async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    info = await get_level_info(user_id)
    if not info:
        await update.message.reply_text("Сначала напиши /start.")
        return
    lvl, xp = info
    next_xp = lvl * 100
    await update.message.reply_text(f"⭐ Уровень: {lvl}\n✨ XP: {xp}/{next_xp}")

async def quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    quest = await assign_random_quest(user_id)
    if not quest:
        await update.message.reply_text("У тебя уже есть активный квест.")
    else:
        await update.message.reply_text(f"Новый квест: {quest['name']}\n{quest['desc']}\nНаграда: {quest['reward_xp']} XP, {quest['reward_coins']} 🪙, {quest['reward_fish']} 🐟")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reward = await daily_reward(user_id)
    if not reward:
        await update.message.reply_text("Ты уже получал награду сегодня. Приходи завтра!")
    else:
        coins, fish, xp = reward
        await add_xp(user_id, xp)
        await update.message.reply_text(f"🎁 Ежедневная награда: +{coins} 🪙, +{fish} 🐟, +{xp} ✨")

async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    items = await get_inventory(user_id)
    if not items:
        await update.message.reply_text("📦 Инвентарь пуст.")
        return
    text = "📦 Инвентарь:\n" + "\n".join([f"{name}: {qty}" for name, qty in items])
    await update.message.reply_text(text)

async def battle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи противника: /battle @user")
        return
    target = context.args[0]
    if not target.startswith('@'):
        await update.message.reply_text("Упоминание должно начинаться с @")
        return
    username = target[1:]
    user2 = await get_user_by_username(username)
    if not user2:
        await update.message.reply_text("Пользователь не найден.")
        return
    user1_id = update.effective_user.id
    user2_id = user2[0]
    result = await battle(user1_id, user2_id)
    await update.message.reply_text(result)

async def territory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await territory_status()
    keyboard = [[InlineKeyboardButton("⚔️ Атаковать", callback_data="territory_attack")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(escape_markdown(status), reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def territory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "territory_attack":
        await query.edit_message_text("Функция атаки в разработке.")

# ---------- Изображения ----------
async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Напиши, что нарисовать. Например: /draw пушистый дракон")
        return
    await update.message.reply_text("🎨 Рисую... это может занять несколько секунд.")
    try:
        image_data = await generate_image(prompt)
        await update.message.reply_photo(photo=image_data, caption=f"По запросу: {prompt}")
    except Exception as e:
        await update.message.reply_text(f"Не удалось нарисовать: {e}")

# ---------- Взаимодействия ----------
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await add_xp(user_id, 5)
    await update.message.reply_text(f"*обнимает тебя* Муррр! 🤗 (настроение: {mood})")

async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await add_xp(user_id, 5)
    await update.message.reply_text(f"*гладит по головке* Мяу, приятно~ 🐾 (настроение: {mood})")

async def purr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await add_xp(user_id, 5)
    await update.message.reply_text(f"Ррр... мур-мур-мур... 😸 (настроение: {mood})")

async def growl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await add_xp(user_id, 5)
    await update.message.reply_text(f"Рррр! Сердитый пушистик! 🐯 (настроение: {mood})")

async def bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await add_xp(user_id, 5)
    await update.message.reply_text(f"*кусает за нос* Хрум! 🐊 (настроение: {mood})")

# ---------- Настройки группы ----------
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("Эта команда только для групп.")
        return
    settings = await get_group_settings(chat.id)
    text = f"⚙️ **Настройки группы**\nПриветствие: {'включено' if settings['welcome_enabled'] else 'выключено'}\nРазрешённые команды: {settings['allowed_commands']}"
    keyboard = [
        [InlineKeyboardButton("🔄 Переключить приветствие", callback_data="toggle_welcome")],
        [InlineKeyboardButton("🔧 Изменить команды", callback_data="edit_commands")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(escape_markdown(text), reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    if data == "toggle_welcome":
        settings = await get_group_settings(chat_id)
        new_val = not settings["welcome_enabled"]
        await update_group_settings(chat_id, welcome_enabled=new_val)
        await query.edit_message_text(f"Приветствие теперь {'включено' if new_val else 'выключено'}.")
    elif data == "edit_commands":
        await query.edit_message_text("Функция в разработке.")

# ---------- Голосовые сообщения ----------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        return
    file = await voice.get_file()
    await file.download_to_drive("voice.ogg")
    text = await transcribe_audio("voice.ogg")
    if text:
        await update.message.reply_text(f"Ты сказал: {text}")
        mood = user_moods.get(update.effective_user.id, random_mood())
        reply = await generate_reply(text, mood)
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("Не удалось распознать голос.")

# ---------- Обработка текстовых сообщений (AI) ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # В группах реагируем только на упоминания
    if update.effective_chat.type != "private":
        bot_username = context.bot.username
        if bot_username not in update.message.text:
            return

    user_id = update.effective_user.id
    user_message = update.message.text
    await create_user(user_id, update.effective_user.username or update.effective_user.first_name)
    await add_xp(user_id, 2)

    mood = user_moods.get(user_id)
    if not mood or random.random() < 0.1:
        mood = random_mood()
        user_moods[user_id] = mood

    reply = await generate_reply(user_message, mood)
    # AI ответ тоже нужно экранировать, так как может содержать спецсимволы
    await update.message.reply_text(escape_markdown(reply), parse_mode=ParseMode.MARKDOWN_V2)

# ---------- Инициализация и запуск ----------
async def init_all():
    await init_db()
    await init_territories()

def main():
    # Инициализация БД (однократно)
    asyncio.run(init_all())

    # Создание приложения
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("fursona", fursona))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("match", match))
    app.add_handler(CommandHandler("compatibility", compatibility))
    app.add_handler(CommandHandler("create_group", create_group_cmd))
    app.add_handler(CommandHandler("join_group", join_group_cmd))
    app.add_handler(CommandHandler("level", level))
    app.add_handler(CommandHandler("quest", quest))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("inventory", inventory))
    app.add_handler(CommandHandler("battle", battle_cmd))
    app.add_handler(CommandHandler("territory", territory_cmd))
    app.add_handler(CommandHandler("draw", draw))
    app.add_handler(CommandHandler("hug", hug))
    app.add_handler(CommandHandler("pat", pat))
    app.add_handler(CommandHandler("purr", purr))
    app.add_handler(CommandHandler("growl", growl))
    app.add_handler(CommandHandler("bite", bite))
    app.add_handler(CommandHandler("settings", settings))

    # Callback-обработчики
    app.add_handler(CallbackQueryHandler(fursona_callback, pattern="^fursona_"))
    app.add_handler(CallbackQueryHandler(match_callback, pattern="^(like|pass)_"))
    app.add_handler(CallbackQueryHandler(territory_callback, pattern="^territory_"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_welcome|edit_commands)$"))

    # Текстовые сообщения (меню)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    # Голосовые
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    # Обычные сообщения (для AI)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Глобальный обработчик ошибок
    app.add_error_handler(error_handler)

    # Запуск бота (синхронный метод)
    app.run_polling()

if __name__ == "__main__":
    main()
