import httpx
from config import AI_API_KEY, AI_BASE_URL, IMAGE_MODEL

async def generate_image(prompt: str) -> bytes:
    """Генерирует изображение по тексту (DALL-E или аналоги)"""
    if not AI_API_KEY:
        raise Exception("Нет API ключа для генерации изображений")

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{AI_BASE_URL}/images/generations", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        image_url = data['data'][0]['url']
        # Скачиваем изображение
        image_resp = await client.get(image_url)
        return image_resp.content
