"""
LLM client factory with Perplexity-first, OpenAI-fallback strategy.

This module centralizes LLM provider selection and instantiation.
It ensures:
  1. Perplexity is the primary provider (cheaper, built-in web search)
  2. OpenAI is the fallback (if Perplexity key is not set or unavailable)
  3. Clear error messages if no LLM is configured
  4. Consistent configuration across all graph nodes

Usage:
    from src.tools.llm_client import get_llm
    
    llm = get_llm()
    response = llm.invoke("Your prompt here")
"""

from __future__ import annotations

import os
from typing import Literal

from langchain_openai import ChatOpenAI

from src.config import config
from src.utils.logging_config import logger


def get_llm(
    provider: Literal["auto", "perplexity", "openai"] = "auto",
    temperature: float = 0.7,
    timeout: int = 30,
) -> ChatOpenAI:
    """
    Get an LLM client with automatic provider fallback.

    Strategy:
      1. If provider="auto" (default):
         - Use Perplexity if PERPLEXITY_API_KEY is set
         - Fall back to OpenAI if OPENAI_API_KEY is set
         - Raise error if neither is configured
      2. If provider="perplexity":
         - Use Perplexity (raise error if key not set)
      3. If provider="openai":
         - Use OpenAI (raise error if key not set)

    Args:
        provider: Which provider to use ("auto", "perplexity", or "openai").
                 "auto" means Perplexity-first, OpenAI-fallback.
        temperature: LLM temperature (0.0=deterministic, 1.0=creative).
                    Default 0.7 balances creativity with consistency.
        timeout: Request timeout in seconds. Default 30s.

    Returns:
        ChatOpenAI: Configured LLM client (works with OpenAI API endpoint).

    Raises:
        ValueError: If no LLM provider is configured or requested provider
                   is not available.

    Example:
        >>> llm = get_llm()  # Uses Perplexity if available, else OpenAI
        >>> response = llm.invoke("What is the meaning of life?")
        >>> print(response.content)
    """

    if provider == "auto":
        # Perplexity-first strategy
        if config.PERPLEXITY_API_KEY:
            logger.debug("Using Perplexity as LLM provider (primary)")
            return _create_perplexity_client(temperature=temperature, timeout=timeout)
        elif config.OPENAI_API_KEY:
            logger.warning(
                "Perplexity API key not set; falling back to OpenAI. "
                "Set PERPLEXITY_API_KEY to use the primary provider."
            )
            return _create_openai_client(temperature=temperature, timeout=timeout)
        else:
            raise ValueError(
                "No LLM provider configured. "
                "Set either PERPLEXITY_API_KEY or OPENAI_API_KEY in .env"
            )

    elif provider == "perplexity":
        if not config.PERPLEXITY_API_KEY:
            raise ValueError(
                "Perplexity provider requested but PERPLEXITY_API_KEY not set in .env"
            )
        logger.debug("Using Perplexity as LLM provider (explicit)")
        return _create_perplexity_client(temperature=temperature, timeout=timeout)

    elif provider == "openai":
        if not config.OPENAI_API_KEY:
            raise ValueError(
                "OpenAI provider requested but OPENAI_API_KEY not set in .env"
            )
        logger.debug("Using OpenAI as LLM provider (explicit)")
        return _create_openai_client(temperature=temperature, timeout=timeout)

    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'auto', 'perplexity', or 'openai'")


def _create_perplexity_client(
    temperature: float = 0.7, timeout: int = 30
) -> ChatOpenAI:
    """
    Create a ChatOpenAI client configured for Perplexity API.

    Perplexity provides an OpenAI-compatible Chat Completions API endpoint,
    so we use ChatOpenAI with a custom base_url.

    Args:
        temperature: LLM temperature parameter.
        timeout: Request timeout in seconds.

    Returns:
        ChatOpenAI: Client configured for Perplexity endpoint.

    Raises:
        ValueError: If PERPLEXITY_API_KEY is not set.
    """
    if not config.PERPLEXITY_API_KEY:
        raise ValueError("PERPLEXITY_API_KEY must be set to use Perplexity provider")

    return ChatOpenAI(
        api_key=config.PERPLEXITY_API_KEY,
        model=config.PERPLEXITY_MODEL,
        base_url="https://api.perplexity.ai",  # Perplexity API endpoint
        temperature=temperature,
        timeout=timeout,
    )


def _create_openai_client(
    temperature: float = 0.7, timeout: int = 30
) -> ChatOpenAI:
    """
    Create a ChatOpenAI client configured for OpenAI API.

    Args:
        temperature: LLM temperature parameter.
        timeout: Request timeout in seconds.

    Returns:
        ChatOpenAI: Client configured for OpenAI endpoint.

    Raises:
        ValueError: If OPENAI_API_KEY is not set.
    """
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY must be set to use OpenAI provider")

    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=config.OPENAI_MODEL,
        temperature=temperature,
        timeout=timeout,
    )


def get_llm_provider_info() -> dict:
    """
    Return information about available LLM providers.

    Useful for logging/debugging which provider will be used.

    Returns:
        dict: Provider availability and configuration.

    Example:
        >>> info = get_llm_provider_info()
        >>> print(info)
        {
            'perplexity_available': True,
            'perplexity_model': 'llama-3.1-sonar-small-128k-online',
            'openai_available': True,
            'openai_model': 'gpt-3.5-turbo',
            'primary_provider': 'perplexity'
        }
    """
    perplexity_available = bool(config.PERPLEXITY_API_KEY)
    openai_available = bool(config.OPENAI_API_KEY)

    # Determine which will be used with "auto" strategy
    if perplexity_available:
        primary = "perplexity"
    elif openai_available:
        primary = "openai"
    else:
        primary = "none"

    return {
        "perplexity_available": perplexity_available,
        "perplexity_model": config.PERPLEXITY_MODEL if perplexity_available else None,
        "openai_available": openai_available,
        "openai_model": config.OPENAI_MODEL if openai_available else None,
        "primary_provider": primary,
    }
