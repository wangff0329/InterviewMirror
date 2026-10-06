import httpx

from app.schemas import ModelConfig


async def transcribe_audio(audio: bytes, filename: str, content_type: str, config: ModelConfig) -> str:
    if config.provider == "demo":
        raise ValueError("语音转文字需要配置真实的 OpenAI-compatible API。")
    if not config.api_key or not config.base_url:
        raise ValueError("语音转文字需要同时配置 API Key 和 Base URL。")

    endpoint = f"{config.base_url.rstrip('/')}/audio/transcriptions"
    files = {"file": (filename, audio, content_type or "audio/webm")}
    data = {"model": config.transcription_model, "response_format": "json"}
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(endpoint, headers={"Authorization": f"Bearer {config.api_key}"}, data=data, files=files)
    if response.is_error:
        detail = response.text[:500]
        raise ValueError(f"语音转写服务调用失败：{detail}")
    payload = response.json()
    text = payload.get("text", "").strip()
    if not text:
        raise ValueError("没有识别到有效语音内容，请重新录音。")
    return text