import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import config
from database import init_db, create_user, get_user
from ai import generate_reply
from utils import random_mood, format_profile
import game
import social

# Логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище настроений пользователей (в памяти, для простоты)
user_moods = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await create_user(user.id, user.username or user.first_name)
    await update.message.reply_text(
        f"Ня! Привет, {user.first_name}!\n"
        "Я Пушистик, твой фурри-друг. Расскажи мне что-нибудь или используй /help."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🐾 **Команды:**\n"
        "/start - Начало\n"
        "/help - Это сообщение\n"
        "/profile - Твой профиль\n"
        "/find <тег> - Поиск по тегам\n"
        "/create_group - Создать группу (имя;описание;теги;уровень;цена)\n"
        "/join_group <id> - Вступить в группу\n"
        "/level - Твой уровень и XP\n"
        "/quest - Взять новый квест\n"
        "/daily - Ежедневная награда\n"
        "/inventory - Инвентарь\n"
        "/hug, /pat, /purr - Обнимашки и ласка\n"
        "/draw - Нарисовать что-нибудь\n"
        "Просто напиши сообщение — я отвечу!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    profile_data = await social.get_profile(user_id)
    await update.message.reply_text(format_profile(user_data, profile_data), parse_mode="Markdown")

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи тег для поиска. Например: /find пушистик")
        return
    tag = " ".join(context.args)
    results = await social.find_users_by_tags(tag)
    if not results:
        await update.message.reply_text("Никого не найдено по этому тегу.")
        return
    text = "Найденные пользователи:\n" + "\n".join([f"@{r[1]} (ID: {r[0]}) — теги: {r[2]}" for r in results])
    await update.message.reply_text(text)

async def create_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Формат: имя;описание;теги;требуемый уровень;цена
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
    ok, msg = await social.create_group(name, desc, tags, req_lvl, price, update.effective_user.id)
    await update.message.reply_text(msg)

async def join_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи ID группы. Например: /join_group 1")
        return
    try:
        gid = int(context.args[0])
    except:
        await update.message.reply_text("ID группы должен быть числом.")
        return
    ok, msg = await social.join_group(gid, update.effective_user.id)
    await update.message.reply_text(msg)

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    info = await game.get_level_info(user_id)
    if not info:
        await update.message.reply_text("Сначала напиши /start.")
        return
    lvl, xp = info
    next_xp = lvl * 100
    await update.message.reply_text(f"⭐ Уровень: {lvl}\n✨ XP: {xp}/{next_xp}")

async def quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    quest = await game.assign_random_quest(user_id)
    if not quest:
        await update.message.reply_text("У тебя уже есть активный квест. Сначала выполни его!")
    else:
        await update.message.reply_text(f"Новый квест: {quest['name']}\n{quest['desc']}\nНаграда: {quest['reward_xp']} XP, {quest['reward_coins']} 🪙, {quest['reward_fish']} 🐟")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reward = await game.daily_reward(user_id)
    if not reward:
        await update.message.reply_text("Ты уже получал награду сегодня. Приходи завтра!")
    else:
        coins, fish, xp = reward
        await game.add_xp(user_id, xp)
        await update.message.reply_text(f"🎁 Ежедневная награда: +{coins} 🪙, +{fish} 🐟, +{xp} ✨")

async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    items = await game.get_inventory(user_id)
    if not items:
        await update.message.reply_text("Твой инвентарь пуст.")
        return
    text = "📦 Инвентарь:\n" + "\n".join([f"{name}: {qty}" for name, qty in items])
    await update.message.reply_text(text)

async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await game.add_xp(user_id, 5)
    await update.message.reply_text(f"*обнимает тебя* Муррр! 🤗 (настроение: {mood})")

async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await game.add_xp(user_id, 5)
    await update.message.reply_text(f"*гладит по головке* Мяу, приятно~ 🐾 (настроение: {mood})")

async def purr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mood = user_moods.get(user_id, random_mood())
    await game.add_xp(user_id, 5)
    await update.message.reply_text(f"Ррр... мур-мур-мур... 😸 (настроение: {mood})")

async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Простейший ответ, можно заменить на генерацию картинки через AI в будущем
    await update.message.reply_text("🎨 Нарисовал для тебя пушистика! (тут должна быть картинка)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Создаём пользователя, если его нет
    await create_user(user_id, update.effective_user.username or update.effective_user.first_name)

    # Добавляем XP за сообщение
    await game.add_xp(user_id, 2)

    # Получаем или генерируем настроение
    mood = user_moods.get(user_id)
    if not mood or random.random() < 0.1:  # 10% шанс смены настроения
        mood = random_mood()
        user_moods[user_id] = mood

    # Генерируем ответ от AI
    reply = await generate_reply(user_message, mood)
    await update.message.reply_text(reply)

def main():
    # Инициализация БД
    import asyncio
    asyncio.run(init_db())

    # Создаём приложение
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("create_group", create_group))
    app.add_handler(CommandHandler("join_group", join_group))
    app.add_handler(CommandHandler("level", level))
    app.add_handler(CommandHandler("quest", quest))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("inventory", inventory))
    app.add_handler(CommandHandler("hug", hug))
    app.add_handler(CommandHandler("pat", pat))
    app.add_handler(CommandHandler("purr", purr))
    app.add_handler(CommandHandler("draw", draw))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем polling
    app.run_polling()

if __name__ == "__main__":
    main()
