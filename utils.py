import random
import time
from datetime import datetime, timedelta

MOODS = ["happy", "sleepy", "chaotic", "cute"]

def random_mood() -> str:
    return random.choice(MOODS)

def cooldown_check(last_time: str, seconds: int = 86400) -> bool:
    """Проверяет, прошло ли достаточно времени (по умолчанию 24 часа)"""
    if not last_time:
        return True
    last = datetime.fromisoformat(last_time)
    return datetime.now() - last > timedelta(seconds=seconds)

def format_profile(user_data: tuple, profile_data: tuple) -> str:
    """Форматирует профиль для вывода"""
    # user_data: user_id, username, xp, level, coins, fish, last_daily, created_at
    # profile_data: user_id, bio, tags
    if not user_data:
        return "Профиль не найден"
    uid, username, xp, lvl, coins, fish, _, created = user_data
    bio, tags = profile_data[1], profile_data[2] if profile_data else ("", "")
    return (
        f"🐾 **Профиль {username}**\n"
        f"🆔 ID: {uid}\n"
        f"📅 С нами с: {created[:10]}\n"
        f"⭐ Уровень: {lvl} (XP: {xp})\n"
        f"🪙 Монет: {coins}\n"
        f"🐟 Рыбок: {fish}\n"
        f"📝 О себе: {bio or '—'}\n"
        f"🏷️ Теги: {tags or '—'}"
    )
