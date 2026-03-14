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
        # Профили
        await db.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                bio TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        # Фурсоны
        await db.execute('''
            CREATE TABLE IF NOT EXISTS fursonas (
                user_id INTEGER PRIMARY KEY,
                species TEXT,
                color TEXT,
                personality TEXT,
                interests TEXT,
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
        # Инвентарь
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
                target INTEGER,
                reward_xp INTEGER,
                reward_coins INTEGER,
                reward_fish INTEGER,
                required_level INTEGER DEFAULT 1
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
        # Лайки (для Tinder)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                from_user INTEGER,
                to_user INTEGER,
                PRIMARY KEY (from_user, to_user)
            )
        ''')
        # Матчи (взаимные лайки)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                user1 INTEGER,
                user2 INTEGER,
                matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user1, user2)
            )
        ''')
        # Территории (для игры)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS territories (
                territory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                owner_group_id INTEGER,
                influence INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Настройки групп
        await db.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                group_id INTEGER PRIMARY KEY,
                welcome_enabled BOOLEAN DEFAULT 1,
                allowed_commands TEXT DEFAULT 'all'
            )
        ''')
        await db.commit()

# ---------- Пользователи ----------
async def get_user(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

async def create_user(user_id: int, username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                         (user_id, username))
        await db.execute('INSERT OR IGNORE INTO profiles (user_id) VALUES (?)', (user_id,))
        await db.execute('INSERT OR IGNORE INTO fursonas (user_id) VALUES (?)', (user_id,))
        await db.commit()

async def update_user_xp(user_id: int, xp_delta: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE users SET xp = xp + ? WHERE user_id = ?', (xp_delta, user_id))
        await db.commit()

async def update_user_level(user_id: int, new_level: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE users SET level = ? WHERE user_id = ?', (new_level, user_id))
        await db.commit()

async def get_user_by_username(username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT user_id FROM users WHERE username = ?', (username,))
        return await cursor.fetchone()

# ---------- Профили ----------
async def get_profile(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

async def update_profile(user_id: int, bio: str, tags: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE profiles SET bio = ?, tags = ? WHERE user_id = ?', (bio, tags, user_id))
        await db.commit()

# ---------- Фурсоны ----------
async def get_fursona(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT species, color, personality, interests FROM fursonas WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

async def update_fursona(user_id: int, species: str = None, color: str = None, personality: str = None, interests: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        existing = await get_fursona(user_id)
        if existing:
            query = 'UPDATE fursonas SET species=?, color=?, personality=?, interests=? WHERE user_id=?'
            params = (
                species if species is not None else existing[0],
                color if color is not None else existing[1],
                personality if personality is not None else existing[2],
                interests if interests is not None else existing[3],
                user_id
            )
        else:
            query = 'INSERT INTO fursonas (user_id, species, color, personality, interests) VALUES (?, ?, ?, ?, ?)'
            params = (user_id, species or '', color or '', personality or '', interests or '')
        await db.execute(query, params)
        await db.commit()

# ---------- Поиск по тегам ----------
async def find_users_by_tags(tag: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            SELECT u.user_id, u.username, p.tags
            FROM users u
            JOIN profiles p ON u.user_id = p.user_id
            WHERE p.tags LIKE ?
        ''', (f'%{tag}%',))
        return await cursor.fetchall()

# ---------- Группы ----------
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
        cursor = await db.execute('SELECT required_level, entry_price FROM groups WHERE group_id = ?', (group_id,))
        group = await cursor.fetchone()
        if not group:
            return False, "Группа не найдена."
        req_level, price = group
        cursor = await db.execute('SELECT level, coins FROM users WHERE user_id = ?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            return False, "Пользователь не найден."
        level, coins = user
        if level < req_level:
            return False, f"Требуется уровень {req_level}, а у тебя {level}."
        if coins < price:
            return False, f"Не хватает монет. Нужно {price}."
        await db.execute('INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?, ?)', (group_id, user_id))
        if price > 0:
            await db.execute('UPDATE users SET coins = coins - ? WHERE user_id = ?', (price, user_id))
        await db.commit()
        return True, f"Ты вступил в группу!"

# ---------- Лайки и матчи ----------
async def add_like(from_user: int, to_user: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO likes (from_user, to_user) VALUES (?, ?)', (from_user, to_user))
        await db.commit()

async def check_mutual_like(user1: int, user2: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT 1 FROM likes WHERE from_user = ? AND to_user = ?', (user2, user1))
        return await cursor.fetchone() is not None

async def add_match(user1: int, user2: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        a, b = sorted([user1, user2])
        await db.execute('INSERT OR IGNORE INTO matches (user1, user2) VALUES (?, ?)', (a, b))
        await db.commit()

async def get_random_profile(exclude_user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('''
            SELECT u.user_id, u.username, f.species, f.color, f.personality, f.interests
            FROM users u
            JOIN fursonas f ON u.user_id = f.user_id
            WHERE u.user_id != ? AND u.user_id NOT IN (
                SELECT to_user FROM likes WHERE from_user = ?
            )
            ORDER BY RANDOM() LIMIT 1
        ''', (exclude_user_id, exclude_user_id))
        return await cursor.fetchone()

# ---------- Территории ----------
async def init_territories():
    # Создаём несколько территорий при первом запуске
    async with aiosqlite.connect(DATABASE_PATH) as db:
        count = await (await db.execute('SELECT COUNT(*) FROM territories')).fetchone()
        if count[0] == 0:
            territories = ['Лес', 'Горы', 'Озеро', 'Пустыня', 'Город']
            for name in territories:
                await db.execute('INSERT INTO territories (name, owner_group_id, influence) VALUES (?, 0, 0)', (name,))
            await db.commit()

async def get_territories():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT territory_id, name, owner_group_id, influence FROM territories')
        return await cursor.fetchall()

async def update_territory_owner(territory_id: int, group_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('UPDATE territories SET owner_group_id = ?, last_updated = CURRENT_TIMESTAMP WHERE territory_id = ?', (group_id, territory_id))
        await db.commit()

# ---------- Настройки групп ----------
async def get_group_settings(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT welcome_enabled, allowed_commands FROM group_settings WHERE group_id = ?', (chat_id,))
        row = await cursor.fetchone()
        if row:
            return {"welcome_enabled": bool(row[0]), "allowed_commands": row[1]}
        else:
            # создаём настройки по умолчанию
            await db.execute('INSERT INTO group_settings (group_id) VALUES (?)', (chat_id,))
            await db.commit()
            return {"welcome_enabled": True, "allowed_commands": "all"}

async def update_group_settings(chat_id: int, welcome_enabled: bool = None, allowed_commands: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        current = await get_group_settings(chat_id)
        new_welcome = welcome_enabled if welcome_enabled is not None else current["welcome_enabled"]
        new_commands = allowed_commands if allowed_commands is not None else current["allowed_commands"]
        await db.execute('UPDATE group_settings SET welcome_enabled = ?, allowed_commands = ? WHERE group_id = ?',
                         (int(new_welcome), new_commands, chat_id))
        await db.commit()
