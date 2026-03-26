"""OpenAI-compatible LLM client with retry, rate limiting, and logging."""

import json
import os
import time
import uuid
from pathlib import Path

import openai
import yaml
from dotenv import load_dotenv

load_dotenv()

# Default path to model configs
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "models.yaml"


def load_model_config(model_name: str, config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load a specific model's configuration from models.yaml.

    Args:
        model_name: Key under the 'models' section in the YAML file.
        config_path: Path to the YAML config file.

    Returns:
        Dict with model configuration.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        KeyError: If model_name is not found in config.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    models = config.get("models", {})
    if model_name not in models:
        available = list(models.keys())
        raise KeyError(
            f"Model '{model_name}' not found in config. Available: {available}"
        )

    return models[model_name]


class LLMClient:
    """OpenAI-compatible LLM client with retry, rate limiting, and request logging.

    Usage:
        client = LLMClient("deepseek", run_id="run_001")
        result = client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            purpose="test_call"
        )
        print(result["response"])
    """

    def __init__(self, model_name: str, run_id: str, config_path: Path = DEFAULT_CONFIG_PATH):
        """Load config for model_name from configs/models.yaml.

        Creates an OpenAI-compatible client and sets up logging directory.

        Args:
            model_name: Key in models.yaml (e.g. 'deepseek', 'openrouter_free').
            run_id: Identifier for this pipeline run, used for log directory.
            config_path: Path to models.yaml config file.

        Raises:
            KeyError: If model_name not in config.
            ValueError: If required API key env var is not set.
        """
        self.model_name = model_name
        self.run_id = run_id
        self.config = load_model_config(model_name, config_path)

        # Load API key from environment variable specified in config
        api_key_env = self.config["api_key_env"]
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(
                f"API key environment variable '{api_key_env}' is not set. "
                f"Set it in your .env file or environment."
            )

        # Create OpenAI-compatible client
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.config["base_url"],
            timeout=self.config.get("timeout", 60),
        )

        # Rate limiting state
        self._last_call_time = 0.0
        self._min_delay = self.config.get("min_delay_between_calls", 1.0)

        # Retry config
        retry_config = self.config.get("retry", {})
        self._max_retries = retry_config.get("max_retries", 3)
        self._backoff_seconds = retry_config.get("backoff_seconds", 5)

        # Set up log directory
        self.log_dir = Path("results") / "runs" / run_id / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _enforce_rate_limit(self):
        """Wait if needed to respect minimum delay between calls."""
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self._min_delay:
            time.sleep(self._min_delay - elapsed)
        self._last_call_time = time.time()

    def _log_request(self, request_id: str, purpose: str, messages: list, response_data: dict, response_format: dict | None = None):
        """Log request and response as JSON to the run's log directory.

        Args:
            request_id: Unique identifier for this request.
            purpose: Short label for the log filename.
            messages: The messages sent to the API.
            response_data: The parsed response data.
            response_format: The response_format used in the request, if any.
        """
        log_entry = {
            "request_id": request_id,
            "model_name": self.model_name,
            "model": self.config["model"],
            "purpose": purpose,
            "response_format": response_format,
            "messages": messages,
            "response": response_data,
            "timestamp": time.time(),
        }

        # Build filename: purpose_requestid.json
        safe_purpose = purpose.replace("/", "_").replace(" ", "_") if purpose else "call"
        filename = f"{safe_purpose}_{request_id[:8]}.json"
        log_path = self.log_dir / filename
        self.log_dir.mkdir(parents=True, exist_ok=True)

        with open(log_path, "w") as f:
            json.dump(log_entry, f, indent=2, default=str)

    def chat(self, messages: list[dict], purpose: str = "", response_format: dict | None = None) -> dict:
        """Send messages to the LLM, retry on failure, log everything.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            purpose: Short label for log filenames (e.g. 'baseline_lp_001').
            response_format: Optional response format dict (e.g. {"type": "json_object"}).
                Supported by OpenAI-compatible APIs for structured output.

        Returns:
            Dict with keys:
                - response (str): The assistant's reply text.
                - model (str): The model identifier used.
                - tokens_used (int): Total tokens (prompt + completion).
                - request_id (str): Unique ID for this request.

        Raises:
            openai.APIError: If all retries are exhausted.
        """
        request_id = str(uuid.uuid4())
        last_exception = None

        for attempt in range(self._max_retries + 1):
            try:
                self._enforce_rate_limit()

                create_kwargs = {
                    "model": self.config["model"],
                    "messages": messages,
                    "temperature": self.config.get("temperature", 0),
                    "max_tokens": self.config.get("max_tokens", 2048),
                }
                if response_format:
                    create_kwargs["response_format"] = response_format

                completion = self.client.chat.completions.create(**create_kwargs)

                # Extract response data
                response_text = completion.choices[0].message.content or ""
                usage = completion.usage
                tokens_used = (usage.total_tokens if usage else 0)

                result = {
                    "response": response_text,
                    "model": self.config["model"],
                    "tokens_used": tokens_used,
                    "request_id": request_id,
                }

                # Log successful request
                self._log_request(request_id, purpose, messages, result, response_format)

                return result

            except (openai.RateLimitError, openai.APIStatusError) as e:
                last_exception = e
                # Retry on 429 (RateLimitError) and 503 (APIStatusError with status 503)
                should_retry = isinstance(e, openai.RateLimitError)
                if isinstance(e, openai.APIStatusError) and e.status_code == 503:
                    should_retry = True

                if should_retry and attempt < self._max_retries:
                    wait_time = self._backoff_seconds * (2 ** attempt)
                    time.sleep(wait_time)
                    continue

                # Log the failure
                error_data = {
                    "error": str(e),
                    "attempts": attempt + 1,
                }
                self._log_request(request_id, f"FAILED_{purpose}", messages, error_data, response_format)
                raise

            except Exception as e:
                # Log unexpected errors and re-raise
                last_exception = e
                error_data = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "attempts": attempt + 1,
                }
                self._log_request(request_id, f"FAILED_{purpose}", messages, error_data, response_format)
                raise

        # Should not reach here, but just in case
        raise last_exception  # type: ignore
