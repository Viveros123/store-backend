"""Cliente delgado para la API de Gemini (Google AI Studio) — CU29/CU30/CU32.

Se usa la API REST directa (sin el SDK oficial) para no sumar una
dependencia nueva pesada: el proyecto ya trae `httpx`.
"""

import json

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

# "Flash Lite" en vez de "Flash" a secas: 500 solicitudes/día gratis contra
# apenas 20/día de los modelos "Flash" completos (3.5/3.6/3.7/3.8) — con el
# volumen de pruebas de un proyecto académico, 20/día se agota enseguida.
_MODELO = "gemini-3.5-flash-lite"
_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODELO}:generateContent"


def _llamar(
    *,
    prompt: str,
    instruccion_sistema: str,
    json_mode: bool = False,
) -> str:
    if not settings.gemini_api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El servicio de IA no está configurado (falta GEMINI_API_KEY).",
        )

    body: dict = {
        "system_instruction": {"parts": [{"text": instruccion_sistema}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }
    if json_mode:
        body["generationConfig"] = {"response_mime_type": "application/json"}

    try:
        res = httpx.post(
            _URL,
            params={"key": settings.gemini_api_key},
            json=body,
            timeout=60.0,
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No se pudo contactar al servicio de IA. Intentá de nuevo.",
        ) from e

    if res.status_code != 200:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El servicio de IA no pudo procesar la solicitud.",
        )

    data = res.json()
    try:
        partes = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in partes).strip()
    except (KeyError, IndexError) as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El servicio de IA no devolvió una respuesta válida.",
        ) from e


def generar_texto(prompt: str, instruccion_sistema: str) -> str:
    """Respuesta libre en texto (chatbot, reporte por voz)."""
    return _llamar(prompt=prompt, instruccion_sistema=instruccion_sistema)


def generar_json(prompt: str, instruccion_sistema: str) -> dict | list:
    """Respuesta forzada a JSON válido (recomendaciones)."""
    texto = _llamar(
        prompt=prompt, instruccion_sistema=instruccion_sistema, json_mode=True
    )
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "El servicio de IA no devolvió un JSON válido.",
        ) from e
