# Factory Flow Automation System

## 🏭 Overview

An intelligent order processing system for a garment price tag manufacturing factory that automates email monitoring, order extraction, inventory matching, and human review workflows.

## ✨ Key Features

- **AI-Powered Order Processing**: Uses GPT-4 for intelligent order extraction
- **Enhanced RAG Search**: ChromaDB with Stella-400M embeddings + cross-encoder reranking
- **Human-in-the-Loop**: Confidence-based routing (90%+ auto-approve, <90% human review)
- **Real-time Dashboard**: Gradio-based interface for order processing and review
- **Mock Email System**: Built-in testing without Gmail configuration

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/samar-singh/factory-automation.git
cd factory-automation

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Run the system
python run_factory_automation.py
```

The system will start at http://127.0.0.1:7860

## 📁 Project Structure

```
factory-automation/
├── run_factory_automation.py          # Main entry point
├── factory_automation/
│   ├── factory_agents/                # Agent implementations
│   │   ├── orchestrator_with_human.py # Main orchestrator
│   │   ├── orchestrator_v3_agentic.py # Base agentic orchestrator
│   │   ├── order_processor_agent.py   # Order processing logic
│   │   ├── human_interaction_manager.py # Human review management
│   │   └── mock_gmail_agent.py        # Mock email for testing
│   ├── factory_database/              # Database layer
│   │   ├── vector_db.py              # ChromaDB client
│   │   ├── connection.py             # PostgreSQL connection
│   │   └── models.py                 # SQLAlchemy models
│   ├── factory_rag/                   # RAG components
│   │   ├── enhanced_search.py        # Enhanced search with reranking
│   │   ├── reranker.py              # Cross-encoder reranking
│   │   └── embeddings_config.py      # Embeddings management
│   ├── factory_ui/                    # User interface
│   │   └── human_review_interface_improved.py
│   └── factory_models/                # Data models
│       └── order_models.py           # Pydantic models
├── utilities/                          # Standalone utilities
│   ├── analyze_excel.py              # Excel analysis tool
│   └── extract_excel_images.py       # Image extraction from Excel
├── inventory/                          # Excel inventory files
└── mock_emails/                        # Test email data
```

## 🛠️ Utilities

Standalone utilities for data preparation (not part of main execution flow):

### Excel Processing
```bash
# Analyze Excel inventory files
python utilities/analyze_excel.py

# Extract images from Excel files
python utilities/extract_excel_images.py
```

### Inventory Ingestion
```bash
# Ingest inventory data into ChromaDB
python -c "from factory_automation.factory_rag.excel_ingestion import ExcelInventoryIngestion; \
          ingestion = ExcelInventoryIngestion(); \
          ingestion.ingest_inventory_folder('inventory')"
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
OPENAI_API_KEY=your_openai_api_key_here
TOGETHER_API_KEY=your_together_api_key_here  # Optional, for image processing
```

### config.yaml
- Embeddings settings
- Confidence thresholds
- Database connections
- API configurations

## 📊 System Architecture

```
Email → AI Extraction → RAG Search → Confidence Check → Auto-approve/Human Review
                            ↓
                     ChromaDB + Reranking
```

### Confidence Thresholds
- **90%+**: Auto-approve
- **60-90%**: Human review required
- **<60%**: Request clarification

## 🧪 Testing

The system includes a mock email agent for testing without Gmail setup:

1. Start the system: `python run_factory_automation.py`
2. Go to the "Order Processing" tab
3. Paste a test email (examples in mock_emails/)
4. Process and review results

## 📈 Performance

- **Search Accuracy**: 85-95% with reranking (was 65-75%)
- **False Positives**: Reduced by 60% with cross-encoder
- **Processing Time**: ~2-3 seconds per order
- **Auto-approval Rate**: ~40% of high-confidence orders

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🆘 Support

- GitHub Issues: https://github.com/samar-singh/factory-automation/issues
- Documentation: See /docs folder for detailed guides

## 🎯 Current Status

**Version**: 2.0  
**Stage**: Development  
**Core Features**: ✅ Complete  
**Production Ready**: 🚧 In Progress  

### Recent Updates
- Enhanced RAG with cross-encoder reranking
- Consolidated inventory agents
- Improved human review interface
- Safari compatibility fixes
- Code cleanup and optimization