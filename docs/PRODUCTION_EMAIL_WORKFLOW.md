# Production Email Workflow Documentation

## Overview
This document explains how the Factory Automation system handles emails and attachments in a production environment where it monitors a real Gmail inbox.

## Architecture Flow

```
Gmail Inbox → Gmail API → Download Attachments → Process with File Paths → Cleanup
     ↓            ↓                ↓                      ↓                    ↓
  New Email   Fetch via    Save to Disk         AI Processing          Delete Old Files
             Service Acct   /tmp/factory/       Order Extraction        After 7 days
```

## Why File Paths Instead of Base64?

### Problems with Base64 Approach:
1. **Memory Usage**: Base64 encoding increases data size by ~33%
2. **Context Limits**: Large attachments exceed GPT-4's context window
3. **Processing Overhead**: Constant encoding/decoding
4. **Data Corruption**: Padding issues can corrupt binary data
5. **Performance**: Slower processing of large files

### Benefits of File Path Approach:
1. **Efficiency**: Files are downloaded once and referenced multiple times
2. **Scalability**: Can handle large attachments (100MB+ PDFs, Excel files)
3. **Reliability**: No encoding/decoding errors
4. **AI-Friendly**: AI tools can read files directly when needed
5. **Caching**: Files can be reused if processing fails

## Production Workflow

### 1. Email Monitoring
```python
# Production orchestrator polls Gmail every 60 seconds
orchestrator = ProductionOrchestrator(
    chromadb_client=chromadb,
    gmail_credentials_path="path/to/service-account.json",
    attachment_storage_path="/var/factory/attachments",
    polling_interval=60
)
await orchestrator.start_email_monitoring()
```

### 2. Email Fetching
When the Gmail agent finds new emails:
```python
# GmailProductionAgent.fetch_unread_orders()
1. Query Gmail API for unread orders
2. For each email:
   - Extract metadata (subject, from, date)
   - Extract email body
   - Download attachments to disk
   - Return email data with file paths
```

### 3. Attachment Download Process
```python
# Attachments are saved to a structured directory:
/var/factory/attachments/
├── msg_12345_20250108_143022/
│   ├── order_details.xlsx
│   ├── invoice.pdf
│   └── product_image.jpg
├── msg_12346_20250108_144515/
│   └── purchase_order.pdf
```

Each email gets its own directory with timestamp for organization.

### 4. Processing with File Paths
```python
# Email data passed to orchestrator:
email_data = {
    'message_id': 'gmail_message_id',
    'subject': 'Order for Blue Tags',
    'from': 'customer@example.com',
    'body': 'Full email text...',
    'attachments': [
        {
            'filename': 'order_details.xlsx',
            'filepath': '/var/factory/attachments/msg_12345/order_details.xlsx',
            'mime_type': 'application/vnd.ms-excel',
            'size_bytes': 45678
        },
        {
            'filename': 'invoice.pdf',
            'filepath': '/var/factory/attachments/msg_12345/invoice.pdf',
            'mime_type': 'application/pdf',
            'size_bytes': 123456
        }
    ]
}
```

### 5. AI Processing
The orchestrator and order processor can now:
```python
# Read Excel directly from disk
df = pd.read_excel(attachment['filepath'])

# Process PDF without loading into memory
with pdfplumber.open(attachment['filepath']) as pdf:
    text = pdf.pages[0].extract_text()

# Pass image path to vision model
image_analysis = await vision_model.analyze(attachment['filepath'])
```

### 6. Automatic Cleanup
```python
# Old attachments are automatically deleted after 7 days
orchestrator.gmail_agent.cleanup_old_attachments(days_old=7)
```

## Deployment Configuration

### Required Environment Variables
```bash
# Gmail Service Account Credentials
export GMAIL_SERVICE_ACCOUNT_PATH="/path/to/service-account.json"

# Attachment Storage Directory
export ATTACHMENT_STORAGE_PATH="/var/factory_automation/attachments"

# OpenAI API Key
export OPENAI_API_KEY="sk-..."

# Optional: Override polling interval (seconds)
export EMAIL_POLL_INTERVAL=60
```

### Gmail Service Account Setup
1. Create a service account in Google Cloud Console
2. Enable Gmail API
3. Grant domain-wide delegation (for Google Workspace)
4. Download credentials JSON
5. Set appropriate scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.modify` (to mark as read)

### File System Requirements
```bash
# Create attachment directory with proper permissions
sudo mkdir -p /var/factory_automation/attachments
sudo chown -R app_user:app_group /var/factory_automation/attachments
sudo chmod 755 /var/factory_automation/attachments

# Ensure sufficient disk space (recommend 10GB minimum)
df -h /var/factory_automation/attachments
```

## Security Considerations

### 1. Attachment Scanning
```python
# Add virus scanning before processing
import clamd
cd = clamd.ClamdUnixSocket()
scan_result = cd.scan(attachment['filepath'])
if scan_result[attachment['filepath']][0] == 'ERROR':
    logger.error(f"Malware detected in {attachment['filename']}")
    os.remove(attachment['filepath'])
```

### 2. File Type Validation
```python
# Whitelist allowed file types
ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.pdf', '.jpg', '.png', '.csv'}
file_ext = Path(attachment['filename']).suffix.lower()
if file_ext not in ALLOWED_EXTENSIONS:
    logger.warning(f"Rejected file type: {file_ext}")
    continue
```

### 3. Size Limits
```python
# Enforce maximum file size (e.g., 50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
if attachment['size_bytes'] > MAX_FILE_SIZE:
    logger.warning(f"File too large: {attachment['filename']}")
    continue
```

## Monitoring & Logging

### Key Metrics to Track
1. **Email Processing Rate**: Emails processed per hour
2. **Attachment Storage**: Disk usage trends
3. **Processing Time**: Average time per email
4. **Error Rate**: Failed processing attempts
5. **Confidence Scores**: Distribution of AI confidence

### Example Monitoring Setup
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

emails_processed = Counter('factory_emails_processed_total', 'Total emails processed')
processing_time = Histogram('factory_email_processing_seconds', 'Email processing time')
attachment_storage = Gauge('factory_attachment_storage_bytes', 'Attachment storage usage')
```

## Troubleshooting

### Common Issues and Solutions

1. **"File not found" errors**
   - Check attachment directory permissions
   - Verify disk space available
   - Ensure cleanup isn't too aggressive

2. **Gmail API rate limits**
   - Increase polling interval
   - Implement exponential backoff
   - Use batch requests where possible

3. **Large attachments timing out**
   - Process attachments asynchronously
   - Implement chunked reading for large files
   - Consider using cloud storage for very large files

4. **Memory issues with many attachments**
   - Process emails sequentially, not in parallel
   - Clean up processed files immediately
   - Use streaming for large file processing

## Example Production Deployment

### Docker Compose Configuration
```yaml
version: '3.8'
services:
  factory-automation:
    image: factory-automation:latest
    environment:
      - GMAIL_SERVICE_ACCOUNT_PATH=/app/credentials/gmail.json
      - ATTACHMENT_STORAGE_PATH=/app/attachments
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./credentials:/app/credentials:ro
      - attachment-data:/app/attachments
    restart: unless-stopped

volumes:
  attachment-data:
    driver: local
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: factory-automation
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: orchestrator
        image: factory-automation:latest
        env:
        - name: ATTACHMENT_STORAGE_PATH
          value: /attachments
        volumeMounts:
        - name: attachments
          mountPath: /attachments
        - name: gmail-creds
          mountPath: /credentials
          readOnly: true
      volumes:
      - name: attachments
        persistentVolumeClaim:
          claimName: attachment-storage
      - name: gmail-creds
        secret:
          secretName: gmail-service-account
```

## Performance Benchmarks

### Typical Processing Times
- **Email fetch**: 100-500ms per email
- **Attachment download**: 1-5 seconds (depends on size)
- **Excel processing**: 200-500ms for typical order sheets
- **PDF extraction**: 100-300ms per page
- **AI extraction**: 2-5 seconds
- **Inventory search**: 100-200ms
- **Total per email**: 5-15 seconds

### Capacity Planning
- **Storage**: ~10MB per email with attachments
- **Memory**: 512MB baseline + 100MB per concurrent email
- **CPU**: 1 core can handle ~10 emails/minute
- **Network**: Minimal bandwidth, mainly API calls

## Conclusion

The file path approach provides a robust, scalable solution for handling email attachments in production. By downloading files once and referencing them by path, we avoid memory issues, encoding problems, and context limitations while maintaining high performance and reliability.