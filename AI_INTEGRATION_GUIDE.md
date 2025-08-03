# AI Integration Guide

## Overview

The Factory Automation System now includes AI-powered capabilities using GPT-4 and advanced embeddings. This guide explains how to use the new AI features.

## Key Features

### 1. AI-Powered Order Processing
- **Natural Language Understanding**: The AI understands complex order requests in natural language
- **Intelligent Item Extraction**: Automatically extracts quantities, specifications, and urgency
- **Context-Aware Matching**: Uses AI to understand variations in product descriptions

### 2. Enhanced Search
- **Query Understanding**: AI enhances search queries for better results
- **Semantic Matching**: Goes beyond keyword matching to understand intent
- **Multi-Modal Support**: Ready for image-based search (Qwen2.5VL integration pending)

### 3. AI Orchestrator
- **GPT-4 Powered**: Uses OpenAI's most advanced model for decision making
- **Multi-Step Reasoning**: Handles complex workflows automatically
- **Human-in-the-Loop**: Knows when to escalate for human approval

## Setup

1. **Environment Variables**
   ```bash
   # Add to your .env file
   OPENAI_API_KEY=your_openai_api_key_here
   ```

2. **Launch AI-Enhanced App**
   ```bash
   source .venv/bin/activate
   python launch_ai_app.py
   ```

3. **Access Dashboard**
   - Open browser to: http://localhost:7860
   - You'll see the AI status indicator at the top

## Usage Examples

### Example 1: Natural Language Order
```
Dear team,
We urgently need:
- 500 blue cotton tags for VH brand
- 300 Allen Solly main tags with gold print
- 200 Peter England formal tags

Please process ASAP for next week delivery.
```

The AI will:
1. Understand the urgency
2. Extract exact quantities and specifications
3. Match with inventory using semantic understanding
4. Provide confidence scores and recommendations

### Example 2: Complex Search
```
"I need sustainable tags for our eco-friendly line, preferably black or dark colors"
```

The AI enhances this to search for:
- FSC certified tags
- Sustainable materials
- Black/dark color variations
- Eco-friendly options

## Architecture

```
User Input → AI Orchestrator (GPT-4) → Specialized Agents
                    ↓
              Decision Making
                    ↓
         [Email Parser] [Inventory Matcher] [Order Processor]
                    ↓
              AI-Enhanced Results → User Interface
```

## API Costs

- **GPT-4**: ~$0.03 per 1K tokens
- **Average order processing**: ~$0.10-0.15
- **Monthly estimate** (50 orders/day): ~$120-190

## Current Limitations

1. **Visual Analysis**: Qwen2.5VL integration pending
2. **Payment OCR**: Not yet implemented
3. **Document Generation**: Coming soon
4. **Gmail Polling**: Manual trigger only (auto-polling pending)

## Troubleshooting

### AI Not Available
- Check OPENAI_API_KEY in .env
- Verify internet connection
- Check API quota/billing

### Low Confidence Scores
- AI needs more context
- Try more specific queries
- Check inventory data quality

### Slow Response
- First request loads models (30-60s)
- Subsequent requests are faster
- Consider GPU for embeddings

## Development

### Adding New AI Capabilities

1. **Update Orchestrator Instructions**
   ```python
   # In orchestrator_v2_agent.py
   ORCHESTRATOR_INSTRUCTIONS = """
   Your new capability description here...
   """
   ```

2. **Add Function Tools**
   ```python
   # Create new agent with AI capabilities
   class YourNewAgent(BaseAgent):
       async def process_with_ai(self, data):
           # Use OpenAI, Together.ai, etc.
   ```

3. **Wire to UI**
   ```python
   # In ai_bridge.py
   async def your_new_ai_function(self, input):
       # Bridge between UI and AI
   ```

## Best Practices

1. **Prompt Engineering**
   - Be specific in instructions
   - Provide examples in prompts
   - Use system messages for consistency

2. **Error Handling**
   - Always have fallbacks
   - Log AI responses for debugging
   - Handle rate limits gracefully

3. **Cost Management**
   - Cache frequent queries
   - Use smaller models when possible
   - Monitor usage via OpenAI dashboard

## Future Roadmap

- [ ] Qwen2.5VL for visual tag analysis
- [ ] Automatic Gmail polling with AI triage
- [ ] AI-generated quotations and emails
- [ ] Learning from user corrections
- [ ] Multi-language support
- [ ] Voice input/output

## Support

For issues or questions:
- Check logs in `factory_automation.log`
- Review AI responses in the UI
- Contact: github.com/samar-singh/factory-automation/issues