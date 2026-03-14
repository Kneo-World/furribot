import httpx
import random
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL

# Системный промт для фурри-личности
SYSTEM_PROMPT = """Ты — милый фурри-персонаж по имени Пушистик. 
Твои черты:
- Дружелюбный и игривый
- Любишь обнимашки и ласку
- Иногда используешь слова "ня", "мяу", "ррр", "пушистик"
- У тебя есть настроение: happy, sleepy, chaotic, cute
- Ты отвечаешь коротко и с эмодзи

Сейчас твоё настроение: {mood}
"""

async def generate_reply(user_message: str, mood: str = "cute") -> str:
    """Генерирует ответ через AI API"""
    if not AI_API_KEY:
        # Заглушка на случай отсутствия ключа
        return f"{random.choice(['Ня', 'Мяу', 'Ррр'])}! Я бы ответил что-то умное, но у меня нет ключа API. {random.choice(['😿', '😊', '✨'])}"

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(mood=mood)},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.8,
        "max_tokens": 150
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{AI_BASE_URL}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Мяу... что-то пошло не так: {str(e)} 😿"
