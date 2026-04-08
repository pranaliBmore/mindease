import logging
from typing import Optional, Tuple

import httpx

from app.config.settings import get_settings
from groq import AsyncGroq

logger = logging.getLogger(__name__)
settings = get_settings()

OFFLINE_FALLBACK_REPLY = (
    "I'm having trouble reaching our AI services right now, but I'm still here for you. "
    "Try a slow breath: inhale for four counts, hold for four, exhale for four. "
    "What feels hardest for you in this moment?"
)


class AIProviderService:
    async def _groq(self, prompt: str) -> Optional[str]:
        if not settings.groq_api_key:
            return None
        try:
            client = AsyncGroq(api_key=settings.groq_api_key)
            completion = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=220
            )
            if completion.choices:
                return str(completion.choices[0].message.content).strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Groq request failed: %s", exc)
        return None

    async def _huggingface(self, prompt: str) -> Optional[str]:
        if not settings.hf_api_token:
            return None
        url = f"https://router.huggingface.co/hf-inference/models/{settings.hf_model}"
        headers = {"Authorization": f"Bearer {settings.hf_api_token}"}
        payload = {"inputs": prompt, "parameters": {"max_new_tokens": 220, "temperature": 0.7}}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list) and data:
                    generated_text = data[0].get("generated_text", "")
                    return generated_text.strip() if generated_text else None
                if isinstance(data, dict) and "generated_text" in data:
                    return str(data["generated_text"]).strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("HuggingFace request failed: %s", exc)
        return None

    async def _ollama(self, prompt: str) -> Optional[str]:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
        payload = {"model": settings.ollama_model, "prompt": prompt, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return str(data.get("response", "")).strip() or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama request failed: %s", exc)
        return None

    async def _gpt4all(self, prompt: str) -> Optional[str]:
        if not settings.gpt4all_model_path:
            return None
        try:
            from gpt4all import GPT4All
        except Exception:
            return None

        # GPT4All runs sync; keep usage short to stay responsive.
        model = GPT4All(model_name=settings.gpt4all_model_path, allow_download=False)
        with model.chat_session():
            output = model.generate(prompt, max_tokens=220, temp=0.7)
        return str(output).strip() if output else None

    async def generate_response(self, prompt: str) -> Tuple[str, str]:
        errors: list[str] = []
        for provider_name, provider_func in (
            ("groq", self._groq),
            ("huggingface", self._huggingface),
            ("ollama", self._ollama),
            ("gpt4all", self._gpt4all),
        ):
            try:
                result = await provider_func(prompt)
                if result:
                    return result, provider_name
            except Exception as exc:  # noqa: BLE001
                logger.warning("Provider %s failed: %s", provider_name, exc)
                errors.append(f"{provider_name}: {exc}")

        logger.warning("All AI providers unavailable; returning offline fallback. %s", errors)
        return OFFLINE_FALLBACK_REPLY, "fallback"
