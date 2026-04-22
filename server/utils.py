import os
import tomllib
from typing import Any

from deep_translator import DeeplTranslator, GoogleTranslator, LibreTranslator
import httpx

for config_file in ["config.toml", "config.template.toml"]:
    if os.path.exists(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/" + config_file
    ):
        break
else:
    raise FileNotFoundError("No config file found.")

with open(config_file, "rb") as f:
    config_data: dict[str, Any] = tomllib.load(f)


def get_config(key: str, default: Any = "") -> Any:
    return config_data.get(key) or os.getenv(key, default)


LIBRE_URL = get_config("LIBRE_URL", "")
DAILY_QUOTA = get_config("DAILY_QUOTA", 10)
DATA_PATH = get_config("DATA_PATH", "data/db.json")
OPENAI_API_KEY = get_config("OPENAI_API_KEY", "")


def _call_google(text: str, src: str, tgt: str) -> dict:
    try:
        res = GoogleTranslator(source=src, target=tgt).translate(text)
        return {"api": "Google", "translation": res, "error": None}
    except Exception as exc:
        return {"api": "Google", "translation": None, "error": str(exc)}


def _call_deepl(text: str, src: str, tgt: str) -> dict:
    DEEPL_API_KEY = get_config("DEEPL_API_KEY", "")
    try:
        if not DEEPL_API_KEY:
            return {
                "api": "DeepL",
                "translation": None,
                "error": "No DeepL API key configured",
            }
        res = DeeplTranslator(
            api_key=DEEPL_API_KEY, source=src, target=tgt, use_free_api=True
        ).translate(text)
        return {"api": "DeepL", "translation": res, "error": None}
    except Exception as exc:
        return {"api": "DeepL", "translation": None, "error": str(exc)}


def _call_libre(text: str, src: str, tgt: str) -> dict:
    LIBRE_API_KEY = get_config("LIBRE_API_KEY", "")
    try:
        kwargs = {"source": src, "target": tgt}
        if LIBRE_API_KEY:
            kwargs["api_key"] = LIBRE_API_KEY
        else:
            kwargs["api_key"] = "none"
            kwargs["use_free_api"] = True
        if LIBRE_URL:
            kwargs["custom_url"] = LIBRE_URL

        res = LibreTranslator(**kwargs).translate(text)
        return {"api": "LibreTranslate", "translation": res, "error": None}
    except Exception as exc:
        return {"api": "LibreTranslate", "translation": None, "error": str(exc)}


async def _call_mymemory(
    client: httpx.AsyncClient, text: str, src: str, tgt: str
) -> dict:
    try:
        resp = await client.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{src}|{tgt}"},
            timeout=10,
        )
        data = resp.json()
        if data.get("responseStatus") == 200:
            return {
                "api": "MyMemory",
                "translation": data["responseData"]["translatedText"],
                "error": None,
            }
        return {
            "api": "MyMemory",
            "translation": None,
            "error": "API returned an error",
        }
    except Exception as exc:
        return {"api": "MyMemory", "translation": None, "error": str(exc)}
