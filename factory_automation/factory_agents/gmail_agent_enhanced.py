"""Enhanced Gmail Agent - Handles emails with attachments"""

from typing import Dict, List, Any, Optional, Tuple
from .base import BaseAgent
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import re
from datetime import datetime, timedelta
import logging
import os
import pandas as pd
from io import BytesIO
import PyPDF2
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

class GmailAgentEnhanced(BaseAgent):
    """Enhanced Gmail agent that processes emails and attachments"""
    
    def __init__(self, name: str = "GmailAgentEnhanced", credentials_path: str = "gmail_credentials.json"):
        instructions = """You are an enhanced Gmail agent that polls for order emails and extracts comprehensive information.
        You can:
        1. Connect to Gmail using service account credentials
        2. Search for emails matching order patterns
        3. Extract customer details, items, quantities from email body
        4. Process attachments: Excel files, PDFs, Images
        5. Extract structured data from attachments
        6. Combine email body and attachment data for complete order information"""
        
        super().__init__(name, instructions)
        self.credentials_path = credentials_path
        self.service = None
        self.user_email = None
        
    def initialize_service(self, delegated_email: str):
        """Initialize Gmail service with delegated credentials"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=[
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.modify'
                ]
            )
            
            delegated_credentials = credentials.with_subject(delegated_email)
            self.service = build('gmail', 'v1', credentials=delegated_credentials)
            self.user_email = delegated_email
            
            logger.info(f"Gmail service initialized for {delegated_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            return False
    
    def get_message_with_attachments(self, msg_id: str) -> Dict[str, Any]:
        """Get full message including attachments"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id
            ).execute()
            
            # Extract basic info
            result = self.extract_message_content(message)
            
            # Process attachments
            attachments = self._extract_attachments(message)
            result['attachments'] = attachments
            
            # Process attachment content
            result['attachment_data'] = []
            for attachment in attachments:
                att_data = self._process_attachment(
                    attachment['data'],
                    attachment['filename'],
                    attachment['mime_type']
                )
                if att_data:
                    result['attachment_data'].append(att_data)
            
            return result
            
        except HttpError as error:
            logger.error(f'Error getting message: {error}')
            return None
    
    def _extract_attachments(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachments from message"""
        attachments = []
        
        def process_parts(parts):
            for part in parts:
                filename = part.get('filename')
                
                if filename:
                    # Found an attachment
                    att_id = part['body'].get('attachmentId')
                    if att_id:
                        # Get attachment data
                        att = self.service.users().messages().attachments().get(
                            userId='me',
                            messageId=message['id'],
                            id=att_id
                        ).execute()
                        
                        attachments.append({
                            'filename': filename,
                            'mime_type': part.get('mimeType', ''),
                            'size': part['body'].get('size', 0),
                            'data': base64.urlsafe_b64decode(att['data'])
                        })
                
                # Recursively check for nested parts
                if 'parts' in part:
                    process_parts(part['parts'])
        
        # Start processing from payload
        payload = message.get('payload', {})
        if 'parts' in payload:
            process_parts(payload['parts'])
        
        return attachments
    
    def _process_attachment(self, data: bytes, filename: str, mime_type: str) -> Optional[Dict[str, Any]]:
        """Process attachment based on type"""
        
        result = {
            'filename': filename,
            'type': mime_type,
            'content': None,
            'extracted_data': {}
        }
        
        try:
            # Excel files
            if 'spreadsheet' in mime_type or filename.endswith(('.xlsx', '.xls')):
                result['content'] = self._process_excel(data, filename)
                
            # PDF files
            elif 'pdf' in mime_type or filename.endswith('.pdf'):
                result['content'] = self._process_pdf(data)
                
            # Image files
            elif 'image' in mime_type or filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                result['content'] = self._process_image(data)
                
            # Text files
            elif 'text' in mime_type or filename.endswith(('.txt', '.csv')):
                result['content'] = data.decode('utf-8', errors='ignore')
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing attachment {filename}: {e}")
            return None
    
    def _process_excel(self, data: bytes, filename: str) -> Dict[str, Any]:
        """Extract data from Excel files"""
        try:
            # Read Excel file from bytes
            df = pd.read_excel(BytesIO(data))
            
            # Extract order information
            extracted = {
                'type': 'excel',
                'filename': filename,
                'rows': len(df),
                'columns': list(df.columns),
                'data': []
            }
            
            # Look for order-related columns
            order_columns = ['item', 'product', 'description', 'quantity', 'qty', 'code', 'sku']
            relevant_cols = [col for col in df.columns if any(oc in col.lower() for oc in order_columns)]
            
            if relevant_cols:
                # Extract relevant data
                for _, row in df.iterrows():
                    item_data = {}
                    for col in relevant_cols:
                        if pd.notna(row[col]):
                            item_data[col] = str(row[col])
                    if item_data:
                        extracted['data'].append(item_data)
            else:
                # If no specific columns found, get first 10 rows
                extracted['data'] = df.head(10).to_dict('records')
            
            logger.info(f"Extracted {len(extracted['data'])} items from Excel")
            return extracted
            
        except Exception as e:
            logger.error(f"Error processing Excel: {e}")
            return {'type': 'excel', 'error': str(e)}
    
    def _process_pdf(self, data: bytes) -> Dict[str, Any]:
        """Extract text from PDF files"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(data))
            
            extracted = {
                'type': 'pdf',
                'pages': len(pdf_reader.pages),
                'text': []
            }
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text.strip():
                    extracted['text'].append({
                        'page': page_num + 1,
                        'content': text
                    })
            
            # Try to extract order information from text
            all_text = ' '.join([p['content'] for p in extracted['text']])
            extracted['order_items'] = self._extract_items(all_text)
            extracted['quantities'] = self._extract_quantities(all_text)
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return {'type': 'pdf', 'error': str(e)}
    
    def _process_image(self, data: bytes) -> Dict[str, Any]:
        """Extract text from images using OCR"""
        try:
            # Open image
            image = Image.open(BytesIO(data))
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            extracted = {
                'type': 'image',
                'size': image.size,
                'mode': image.mode,
                'text': text
            }
            
            # Try to extract order information
            if text:
                extracted['order_items'] = self._extract_items(text)
                extracted['quantities'] = self._extract_quantities(text)
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return {'type': 'image', 'error': str(e)}
    
    def extract_complete_order(self, email_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order details from email and all attachments"""
        
        # Start with email body extraction
        order = self.extract_order_details(email_content)
        
        # Enhance with attachment data
        if email_content.get('attachment_data'):
            order['has_attachments'] = True
            order['attachment_items'] = []
            
            for att_data in email_content['attachment_data']:
                if att_data['type'] == 'excel' and att_data.get('content', {}).get('data'):
                    # Add Excel items
                    for item in att_data['content']['data']:
                        order['attachment_items'].append({
                            'source': att_data['filename'],
                            'type': 'excel',
                            'data': item
                        })
                
                elif att_data['type'] in ['pdf', 'image']:
                    # Add extracted items from PDF/images
                    if att_data.get('content', {}).get('order_items'):
                        for item in att_data['content']['order_items']:
                            order['attachment_items'].append({
                                'source': att_data['filename'],
                                'type': att_data['type'],
                                'item': item
                            })
        
        # Combine all items
        order['all_items'] = order.get('items', [])
        if order.get('attachment_items'):
            # Add items from attachments
            for att_item in order['attachment_items']:
                if att_item['type'] == 'excel':
                    # Format Excel data as item description
                    item_desc = ' '.join([f"{k}: {v}" for k, v in att_item['data'].items()])
                    order['all_items'].append(item_desc)
                else:
                    order['all_items'].append(att_item.get('item', ''))
        
        return order
    
    def process_order_email(self, msg_id: str) -> Dict[str, Any]:
        """Process a complete order email with attachments"""
        
        # Get message with attachments
        message_data = self.get_message_with_attachments(msg_id)
        
        if not message_data:
            return None
        
        # Extract complete order
        order = self.extract_complete_order(message_data)
        
        # Add summary
        order['summary'] = {
            'total_items_in_body': len(order.get('items', [])),
            'total_items_in_attachments': len(order.get('attachment_items', [])),
            'total_unique_items': len(set(order.get('all_items', []))),
            'has_excel': any(a['type'] == 'excel' for a in message_data.get('attachment_data', [])),
            'has_pdf': any(a['type'] == 'pdf' for a in message_data.get('attachment_data', [])),
            'has_images': any(a['type'] == 'image' for a in message_data.get('attachment_data', []))
        }
        
        return order
    
    # Include all the previous methods from gmail_agent.py
    def extract_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant content from Gmail message"""
        headers = {}
        for header in message['payload'].get('headers', []):
            headers[header['name']] = header['value']
        
        body = self._extract_body(message['payload'])
        
        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'body': body,
            'snippet': message.get('snippet', '')
        }
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Recursively extract body from email payload"""
        body = ''
        
        if 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            return body
        
        if 'parts' in payload:
            for part in payload['parts']:
                part_body = self._extract_body(part)
                if part_body:
                    body += part_body + '\n'
        
        return body
    
    def _extract_items(self, text: str) -> List[str]:
        """Extract item descriptions from text"""
        items = []
        
        patterns = [
            r'(?:need|require|order|want)\s+(.+?tags?)',
            r'(\w+\s+\w+\s+tags?)',
            r'tags?\s+for\s+(.+?)(?:\.|,|\n)',
            r'(\w+\s+(?:SOLLY|ENGLAND|MYNTRA|LIFESTYLE)\s+.+?)(?:\.|,|\n|$)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            items.extend(matches)
        
        cleaned_items = []
        for item in items:
            cleaned = ' '.join(item.split())
            if len(cleaned) > 5 and cleaned not in cleaned_items:
                cleaned_items.append(cleaned)
        
        return cleaned_items[:10]
    
    def _extract_quantities(self, text: str) -> Dict[str, int]:
        """Extract quantities from text"""
        quantities = {}
        
        patterns = [
            r'(\d+)\s*(?:pcs?|pieces?|units?|nos?|tags?)',
            r'quantity[:\s]+(\d+)',
            r'qty[:\s]+(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                qty = int(match) if isinstance(match, str) else int(match[0])
                if 0 < qty < 10000:
                    quantities[f'quantity_{len(quantities)+1}'] = qty
        
        return quantities
    
    def extract_order_details(self, email_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order details from email content"""
        body = email_content['body']
        subject = email_content['subject']
        
        customer_name = self._extract_customer_name(email_content['from'])
        items = self._extract_items(body)
        quantities = self._extract_quantities(body)
        urgency = self._extract_urgency(body)
        
        return {
            'email_id': email_content['id'],
            'customer_name': customer_name,
            'customer_email': email_content['from'],
            'subject': subject,
            'items': items,
            'quantities': quantities,
            'urgency': urgency,
            'raw_body': body[:500] + '...' if len(body) > 500 else body,
            'date': email_content['date']
        }
    
    def _extract_customer_name(self, from_field: str) -> str:
        """Extract customer name from From field"""
        match = re.match(r'"?([^"<]+)"?\s*<?([^>]+)>?', from_field)
        if match:
            return match.group(1).strip()
        return from_field.split('@')[0]
    
    def _extract_urgency(self, body: str) -> str:
        """Determine urgency level from email content"""
        urgent_keywords = ['urgent', 'asap', 'immediately', 'today', 'tomorrow']
        moderate_keywords = ['soon', 'week', 'days']
        
        body_lower = body.lower()
        
        for keyword in urgent_keywords:
            if keyword in body_lower:
                return 'HIGH'
        
        for keyword in moderate_keywords:
            if keyword in body_lower:
                return 'MEDIUM'
        
        return 'NORMAL'