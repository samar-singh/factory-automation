# Configuration Guide

## Overview

The Factory Automation System uses a two-file configuration approach:

1. **`.env`** - For secrets and API keys (never commit this!)
2. **`config.yaml`** - For all other configuration options (safe to commit)

## Quick Start

1. **Copy the example files:**

   ```bash
   cp .env.example .env
   # config.yaml is already ready to use
   ```

2. **Add your API keys to `.env`:**

   ```bash
   # Edit .env and add your keys
   OPENAI_API_KEY=sk-...
   TOGETHER_API_KEY=...
   ```

3. **Adjust configuration in `config.yaml`:**

   ```yaml
   # Example: Enable AI orchestrator
   orchestrator:
     use_ai_version: true
   ```

## Configuration Precedence

Settings are loaded in this order (highest to lowest priority):

1. Environment variables
2. `.env` file
3. `config.yaml` file

This means you can override any config.yaml setting with an environment variable.

## Common Configuration Changes

### Enable AI Orchestrator (v2)

```yaml
# config.yaml
orchestrator:
  use_ai_version: true  # Switch from v1 to v2
```

### Enable A/B Testing

```yaml
# config.yaml
orchestrator:
  enable_comparison_logging: true
```

### Change Ports

```yaml
# config.yaml
app:
  port: 8080  # API port
  gradio_port: 7861  # Dashboard port
```

### Adjust Email Polling

```yaml
# config.yaml
email:
  poll_interval: 600  # 10 minutes instead of 5
  max_results: 100   # Fetch more emails per poll
```

### Enable Features

```yaml
# config.yaml
features:
  payment_processing: true
  ocr_enabled: true
  auto_approval: false  # Keep manual approval
```

## Accessing Configuration in Code

### Basic Usage

```python
from config.settings import settings

# Access direct settings
api_key = settings.openai_api_key
use_ai = settings.use_ai_orchestrator

# Access config.yaml sections
models = settings.get_model_config()
rag_config = settings.get_rag_config()
features = settings.get_feature_flags()
```

### Model Configuration

```python
models = settings.get_model_config()
orchestrator_model = models.get('orchestrator_model', 'gpt-4o')
vision_model = models.get('vision_model')
```

### Business Rules

```python
rules = settings.get_business_rules()
working_hours = rules.get('working_hours')
followup_days = rules.get('auto_followup_days', 7)
```

## Environment Variable Override

Any setting can be overridden via environment variable:

```bash
# Override config.yaml settings
export USE_AI_ORCHESTRATOR=true
export APP_PORT=9000
export LOG_LEVEL=DEBUG
```

## Security Best Practices

### DO Store in `.env`

- API keys (OpenAI, Together.ai, etc.)
- Database passwords
- OAuth client secrets
- Any sensitive credentials

### DO Store in `config.yaml`

- Ports and hostnames
- Feature flags
- Business rules
- Model names
- Timeouts and intervals

### NEVER

- Commit `.env` to git
- Put secrets in `config.yaml`
- Share API keys in logs

## Troubleshooting

### Settings not loading?

```python
# Debug settings
from config.settings import settings
print(settings.config)  # Shows loaded yaml
print(settings.model_dump())  # Shows all settings
```

### Check configuration

```bash
# Verify config.yaml is valid
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check which orchestrator is active
python -c "from config.settings import settings; print('AI Orchestrator:', settings.use_ai_orchestrator)"
```

### Common Issues

1. **Missing API key error**
   - Ensure `.env` has `OPENAI_API_KEY=sk-...`

2. **Config not updating**
   - Restart the application after changes
   - Check for typos in YAML

3. **Wrong orchestrator running**
   - Check `orchestrator.use_ai_version` in config.yaml
   - Verify no environment override exists

## Advanced Configuration

### Dynamic Reloading (Development)

```python
# Reload settings without restart
from importlib import reload
import config.settings
reload(config.settings)
```

### Custom Config Path

```python
# Use different config file
os.environ['CONFIG_PATH'] = '/path/to/custom-config.yaml'
```

### Validate Configuration

```python
# Check all required settings
from config.settings import settings

required = ['openai_api_key', 'database_url']
for key in required:
    if not getattr(settings, key):
        print(f"Missing required setting: {key}")
```
