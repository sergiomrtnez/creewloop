"""
Configuration and LLM factory for CreewLoop Software Factory.
Supports LiteLLM providers: Ollama, LM Studio, OpenAI, Anthropic, Gemini, etc.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ProviderPreset:
    name: str
    default_model: str
    requires_api_key: bool
    default_base_url: Optional[str] = None
    env_key_name: Optional[str] = None


PROVIDERS: Dict[str, ProviderPreset] = {
    "Ollama": ProviderPreset(
        name="Ollama",
        default_model="ollama/llama3.2",
        requires_api_key=False,
        default_base_url="http://localhost:11434",
        env_key_name=None,
    ),
    "LM Studio": ProviderPreset(
        name="LM Studio",
        default_model="openai/local-model",
        requires_api_key=False,
        default_base_url="http://localhost:1234/v1",
        env_key_name=None,
    ),
    "OpenAI": ProviderPreset(
        name="OpenAI",
        default_model="openai/gpt-4o-mini",
        requires_api_key=True,
        default_base_url=None,
        env_key_name="OPENAI_API_KEY",
    ),
    "Anthropic": ProviderPreset(
        name="Anthropic",
        default_model="anthropic/claude-3-5-sonnet-20241022",
        requires_api_key=True,
        default_base_url=None,
        env_key_name="ANTHROPIC_API_KEY",
    ),
    "Gemini": ProviderPreset(
        name="Gemini",
        default_model="gemini/gemini-2.0-flash",
        requires_api_key=True,
        default_base_url=None,
        env_key_name="GEMINI_API_KEY",
    ),
}


@dataclass
class AppConfig:
    provider: str = "Ollama"
    model_name: str = "ollama/llama3.2"
    api_key: str = ""
    base_url: str = "http://localhost:11434"
    workspace_dir: str = os.path.join(os.getcwd(), "output")
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> AppConfig:
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "Ollama")
        preset = PROVIDERS.get(provider, PROVIDERS["Ollama"])
        api_key = ""
        if preset.env_key_name:
            api_key = os.getenv(preset.env_key_name, "")
        
        return cls(
            provider=provider,
            model_name=os.getenv("DEFAULT_LLM_MODEL", preset.default_model),
            api_key=api_key,
            base_url=preset.default_base_url or "",
            workspace_dir=os.path.abspath(os.getenv("WORKSPACE_DIR", os.path.join(os.getcwd(), "output"))),
        )


def build_crewai_llm(
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.2,
):
    """
    Creates and returns a CrewAI LLM instance backed by LiteLLM.
    """
    from crewai import LLM

    # Clean inputs
    model = model_name.strip() if model_name else "ollama/llama3.2"
    key = api_key.strip() if api_key else None
    url = base_url.strip() if base_url else None

    # Handle LM Studio / Ollama defaults if user didn't specify url
    preset = PROVIDERS.get(provider)
    if preset and preset.default_base_url and not url:
        url = preset.default_base_url

    # In LM Studio, LiteLLM expects 'openai/' prefix and any dummy api_key if None
    if provider == "LM Studio" and not key:
        key = "lm-studio"

    kwargs = {
        "model": model,
        "temperature": temperature,
    }
    if key:
        kwargs["api_key"] = key
    if url:
        kwargs["base_url"] = url

    return LLM(**kwargs)
