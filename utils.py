import random
from datetime import datetime, timedelta

MOODS = ["happy", "sleepy", "chaotic", "aggressive", "cute"]

def random_mood() -> str:
    return random.choice(MOODS)

def cooldown_check(last_time: str, seconds: int = 86400) -> bool:
    """Проверяет, прошло ли достаточно времени (по умолчанию 24 часа)"""
    if not last_time:
        return True
    last = datetime.fromisoformat(last_time)
    return datetime.now() - last > timedelta(seconds=seconds)

def format_profile(user_data: tuple, profile_data: tuple, fursona_data: tuple) -> str:
    """Форматирует профиль для вывода (MarkdownV2)"""
    if not user_data:
        return "🐾 Профиль не найден"
    uid, username, xp, lvl, coins, fish, _, created = user_data
    bio, tags = profile_data[1], profile_data[2] if profile_data else ("", "")
    species, color, personality, interests = fursona_data if fursona_data else ("не указан", "не указан", "не указан", "не указан")

    # Экранируем специальные символы для MarkdownV2
    def esc(s):
        return str(s).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')

    return (
        f"🐾 **Профиль {esc(username)}**\n"
        f"┌ ID: `{uid}`\n"
        f"├ С нами: {created[:10]}\n"
        f"├ Уровень: {lvl} (XP: {xp})\n"
        f"├ Монет: {coins} 🪙\n"
        f"├ Рыбок: {fish} 🐟\n"
        f"├── **Фурсона**\n"
        f"│  ├ Вид: {esc(species)}\n"
        f"│  ├ Цвет: {esc(color)}\n"
        f"│  ├ Характер: {esc(personality)}\n"
        f"│  └ Интересы: {esc(interests)}\n"
        f"└── **О себе**\n"
        f"   ├ {esc(bio) or '—'}\n"
        f"   └ Теги: {esc(tags) or '—'}"
    )
