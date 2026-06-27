"""Optional model provider for the LLM-backed tiers (1 and 2).

The harness must run with **no network access** and must **not block CI on an LLM
judge** (both are explicit non-goals/MVP constraints). So the default provider is
``none``: the LLM tiers build their prompts from the real shipped skill files,
then report ``skipped`` instead of calling out.

To actually score Tier 1 / Tier 2 locally, set:

    GREYBEARD_EVAL_PROVIDER=openai
    GREYBEARD_EVAL_MODEL=<model name>
    OPENAI_API_KEY=<key>            # read from the environment, never committed
    OPENAI_BASE_URL=<optional override, default https://api.openai.com/v1>

The OpenAI-compatible client uses only the standard library (``urllib``) to keep
the dependency footprint at zero.
"""

from __future__ import annotations

import json
import os
import urllib.request


def get_classifier():
    """Return a ``classify(system, user) -> str | None`` callable, or ``None``.

    Returns ``None`` when no provider is configured, which signals the tiers to
    skip (rather than fail) their LLM-backed cases.
    """
    provider = os.environ.get("GREYBEARD_EVAL_PROVIDER", "none").strip().lower()
    if provider in ("", "none", "off", "skip"):
        return None
    if provider == "openai":
        return _openai_classifier()
    raise ValueError(f"unknown GREYBEARD_EVAL_PROVIDER: {provider!r}")


def _openai_classifier():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Configured to use a provider but no credentials -> skip, do not crash.
        return None
    model = os.environ.get("GREYBEARD_EVAL_MODEL", "gpt-4o-mini")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    def classify(system, user):
        body = json.dumps(
            {
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]

    return classify
