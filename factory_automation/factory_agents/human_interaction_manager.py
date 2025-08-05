"""Human Interaction Manager for Manual Review Cases"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Status of human review"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"
    ALTERNATIVE_SUGGESTED = "alternative_suggested"


class Priority(Enum):
    """Priority levels for review"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ReviewRequest:
    """A request for human review"""
    request_id: str
    email_id: str
    customer_email: str
    subject: str
    confidence_score: float
    items: List[Dict[str, Any]]
    search_results: List[Dict[str, Any]]
    priority: Priority
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    decision: Optional[str] = None
    alternative_items: List[Dict[str, Any]] = field(default_factory=list)


class HumanInteractionManager:
    """Manages human-in-the-loop interactions for order approvals"""
    
    def __init__(self):
        """Initialize the human interaction manager"""
        self.pending_reviews: Dict[str, ReviewRequest] = {}
        self.completed_reviews: Dict[str, ReviewRequest] = {}
        self.review_queue: asyncio.Queue = asyncio.Queue()
        self.reviewers: Dict[str, str] = {}  # reviewer_id -> name
        self.notification_handlers = []
        
        logger.info("Initialized Human Interaction Manager")
    
    async def create_review_request(
        self,
        email_data: Dict[str, Any],
        search_results: List[Dict[str, Any]],
        confidence_score: float,
        extracted_items: List[Dict[str, Any]]
    ) -> ReviewRequest:
        """Create a new review request for human approval"""
        
        # Generate request ID
        request_id = f"REV-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{len(self.pending_reviews) + 1:04d}"
        
        # Determine priority based on email content
        priority = self._determine_priority(email_data, confidence_score)
        
        # Create review request
        review_request = ReviewRequest(
            request_id=request_id,
            email_id=email_data.get("message_id", "unknown"),
            customer_email=email_data.get("from", "unknown"),
            subject=email_data.get("subject", "No subject"),
            confidence_score=confidence_score,
            items=extracted_items,
            search_results=search_results,
            priority=priority
        )
        
        # Add to pending reviews
        self.pending_reviews[request_id] = review_request
        
        # Add to review queue
        await self.review_queue.put(review_request)
        
        # Send notifications
        await self._send_notifications(review_request)
        
        logger.info(f"Created review request {request_id} with {priority.value} priority")
        
        return review_request
    
    def _determine_priority(self, email_data: Dict[str, Any], confidence_score: float) -> Priority:
        """Determine priority based on email content and confidence"""
        
        body = email_data.get("body", "").lower()
        subject = email_data.get("subject", "").lower()
        
        # Check for urgency indicators
        urgent_keywords = ["urgent", "asap", "immediately", "rush", "critical", "today"]
        if any(keyword in body or keyword in subject for keyword in urgent_keywords):
            return Priority.URGENT
        
        # Check confidence level
        if confidence_score < 65:
            return Priority.HIGH  # Low confidence needs quick attention
        elif confidence_score < 70:
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    async def _send_notifications(self, review_request: ReviewRequest):
        """Send notifications to reviewers"""
        
        for handler in self.notification_handlers:
            try:
                await handler(review_request)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")
        
        # Log notification
        logger.info(f"Notifications sent for {review_request.request_id}")
    
    async def get_pending_reviews(
        self,
        priority_filter: Optional[Priority] = None,
        assigned_to: Optional[str] = None
    ) -> List[ReviewRequest]:
        """Get list of pending reviews with optional filters"""
        
        reviews = list(self.pending_reviews.values())
        
        # Apply filters
        if priority_filter:
            reviews = [r for r in reviews if r.priority == priority_filter]
        
        if assigned_to:
            reviews = [r for r in reviews if r.assigned_to == assigned_to]
        
        # Sort by priority and creation time
        priority_order = {
            Priority.URGENT: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3
        }
        
        reviews.sort(key=lambda r: (priority_order[r.priority], r.created_at))
        
        return reviews
    
    async def assign_review(self, request_id: str, reviewer_id: str) -> bool:
        """Assign a review to a specific reviewer"""
        
        if request_id not in self.pending_reviews:
            logger.error(f"Review request {request_id} not found")
            return False
        
        review = self.pending_reviews[request_id]
        review.assigned_to = reviewer_id
        review.status = ReviewStatus.IN_REVIEW
        
        logger.info(f"Assigned {request_id} to reviewer {reviewer_id}")
        return True
    
    async def submit_review_decision(
        self,
        request_id: str,
        decision: str,
        notes: Optional[str] = None,
        alternative_items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Submit a human review decision"""
        
        if request_id not in self.pending_reviews:
            return {
                "success": False,
                "error": f"Review request {request_id} not found"
            }
        
        review = self.pending_reviews[request_id]
        
        # Update review with decision
        review.decision = decision
        review.review_notes = notes
        review.reviewed_at = datetime.now()
        
        # Set status based on decision
        if decision.lower() == "approve":
            review.status = ReviewStatus.APPROVED
        elif decision.lower() == "reject":
            review.status = ReviewStatus.REJECTED
        elif decision.lower() == "clarify":
            review.status = ReviewStatus.NEEDS_CLARIFICATION
        elif decision.lower() == "alternative" and alternative_items:
            review.status = ReviewStatus.ALTERNATIVE_SUGGESTED
            review.alternative_items = alternative_items
        else:
            return {
                "success": False,
                "error": f"Invalid decision: {decision}"
            }
        
        # Move to completed reviews
        self.completed_reviews[request_id] = review
        del self.pending_reviews[request_id]
        
        logger.info(f"Review {request_id} completed with decision: {decision}")
        
        # Return decision details
        return {
            "success": True,
            "request_id": request_id,
            "decision": decision,
            "status": review.status.value,
            "reviewed_at": review.reviewed_at.isoformat(),
            "review_time_seconds": (review.reviewed_at - review.created_at).total_seconds(),
            "notes": notes,
            "alternative_items": alternative_items
        }
    
    async def get_review_details(self, request_id: str) -> Optional[ReviewRequest]:
        """Get detailed information about a review request"""
        
        # Check pending reviews
        if request_id in self.pending_reviews:
            return self.pending_reviews[request_id]
        
        # Check completed reviews
        if request_id in self.completed_reviews:
            return self.completed_reviews[request_id]
        
        return None
    
    def get_review_statistics(self) -> Dict[str, Any]:
        """Get statistics about reviews"""
        
        total_pending = len(self.pending_reviews)
        total_completed = len(self.completed_reviews)
        
        # Count by status
        status_counts = {}
        for review in self.completed_reviews.values():
            status = review.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by priority (pending only)
        priority_counts = {}
        for review in self.pending_reviews.values():
            priority = review.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Calculate average review time
        review_times = []
        for review in self.completed_reviews.values():
            if review.reviewed_at and review.created_at:
                time_diff = (review.reviewed_at - review.created_at).total_seconds()
                review_times.append(time_diff)
        
        avg_review_time = sum(review_times) / len(review_times) if review_times else 0
        
        return {
            "total_pending": total_pending,
            "total_completed": total_completed,
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "average_review_time_seconds": avg_review_time,
            "oldest_pending": min(
                (r.created_at for r in self.pending_reviews.values()),
                default=None
            )
        }
    
    def register_notification_handler(self, handler):
        """Register a notification handler function"""
        self.notification_handlers.append(handler)
        logger.info(f"Registered notification handler: {handler.__name__}")
    
    async def escalate_review(self, request_id: str, reason: str) -> bool:
        """Escalate a review to higher priority"""
        
        if request_id not in self.pending_reviews:
            return False
        
        review = self.pending_reviews[request_id]
        
        # Upgrade priority
        if review.priority == Priority.LOW:
            review.priority = Priority.MEDIUM
        elif review.priority == Priority.MEDIUM:
            review.priority = Priority.HIGH
        elif review.priority == Priority.HIGH:
            review.priority = Priority.URGENT
        
        # Add escalation note
        if review.review_notes:
            review.review_notes += f"\n[ESCALATED: {reason}]"
        else:
            review.review_notes = f"[ESCALATED: {reason}]"
        
        logger.info(f"Escalated {request_id} to {review.priority.value} priority")
        
        # Send escalation notification
        await self._send_notifications(review)
        
        return True
    
    def export_review_data(self) -> Dict[str, Any]:
        """Export all review data for analysis"""
        
        return {
            "pending_reviews": [
                {
                    "request_id": r.request_id,
                    "customer": r.customer_email,
                    "confidence": r.confidence_score,
                    "priority": r.priority.value,
                    "status": r.status.value,
                    "created_at": r.created_at.isoformat(),
                    "assigned_to": r.assigned_to
                }
                for r in self.pending_reviews.values()
            ],
            "completed_reviews": [
                {
                    "request_id": r.request_id,
                    "customer": r.customer_email,
                    "confidence": r.confidence_score,
                    "decision": r.decision,
                    "status": r.status.value,
                    "created_at": r.created_at.isoformat(),
                    "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                    "review_time": (
                        (r.reviewed_at - r.created_at).total_seconds()
                        if r.reviewed_at else None
                    )
                }
                for r in self.completed_reviews.values()
            ],
            "statistics": self.get_review_statistics()
        }