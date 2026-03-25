"""Tests for src/llm_client.py — config loading, error handling, retry logic.

All tests use mocks; no real API calls are made.
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import openai
import pytest

from src.llm_client import LLMClient, load_model_config

# Path to the real configs/models.yaml in the project
CONFIG_PATH = Path(__file__).parent.parent / "configs" / "models.yaml"


class TestLoadConfig:
    """Tests for load_model_config."""

    def test_load_config_deepseek(self):
        """Config loads correctly for the deepseek model."""
        config = load_model_config("deepseek", CONFIG_PATH)
        assert config["provider"] == "openai_compatible"
        assert config["base_url"] == "https://api.deepseek.com"
        assert config["model"] == "deepseek-chat"
        assert config["api_key_env"] == "DEEPSEEK_API_KEY"
        assert config["temperature"] == 0
        assert config["max_tokens"] == 2048
        assert config["retry"]["max_retries"] == 3

    def test_load_config_openrouter(self):
        """Config loads correctly for the openrouter_free model."""
        config = load_model_config("openrouter_free", CONFIG_PATH)
        assert config["base_url"] == "https://openrouter.ai/api/v1"
        assert config["model"] == "openai/gpt-oss-120b:free"
        assert config["api_key_env"] == "OPENROUTER_API_KEY"

    def test_load_config_unknown_model(self):
        """Raises KeyError for an unknown model name."""
        with pytest.raises(KeyError, match="not_a_real_model"):
            load_model_config("not_a_real_model", CONFIG_PATH)

    def test_load_config_missing_file(self, tmp_path):
        """Raises FileNotFoundError for a missing config file."""
        with pytest.raises(FileNotFoundError):
            load_model_config("deepseek", tmp_path / "nonexistent.yaml")


class TestLLMClientInit:
    """Tests for LLMClient initialization."""

    def test_missing_api_key_raises(self, monkeypatch):
        """Clear error when the required env var is not set."""
        # Ensure the env var is definitely not set
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            LLMClient("deepseek", run_id="test_run", config_path=CONFIG_PATH)

    def test_init_success(self, monkeypatch, tmp_path):
        """Client initializes successfully when API key is present."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-12345")
        # Remove proxy env vars so httpx doesn't try to use a SOCKS proxy
        for var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
            monkeypatch.delenv(var, raising=False)
        # Use tmp_path so log directory doesn't pollute project
        monkeypatch.chdir(tmp_path)

        client = LLMClient("deepseek", run_id="test_run", config_path=CONFIG_PATH)
        assert client.model_name == "deepseek"
        assert client.config["model"] == "deepseek-chat"
        assert client.log_dir.exists()


class TestLLMClientChat:
    """Tests for LLMClient.chat with mocked API calls."""

    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        """Create a client with mocked API key and working directory."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-12345")
        # Remove proxy env vars so httpx doesn't try to use a SOCKS proxy
        for var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.chdir(tmp_path)
        c = LLMClient("deepseek", run_id="test_run", config_path=CONFIG_PATH)
        # Zero out rate limit delay for faster tests
        c._min_delay = 0.0
        return c

    def _make_mock_completion(self, content="Hello!", total_tokens=42):
        """Helper to build a mock completion response."""
        mock_message = MagicMock()
        mock_message.content = content

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_usage = MagicMock()
        mock_usage.total_tokens = total_tokens

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage
        return mock_completion

    def test_chat_success(self, client):
        """Successful chat returns expected structure."""
        mock_completion = self._make_mock_completion("Test response", 100)

        with patch.object(
            client.client.chat.completions, "create", return_value=mock_completion
        ):
            result = client.chat(
                messages=[{"role": "user", "content": "Hi"}],
                purpose="test_success",
            )

        assert result["response"] == "Test response"
        assert result["model"] == "deepseek-chat"
        assert result["tokens_used"] == 100
        assert "request_id" in result

    def test_chat_logs_request(self, client):
        """Chat call creates a log file."""
        mock_completion = self._make_mock_completion()

        with patch.object(
            client.client.chat.completions, "create", return_value=mock_completion
        ):
            client.chat(
                messages=[{"role": "user", "content": "Hi"}],
                purpose="log_test",
            )

        log_files = list(client.log_dir.glob("*.json"))
        assert len(log_files) == 1
        assert "log_test" in log_files[0].name

    def test_retry_on_429(self, client):
        """Retries with backoff on RateLimitError (429)."""
        # Set very short backoff for testing
        client._backoff_seconds = 0.01

        mock_completion = self._make_mock_completion("Recovered!")

        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise rate_limit_error
            return mock_completion

        with patch.object(
            client.client.chat.completions, "create", side_effect=side_effect
        ):
            result = client.chat(
                messages=[{"role": "user", "content": "Hi"}],
                purpose="retry_test",
            )

        assert call_count == 3  # 2 failures + 1 success
        assert result["response"] == "Recovered!"

    def test_retry_exhaustion_raises(self, client):
        """Raises after all retries are exhausted."""
        client._backoff_seconds = 0.01

        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": "Rate limit exceeded"}},
        )

        with patch.object(
            client.client.chat.completions, "create", side_effect=rate_limit_error
        ):
            with pytest.raises(openai.RateLimitError):
                client.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    purpose="exhaust_test",
                )

    def test_retry_on_503(self, client):
        """Retries on 503 Service Unavailable."""
        client._backoff_seconds = 0.01

        mock_completion = self._make_mock_completion("Back online!")

        service_error = openai.APIStatusError(
            message="Service unavailable",
            response=MagicMock(status_code=503, headers={}),
            body={"error": {"message": "Service unavailable"}},
        )

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise service_error
            return mock_completion

        with patch.object(
            client.client.chat.completions, "create", side_effect=side_effect
        ):
            result = client.chat(
                messages=[{"role": "user", "content": "Hi"}],
                purpose="503_test",
            )

        assert call_count == 2
        assert result["response"] == "Back online!"

    def test_non_retryable_error_raises_immediately(self, client):
        """Non-retryable errors raise immediately without retry."""
        auth_error = openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401, headers={}),
            body={"error": {"message": "Invalid API key"}},
        )

        with patch.object(
            client.client.chat.completions, "create", side_effect=auth_error
        ):
            with pytest.raises(openai.AuthenticationError):
                client.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    purpose="auth_fail",
                )

    def test_rate_limit_enforced(self, client):
        """Minimum delay between calls is respected."""
        client._min_delay = 0.1  # 100ms for testing

        mock_completion = self._make_mock_completion()

        with patch.object(
            client.client.chat.completions, "create", return_value=mock_completion
        ):
            start = time.time()
            client.chat(messages=[{"role": "user", "content": "1"}], purpose="rate1")
            client.chat(messages=[{"role": "user", "content": "2"}], purpose="rate2")
            elapsed = time.time() - start

        # Second call should have waited at least min_delay
        assert elapsed >= 0.1
