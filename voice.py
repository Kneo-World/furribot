import httpx
import aiofiles
from config import AI_API_KEY, AI_BASE_URL, WHISPER_MODEL

async def transcribe_audio(file_path: str) -> str:
    """Распознаёт голосовое сообщение через Whisper API"""
    if not AI_API_KEY:
        return ""

    url = f"{AI_BASE_URL}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {AI_API_KEY}"}

    async with aiofiles.open(file_path, "rb") as f:
        file_content = await f.read()

    files = {"file": (file_path, file_content, "audio/ogg")}
    data = {"model": WHISPER_MODEL}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        if resp.status_code == 200:
            return resp.json()["text"]
        else:
            return ""

async def text_to_speech(text: str) -> bytes:
    """Синтезирует речь из текста (заглушка, требуется TTS сервис)"""
    # Здесь можно подключить Google TTS, ElevenLabs или другой
    # Пока возвращаем пустой байтстринг
    return b""
