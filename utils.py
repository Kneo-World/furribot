import random
from datetime import datetime, timedelta

MOODS = ["happy", "sleepy", "chaotic", "aggressive", "cute"]

def random_mood() -> str:
    return random.choice(MOODS)

def cooldown_check(last_time: str, seconds: int = 86400) -> bool:
    if not last_time:
        return True
    last = datetime.fromisoformat(last_time)
    return datetime.now() - last > timedelta(seconds=seconds)

def escape_markdown(text: str) -> str:
    """
    Экранирует все специальные символы для MarkdownV2.
    Символы: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if not isinstance(text, str):
        text = str(text)
    # Последовательно заменяем каждый символ на экранированную версию
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for ch in chars:
        text = text.replace(ch, '\\' + ch)
    return text

def format_profile(user_data: tuple, profile_data: tuple, fursona_data: tuple) -> str:
    if not user_data:
        return "🐾 Профиль не найден"
    uid, username, xp, lvl, coins, fish, _, created = user_data
    bio, tags = profile_data[1], profile_data[2] if profile_data else ("", "")
    species, color, personality, interests = fursona_data if fursona_data else ("не указан", "не указан", "не указан", "не указан")

    def esc(s):
        return escape_markdown(str(s))

    return (
        f"🐾 **Профиль {esc(username)}**\n"
        f"┌ ID: `{uid}`\n"
        f"├ С нами: {esc(created[:10])}\n"
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
