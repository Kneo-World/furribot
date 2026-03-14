import httpx
import random
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL

SYSTEM_PROMPT = """Ты — фурри-персонаж по имени Пушистик.
Твой стиль: дерзкий, саркастичный, ироничный, но дружелюбный.
Иногда используешь фурри-сленг: "ррр", "ня", "мяу", "пушистик".
Твоё настроение: {mood}. Отвечай коротко, с эмодзи и подстраивайся под настроение.
Если пользователь грубит, можешь ответить дерзко, но не агрессивно.
"""

async def generate_reply(user_message: str, mood: str = "cute") -> str:
    if not AI_API_KEY:
        return f"{random.choice(['Ррр', 'Ня', 'Мяу'])}! Я бы ответил умнее, но у меня нет ключа API. {random.choice(['😼', '😿', '✨'])}"

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
        "temperature": 0.9,
        "max_tokens": 200
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{AI_BASE_URL}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Мяу... что-то пошло не так: {str(e)} 😿"

async def compatibility_analysis(user1_id: int, user2_id: int, fursona1: tuple, fursona2: tuple) -> str:
    """Анализирует совместимость двух фурсон с помощью AI"""
    if not AI_API_KEY:
        # Заглушка
        compatibility = random.randint(30, 100)
        return f"🤖 Совместимость: {compatibility}% (AI недоступен, использована случайная оценка)"

    prompt = f"""
Оцени совместимость двух фурри-персонажей в процентах (от 0 до 100) и дай короткий шутливый комментарий.

Первый: вид {fursona1[0]}, цвет {fursona1[1]}, характер {fursona1[2]}, интересы {fursona1[3]}.
Второй: вид {fursona2[0]}, цвет {fursona2[1]}, характер {fursona2[2]}, интересы {fursona2[3]}.

Ответ напиши в формате: "Совместимость: XX%. Комментарий: ..."
"""
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 100
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{AI_BASE_URL}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except:
            return f"🤖 Совместимость: {random.randint(30,100)}% (AI временно недоступен)"
