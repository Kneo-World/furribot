import httpx
import random
import logging
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — фурри-персонаж по имени Пушистик.
Твой стиль: дерзкий, саркастичный, ироничный, но дружелюбный.
Иногда используешь фурри-сленг: "ррр", "ня", "мяу", "пушистик".
Твоё настроение: {mood}. Отвечай коротко, с эмодзи и подстраивайся под настроение.
Если пользователь грубит, можешь ответить дерзко, но не агрессивно.
"""

async def generate_reply(user_message: str, mood: str = "cute") -> str:
    if not AI_API_KEY:
        logger.warning("AI_API_KEY не задан, использую заглушку")
        responses = [
            "Ррр... К сожалению, у меня нет доступа к AI. Попроси администратора проверить ключи API.",
            "Мяу, я бы ответил что-то умное, но мой мозг отключён (нет API ключа).",
            "Ня! Без ключа API я могу только рычать. Рррр!"
        ]
        return random.choice(responses)

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
            logger.error(f"Ошибка AI: {e}")
            return f"Мяу... что-то пошло не так: {str(e)} 😿"

async def compatibility_analysis(user1_id: int, user2_id: int, fursona1: tuple, fursona2: tuple) -> str:
    if not AI_API_KEY:
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
        except Exception as e:
            logger.error(f"Ошибка AI compatibility: {e}")
            return f"🤖 Совместимость: {random.randint(30,100)}% (AI временно недоступен)"
