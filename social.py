import aiosqlite
from database import DATABASE_PATH

async def create_profile(user_id: int, bio: str, tags: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE profiles SET bio = ?, tags = ? WHERE user_id = ?',
                         (bio, tags, user_id))
        await db.commit()

async def get_profile(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

async def find_users_by_tags(tag_query: str):
    """Простой поиск по тегам (содержит подстроку)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            SELECT u.user_id, u.username, p.tags
            FROM users u
            JOIN profiles p ON u.user_id = p.user_id
            WHERE p.tags LIKE ?
        ''', (f'%{tag_query}%',))
        return await cursor.fetchall()

async def create_group(name: str, description: str, tags: str, required_level: int, entry_price: int, creator_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверим, сколько групп создал пользователь
        cursor = await db.execute('SELECT COUNT(*) FROM groups WHERE creator_id = ?', (creator_id,))
        count = (await cursor.fetchone())[0]
        if count >= 2:
            return False, "Ты уже создал максимальное количество групп (2)."
        await db.execute('''
            INSERT INTO groups (name, description, tags, required_level, entry_price, creator_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, tags, required_level, entry_price, creator_id))
        await db.commit()
        return True, "Группа создана!"

async def join_group(group_id: int, user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверим, существует ли группа и соответствует ли пользователь требованиям
        cursor = await db.execute('SELECT required_level, entry_price FROM groups WHERE group_id = ?', (group_id,))
        group = await cursor.fetchone()
        if not group:
            return False, "Группа не найдена."
        req_level, price = group
        # Проверим уровень пользователя
        cursor = await db.execute('SELECT level, coins FROM users WHERE user_id = ?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            return False, "Пользователь не найден."
        level, coins = user
        if level < req_level:
            return False, f"Требуется уровень {req_level}, а у тебя {level}."
        if coins < price:
            return False, f"Не хватает монет. Нужно {price}."
        # Вступим
        await db.execute('INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?, ?)', (group_id, user_id))
        if price > 0:
            await db.execute('UPDATE users SET coins = coins - ? WHERE user_id = ?', (price, user_id))
        await db.commit()
        return True, f"Ты вступил в группу!"
