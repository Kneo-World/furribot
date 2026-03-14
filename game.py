import random
import aiosqlite
from datetime import datetime
from database import DATABASE_PATH

# ---------- XP и уровни ----------
async def add_xp(user_id: int, xp_amount: int = 10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        if not row:
            return
        current_xp, level = row
        new_xp = current_xp + xp_amount
        new_level = level
        while new_xp >= new_level * 100:
            new_xp -= new_level * 100
            new_level += 1
        await db.execute('UPDATE users SET xp = ?, level = ? WHERE user_id = ?', (new_xp, new_level, user_id))
        await db.commit()

async def get_level_info(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT level, xp FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone()

# ---------- Ежедневная награда ----------
async def daily_reward(user_id: int):
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

# ---------- Инвентарь ----------
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
        return await cursor.fetchall()

# ---------- Квесты ----------
QUESTS = [
    {"name": "Болтун", "desc": "Напиши 5 сообщений", "target": 5, "reward_xp": 50, "reward_coins": 30, "reward_fish": 5},
    {"name": "Ласкатель", "desc": "Используй /hug 3 раза", "target": 3, "reward_xp": 30, "reward_coins": 20, "reward_fish": 3},
    {"name": "Коллекционер", "desc": "Собери 3 разных предмета", "target": 3, "reward_xp": 100, "reward_coins": 50, "reward_fish": 10},
    {"name": "Охотник за головами", "desc": "Победи в 2 битвах", "target": 2, "reward_xp": 200, "reward_coins": 100, "reward_fish": 15},
]

async def assign_random_quest(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute('SELECT quest_id FROM user_quests WHERE user_id = ? AND completed = 0', (user_id,))
        existing = await cursor.fetchone()
        if existing:
            return None
        quest = random.choice(QUESTS)
        await db.execute('INSERT INTO quests (name, description, target, reward_xp, reward_coins, reward_fish) VALUES (?, ?, ?, ?, ?, ?)',
                         (quest["name"], quest["desc"], quest["target"], quest["reward_xp"], quest["reward_coins"], quest["reward_fish"]))
        quest_id = (await db.execute('SELECT last_insert_rowid()')).fetchone()[0]
        await db.execute('INSERT INTO user_quests (user_id, quest_id) VALUES (?, ?)', (user_id, quest_id))
        await db.commit()
        return quest

# ---------- Битвы ----------
async def battle(user1_id: int, user2_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Получаем уровень и силу (уровень + бонусы)
        u1 = await (await db.execute('SELECT level, coins FROM users WHERE user_id = ?', (user1_id,))).fetchone()
        u2 = await (await db.execute('SELECT level, coins FROM users WHERE user_id = ?', (user2_id,))).fetchone()
        if not u1 or not u2:
            return "Один из участников не найден."

        # Простая формула: сила = уровень * 10 + случайность
        power1 = u1[0] * 10 + random.randint(-5, 5)
        power2 = u2[0] * 10 + random.randint(-5, 5)

        if power1 > power2:
            winner, loser = user1_id, user2_id
            result = f"Победил @{winner}!"
            xp_gain = 50
            coins_gain = 30
        elif power2 > power1:
            winner, loser = user2_id, user1_id
            result = f"Победил @{winner}!"
            xp_gain = 50
            coins_gain = 30
        else:
            result = "Ничья! Никто не победил."
            xp_gain = 20
            coins_gain = 10

        # Начисляем награды
        if winner:
            await db.execute('UPDATE users SET xp = xp + ?, coins = coins + ? WHERE user_id = ?', (xp_gain, coins_gain, winner))
            await db.execute('UPDATE users SET xp = xp + 10 WHERE user_id = ?', (loser,))  # утешительный приз
        else:
            # ничья - оба получают немного
            await db.execute('UPDATE users SET xp = xp + ? WHERE user_id IN (?, ?)', (xp_gain, user1_id, user2_id))
            await db.execute('UPDATE users SET coins = coins + ? WHERE user_id IN (?, ?)', (coins_gain, user1_id, user2_id))

        await db.commit()
        return result

# ---------- Территории ----------
async def territory_status():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        territories = await (await db.execute('''
            SELECT t.name, COALESCE(g.name, 'Ничья'), t.influence
            FROM territories t
            LEFT JOIN groups g ON t.owner_group_id = g.group_id
        ''')).fetchall()
        lines = ["📍 **Карта территорий**"]
        for name, owner, inf in territories:
            lines.append(f"• {name}: владеет **{owner}** (влияние {inf})")
        return "\n".join(lines)

async def attack_territory(territory_id: int, group_id: int, attacker_power: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Получаем текущего владельца и влияние
        ter = await (await db.execute('SELECT owner_group_id, influence FROM territories WHERE territory_id = ?', (territory_id,))).fetchone()
        if not ter:
            return False, "Территория не найдена."
        owner, inf = ter
        if owner == group_id:
            return False, "Ты уже владеешь этой территорией."
        # Простая механика: если сила атакующего больше влияния, захват
        if attacker_power > inf:
            await db.execute('UPDATE territories SET owner_group_id = ?, influence = ? WHERE territory_id = ?', (group_id, attacker_power, territory_id))
            await db.commit()
            return True, "Территория захвачена!"
        else:
            # Увеличиваем влияние защитника
            await db.execute('UPDATE territories SET influence = influence + 10 WHERE territory_id = ?', (territory_id,))
            await db.commit()
            return False, "Атака отражена! Влияние защитника увеличилось."
