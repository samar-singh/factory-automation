#!/usr/bin/env python3
"""Test API keys and basic functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "factory_automation"))

import requests
from openai import OpenAI

from factory_automation.factory_config.settings import settings


def test_openai_api():
    """Test OpenAI API key."""
    print("Testing OpenAI API...")
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API key works!'"}],
            max_tokens=10,
        )
        print("✓ OpenAI API key is valid!")
        print(f"  Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"✗ OpenAI API key error: {str(e)}")
        return False


def test_together_api():
    """Test Together AI API key."""
    print("\nTesting Together AI API...")
    if not settings.together_api_key:
        print("✗ Together AI API key not configured")
        return False

    try:
        headers = {"Authorization": f"Bearer {settings.together_api_key}"}
        response = requests.get("https://api.together.xyz/models", headers=headers)
        if response.status_code == 200:
            print("✓ Together AI API key is valid!")
            return True
        else:
            print(f"✗ Together AI API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Together AI connection error: {str(e)}")
        return False


def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    print(f"✓ Environment: {settings.app_env}")
    print(f"✓ App port: {settings.app_port}")
    print(f"✓ Gradio port: {settings.gradio_port}")
    print(f"✓ Use AI Orchestrator: {settings.use_ai_orchestrator}")
    print(f"✓ ChromaDB directory: {settings.chroma_persist_directory}")

    # Check model config
    models = settings.get_model_config()
    print(f"✓ Orchestrator model: {models.get('orchestrator_model', 'Not configured')}")
    print(f"✓ Vision model: {models.get('vision_model', 'Not configured')}")

    return True


def main():
    """Run all tests."""
    print("Factory Automation API Key Tester")
    print("=" * 40)

    results = {
        "OpenAI": test_openai_api(),
        "Together AI": test_together_api(),
        "Configuration": test_configuration(),
    }

    print("\n" + "=" * 40)
    print("Summary:")
    for service, status in results.items():
        status_icon = "✓" if status else "✗"
        print(f"{status_icon} {service}")

    if all(results.values()):
        print("\nAll tests passed! Ready to proceed.")
        return 0
    else:
        print("\nSome tests failed. Please check your configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
