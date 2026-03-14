import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

import config
from database import init_db, get_user, create_user
from ai import generate_reply, compatibility_analysis
from social import get_profile, update_fursona, find_users_by_tags, create_group, join_group, get_random_profile, add_match
from game import add_xp, get_level_info, daily_reward, battle, territory_status, attack_territory
from image import generate_image
from voice import transcribe_audio, text_to_speech
from utils import random_mood, format_profile, cooldown_check

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище настроений (в памяти)
user_moods = {}
group_settings_cache = {}  # chat_id: settings

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await create_user(user.id, user.username or user.first_name)
    text = f"Ррр… Привет, {user.first_name}! Я Пушистик – твой фурри‑друг.\nНапиши /menu, чтобы начать."
    await update.message.reply_text(text)

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

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    profile_data = await get_profile(user_id)
    fursona_data = await get_fursona(user_id)  # из social
    await update.message.reply_text(
        format_profile(user_data, profile_data, fursona_data),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def fursona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Интерактивный конструктор через inline кнопки
    keyboard = [
        [InlineKeyboardButton("🐺 Волк", callback_data="fursona_wolf"),
         InlineKeyboardButton("🦊 Лис", callback_data="fursona_fox")],
        [InlineKeyboardButton("🐱 Кошка", callback_data="fursona_cat"),
         InlineKeyboardButton("🐉 Дракон", callback_data="fursona_dragon")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери вид твоей фурсоны:", reply_markup=reply_markup)

async def fursona_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    # Сохраняем выбранный вид, затем запрашиваем цвет и т.д.
    # Упрощённо – сохраняем сразу.
    user_id = query.from_user.id
    species = data.split('_')[1]
    await update_fursona(user_id, species=species)
    await query.edit_message_text(f"Отлично! Ты выбрал {species}. Теперь укажи цвет (например: рыжий, серый).")

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
    await update.message.reply_text(text)

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Получаем случайного пользователя (кроме себя и тех, с кем уже был матч)
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
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def match_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    action, other_id = data.split('_')
    other_id = int(other_id)
    if action == "like":
        # Проверяем взаимность
        if await check_mutual_like(user_id, other_id):
            await query.edit_message_text("Это взаимно! Вы теперь друзья.")
            await add_match(user_id, other_id)
        else:
            await query.edit_message_text("Лайк отправлен!")
            await save_like(user_id, other_id)
    else:
        await query.edit_message_text("Пропущено.")

async def battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи противника: /battle @user")
        return
    # Получаем user_id по упоминанию (упрощённо)
    target = context.args[0]
    if not target.startswith('@'):
        await update.message.reply_text("Упоминание должно начинаться с @")
        return
    username = target[1:]
    # Ищем в БД
    # ... (код получения user_id)
    user1 = update.effective_user.id
    user2 = 123  # заменить на реальный
    result = await battle(user1, user2)
    await update.message.reply_text(result)

async def territory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Показывает карту территорий и кнопки для атаки
    status = await territory_status()
    keyboard = [[InlineKeyboardButton("Атаковать", callback_data="attack_territory")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(status, reply_markup=reply_markup)

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

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        return
    file = await voice.get_file()
    await file.download_to_drive("voice.ogg")
    text = await transcribe_audio("voice.ogg")
    if text:
        await update.message.reply_text(f"Ты сказал: {text}")
        # Отправляем в AI для ответа
        reply = await generate_reply(text, user_moods.get(update.effective_user.id, "cute"))
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("Не удалось распознать голос.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # В группах реагируем только на упоминания или если бот отвечает
    if update.effective_chat.type != "private":
        # Проверяем, упомянут ли бот
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
    await update.message.reply_text(reply)

def main():
    asyncio.run(init_db())
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("fursona", fursona))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("match", match))
    app.add_handler(CommandHandler("battle", battle))
    app.add_handler(CommandHandler("territory", territory))
    app.add_handler(CommandHandler("draw", draw))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("inventory", inventory))
    app.add_handler(CommandHandler("compatibility", compatibility))

    # Обработчики кнопок
    app.add_handler(CallbackQueryHandler(fursona_callback, pattern="^fursona_"))
    app.add_handler(CallbackQueryHandler(match_callback, pattern="^(like|pass)_"))

    # Текстовые сообщения (меню и обычные)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()

if __name__ == "__main__":
    main()
