"""
Proposal Engine for Orchestrator Action Proposal System
Generates comprehensive workflow proposals for human review
"""

import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from factory_automation.factory_models.workflow_models import (
    WorkflowType,
    ActionType,
    RiskLevel,
    CustomerTier,
    ProposedWorkflow,
    ProposedAction,
    AlternativeAction,
    RiskAssessment,
    WorkflowAnalysis,
    EmailContent,
    DatabaseOperation
)
from factory_automation.factory_models.order_models import ExtractedOrder, CustomerInfo, OrderItem
from factory_automation.factory_database.models import Customer as DBCustomer

logger = logging.getLogger(__name__)


class ProposalEngine:
    """
    Engine for generating comprehensive workflow proposals
    Analyzes emails and creates complete action plans for human review
    """
    
    def __init__(self):
        self.workflow_templates = self._load_workflow_templates()
        
    def generate_workflow_proposal(
        self,
        email_data: Dict[str, Any],
        order_data: Optional[ExtractedOrder] = None,
        inventory_matches: List[Dict[str, Any]] = None,
        customer_data: Optional[Dict[str, Any]] = None
    ) -> ProposedWorkflow:
        """
        Generate a comprehensive workflow proposal based on email analysis
        
        Args:
            email_data: Parsed email information
            order_data: Extracted order details if available
            inventory_matches: Matching inventory items found
            customer_data: Customer history and context
            
        Returns:
            ProposedWorkflow: Complete workflow proposal for review
        """
        # Perform comprehensive analysis
        analysis = self._analyze_email_context(
            email_data, order_data, inventory_matches, customer_data
        )
        
        # Determine workflow type
        workflow_type = self._determine_workflow_type(analysis)
        
        # Get customer tier
        customer_tier = self._determine_customer_tier(customer_data)
        
        # Generate workflow ID
        workflow_id = f"WF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        
        # Build action sequence based on workflow type
        proposed_actions = self._build_action_sequence(
            workflow_type, analysis, order_data, inventory_matches
        )
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(proposed_actions, analysis)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            workflow_type, analysis, proposed_actions, customer_tier
        )
        
        # Identify alternatives
        alternatives = self._identify_alternatives(workflow_type, analysis)
        
        # Assess risks
        risks = self._assess_risks(workflow_type, analysis, proposed_actions)
        
        # Generate email content
        email_content = self._generate_email_content(
            workflow_type, analysis, customer_data, order_data, inventory_matches
        )
        
        # Estimate value if applicable
        estimated_value = self._estimate_order_value(order_data, inventory_matches)
        
        # Create the workflow proposal
        workflow = ProposedWorkflow(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            confidence=overall_confidence,
            customer_tier=customer_tier,
            estimated_value=estimated_value,
            analysis=analysis,
            proposed_actions=proposed_actions,
            reasoning=reasoning,
            alternatives=alternatives,
            risks=risks,
            email_content=email_content,
            documents_to_generate=self._determine_documents_needed(workflow_type)
        )
        
        logger.info(f"Generated workflow proposal {workflow_id} with {len(proposed_actions)} actions")
        return workflow
    
    def _analyze_email_context(
        self,
        email_data: Dict[str, Any],
        order_data: Optional[ExtractedOrder],
        inventory_matches: List[Dict[str, Any]],
        customer_data: Optional[Dict[str, Any]]
    ) -> WorkflowAnalysis:
        """Perform comprehensive analysis of the email and context"""
        
        # Classify the email
        email_classification = self._classify_email(email_data)
        
        # Build customer context
        customer_context = self._build_customer_context(customer_data, email_data)
        
        # Calculate confidence metrics
        confidence_metrics = self._calculate_confidence_metrics(
            email_classification, inventory_matches, customer_context
        )
        
        # Extract requirements
        extracted_requirements = self._extract_requirements(email_data, order_data)
        
        # Initial risk assessment
        risk_assessment = self._initial_risk_assessment(
            email_classification, customer_context, inventory_matches
        )
        
        return WorkflowAnalysis(
            email_classification=email_classification,
            customer_context=customer_context,
            inventory_matches=inventory_matches or [],
            confidence_metrics=confidence_metrics,
            risk_assessment=risk_assessment,
            extracted_requirements=extracted_requirements
        )
    
    def _determine_workflow_type(self, analysis: WorkflowAnalysis) -> WorkflowType:
        """Determine the appropriate workflow type based on analysis"""
        classification = analysis.email_classification.lower()
        
        workflow_mapping = {
            "new_order": WorkflowType.NEW_ORDER,
            "order_inquiry": WorkflowType.ORDER_CLARIFICATION,
            "payment": WorkflowType.PAYMENT_PROCESSING,
            "inventory_check": WorkflowType.INVENTORY_INQUIRY,
            "complaint": WorkflowType.COMPLAINT_HANDLING,
            "modification": WorkflowType.ORDER_MODIFICATION,
            "cancellation": WorkflowType.ORDER_CANCELLATION,
            "quotation": WorkflowType.QUOTATION_REQUEST,
            "follow_up": WorkflowType.FOLLOW_UP
        }
        
        for key, workflow_type in workflow_mapping.items():
            if key in classification:
                return workflow_type
        
        return WorkflowType.CUSTOMER_SERVICE
    
    def _determine_customer_tier(self, customer_data: Optional[Dict[str, Any]]) -> CustomerTier:
        """Determine customer tier based on history"""
        if not customer_data:
            return CustomerTier.NEW
        
        order_count = customer_data.get("order_count", 0)
        total_value = customer_data.get("total_value", 0)
        days_since_first_order = customer_data.get("days_since_first_order", 0)
        
        if order_count == 0:
            return CustomerTier.NEW
        elif order_count > 20 or total_value > 100000:
            return CustomerTier.VIP
        elif order_count > 10 or total_value > 50000:
            return CustomerTier.PREMIUM
        elif order_count > 3:
            return CustomerTier.REGULAR
        elif days_since_first_order > 180:
            return CustomerTier.INACTIVE
        else:
            return CustomerTier.NEW
    
    def _build_action_sequence(
        self,
        workflow_type: WorkflowType,
        analysis: WorkflowAnalysis,
        order_data: Optional[ExtractedOrder],
        inventory_matches: List[Dict[str, Any]]
    ) -> List[ProposedAction]:
        """Build the sequence of actions for the workflow"""
        actions = []
        step = 1
        
        if workflow_type == WorkflowType.NEW_ORDER:
            # Validate inventory
            if inventory_matches:
                actions.append(self._create_inventory_validation_action(
                    step, inventory_matches, order_data
                ))
                step += 1
            
            # Calculate pricing
            actions.append(self._create_pricing_calculation_action(
                step, order_data, inventory_matches
            ))
            step += 1
            
            # Generate quotation
            actions.append(self._create_quotation_generation_action(
                step, order_data
            ))
            step += 1
            
            # Compose email
            actions.append(self._create_email_composition_action(
                step, workflow_type
            ))
            step += 1
            
            # Update database
            actions.append(self._create_database_update_action(
                step, workflow_type, order_data
            ))
            step += 1
            
            # Schedule follow-up
            actions.append(self._create_followup_action(step))
            
        elif workflow_type == WorkflowType.ORDER_CLARIFICATION:
            # Request information
            actions.append(ProposedAction(
                step=step,
                action=ActionType.REQUEST_INFORMATION,
                details="Request clarification on order specifications",
                confidence=0.85,
                risk=RiskLevel.LOW,
                data={"questions": self._generate_clarification_questions(analysis)}
            ))
            step += 1
            
            # Send catalog if needed
            if analysis.confidence_metrics.get("match_confidence", 0) < 0.5:
                actions.append(ProposedAction(
                    step=step,
                    action=ActionType.SEND_CATALOG,
                    details="Send product catalog for reference",
                    confidence=0.9,
                    risk=RiskLevel.LOW,
                    data={"catalog_type": "full"}
                ))
                step += 1
            
            # Compose email
            actions.append(self._create_email_composition_action(
                step, workflow_type
            ))
            
        elif workflow_type == WorkflowType.PAYMENT_PROCESSING:
            # Update payment status
            actions.append(ProposedAction(
                step=step,
                action=ActionType.UPDATE_PAYMENT,
                details="Record payment details in system",
                confidence=0.95,
                risk=RiskLevel.MEDIUM,
                data={"payment_info": analysis.extracted_requirements.get("payment_details", {})}
            ))
            step += 1
            
            # Generate invoice if needed
            if analysis.extracted_requirements.get("needs_invoice"):
                actions.append(ProposedAction(
                    step=step,
                    action=ActionType.GENERATE_INVOICE,
                    details="Generate formal invoice for payment",
                    confidence=0.9,
                    risk=RiskLevel.LOW,
                    data={}
                ))
                step += 1
            
            # Update order status
            actions.append(ProposedAction(
                step=step,
                action=ActionType.UPDATE_DATABASE,
                details="Update order status to paid",
                confidence=0.95,
                risk=RiskLevel.LOW,
                data={"status": "paid"}
            ))
        
        return actions
    
    def _create_inventory_validation_action(
        self,
        step: int,
        inventory_matches: List[Dict[str, Any]],
        order_data: Optional[ExtractedOrder]
    ) -> ProposedAction:
        """Create inventory validation action"""
        total_available = sum(m.get("quantity", 0) for m in inventory_matches)
        required = order_data.items[0].quantity_ordered if order_data and order_data.items else 0
        sufficient = total_available >= required
        
        return ProposedAction(
            step=step,
            action=ActionType.VALIDATE_INVENTORY,
            details=f"Check availability of {required} items",
            confidence=0.92 if sufficient else 0.6,
            risk=RiskLevel.LOW if sufficient else RiskLevel.MEDIUM,
            data={
                "current_stock": total_available,
                "required": required,
                "sufficient": sufficient,
                "items": [m.get("tag_code") for m in inventory_matches[:5]]
            }
        )
    
    def _create_pricing_calculation_action(
        self,
        step: int,
        order_data: Optional[ExtractedOrder],
        inventory_matches: List[Dict[str, Any]]
    ) -> ProposedAction:
        """Create pricing calculation action"""
        quantity = order_data.items[0].quantity_ordered if order_data and order_data.items else 0
        unit_price = 12  # Default price
        
        # Apply bulk discount
        discount = 0
        if quantity > 1000:
            discount = 0.1
        elif quantity > 500:
            discount = 0.05
        
        subtotal = quantity * unit_price
        total = subtotal * (1 - discount)
        
        return ProposedAction(
            step=step,
            action=ActionType.CALCULATE_PRICING,
            details=f"Calculate quote for {quantity} items",
            confidence=0.88,
            risk=RiskLevel.MEDIUM,
            data={
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": subtotal,
                "discount": f"{discount*100}%" if discount else "None",
                "total": total
            }
        )
    
    def _create_quotation_generation_action(
        self,
        step: int,
        order_data: Optional[ExtractedOrder]
    ) -> ProposedAction:
        """Create quotation generation action"""
        quote_id = f"QUO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}"
        
        return ProposedAction(
            step=step,
            action=ActionType.GENERATE_QUOTATION,
            details=f"Create PDF quotation {quote_id}",
            confidence=0.95,
            risk=RiskLevel.LOW,
            content="[Quotation content will be generated]",
            editable=True,
            preview_url=f"/preview/quotation/{quote_id}",
            data={"quotation_id": quote_id}
        )
    
    def _create_email_composition_action(
        self,
        step: int,
        workflow_type: WorkflowType
    ) -> ProposedAction:
        """Create email composition action"""
        return ProposedAction(
            step=step,
            action=ActionType.COMPOSE_EMAIL,
            details="Send response email to customer",
            confidence=0.9,
            risk=RiskLevel.LOW,
            content={
                "subject": f"Re: {workflow_type.value.replace('_', ' ').title()}",
                "body": "[Email content will be generated based on context]",
                "attachments": []
            },
            editable=True
        )
    
    def _create_database_update_action(
        self,
        step: int,
        workflow_type: WorkflowType,
        order_data: Optional[ExtractedOrder]
    ) -> ProposedAction:
        """Create database update action"""
        operations = []
        
        if workflow_type == WorkflowType.NEW_ORDER:
            operations.append(DatabaseOperation(
                type="create_order",
                table="orders",
                data={"status": "pending", "created_at": datetime.now().isoformat()}
            ))
            
            operations.append(DatabaseOperation(
                type="reserve_inventory",
                table="inventory",
                data={"reserved": True}
            ))
        
        return ProposedAction(
            step=step,
            action=ActionType.UPDATE_DATABASE,
            details="Update system databases",
            confidence=0.95,
            risk=RiskLevel.MEDIUM,
            database_operations=operations,
            data={"operation_count": len(operations)}
        )
    
    def _create_followup_action(self, step: int) -> ProposedAction:
        """Create follow-up scheduling action"""
        followup_date = datetime.now() + timedelta(days=3)
        
        return ProposedAction(
            step=step,
            action=ActionType.SCHEDULE_FOLLOWUP,
            details="Schedule automatic follow-up if no response",
            confidence=0.85,
            risk=RiskLevel.LOW,
            data={
                "date": followup_date.isoformat(),
                "type": "email_reminder",
                "message": "Follow up on quotation"
            }
        )
    
    def _calculate_overall_confidence(
        self,
        actions: List[ProposedAction],
        analysis: WorkflowAnalysis
    ) -> float:
        """Calculate overall workflow confidence"""
        if not actions:
            return 0.0
        
        # Weight actions by risk level
        weights = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 1.5,
            RiskLevel.HIGH: 2.0,
            RiskLevel.CRITICAL: 3.0
        }
        
        total_weighted_confidence = sum(
            action.confidence * weights[action.risk] for action in actions
        )
        total_weight = sum(weights[action.risk] for action in actions)
        
        if total_weight == 0:
            return 0.0
        
        return total_weighted_confidence / total_weight
    
    def _generate_reasoning(
        self,
        workflow_type: WorkflowType,
        analysis: WorkflowAnalysis,
        actions: List[ProposedAction],
        customer_tier: CustomerTier
    ) -> str:
        """Generate explanation for the proposed workflow"""
        reasoning_parts = []
        
        # Add customer context
        tier_descriptions = {
            CustomerTier.VIP: "VIP customer with extensive order history",
            CustomerTier.PREMIUM: "Premium tier customer with excellent payment history",
            CustomerTier.REGULAR: "Regular customer with good standing",
            CustomerTier.NEW: "New customer requiring standard processing",
            CustomerTier.INACTIVE: "Inactive customer, may need re-engagement"
        }
        reasoning_parts.append(f"Customer is classified as {tier_descriptions[customer_tier]}.")
        
        # Add workflow justification
        if workflow_type == WorkflowType.NEW_ORDER:
            if analysis.inventory_matches:
                reasoning_parts.append(
                    f"Found {len(analysis.inventory_matches)} matching inventory items."
                )
            reasoning_parts.append("Standard new order workflow initiated.")
        elif workflow_type == WorkflowType.ORDER_CLARIFICATION:
            reasoning_parts.append(
                "Order details need clarification before processing can continue."
            )
        
        # Add confidence note
        avg_confidence = sum(a.confidence for a in actions) / len(actions) if actions else 0
        if avg_confidence > 0.8:
            reasoning_parts.append("High confidence in proposed actions.")
        elif avg_confidence > 0.6:
            reasoning_parts.append("Moderate confidence, human review recommended.")
        else:
            reasoning_parts.append("Low confidence, careful review required.")
        
        return " ".join(reasoning_parts)
    
    def _identify_alternatives(
        self,
        workflow_type: WorkflowType,
        analysis: WorkflowAnalysis
    ) -> List[AlternativeAction]:
        """Identify alternative actions that could be taken"""
        alternatives = []
        
        # Common alternatives
        if not analysis.extracted_requirements.get("delivery_date"):
            alternatives.append(AlternativeAction(
                action="request_delivery_timeline",
                reason="Email didn't specify urgency or delivery requirements",
                confidence=0.7,
                impact="Could affect order prioritization"
            ))
        
        if workflow_type == WorkflowType.NEW_ORDER:
            if analysis.confidence_metrics.get("match_confidence", 0) < 0.8:
                alternatives.append(AlternativeAction(
                    action="suggest_similar_items",
                    reason="Exact matches may not be available",
                    confidence=0.6,
                    impact="Could increase conversion rate"
                ))
            
            customer_tier = analysis.customer_context.get("tier")
            if customer_tier in ["premium", "vip"]:
                alternatives.append(AlternativeAction(
                    action="offer_express_processing",
                    reason="Premium customer might need rush delivery",
                    confidence=0.5,
                    impact="Could improve customer satisfaction"
                ))
        
        return alternatives
    
    def _assess_risks(
        self,
        workflow_type: WorkflowType,
        analysis: WorkflowAnalysis,
        actions: List[ProposedAction]
    ) -> List[RiskAssessment]:
        """Assess risks in the proposed workflow"""
        risks = []
        
        # Inventory risk
        if any(a.action == ActionType.VALIDATE_INVENTORY for a in actions):
            risks.append(RiskAssessment(
                risk="inventory_commitment",
                description="Stock might be allocated to another order before confirmation",
                likelihood="medium",
                impact="high",
                mitigation="Reserve inventory immediately upon approval",
                risk_level=RiskLevel.MEDIUM
            ))
        
        # Pricing risk
        if any(a.action == ActionType.CALCULATE_PRICING for a in actions):
            if analysis.customer_context.get("discount_requested"):
                risks.append(RiskAssessment(
                    risk="price_approval",
                    description="Discount might need manager approval",
                    likelihood="high",
                    impact="medium",
                    mitigation="Flag for manager review if discount >10%",
                    risk_level=RiskLevel.MEDIUM
                ))
        
        # Payment risk
        if workflow_type == WorkflowType.NEW_ORDER:
            customer_tier = analysis.customer_context.get("tier")
            if customer_tier == "new":
                risks.append(RiskAssessment(
                    risk="payment_default",
                    description="New customer payment history unknown",
                    likelihood="low",
                    impact="high",
                    mitigation="Require advance payment or partial deposit",
                    risk_level=RiskLevel.MEDIUM
                ))
        
        return risks
    
    def _generate_email_content(
        self,
        workflow_type: WorkflowType,
        analysis: WorkflowAnalysis,
        customer_data: Optional[Dict[str, Any]],
        order_data: Optional[ExtractedOrder],
        inventory_matches: List[Dict[str, Any]]
    ) -> EmailContent:
        """Generate contextual email content"""
        customer_name = self._extract_customer_name(customer_data)
        company = customer_data.get("company", "") if customer_data else ""
        
        # Generate subject
        subject_templates = {
            WorkflowType.NEW_ORDER: "Re: Your Order Request - Quotation Attached",
            WorkflowType.ORDER_CLARIFICATION: "Re: Your Order - Clarification Needed",
            WorkflowType.PAYMENT_PROCESSING: "Re: Payment Received - Order Confirmation",
            WorkflowType.INVENTORY_INQUIRY: "Re: Product Availability Information"
        }
        subject = subject_templates.get(workflow_type, "Re: Your Inquiry")
        
        # Generate body based on workflow and confidence
        confidence = analysis.confidence_metrics.get("overall", 0.5)
        body = self._generate_email_body(
            workflow_type, customer_name, company,
            confidence, inventory_matches, order_data
        )
        
        # Determine attachments
        attachments = []
        if workflow_type == WorkflowType.NEW_ORDER:
            attachments.append("quotation.pdf")
        elif workflow_type == WorkflowType.INVENTORY_INQUIRY:
            attachments.append("product_catalog.pdf")
        
        return EmailContent(
            subject=subject,
            body=body,
            attachments=attachments,
            is_html=False,
            template_used=f"{workflow_type.value}_template"
        )
    
    def _generate_email_body(
        self,
        workflow_type: WorkflowType,
        customer_name: str,
        company: str,
        confidence: float,
        inventory_matches: List[Dict[str, Any]],
        order_data: Optional[ExtractedOrder]
    ) -> str:
        """Generate the email body content"""
        greeting = f"Dear {customer_name}" if customer_name else "Dear Customer"
        if company:
            greeting += f" ({company})"
        
        if workflow_type == WorkflowType.NEW_ORDER and confidence > 0.8:
            body = f"""{greeting},

Thank you for your order request. We are pleased to confirm that we have the requested items in stock and have prepared a detailed quotation for your review.

Items Available:"""
            
            for match in inventory_matches[:5]:
                body += f"\n- {match.get('tag_code', 'Item')}: {match.get('tag_name', 'N/A')}"
            
            if len(inventory_matches) > 5:
                body += f"\n... and {len(inventory_matches) - 5} more items"
            
            body += """

Please find the attached quotation with pricing details and terms. The quoted prices are valid for 15 days from today.

We can begin processing your order immediately upon confirmation. Standard delivery time is 5-7 business days.

Please let us know if you have any questions or need any modifications to the quotation.

Best regards,
Factory Automation Team"""
        
        elif workflow_type == WorkflowType.ORDER_CLARIFICATION:
            body = f"""{greeting},

Thank you for your inquiry. To provide you with accurate pricing and availability, we need some additional information:

1. Could you please specify the exact quantities needed for each item?
2. Do you have any specific delivery timeline requirements?
3. Will this be a one-time order or recurring requirement?

We have several options that might match your requirements. Our team is ready to assist you in finding the perfect solution.

Please feel free to call us at +91-XXXXXXXXXX for immediate assistance.

Best regards,
Factory Automation Team"""
        
        else:
            # Generic response
            body = f"""{greeting},

Thank you for contacting us. We have received your message and our team is reviewing your requirements.

We will get back to you with detailed information shortly.

Best regards,
Factory Automation Team"""
        
        return body
    
    def _extract_customer_name(self, customer_data: Optional[Dict[str, Any]]) -> str:
        """Extract customer name from data"""
        if not customer_data:
            return "Customer"
        
        # Try different fields
        name = customer_data.get("contact_name")
        if not name:
            email = customer_data.get("email", "")
            if email and "@" in email:
                name = email.split("@")[0].replace(".", " ").title()
        
        return name or "Customer"
    
    def _estimate_order_value(
        self,
        order_data: Optional[ExtractedOrder],
        inventory_matches: List[Dict[str, Any]]
    ) -> Optional[float]:
        """Estimate the value of the order"""
        if not order_data or not order_data.items:
            return None
        
        total_quantity = sum(item.quantity_ordered for item in order_data.items)
        unit_price = 12  # Default price per tag
        
        # Apply bulk discount
        if total_quantity > 1000:
            unit_price *= 0.9
        elif total_quantity > 500:
            unit_price *= 0.95
        
        return total_quantity * unit_price
    
    def _classify_email(self, email_data: Dict[str, Any]) -> str:
        """Classify the type of email"""
        body = email_data.get("body", "").lower()
        subject = email_data.get("subject", "").lower()
        
        # Check for keywords
        if any(word in body + subject for word in ["order", "purchase", "buy", "need", "require"]):
            if any(word in body + subject for word in ["quote", "quotation", "price", "cost"]):
                return "quotation_request"
            return "new_order"
        elif any(word in body + subject for word in ["payment", "paid", "utr", "transfer"]):
            return "payment"
        elif any(word in body + subject for word in ["cancel", "cancellation"]):
            return "cancellation"
        elif any(word in body + subject for word in ["modify", "change", "update"]):
            return "modification"
        elif any(word in body + subject for word in ["complaint", "issue", "problem"]):
            return "complaint"
        elif any(word in body + subject for word in ["availability", "stock", "catalog"]):
            return "inventory_check"
        else:
            return "general_inquiry"
    
    def _build_customer_context(
        self,
        customer_data: Optional[Dict[str, Any]],
        email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build comprehensive customer context"""
        context = {
            "tier": "new",
            "order_count": 0,
            "total_value": 0,
            "average_order_value": 0,
            "payment_history": "unknown",
            "preferred_products": [],
            "communication_preferences": {}
        }
        
        if customer_data:
            context.update(customer_data)
        
        # Extract from email if needed
        email_from = email_data.get("from", "")
        if email_from:
            context["email"] = email_from
        
        return context
    
    def _calculate_confidence_metrics(
        self,
        email_classification: str,
        inventory_matches: List[Dict[str, Any]],
        customer_context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate various confidence metrics"""
        metrics = {
            "classification_confidence": 0.8,  # How confident in email classification
            "match_confidence": 0.0,  # How well inventory matches
            "customer_confidence": 0.5,  # How well we know customer
            "overall": 0.0
        }
        
        # Calculate match confidence
        if inventory_matches:
            avg_score = sum(m.get("confidence", 0.5) for m in inventory_matches) / len(inventory_matches)
            metrics["match_confidence"] = avg_score
        
        # Calculate customer confidence
        if customer_context.get("order_count", 0) > 5:
            metrics["customer_confidence"] = 0.9
        elif customer_context.get("order_count", 0) > 0:
            metrics["customer_confidence"] = 0.7
        
        # Calculate overall
        metrics["overall"] = (
            metrics["classification_confidence"] * 0.3 +
            metrics["match_confidence"] * 0.4 +
            metrics["customer_confidence"] * 0.3
        )
        
        return metrics
    
    def _extract_requirements(
        self,
        email_data: Dict[str, Any],
        order_data: Optional[ExtractedOrder]
    ) -> Dict[str, Any]:
        """Extract specific requirements from email"""
        requirements = {
            "items_requested": [],
            "quantities": {},
            "delivery_date": None,
            "payment_terms": None,
            "special_instructions": None
        }
        
        if order_data and order_data.items:
            for item in order_data.items:
                requirements["items_requested"].append(item.tag_specification.description if hasattr(item, 'tag_specification') else 'Item')
                requirements["quantities"][item.tag_specification.description if hasattr(item, 'tag_specification') else 'Item'] = item.quantity
        
        # Extract from email body
        body = email_data.get("body", "")
        
        # Look for delivery mentions
        if "urgent" in body.lower() or "asap" in body.lower():
            requirements["delivery_date"] = "urgent"
        
        # Look for payment terms
        if "credit" in body.lower():
            requirements["payment_terms"] = "credit_requested"
        
        return requirements
    
    def _initial_risk_assessment(
        self,
        email_classification: str,
        customer_context: Dict[str, Any],
        inventory_matches: List[Dict[str, Any]]
    ) -> List[RiskAssessment]:
        """Perform initial risk assessment"""
        risks = []
        
        # New customer risk
        if customer_context.get("order_count", 0) == 0:
            risks.append(RiskAssessment(
                risk="new_customer",
                description="No order history with this customer",
                likelihood="high",
                impact="medium",
                mitigation="Require advance payment or verification",
                risk_level=RiskLevel.MEDIUM
            ))
        
        # Low inventory match risk
        if inventory_matches:
            avg_confidence = sum(m.get("confidence", 0) for m in inventory_matches) / len(inventory_matches)
            if avg_confidence < 0.6:
                risks.append(RiskAssessment(
                    risk="incorrect_item_match",
                    description="Low confidence in item matching",
                    likelihood="medium",
                    impact="high",
                    mitigation="Request clarification before processing",
                    risk_level=RiskLevel.HIGH
                ))
        
        return risks
    
    def _generate_clarification_questions(self, analysis: WorkflowAnalysis) -> List[str]:
        """Generate questions for clarification"""
        questions = []
        
        if not analysis.extracted_requirements.get("quantities"):
            questions.append("What quantities do you need for each item?")
        
        if not analysis.extracted_requirements.get("delivery_date"):
            questions.append("When do you need these items delivered?")
        
        if analysis.confidence_metrics.get("match_confidence", 0) < 0.7:
            questions.append("Could you provide more specific product codes or descriptions?")
        
        return questions
    
    def _determine_documents_needed(self, workflow_type: WorkflowType) -> List[str]:
        """Determine what documents need to be generated"""
        documents = []
        
        if workflow_type == WorkflowType.NEW_ORDER:
            documents.append("quotation")
            documents.append("order_confirmation")
        elif workflow_type == WorkflowType.PAYMENT_PROCESSING:
            documents.append("invoice")
            documents.append("receipt")
        elif workflow_type == WorkflowType.ORDER_MODIFICATION:
            documents.append("revised_quotation")
        
        return documents
    
    def _load_workflow_templates(self) -> Dict[str, Any]:
        """Load predefined workflow templates"""
        # This would normally load from a configuration file or database
        return {
            "standard_new_order": {
                "steps": ["validate", "price", "quote", "email", "update", "followup"],
                "confidence_threshold": 0.7
            },
            "express_order": {
                "steps": ["validate", "price", "email", "update"],
                "confidence_threshold": 0.9
            }
        }