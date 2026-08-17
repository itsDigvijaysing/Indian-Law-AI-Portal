"""
LLM Client Adapters

Provider clients normalized to the google.generativeai surface the agents
expect: .generate_content(prompt).text plus .generate_content_stream(prompt).
"""


class _GroqResponse:
    """Mimics google.generativeai response shape (.text)."""
    def __init__(self, text: str):
        self.text = text


class GroqLLMClient:
    """Adapter giving Groq's chat-completions API the same .generate_content(prompt).text shape the agents expect.

    Handles both plain chat models (llama-3.1-8b-instant) and reasoning models
    (openai/gpt-oss-20b): the latter emit a separate 'reasoning' channel, so we
    pass reasoning_effort='low' (fast, minimal reasoning) and only read the final
    answer content. max_completion_tokens must cover reasoning + answer."""

    def __init__(self, api_key: str, model: str):
        from groq import Groq
        self._client = Groq(api_key=api_key)
        self._model = model
        self._is_reasoning = 'gpt-oss' in model.lower() or 'reasoning' in model.lower()

    def _params(self, stream: bool) -> dict:
        p = {
            "messages": None,  # filled by caller
            "model": self._model,
            # 0.0, not 0.3: the same question should give the same answer.
            # NOTE this does NOT make generation reproducible — Groq's batched
            # MoE serving still varies long answers run to run. `seed=42` was
            # measured 2026-07-30 and made no difference (6/6 distinct answers),
            # so it is deliberately not set. Retrieval IS deterministic; only
            # the final wording/citation selection drifts.
            "temperature": 0.0,
            "max_completion_tokens": 3000,  # room for reasoning + a full answer
            "stream": stream,
        }
        if self._is_reasoning:
            p["reasoning_effort"] = "low"   # minimal reasoning → fast, cheap, clean content
        return p

    def generate_content(self, prompt: str) -> _GroqResponse:
        p = self._params(stream=False)
        p["messages"] = [{"role": "user", "content": prompt}]
        completion = self._client.chat.completions.create(**p)
        return _GroqResponse(completion.choices[0].message.content or "")

    def generate_content_stream(self, prompt: str):
        """Yield answer text deltas as they arrive (SSE streaming path).
        Reasoning deltas go to delta.reasoning (ignored); only content is streamed."""
        p = self._params(stream=True)
        p["messages"] = [{"role": "user", "content": prompt}]
        stream = self._client.chat.completions.create(**p)
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
