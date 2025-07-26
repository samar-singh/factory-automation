# Factory Price Tag Automation System - Complete Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to automate your friend's garment price tag manufacturing factory workflow using cutting-edge AI technologies. The system will automate email processing, order interpretation, inventory matching, and payment tracking while maintaining human oversight for critical decisions.

## System Overview

### Core Objectives
1. **Automate Email Processing**: Poll Gmail for order requests and payment updates
2. **Intelligent Order Understanding**: Use LLMs to interpret requests and extract key information
3. **Smart Inventory Matching**: Leverage multimodal RAG for accurate tag matching
4. **Human-in-the-Loop Approvals**: Maintain quality control through strategic human intervention
5. **Payment Tracking**: Automate UTR and cheque processing
6. **Real-time Dashboard**: Provide visibility into order pipeline and system status

### Key Technologies
- **OpenAI Agents SDK**: Production-ready framework for multi-agent orchestration
- **ChromaDB**: Free, open-source vector database for RAG
- **CLIP + Sentence Transformers**: Free multimodal embeddings
- **Gradio**: Interactive web dashboard
- **PostgreSQL**: Relational database for structured data
- **Docker**: Containerized deployment

## Detailed Architecture

### 1. Multi-Agent System Design

```python
# Agent Hierarchy
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator Agent                     │
│         (Routes requests to specialized agents)          │
└────────────────────┬────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┬─────────────┬────────────┐
      ▼              ▼              ▼             ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Email   │  │  Order   │  │Inventory │  │ Document │  │ Payment  │
│ Monitor  │  │Interpreter│  │ Matcher  │  │ Creator  │  │ Tracker  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

#### Agent Descriptions

**1. Orchestrator Agent**
- Central coordinator for all workflows
- Implements handoffs based on email content
- Maintains session context across interactions

**2. Email Monitor Agent**
- Polls Gmail API every 5 minutes
- Filters order-related emails
- Extracts attachments and metadata
- Classifies email intent (new order, payment, follow-up)

**3. Order Interpreter Agent**
- Processes email content with GPT-4
- Analyzes tag images with Qwen2.5VL72B
- Extracts: tag details, quantities, delivery requirements
- Handles multiple attachment formats

**4. Inventory Matcher Agent**
- Searches ChromaDB for similar tags
- Uses multimodal embeddings (text + image)
- Calculates similarity scores
- Returns ranked matches with confidence levels

**5. Document Creator Agent**
- Generates Pro-Forma Invoices
- Composes professional email responses
- Uses factory supervisor persona
- Maintains consistent communication style

**6. Payment Tracker Agent**
- Monitors payment confirmations
- Extracts UTR numbers from emails
- Processes cheque images with OCR
- Updates payment status in database

### 2. RAG System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   ChromaDB Vector Store                  │
├─────────────────────────────────────────────────────────┤
│  Collections:                                           │
│  - tag_inventory (multimodal embeddings)                │
│  - order_history (text embeddings)                      │
│  - customer_preferences (learned patterns)              │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Embedding Pipeline                      │
├─────────────────────────────────────────────────────────┤
│  Text: all-MiniLM-L6-v2 (384 dims)                     │
│  Image: CLIP ViT-B/32 (512 dims)                       │
│  Combined: Concatenated (896 dims)                      │
└─────────────────────────────────────────────────────────┘
```

### 3. Workflow Details

#### A. New Order Processing Flow

1. **Email Reception**
   ```
   Customer Email → Gmail API → Email Monitor Agent
   ```

2. **Content Extraction**
   ```
   Email Monitor → Extract attachments → Order Interpreter Agent
   ```

3. **Order Analysis**
   ```
   Order Interpreter → Parse requirements → Extract tag image → 
   Generate embeddings → Search ChromaDB
   ```

4. **Inventory Matching**
   ```
   Inventory Matcher → Similarity search → Filter by stock → 
   Rank results → Present to human
   ```

5. **Human Approval**
   ```
   Gradio Dashboard → Show matches → Get decision → 
   Update inventory → Create PI
   ```

6. **Response Generation**
   ```
   Document Creator → Generate PI → Compose email → 
   Send response → Log in database
   ```

#### B. Payment Processing Flow

1. **Payment Email Detection**
   ```
   Email with "payment"/"UTR"/"cheque" → Payment Tracker Agent
   ```

2. **Information Extraction**
   ```
   If UTR: Extract number from text
   If Cheque: OCR image → Extract details
   ```

3. **Verification**
   ```
   Match payment to order → Update status → 
   Notify dispatch team if complete
   ```

4. **Follow-up Management**
   ```
   Check payment age → If > 7 days → Send reminder → 
   Log follow-up → Escalate if needed
   ```

### 4. Database Schema

```sql
-- Main database structure
CREATE DATABASE factory_automation;

-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    pi_number VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    total_amount DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by VARCHAR(100),
    approval_timestamp TIMESTAMP
);

-- Order items table
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id),
    tag_code VARCHAR(50),
    description TEXT,
    size VARCHAR(50),
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    matched_inventory_id UUID,
    similarity_score FLOAT
);

-- Communications log
CREATE TABLE communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id),
    email_id VARCHAR(255) UNIQUE,
    thread_id VARCHAR(255),
    sender_email VARCHAR(255),
    subject TEXT,
    body TEXT,
    attachments JSONB,
    processed_at TIMESTAMP,
    agent_actions JSONB
);

-- Payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id),
    payment_type VARCHAR(50), -- 'UTR' or 'Cheque'
    reference_number VARCHAR(100),
    amount DECIMAL(10,2),
    payment_date DATE,
    verification_status VARCHAR(50),
    cheque_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent sessions for context
CREATE TABLE agent_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    conversation_history JSONB,
    last_agent VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory tracking (synced with ChromaDB)
CREATE TABLE inventory_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_code VARCHAR(50) UNIQUE,
    description TEXT,
    size VARCHAR(50),
    current_stock INTEGER,
    reserved_stock INTEGER,
    excel_source VARCHAR(255),
    row_index INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Implementation Code Structure

```
factory_automation/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── email_monitor.py
│   ├── order_interpreter.py
│   ├── inventory_matcher.py
│   ├── document_creator.py
│   └── payment_tracker.py
├── rag/
│   ├── __init__.py
│   ├── chromadb_client.py
│   ├── embeddings.py
│   └── search.py
├── utils/
│   ├── __init__.py
│   ├── gmail_client.py
│   ├── image_processor.py
│   ├── ocr_engine.py
│   └── excel_parser.py
├── database/
│   ├── __init__.py
│   ├── models.py
│   └── crud.py
├── ui/
│   ├── __init__.py
│   └── gradio_app.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── tests/
│   └── ...
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### 6. Key Implementation Details

#### A. Multimodal Search Implementation

```python
class MultimodalSearch:
    def __init__(self, chroma_client):
        self.client = chroma_client
        self.text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.clip_model, self.preprocess = clip.load("ViT-B/32")
        
    def search(self, image=None, text=None, k=10):
        embeddings = []
        
        if text:
            text_emb = self.text_encoder.encode(text)
            embeddings.append(text_emb)
            
        if image:
            image_emb = self.encode_image(image)
            embeddings.append(image_emb)
            
        # Combine embeddings
        if len(embeddings) > 1:
            combined = np.concatenate(embeddings)
        else:
            combined = embeddings[0]
            
        # Search ChromaDB
        results = self.client.query(
            query_embeddings=[combined.tolist()],
            n_results=k
        )
        
        return results
```

#### B. Agent Handoff Logic

```python
async def orchestrator_logic(context):
    email_type = context.get("email_type")
    
    if email_type == "new_order":
        # Extract order details
        order_data = await order_interpreter.run(context)
        
        # Find matches
        matches = await inventory_matcher.run(order_data)
        
        # Get human approval
        decision = await approval_coordinator.run(matches)
        
        # Create documents
        if decision["approved"]:
            await document_creator.run(decision)
            
    elif email_type == "payment":
        await payment_tracker.run(context)
```

### 7. Gradio Dashboard Features

```python
# Main dashboard sections
1. Order Pipeline View
   - Visual kanban board showing order stages
   - Click to view details
   - Drag to update status

2. Smart Search Interface
   - Upload tag image
   - Enter description
   - View similarity scores
   - Side-by-side comparison

3. Approval Queue
   - Pending decisions
   - Match confidence levels
   - Quick approve/reject buttons
   - Add notes feature

4. Payment Tracker
   - Outstanding payments grid
   - Age indicators (color-coded)
   - Quick follow-up actions
   - Payment history

5. Analytics Dashboard
   - Order volume trends
   - Payment collection metrics
   - Popular tag types
   - Customer insights
```

### 8. Deployment Strategy

#### Local Development
```bash
# Clone repository
git clone <repo-url>
cd factory_automation

# Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Start services
docker-compose up -d

# Run application
python main.py
```

#### Production Deployment
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: factory-automation:latest
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GMAIL_API_KEY=${GMAIL_API_KEY}
      - DATABASE_URL=postgresql://user:pass@postgres:5432/factory_db
    depends_on:
      - postgres
      - chromadb
      - redis
    ports:
      - "80:7860"
      
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "443:443"
```

### 9. Security Considerations

1. **API Key Management**
   - Use environment variables
   - Implement key rotation
   - Monitor usage limits

2. **Data Privacy**
   - Encrypt sensitive data at rest
   - Use HTTPS for all communications
   - Implement access controls

3. **Email Security**
   - OAuth2 for Gmail access
   - Rate limiting on API calls
   - Email validation

### 10. Monitoring & Maintenance

1. **System Monitoring**
   - Agent performance metrics
   - API usage tracking
   - Error logging and alerts

2. **Data Quality**
   - Regular embedding updates
   - Inventory synchronization
   - Search quality metrics

3. **User Feedback Loop**
   - Track approval patterns
   - Improve matching algorithms
   - Update agent instructions

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)
- Set up development environment
- Configure ChromaDB and PostgreSQL
- Implement basic agent structure
- Create Gmail integration

### Phase 2: Core Features (Weeks 3-4)
- Build email processing pipeline
- Implement multimodal RAG search
- Create inventory matching logic
- Develop OCR capabilities

### Phase 3: Agent Integration (Weeks 5-6)
- Connect all agents with handoffs
- Implement approval workflows
- Build document generation
- Add payment tracking

### Phase 4: UI & Testing (Weeks 7-8)
- Complete Gradio dashboard
- End-to-end testing
- Performance optimization
- User training

## Budget Estimation

### One-time Costs
- Development: 8 weeks
- Server setup: $0 (using existing infrastructure)
- Software licenses: $0 (all open source)

### Recurring Costs (Monthly)
- OpenAI API: ~$50-100 (depending on volume)
- Server hosting: ~$50 (if cloud deployed)
- Total: ~$100-150/month

## Success Metrics

1. **Efficiency Gains**
   - 90% reduction in manual email processing
   - 75% faster order response time
   - 95% accuracy in payment tracking

2. **Quality Improvements**
   - 99% accurate inventory matching
   - Zero missed follow-ups
   - Complete audit trail

3. **Business Impact**
   - Increased order throughput
   - Improved customer satisfaction
   - Better cash flow management

## Conclusion

This comprehensive system will transform your friend's factory operations by automating repetitive tasks while maintaining human oversight for critical decisions. The use of cutting-edge AI technologies with free, open-source tools ensures a cost-effective solution that can scale with the business.

The modular architecture allows for incremental implementation and easy maintenance, while the multi-agent design ensures each component can be optimized independently. With proper implementation, this system will significantly improve operational efficiency and customer satisfaction.