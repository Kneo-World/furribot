import sqlite3
import aiosqlite
from config import DATABASE_PATH

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Пользователи
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                coins INTEGER DEFAULT 100,
                fish INTEGER DEFAULT 10,
                last_daily TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Профили (социальная сеть)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                bio TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        # Группы
        await db.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                required_level INTEGER DEFAULT 1,
                entry_price INTEGER DEFAULT 0,
                creator_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Участники групп
        await db.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                user_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id)
            )
        ''')
        # Инвентарь (простые предметы)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_name)
            )
        ''')
        # Квесты
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                quest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                reward_xp INTEGER,
                reward_coins INTEGER,
                reward_fish INTEGER,
                required_level INTEGER
            )
        ''')
        # Активные квесты пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_quests (
                user_id INTEGER,
                quest_id INTEGER,
                progress INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT 0,
                PRIMARY KEY (user_id, quest_id)
            )
        ''')
        await db.commit()

# Вспомогательные функции для работы с БД
async def get_user(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

async def create_user(user_id: int, username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                         (user_id, username))
        await db.execute('INSERT OR IGNORE INTO profiles (user_id) VALUES (?)', (user_id,))
        await db.commit()
