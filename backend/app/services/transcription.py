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
        detail = response.text.strip()
        try:
            payload = response.json()
            detail = payload.get("error", {}).get("message") or payload.get("message") or detail
        except ValueError:
            pass
        detail = detail[:500] or "上游没有返回错误详情。"
        if response.status_code in {404, 405}:
            detail = "当前 Base URL 不支持 /audio/transcriptions。请使用支持语音转写的 OpenAI API，或单独配置语音服务。"
        elif response.status_code == 422 and "whisper" in config.transcription_model.lower():
            detail = f"语音服务不接受转写模型 {config.transcription_model}，请确认该服务支持 Whisper 转写接口。原始信息：{detail}"
        raise ValueError(f"语音转写服务调用失败（HTTP {response.status_code}）：{detail}")
    payload = response.json()
    text = payload.get("text", "").strip()
    if not text:
        raise ValueError("没有识别到有效语音内容，请重新录音。")
    return text