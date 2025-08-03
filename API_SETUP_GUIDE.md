# API Setup Guide for Factory Automation System

## 1. Gmail API Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it "Factory-Automation" and create

### Step 2: Enable Gmail API

1. In the project dashboard, go to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click on it and press "Enable"

### Step 3: Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Fill in:
   - Service account name: `factory-automation-gmail`
   - Service account ID: (auto-generated)
   - Description: Gmail access for factory automation
4. Click "Create and Continue"
5. Grant role: "Gmail API Admin"
6. Click "Done"

### Step 4: Generate Key

1. Click on the created service account
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose JSON format
5. Save the downloaded file as `gmail_credentials.json` in your project

### Step 5: Enable Domain-Wide Delegation (if using G Suite)

1. In service account details, click "Show Domain-Wide Delegation"
2. Enable "Enable G Suite Domain-wide Delegation"
3. Note the Client ID for admin console setup

## 2. OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create account
3. Navigate to API keys section
4. Click "Create new secret key"
5. Name it "factory-automation"
6. Copy the key immediately (you won't see it again)
7. Add to `.env` file:

   ```
   OPENAI_API_KEY=sk-...
   ```

## 3. Together.ai API Key (for Qwen2.5VL)

1. Go to [Together.ai](https://together.ai/)
2. Sign up or log in
3. Navigate to API Keys in dashboard
4. Create new API key
5. Copy the key
6. Add to `.env` file:

   ```
   TOGETHER_API_KEY=...
   ```

## 4. Environment Configuration

Create a `.env` file in your project root:

```bash
# API Keys
OPENAI_API_KEY=sk-...
TOGETHER_API_KEY=...

# Gmail Configuration
GMAIL_CREDENTIALS_PATH=./gmail_credentials.json
GMAIL_USER_EMAIL=your-email@company.com

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/factory_automation
CHROMADB_PATH=./chromadb_data

# Application Settings
DEBUG=True
LOG_LEVEL=INFO
```

## 5. Verify Setup

Run this verification script:

```python
# verify_setup.py
import os
from dotenv import load_dotenv
import openai
import litellm
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

def verify_apis():
    print("Verifying API configurations...")

    # Check OpenAI
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.models.list()
        print("✅ OpenAI API: Connected")
    except Exception as e:
        print(f"❌ OpenAI API: {e}")

    # Check Together.ai via LiteLLM
    try:
        litellm.api_key = os.getenv("TOGETHER_API_KEY")
        # Test with a simple completion
        response = litellm.completion(
            model="together_ai/Qwen/Qwen2.5-VL-72B-Instruct",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("✅ Together.ai API: Connected")
    except Exception as e:
        print(f"❌ Together.ai API: {e}")

    # Check Gmail
    try:
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GMAIL_CREDENTIALS_PATH"),
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        service = build('gmail', 'v1', credentials=credentials)
        print("✅ Gmail API: Credentials loaded")
    except Exception as e:
        print(f"❌ Gmail API: {e}")

if __name__ == "__main__":
    verify_apis()
```

## 6. Security Best Practices

1. **Never commit credentials to git**
   - Add to `.gitignore`:

     ```
     .env
     gmail_credentials.json
     *.key
     ```

2. **Use environment variables**
   - Always load from `.env` file
   - Never hardcode keys in code

3. **Rotate keys regularly**
   - Set calendar reminders
   - Update in production carefully

4. **Monitor usage**
   - Set up billing alerts
   - Track API usage metrics
