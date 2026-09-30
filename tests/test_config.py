"""
Unit Tests for Configuration & LLM Factory (src/config.py).
"""

from __future__ import annotations

import os
from unittest.mock import patch
import pytest

from src.config import AppConfig, PROVIDERS, ProviderPreset, build_crewai_llm


class TestProvidersConfig:
    def test_providers_presets_exist(self):
        expected_providers = ["Ollama", "LM Studio", "OpenAI", "Anthropic", "Gemini"]
        for provider in expected_providers:
            assert provider in PROVIDERS, f"Provider '{provider}' missing from PROVIDERS"
            preset = PROVIDERS[provider]
            assert isinstance(preset, ProviderPreset)
            assert preset.name == provider
            assert preset.default_model

    def test_local_providers_do_not_require_api_key(self):
        assert PROVIDERS["Ollama"].requires_api_key is False
        assert PROVIDERS["Ollama"].default_base_url == "http://localhost:11434"
        assert PROVIDERS["LM Studio"].requires_api_key is False
        assert PROVIDERS["LM Studio"].default_base_url == "http://localhost:1234/v1"

    def test_cloud_providers_require_api_key(self):
        assert PROVIDERS["OpenAI"].requires_api_key is True
        assert PROVIDERS["OpenAI"].env_key_name == "OPENAI_API_KEY"
        assert PROVIDERS["Anthropic"].requires_api_key is True
        assert PROVIDERS["Anthropic"].env_key_name == "ANTHROPIC_API_KEY"
        assert PROVIDERS["Gemini"].requires_api_key is True
        assert PROVIDERS["Gemini"].env_key_name == "GEMINI_API_KEY"


class TestAppConfig:
    def test_default_app_config(self):
        config = AppConfig()
        assert config.provider == "Ollama"
        assert config.model_name == "ollama/llama3.2"
        assert config.temperature == 0.2
        assert os.path.isabs(config.workspace_dir)

    def test_from_env_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig.from_env()
            assert config.provider == "Ollama"
            assert config.model_name == "ollama/llama3.2"
            assert config.api_key == ""

    def test_from_env_custom_provider_and_keys(self):
        env_vars = {
            "DEFAULT_LLM_PROVIDER": "OpenAI",
            "DEFAULT_LLM_MODEL": "openai/gpt-4o",
            "OPENAI_API_KEY": "sk-test-secret-key-12345",
            "WORKSPACE_DIR": "./custom_workspace",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = AppConfig.from_env()
            assert config.provider == "OpenAI"
            assert config.model_name == "openai/gpt-4o"
            assert config.api_key == "sk-test-secret-key-12345"
            assert config.workspace_dir.endswith("custom_workspace")

    def test_from_env_unknown_provider_fallback(self):
        env_vars = {"DEFAULT_LLM_PROVIDER": "NonExistentProvider"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = AppConfig.from_env()
            assert config.provider == "NonExistentProvider"
            assert config.model_name == "ollama/llama3.2"


class TestBuildCrewAILLM:
    def test_build_ollama_llm(self):
        llm = build_crewai_llm(
            provider="Ollama",
            model_name="ollama/mistral",
            base_url="http://localhost:11434",
            temperature=0.1,
        )
        assert llm.model == "mistral"
        assert getattr(llm, "provider", None) == "ollama"
        assert llm.temperature == 0.1

    def test_build_lm_studio_auto_injects_dummy_key(self):
        llm = build_crewai_llm(
            provider="LM Studio",
            model_name="openai/local-qwen",
            api_key=None,
        )
        assert llm.model == "local-qwen"
        assert getattr(llm, "provider", None) == "openai"
        assert llm.api_key == "lm-studio"
        assert llm.base_url == "http://localhost:1234/v1"

    def test_build_llm_strips_whitespace(self):
        llm = build_crewai_llm(
            provider="OpenAI",
            model_name="  openai/gpt-4o-mini  ",
            api_key="  sk-openai-key  ",
            base_url="  https://api.openai.com/v1  ",
        )
        assert llm.model == "gpt-4o-mini"
        assert getattr(llm, "provider", None) == "openai"
        assert llm.api_key == "sk-openai-key"
        assert llm.base_url == "https://api.openai.com/v1"

    def test_build_llm_empty_model_fallback(self):
        llm = build_crewai_llm(
            provider="Ollama",
            model_name="",
        )
        assert llm.model == "llama3.2"
        assert getattr(llm, "provider", None) == "ollama"
