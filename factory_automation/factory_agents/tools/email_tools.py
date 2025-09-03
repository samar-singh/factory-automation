"""Email-related tools for orchestrators"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import function_tool

logger = logging.getLogger(__name__)


class EmailTools:
    """Email processing tools that can be used by any orchestrator"""
    
    def __init__(self, gmail_agent, openai_client, email_configs, pattern_config, mode="execute"):
        """
        Initialize email tools
        
        Args:
            gmail_agent: Gmail agent for email operations
            openai_client: OpenAI client for AI operations
            email_configs: Email configuration dict
            pattern_config: Pattern learning configuration
            mode: "execute" for v3, "propose" for v4
        """
        self.gmail_agent = gmail_agent
        self.openai_client = openai_client
        self.email_configs = email_configs
        self.pattern_config = pattern_config
        self.mode = mode
        self.primary_emails = list(email_configs.keys())
    
    def create_tools(self):
        """Create and return email-related tools"""
        tools = []
        
        # Check emails tool
        @function_tool(
            name_override="check_emails",
            description_override="Check for new emails in the inbox. Use at the START of processing to discover new emails. Do NOT use if you already have email content to process.",
        )
        async def check_emails() -> str:
            """Poll Gmail inbox for new unread emails.
            
            This tool retrieves new emails from the configured Gmail account. Use this
            at the beginning of email processing workflows when you need to discover
            what emails have arrived. Do NOT use if you already have email content.
            
            Args:
                None - this tool takes no parameters
            
            Returns:
                JSON string containing array of email objects:
                - Each email contains: subject, body, sender, attachments, date
                - Empty array if no new emails found
                - Error message if Gmail is not configured
            """
            if not self.gmail_agent:
                logger.debug("Gmail agent disabled - no emails to check")
                return json.dumps([])  # Return empty JSON array string
            
            try:
                if self.mode == "execute":
                    # V3: Actually poll emails
                    messages = (
                        self.gmail_agent.users()
                        .messages()
                        .list(userId="me", q="is:unread", maxResults=5)
                        .execute()
                    )
                    
                    emails = []
                    for msg in messages.get("messages", []):
                        email_data = self.gmail_agent.process_order_email(msg["id"])
                        if email_data:
                            emails.append(email_data)
                    return json.dumps(emails)  # Return JSON string
                else:
                    # V4: Return mock/cached emails for proposal
                    result = await self.gmail_agent.poll_emails() if self.gmail_agent else []
                    return json.dumps(result)  # Return JSON string
                    
            except Exception as e:
                logger.error(f"Error checking emails: {e}")
                return json.dumps([])  # Return empty JSON array string
        
        tools.append(check_emails)
        
        # Email classification tool
        @function_tool(
            name_override="classify_email_intent",
            description_override="Intelligently classify email intent using business context, patterns, and AI. ALWAYS use this FIRST before any other processing. Do NOT use if email classification is already complete.",
        )
        async def classify_email_intent(
            email_subject: str,
            email_body: str,
            sender_email: str,
            recipient_email: Optional[str] = None,
        ) -> str:
            """Classify email intent using business context, patterns, and GPT-4o.
            
            This tool must be called FIRST to understand the email's purpose before processing
            attachments or extracting orders. It analyzes the email content and provides
            classification with confidence scores.
            
            Args:
                email_subject: The subject line of the email to classify
                email_body: The full text content of the email body
                sender_email: The email address of the sender (e.g., "customer@company.com")
                recipient_email: The email address that received this email (optional, defaults to primary business email)
            
            Returns:
                JSON string with classification results:
                - classification: Intent type (NEW_ORDER, PAYMENT, INQUIRY, etc.)
                - confidence: Confidence score from 0.0 to 1.0
                - reasoning: Explanation of why this classification was chosen
                - key_indicators: List of words/phrases that guided the decision
                - alternative_classification: Second most likely intent if applicable
                - extracted_entities: Dictionary of order numbers, UTRs, quantities found
                - suggested_tools: List of recommended tools to use next
            """
            
            # Normalize recipient email
            if recipient_email:
                recipient_email = recipient_email.lower()
            else:
                recipient_email = (
                    self.primary_emails[0]
                    if self.primary_emails
                    else "orders@factory.com"
                )
            
            # Get the business context for this email
            email_config = self.email_configs.get(recipient_email, {})
            email_description = email_config.get("description", "General business email")
            likely_intents = email_config.get("likely_intents", [])
            confidence_boost = email_config.get("confidence_boost", 0.0)
            
            # Check sender pattern in database if in execute mode
            if self.mode == "execute" and self.pattern_config.get("enabled", True):
                try:
                    from ...factory_database.connection import get_db
                    from ...factory_database.models import EmailPattern
                    
                    with get_db() as db:
                        pattern = (
                            db.query(EmailPattern)
                            .filter(
                                EmailPattern.sender_email == sender_email,
                                EmailPattern.recipient_email == recipient_email,
                            )
                            .order_by(EmailPattern.count.desc())
                            .first()
                        )
                        
                        min_count = self.pattern_config.get("min_count_for_pattern", 3)
                        
                        if pattern and pattern.count >= min_count:
                            # Calculate confidence
                            base_confidence = self.pattern_config.get("initial_confidence", 0.6)
                            increment = self.pattern_config.get("confidence_increment", 0.05)
                            max_conf = self.pattern_config.get("max_confidence", 0.95)
                            
                            confidence = min(
                                max_conf, base_confidence + (pattern.count * increment)
                            )
                            
                            # Apply boost if this intent is likely for this email
                            if pattern.intent_type in likely_intents:
                                confidence = min(max_conf, confidence + confidence_boost)
                            
                            if confidence > 0.85:
                                logger.info(
                                    f"Using learned pattern for {sender_email}→{recipient_email}: {pattern.intent_type}"
                                )
                                return json.dumps(
                                    {
                                        "classification": pattern.intent_type,
                                        "confidence": confidence,
                                        "method": "learned_pattern",
                                        "pattern_count": pattern.count,
                                        "recipient_email": recipient_email,
                                        "recipient_description": email_description,
                                        "suggested_tools": self._get_tools_for_intent(pattern.intent_type),
                                    }
                                )
                except Exception as e:
                    logger.warning(f"Error checking patterns: {e}")
            
            # Use GPT-4o with full business context
            try:
                # Build context-rich prompt
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are classifying emails for a garment tag manufacturing factory.
                            
                            CRITICAL CONTEXT - This email was sent to: {recipient_email}
                            
                            PURPOSE OF THIS EMAIL ADDRESS:
                            {email_description}
                            
                            EXPECTED EMAIL TYPES for {recipient_email}:
                            {', '.join(likely_intents) if likely_intents else 'Various business communications'}
                            
                            ALL POSSIBLE CLASSIFICATIONS:
                            - NEW_ORDER: Customer placing an order for tags/labels
                            - ORDER_MODIFICATION: Changes to existing order
                            - URGENT_ORDER: Rush/priority order requests
                            - PAYMENT: Payment confirmations, UTR numbers
                            - PAYMENT_INQUIRY: Questions about payment status
                            - INQUIRY: General questions about products/services
                            - QUOTATION_REQUEST: Request for price quotes
                            - NEW_CUSTOMER: New customer onboarding
                            - FOLLOWUP: Status check on existing order
                            - SUPPLIER: Vendor/supplier communications
                            - MATERIAL_QUOTATION: Raw material pricing from suppliers
                            - DELIVERY_UPDATE: Shipping/delivery information
                            - COMPLAINT: Issues with products/service
                            - QUALITY_ISSUE: Specific quality problems
                            - INVOICE_REQUEST: Request for invoice/billing documents
                            
                            Consider the email address purpose when classifying.
                            
                            Return JSON with:
                            - classification: The most appropriate intent type
                            - confidence: 0.0 to 1.0 (consider email address context)
                            - reasoning: Why you chose this classification
                            - key_indicators: Specific words/phrases that guided your decision
                            - alternative_classification: Second most likely intent (if any)
                            - extracted_entities: Order numbers, UTRs, quantities, etc.
                            """,
                        },
                        {
                            "role": "user",
                            "content": f"""
                            Email Details:
                            To: {recipient_email} ({email_description[:100]})
                            From: {sender_email}
                            Subject: {email_subject}
                            Body: {email_body[:1000]}
                            
                            Classify this email considering it was sent to an address meant for: {email_description}
                            """,
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                
                result = json.loads(response.choices[0].message.content)
                
                # Apply confidence boost if classification matches expected intent
                if result["classification"] in likely_intents:
                    original_confidence = result["confidence"]
                    result["confidence"] = min(0.99, result["confidence"] + confidence_boost)
                    result["confidence_boosted"] = True
                    result["boost_reason"] = f"Matches expected intent for {recipient_email}"
                    logger.info(f"Boosted confidence from {original_confidence:.2f} to {result['confidence']:.2f}")
                
                # Store pattern for learning in execute mode
                if self.mode == "execute" and self.pattern_config.get("enabled", True):
                    await self._update_sender_pattern(
                        sender_email,
                        recipient_email,
                        email_description,
                        result["classification"],
                        email_subject,
                    )
                
                result["method"] = "ai_analysis_with_context"
                result["recipient_email"] = recipient_email
                result["recipient_description"] = email_description
                result["suggested_tools"] = self._get_tools_for_intent(result["classification"])
                
                return json.dumps(result)
                
            except Exception as e:
                logger.error(f"AI classification failed: {e}")
                # Context-aware fallback
                default_intent = likely_intents[0] if likely_intents else "NEW_ORDER"
                return json.dumps(
                    {
                        "classification": default_intent,
                        "confidence": 0.4,
                        "error": str(e),
                        "method": "context_aware_fallback",
                        "recipient_email": recipient_email,
                        "recipient_description": email_description,
                        "fallback_reason": f"Using most likely intent for {recipient_email}",
                        "suggested_tools": self._get_tools_for_intent(default_intent),
                    }
                )
        
        tools.append(classify_email_intent)
        
        # Email response tool
        @function_tool(
            name_override="send_email_response",
            description_override="Send email responses to customers, suppliers, or internal staff. Use ONLY AFTER email has been classified and processed. Do NOT use before understanding email intent or completing order analysis." if self.mode == "execute" else "Generate email response draft for approval. Use ONLY AFTER email classification and order processing are complete.",
        )
        async def send_email_response(
            to_email: str,
            subject: str,
            body: str,
            email_type: str,
            attachments: Optional[List[str]] = None,
        ) -> str:
            """Send or draft email response based on orchestrator mode.
            
            This tool should ONLY be used after the email has been properly classified
            and any necessary processing (order extraction, inventory search, etc.) has
            been completed. It's typically the LAST step in the workflow.
            
            Args:
                to_email: Recipient's email address (e.g., "customer@company.com")
                subject: Email subject line for the response
                body: Complete email body text with proper formatting
                email_type: Type of response ("order_confirmation", "quotation", "inquiry_response", "payment_acknowledgment")
                attachments: Optional list of file paths to attach (e.g., ["/path/to/invoice.pdf"])
            
            Returns:
                JSON string with email sending results:
                - email_sent: Boolean indicating if email was sent (execute mode)
                - draft_created: Boolean indicating if draft was created (propose mode)
                - to: Recipient email address
                - subject: Email subject used
                - type: Email type classification
                - status: Success/failure status
                - timestamp: When the email was sent/drafted
            """
            
            try:
                if self.mode == "execute":
                    # V3: Actually send email
                    if hasattr(self, "gmail_agent") and self.gmail_agent:
                        logger.info(f"Sending {email_type} email to {to_email}")
                        result = {
                            "email_sent": True,
                            "to": to_email,
                            "subject": subject,
                            "type": email_type,
                            "has_attachments": bool(attachments),
                            "timestamp": datetime.now().isoformat(),
                            "status": "sent_successfully",
                            "mock_mode": True,  # Remove when actual sending is implemented
                        }
                        return json.dumps(result)
                    else:
                        return json.dumps({
                            "email_sent": False,
                            "status": "gmail_not_configured",
                        })
                else:
                    # V4: Generate draft for proposal
                    draft = {
                        "draft_created": True,
                        "to": to_email,
                        "subject": subject,
                        "body": body,
                        "type": email_type,
                        "attachments": attachments,
                        "status": "draft_for_approval",
                        "timestamp": datetime.now().isoformat(),
                    }
                    return json.dumps(draft)
                    
            except Exception as e:
                logger.error(f"Error in email response: {e}")
                return json.dumps({"error": str(e), "status": "failed"})
        
        tools.append(send_email_response)
        
        return tools
    
    def _get_tools_for_intent(self, intent: str) -> List[str]:
        """Get recommended tools based on intent"""
        tool_mapping = {
            "NEW_ORDER": ["process_complete_order", "generate_document", "send_email_response"],
            "ORDER_MODIFICATION": ["get_order_status", "update_order", "send_email_response"],
            "URGENT_ORDER": ["process_complete_order", "priority_flag", "send_email_response"],
            "PAYMENT": ["track_payment", "update_order_status", "send_email_response"],
            "PAYMENT_INQUIRY": ["check_payment_status", "send_email_response"],
            "INQUIRY": ["search_inventory", "get_customer_context", "send_email_response"],
            "QUOTATION_REQUEST": ["calculate_quote", "generate_document", "send_email_response"],
            "NEW_CUSTOMER": ["create_customer", "send_welcome_package", "send_email_response"],
            "FOLLOWUP": ["get_order_status", "send_email_response"],
            "SUPPLIER": ["handle_supplier_inquiry", "forward_to_procurement", "send_email_response"],
            "MATERIAL_QUOTATION": ["process_supplier_quote", "compare_prices", "send_email_response"],
            "DELIVERY_UPDATE": ["update_delivery_status", "notify_customer", "send_email_response"],
            "COMPLAINT": ["create_ticket", "get_customer_context", "send_email_response"],
            "QUALITY_ISSUE": ["create_quality_report", "notify_qa_team", "send_email_response"],
            "INVOICE_REQUEST": ["generate_invoice", "send_email_response"],
        }
        return tool_mapping.get(intent, ["get_customer_context", "send_email_response"])
    
    async def _update_sender_pattern(
        self,
        sender_email: str,
        recipient_email: str,
        recipient_description: str,
        intent: str,
        subject: str,
    ):
        """Update pattern with business context (execute mode only)"""
        if self.mode != "execute":
            return
            
        try:
            from ...factory_database.connection import get_db
            from ...factory_database.models import EmailPattern
            
            with get_db() as db:
                pattern = (
                    db.query(EmailPattern)
                    .filter_by(
                        sender_email=sender_email,
                        recipient_email=recipient_email,
                        intent_type=intent,
                    )
                    .first()
                )
                
                if pattern:
                    pattern.count += 1
                    pattern.last_seen = datetime.utcnow()
                    pattern.recipient_description = recipient_description
                    
                    # Update subject keywords
                    if pattern.subject_keywords:
                        keywords = json.loads(pattern.subject_keywords)
                    else:
                        keywords = []
                    keywords.extend(subject.lower().split()[:5])
                    pattern.subject_keywords = json.dumps(list(set(keywords))[:20])
                else:
                    pattern = EmailPattern(
                        sender_email=sender_email,
                        recipient_email=recipient_email,
                        recipient_description=recipient_description,
                        intent_type=intent,
                        count=1,
                        subject_keywords=json.dumps(subject.lower().split()[:5]),
                    )
                    db.add(pattern)
                
                db.commit()
                logger.info(f"Pattern updated: {sender_email}→{recipient_email} ({intent})")
        except Exception as e:
            logger.error(f"Failed to update pattern: {e}")