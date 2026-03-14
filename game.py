import random
from datetime import datetime
import aiosqlite
from database import DATABASE_PATH

# Простые предметы для инвентаря
ITEMS = ["🍪 печенька", "🐟 рыбка", "🧶 клубок", "🎀 бантик", "🪙 монетка"]

async def add_xp(user_id: int, xp_amount: int = 10):
    """Добавляет опыт и проверяет повышение уровня"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Получаем текущие xp и уровень
        cursor = await db.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        if not row:
            return
        current_xp, level = row
        new_xp = current_xp + xp_amount
        new_level = level
        # Простая формула: следующий уровень требует level * 100 xp
        while new_xp >= new_level * 100:
            new_xp -= new_level * 100
            new_level += 1
        await db.execute('UPDATE users SET xp = ?, level = ? WHERE user_id = ?',
                         (new_xp, new_level, user_id))
        await db.commit()

async def get_level_info(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT level, xp FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

async def daily_reward(user_id: int):
    """Выдаёт ежедневную награду, если прошло 24 часа"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT last_daily FROM users WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        last = row[0] if row else None

        from utils import cooldown_check
        if last and not cooldown_check(last):
            return None  # ещё нельзя

        coins = random.randint(50, 150)
        fish = random.randint(5, 20)
        xp = random.randint(20, 50)

        await db.execute('UPDATE users SET coins = coins + ?, fish = fish + ?, last_daily = ? WHERE user_id = ?',
                         (coins, fish, datetime.now().isoformat(), user_id))
        await db.commit()
        return coins, fish, xp

async def add_item(user_id: int, item_name: str, quantity: int = 1):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT INTO inventory (user_id, item_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + excluded.quantity
        ''', (user_id, item_name, quantity))
        await db.commit()

async def get_inventory(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT item_name, quantity FROM inventory WHERE user_id = ?', (user_id,))
        rows = await cursor.fetchall()
        return rows

# Простые квесты
QUESTS = [
    {"name": "Болтун", "desc": "Напиши 5 сообщений", "target": 5, "reward_xp": 50, "reward_coins": 30, "reward_fish": 5},
    {"name": "Ласкатель", "desc": "Используй /hug 3 раза", "target": 3, "reward_xp": 30, "reward_coins": 20, "reward_fish": 3},
    {"name": "Коллекционер", "desc": "Собери 3 разных предмета", "target": 3, "reward_xp": 100, "reward_coins": 50, "reward_fish": 10},
]

async def assign_random_quest(user_id: int):
    """Назначает случайный квест пользователю, если у него нет активного"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверим, есть ли уже активный квест
        cursor = await db.execute('SELECT quest_id FROM user_quests WHERE user_id = ? AND completed = 0', (user_id,))
        existing = await cursor.fetchone()
        if existing:
            return None
        quest = random.choice(QUESTS)
        # Вставим запись о квесте (для упрощения будем хранить данные прямо здесь, без отдельной таблицы quests)
        # Создадим таблицу quests, если ещё нет
        await db.execute('INSERT OR IGNORE INTO quests (name, description, reward_xp, reward_coins, reward_fish, required_level) VALUES (?, ?, ?, ?, ?, ?)',
                         (quest["name"], quest["desc"], quest["reward_xp"], quest["reward_coins"], quest["reward_fish"], 1))
        cursor = await db.execute('SELECT quest_id FROM quests WHERE name = ?', (quest["name"],))
        qid = (await cursor.fetchone())[0]
        await db.execute('INSERT INTO user_quests (user_id, quest_id, progress, completed) VALUES (?, ?, ?, 0)',
                         (user_id, qid, 0))
        await db.commit()
        return quest
