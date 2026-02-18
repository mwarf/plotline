"""
plotline.llm.client - LLM backend abstraction using litellm.

Provides a unified interface for Ollama, LM Studio, Claude, and OpenAI
with privacy mode enforcement and retry logic.
"""

from __future__ import annotations

import time
from typing import Any


class LLMClient:
    """LLM client wrapper with privacy mode enforcement and retry logic."""

    def __init__(
        self,
        backend: str = "ollama",
        model: str = "llama3.1:70b-instruct-q4_K_M",
        privacy_mode: str = "local",
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        self.backend = backend
        self.model = model
        self.privacy_mode = privacy_mode
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._cloud_backends = {"claude", "openai"}
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _get_model_string(self) -> str:
        """Get the model string for litellm based on backend."""
        if self.backend == "ollama":
            return f"ollama/{self.model}"
        elif self.backend == "lmstudio":
            return f"openai/{self.model}"
        elif self.backend == "claude":
            return f"claude-{self.model}"
        elif self.backend == "openai":
            return self.model
        return self.model

    def _check_privacy(self) -> None:
        """Check if cloud API is allowed in current privacy mode."""
        if self.privacy_mode == "local" and self.backend in self._cloud_backends:
            from plotline.exceptions import LLMPrivacyError

            raise LLMPrivacyError(
                f"Cloud LLM backend '{self.backend}' not allowed in local privacy mode. "
                f"Set privacy_mode: hybrid in plotline.yaml to enable cloud APIs."
            )

    def complete(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        console=None,
    ) -> str:
        """Send prompt to LLM and get completion with retry logic.

        Args:
            prompt: The prompt string
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            console: Optional rich console for output

        Returns:
            LLM response text

        Raises:
            LLMPrivacyError: If cloud API used in local mode
            LLMError: If LLM request fails after all retries
        """
        from plotline.exceptions import LLMError, LLMResponseError

        self._check_privacy()

        try:
            import litellm
        except ImportError as e:
            raise LLMError("litellm not installed. Install with: pip install litellm") from e

        litellm.telemetry = False

        model = self._get_model_string()
        last_error = None

        for attempt in range(self.max_retries):
            if console and attempt > 0:
                console.print(f"[yellow]  Retry {attempt + 1}/{self.max_retries}...[/yellow]")

            try:
                if self.backend == "ollama":
                    litellm.api_base = "http://localhost:11434"
                elif self.backend == "lmstudio":
                    litellm.api_base = "http://localhost:1234/v1"

                response = litellm.completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=self.timeout,
                )

                usage = getattr(response, "usage", None)
                if usage:
                    self._token_usage["prompt_tokens"] += getattr(usage, "prompt_tokens", 0)
                    self._token_usage["completion_tokens"] += getattr(usage, "completion_tokens", 0)
                    self._token_usage["total_tokens"] += getattr(usage, "total_tokens", 0)

                choices = getattr(response, "choices", [])
                if not choices:
                    raise LLMResponseError("Empty response from LLM")

                message = getattr(choices[0], "message", None)
                if message is None:
                    raise LLMResponseError("No message in LLM response")

                content = getattr(message, "content", None)
                if content is None:
                    raise LLMResponseError("No content in LLM message")

                return content

            except LLMResponseError:
                raise
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if "connection" in error_str or "refused" in error_str:
                    if console:
                        console.print(f"[red]  Connection error: {e}[/red]")
                elif "timeout" in error_str:
                    if console:
                        console.print("[yellow]  Timeout, retrying...[/yellow]")
                elif "rate limit" in error_str:
                    if console:
                        console.print("[yellow]  Rate limited, waiting...[/yellow]")
                    time.sleep(self.retry_delay * 2)
                    continue

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise LLMError(
                        f"LLM request failed after {self.max_retries} retries: {last_error}"
                    ) from last_error

        raise LLMError(f"LLM request failed: {last_error}")

    def get_token_usage(self) -> dict[str, int]:
        """Get cumulative token usage."""
        return self._token_usage.copy()

    def reset_token_usage(self) -> None:
        """Reset token usage counters."""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def create_client_from_config(config: Any) -> LLMClient:
    """Create LLM client from PlotlineConfig.

    Args:
        config: PlotlineConfig instance

    Returns:
        Configured LLMClient
    """
    return LLMClient(
        backend=config.llm_backend,
        model=config.llm_model,
        privacy_mode=config.privacy_mode,
    )
