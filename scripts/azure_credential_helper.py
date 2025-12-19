"""
Azure Credential Helper Module.

Provides a shared credential and token provider for Azure OpenAI authentication
using DefaultAzureCredential. This module follows the DRY principle by centralizing
credential management for all scripts that need Azure OpenAI access.

Authentication methods (in order of precedence):
1. Managed Identity (in Azure Container Apps)
2. Azure CLI credentials (local development - run 'az login')
3. Environment credentials (if AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET set)

Usage:
    from scripts.azure_credential_helper import get_token_provider, get_credential

    # For Azure OpenAI clients that accept token_provider
    client = AzureOpenAI(
        azure_ad_token_provider=get_token_provider(),
        azure_endpoint=endpoint,
        api_version=api_version
    )

    # For agent-framework clients
    client = AzureOpenAIChatClient(
        azure_ad_token_provider=get_token_provider(),
        endpoint=endpoint,
        deployment_name=deployment,
        api_version=api_version
    )
"""

import os
import sys
from typing import Callable, Optional

from scripts.logging_config import get_logger

logger = get_logger(__name__)

# Cached credential and token provider (lazy initialization)
_credential = None
_token_provider = None
_initialization_error = None


def _initialize_credential():
    """
    Initialize Azure credential with proper error handling.

    Returns:
        Tuple of (credential, token_provider, error_message)
    """
    global _credential, _token_provider, _initialization_error

    if _initialization_error:
        # Already tried and failed
        return _credential, _token_provider, _initialization_error

    if _credential is not None:
        # Already initialized successfully
        return _credential, _token_provider, None

    try:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider

        # Create credential - this will use:
        # 1. Managed Identity (in Container Apps)
        # 2. Azure CLI (local dev)
        # 3. Environment variables (if configured)
        _credential = DefaultAzureCredential()

        # Create token provider for Azure Cognitive Services scope
        _token_provider = get_bearer_token_provider(
            _credential,
            "https://cognitiveservices.azure.com/.default"
        )

        # Test the credential by getting a token (validates authentication)
        # This catches auth issues early rather than at first API call
        try:
            _credential.get_token("https://cognitiveservices.azure.com/.default")
            logger.debug("Azure credential initialized successfully")
        except Exception as token_error:
            # Credential created but can't get token - auth issue
            _initialization_error = _get_auth_error_message(token_error)
            logger.warning(f"Azure credential created but token acquisition failed: {_initialization_error}")
            # Still return the credential - it might work for some scenarios

        return _credential, _token_provider, None

    except ImportError:
        _initialization_error = (
            "azure-identity package not installed. "
            "Run: pip install azure-identity"
        )
        logger.error(_initialization_error)
        return None, None, _initialization_error

    except Exception as e:
        _initialization_error = _get_auth_error_message(e)
        logger.error(f"Failed to initialize Azure credential: {_initialization_error}")
        return None, None, _initialization_error


def _get_auth_error_message(error: Exception) -> str:
    """
    Create a helpful error message based on the authentication error.

    Args:
        error: The exception that occurred

    Returns:
        User-friendly error message with guidance
    """
    error_str = str(error).lower()

    if "managed identity" in error_str or "imds" in error_str:
        return (
            f"Managed Identity authentication failed. "
            f"If running in Azure, ensure the Container App has a system-assigned managed identity "
            f"and the 'Cognitive Services OpenAI User' role is assigned. "
            f"Error: {error}"
        )
    elif "cli" in error_str or "az login" in error_str:
        return (
            f"Azure CLI authentication failed. "
            f"For local development, run 'az login' to authenticate. "
            f"Error: {error}"
        )
    elif "tenant" in error_str or "subscription" in error_str:
        return (
            f"Azure tenant/subscription issue. "
            f"Ensure you're logged into the correct Azure tenant. "
            f"Try: az login --tenant <your-tenant-id>. "
            f"Error: {error}"
        )
    else:
        return (
            f"Azure authentication failed. "
            f"For local development: run 'az login'. "
            f"For Container Apps: ensure managed identity is configured with proper RBAC roles. "
            f"Error: {error}"
        )


def get_credential():
    """
    Get the DefaultAzureCredential instance.

    Returns:
        DefaultAzureCredential instance

    Raises:
        RuntimeError: If credential initialization failed
    """
    credential, _, error = _initialize_credential()

    if error and credential is None:
        raise RuntimeError(error)

    return credential


def get_token_provider() -> Callable[[], str]:
    """
    Get the token provider for Azure Cognitive Services.

    This is used with Azure OpenAI clients that accept azure_ad_token_provider parameter.

    Returns:
        Callable that returns bearer tokens

    Raises:
        RuntimeError: If credential initialization failed
    """
    _, token_provider, error = _initialize_credential()

    if error and token_provider is None:
        raise RuntimeError(error)

    return token_provider


def is_credential_available() -> bool:
    """
    Check if Azure credential is available without raising an exception.

    Returns:
        True if credential is available, False otherwise
    """
    credential, _, error = _initialize_credential()
    return credential is not None


def get_credential_error() -> Optional[str]:
    """
    Get the credential initialization error message, if any.

    Returns:
        Error message or None if credential initialized successfully
    """
    _, _, error = _initialize_credential()
    return error
