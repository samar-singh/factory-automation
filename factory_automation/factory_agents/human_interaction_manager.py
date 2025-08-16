"""Human Interaction Manager for Manual Review Cases"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from ..factory_database.connection import engine, get_db_session
from ..factory_database.models import Order, ReviewDecision
from ..factory_models.order_models import (
    BatchOperation,
    QueuedRecommendation,
)

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Status of human review"""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"
    ALTERNATIVE_SUGGESTED = "alternative_suggested"
    DEFERRED = "deferred"


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
    image_matches: Optional[List[Dict[str, Any]]] = None
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    decision: Optional[str] = None
    alternative_items: List[Dict[str, Any]] = field(default_factory=list)
    order_id: Optional[str] = None  # Link to order
    orchestrator_recommendation: Optional[str] = None  # AI's recommendation
    recommended_action: Optional[str] = None  # Action suggested by orchestrator


class HumanInteractionManager:
    """Manages human-in-the-loop interactions for order approvals"""

    def __init__(self):
        """Initialize the human interaction manager"""
        self.pending_reviews: Dict[str, ReviewRequest] = {}
        self.completed_reviews: Dict[str, ReviewRequest] = {}
        self.review_queue: asyncio.Queue = asyncio.Queue()
        self.reviewers: Dict[str, str] = {}  # reviewer_id -> name
        self.notification_handlers = []
        self.processed_email_ids: set = (
            set()
        )  # Track processed emails to avoid duplicates

        # Database queue support
        self.use_db_queue = True  # Flag to use database queue

        logger.info("Initialized Human Interaction Manager with database queue support")

    async def create_review_request(
        self,
        email_data: Dict[str, Any],
        search_results: List[Dict[str, Any]],
        confidence_score: float,
        extracted_items: List[Dict[str, Any]],
        image_matches: Optional[List[Dict[str, Any]]] = None,
    ) -> ReviewRequest:
        """Create a new review request for human approval"""

        # Check for duplicate based on email ID and content hash
        email_id = email_data.get("message_id", "unknown")
        email_subject = email_data.get("subject", "")
        email_from = email_data.get("from", "")

        # Create a content hash to detect duplicates even with different IDs
        import hashlib

        hashlib.md5(f"{email_from}:{email_subject}".encode()).hexdigest()

        # Check by email ID first
        if email_id != "unknown" and email_id in self.processed_email_ids:
            logger.warning(
                f"Email {email_id} already processed, skipping duplicate review"
            )
            # Find and return existing review
            for review in self.pending_reviews.values():
                if review.email_id == email_id:
                    return review
            for review in self.completed_reviews.values():
                if review.email_id == email_id:
                    return review

        # Check by content hash to catch duplicates with different IDs
        for review in self.pending_reviews.values():
            if review.customer_email == email_from and review.subject == email_subject:
                logger.warning(
                    f"Duplicate email detected from {email_from} with subject '{email_subject}'"
                )
                return review

        # Mark email as processed
        if email_id != "unknown":
            self.processed_email_ids.add(email_id)

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
            priority=priority,
            image_matches=image_matches,
            order_id=email_data.get("order_id"),
            orchestrator_recommendation=email_data.get("orchestrator_recommendation"),
            recommended_action=email_data.get("recommended_action"),
        )

        # Add to pending reviews
        self.pending_reviews[request_id] = review_request

        # Add to review queue
        await self.review_queue.put(review_request)

        # Send notifications
        await self._send_notifications(review_request)

        logger.info(
            f"Created review request {request_id} with {priority.value} priority"
        )

        return review_request

    def _determine_priority(
        self, email_data: Dict[str, Any], confidence_score: float
    ) -> Priority:
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
        assigned_to: Optional[str] = None,
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
            Priority.LOW: 3,
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
        alternative_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Submit a human review decision"""

        if request_id not in self.pending_reviews:
            return {"success": False, "error": f"Review request {request_id} not found"}

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
        elif decision.lower() == "defer":
            review.status = ReviewStatus.DEFERRED
            # Move to back of queue by updating created_at
            review.created_at = datetime.now()
            # Keep in pending reviews but with updated timestamp
            logger.info(f"Review {request_id} deferred to back of queue")
            return {
                "success": True,
                "request_id": request_id,
                "decision": "defer",
                "status": review.status.value,
                "deferred_at": review.created_at.isoformat(),
                "notes": notes,
            }
        else:
            return {"success": False, "error": f"Invalid decision: {decision}"}

        # Move to completed reviews (except for defer)
        self.completed_reviews[request_id] = review
        del self.pending_reviews[request_id]

        # Save to database
        try:
            session = get_db_session()

            # Calculate review duration
            review_duration = (review.reviewed_at - review.created_at).total_seconds()

            # Find or create the order
            order = None
            if hasattr(review, "order_id") and review.order_id:
                order = (
                    session.query(Order).filter_by(order_number=review.order_id).first()
                )
                if not order:
                    # Create a basic order record if it doesn't exist
                    order = Order(
                        order_number=review.order_id
                        or f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        customer_id=None,  # Would need to link to customer
                        status=(
                            decision.lower()
                            if decision.lower() in ["approve", "reject"]
                            else "pending"
                        ),
                        email_thread_id=review.email_id,
                    )
                    session.add(order)
                    session.flush()

            # Create review decision record
            review_decision = ReviewDecision(
                review_id=request_id,
                order_id=order.id if order else None,
                email_id=review.email_id,
                customer_email=review.customer_email,
                subject=review.subject,
                confidence_score=review.confidence_score,
                items=review.items,
                search_results=review.search_results,
                decision=decision,
                status=review.status.value,
                review_notes=notes,
                alternative_items=alternative_items,
                reviewed_by=review.assigned_to or "human_reviewer",
                reviewed_at=review.reviewed_at,
                review_duration_seconds=review_duration,
                priority=review.priority.value,
                created_at=review.created_at,
            )

            session.add(review_decision)
            session.commit()
            logger.info(f"Review decision saved to database for {request_id}")

        except Exception as e:
            logger.error(f"Error saving review decision to database: {e}")
            if "session" in locals():
                session.rollback()
        finally:
            if "session" in locals():
                session.close()

        logger.info(f"Review {request_id} completed with decision: {decision}")

        # Return decision details
        return {
            "success": True,
            "request_id": request_id,
            "decision": decision,
            "status": review.status.value,
            "reviewed_at": review.reviewed_at.isoformat(),
            "review_time_seconds": (
                review.reviewed_at - review.created_at
            ).total_seconds(),
            "notes": notes,
            "alternative_items": alternative_items,
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
                (r.created_at for r in self.pending_reviews.values()), default=None
            ),
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
                    "assigned_to": r.assigned_to,
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
                        if r.reviewed_at
                        else None
                    ),
                }
                for r in self.completed_reviews.values()
            ],
            "statistics": self.get_review_statistics(),
        }

    def get_review_history_from_db(
        self,
        limit: int = 100,
        offset: int = 0,
        customer_email: Optional[str] = None,
        decision_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get review history from database"""

        try:
            session = get_db_session()

            # Build query
            query = session.query(ReviewDecision)

            # Apply filters
            if customer_email:
                query = query.filter(ReviewDecision.customer_email == customer_email)
            if decision_filter:
                query = query.filter(ReviewDecision.decision == decision_filter)

            # Order by most recent first
            query = query.order_by(ReviewDecision.reviewed_at.desc())

            # Apply pagination
            reviews = query.offset(offset).limit(limit).all()

            # Convert to dict
            result = []
            for review in reviews:
                result.append(
                    {
                        "review_id": review.review_id,
                        "order_id": review.order_id,
                        "customer_email": review.customer_email,
                        "subject": review.subject,
                        "confidence_score": review.confidence_score,
                        "decision": review.decision,
                        "status": review.status,
                        "review_notes": review.review_notes,
                        "reviewed_by": review.reviewed_by,
                        "reviewed_at": (
                            review.reviewed_at.isoformat()
                            if review.reviewed_at
                            else None
                        ),
                        "review_duration_seconds": review.review_duration_seconds,
                        "priority": review.priority,
                        "created_at": (
                            review.created_at.isoformat() if review.created_at else None
                        ),
                        "items": review.items,
                        "alternative_items": review.alternative_items,
                    }
                )

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error retrieving review history from database: {e}")
            if "session" in locals():
                session.close()
            return []

    # ========== Database Queue Methods ==========

    def add_to_recommendation_queue(self, recommendation: QueuedRecommendation) -> str:
        """Add a recommendation to the database queue"""

        try:
            with engine.connect() as conn:
                # Insert into recommendation_queue table
                query = text(
                    """
                    INSERT INTO recommendation_queue (
                        queue_id, order_id, customer_email, 
                        recommendation_type, recommendation_data,
                        confidence_score, priority, status, created_at
                    ) VALUES (
                        :queue_id, :order_id, :customer_email,
                        :recommendation_type, :recommendation_data,
                        :confidence_score, :priority, :status, :created_at
                    )
                """
                )

                conn.execute(
                    query,
                    {
                        "queue_id": recommendation.queue_id,
                        "order_id": recommendation.order_id,
                        "customer_email": recommendation.customer_email,
                        "recommendation_type": recommendation.recommendation_type.value,
                        "recommendation_data": json.dumps(
                            recommendation.recommendation_data
                        ),
                        "confidence_score": recommendation.confidence_score,
                        "priority": recommendation.priority.value,
                        "status": recommendation.status,
                        "created_at": recommendation.created_at,
                    },
                )
                conn.commit()

                logger.info(
                    f"Added recommendation {recommendation.queue_id} to database queue"
                )
                return recommendation.queue_id

        except Exception as e:
            logger.error(f"Error adding to recommendation queue: {e}")
            raise

    def get_pending_recommendations(
        self, limit: int = 50, priority_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get pending recommendations from database queue"""

        try:
            with engine.connect() as conn:
                query = """
                    SELECT queue_id, order_id, customer_email, 
                           recommendation_type, recommendation_data,
                           confidence_score, priority, status, 
                           created_at, batch_id
                    FROM recommendation_queue
                    WHERE status = 'pending'
                """

                if priority_filter:
                    query += " AND priority = :priority"

                query += " ORDER BY "
                query += "CASE priority "
                query += "WHEN 'urgent' THEN 1 "
                query += "WHEN 'high' THEN 2 "
                query += "WHEN 'medium' THEN 3 "
                query += "WHEN 'low' THEN 4 END, "
                query += "created_at ASC "
                query += f"LIMIT {limit}"

                params = {}
                if priority_filter:
                    params["priority"] = priority_filter

                result = conn.execute(text(query), params)

                recommendations = []
                for row in result:
                    # Handle recommendation_data - it might be a dict (from JSONB) or a string
                    rec_data = row[4]
                    if rec_data:
                        if isinstance(rec_data, str):
                            rec_data = json.loads(rec_data)
                        elif isinstance(rec_data, dict):
                            rec_data = rec_data  # Already a dict from JSONB
                        else:
                            rec_data = {}
                    else:
                        rec_data = {}

                    recommendations.append(
                        {
                            "queue_id": row[0],
                            "order_id": row[1],
                            "customer_email": row[2],
                            "recommendation_type": row[3],
                            "recommendation_data": rec_data,
                            "confidence_score": row[5],
                            "priority": row[6],
                            "status": row[7],
                            "created_at": row[8].isoformat() if row[8] else None,
                            "batch_id": row[9],
                        }
                    )

                return recommendations

        except Exception as e:
            logger.error(f"Error getting pending recommendations: {e}")
            return []

    def create_batch_from_queue(
        self,
        queue_ids: List[str],
        batch_name: Optional[str] = None,
        batch_type: str = "manual",
    ) -> str:
        """Create a batch from selected queue items"""

        batch = BatchOperation(
            batch_name=batch_name,
            batch_type=batch_type,
            total_items=len(queue_ids),
            created_by="system",
        )

        try:
            with engine.connect() as conn:
                # Insert batch
                query = text(
                    """
                    INSERT INTO batch_operations (
                        batch_id, batch_name, batch_type, 
                        total_items, status, created_at, created_by
                    ) VALUES (
                        :batch_id, :batch_name, :batch_type,
                        :total_items, :status, :created_at, :created_by
                    )
                """
                )

                conn.execute(
                    query,
                    {
                        "batch_id": batch.batch_id,
                        "batch_name": batch.batch_name,
                        "batch_type": batch.batch_type,
                        "total_items": batch.total_items,
                        "status": batch.status,
                        "created_at": batch.created_at,
                        "created_by": batch.created_by,
                    },
                )

                # Update queue items with batch_id
                update_query = text(
                    """
                    UPDATE recommendation_queue 
                    SET batch_id = :batch_id, status = 'in_review'
                    WHERE queue_id = ANY(:queue_ids)
                """
                )

                conn.execute(
                    update_query, {"batch_id": batch.batch_id, "queue_ids": queue_ids}
                )

                conn.commit()

                logger.info(
                    f"Created batch {batch.batch_id} with {len(queue_ids)} items"
                )
                return batch.batch_id

        except Exception as e:
            logger.error(f"Error creating batch: {e}")
            raise

    def get_batch_for_review(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get a batch with all its queue items for review"""

        try:
            with engine.connect() as conn:
                # Get batch info
                batch_query = text(
                    """
                    SELECT batch_id, batch_name, batch_type, total_items,
                           status, created_at, created_by
                    FROM batch_operations
                    WHERE batch_id = :batch_id
                """
                )

                batch_result = conn.execute(batch_query, {"batch_id": batch_id}).first()

                if not batch_result:
                    return None

                # Get queue items in batch
                items_query = text(
                    """
                    SELECT queue_id, order_id, customer_email,
                           recommendation_type, recommendation_data,
                           confidence_score, priority
                    FROM recommendation_queue
                    WHERE batch_id = :batch_id
                    ORDER BY created_at
                """
                )

                items_result = conn.execute(items_query, {"batch_id": batch_id})

                items = []
                for row in items_result:
                    # Handle recommendation_data - it might be a dict (from JSONB) or a string
                    rec_data = row[4]
                    if rec_data:
                        if isinstance(rec_data, str):
                            rec_data = json.loads(rec_data)
                        elif isinstance(rec_data, dict):
                            rec_data = rec_data  # Already a dict from JSONB
                        else:
                            rec_data = {}
                    else:
                        rec_data = {}

                    items.append(
                        {
                            "queue_id": row[0],
                            "order_id": row[1],
                            "customer_email": row[2],
                            "recommendation_type": row[3],
                            "recommendation_data": rec_data,
                            "confidence_score": row[5],
                            "priority": row[6],
                        }
                    )

                return {
                    "batch_id": batch_result[0],
                    "batch_name": batch_result[1],
                    "batch_type": batch_result[2],
                    "total_items": batch_result[3],
                    "status": batch_result[4],
                    "created_at": (
                        batch_result[5].isoformat() if batch_result[5] else None
                    ),
                    "created_by": batch_result[6],
                    "items": items,
                }

        except Exception as e:
            logger.error(f"Error getting batch for review: {e}")
            return None

    def approve_batch_items(
        self,
        batch_id: str,
        approved_queue_ids: List[str],
        rejected_queue_ids: List[str],
        modifications: Dict[str, Any] = None,
    ) -> bool:
        """Approve or reject items in a batch"""

        try:
            with engine.connect() as conn:
                # Update approved items
                if approved_queue_ids:
                    approve_query = text(
                        """
                        UPDATE recommendation_queue
                        SET status = 'approved', 
                            reviewed_at = NOW(),
                            reviewed_by = :reviewer
                        WHERE queue_id = ANY(:queue_ids)
                    """
                    )

                    conn.execute(
                        approve_query,
                        {"queue_ids": approved_queue_ids, "reviewer": "human_reviewer"},
                    )

                # Update rejected items
                if rejected_queue_ids:
                    reject_query = text(
                        """
                        UPDATE recommendation_queue
                        SET status = 'rejected',
                            reviewed_at = NOW(),
                            reviewed_by = :reviewer
                        WHERE queue_id = ANY(:queue_ids)
                    """
                    )

                    conn.execute(
                        reject_query,
                        {"queue_ids": rejected_queue_ids, "reviewer": "human_reviewer"},
                    )

                # Update batch status
                batch_query = text(
                    """
                    UPDATE batch_operations
                    SET approved_items = :approved,
                        rejected_items = :rejected,
                        modified_items = :modifications,
                        status = 'processing',
                        reviewed_at = NOW(),
                        reviewed_by = :reviewer
                    WHERE batch_id = :batch_id
                """
                )

                conn.execute(
                    batch_query,
                    {
                        "batch_id": batch_id,
                        "approved": approved_queue_ids,
                        "rejected": rejected_queue_ids,
                        "modifications": (
                            json.dumps(modifications) if modifications else "{}"
                        ),
                        "reviewer": "human_reviewer",
                    },
                )

                conn.commit()

                logger.info(
                    f"Batch {batch_id} reviewed: {len(approved_queue_ids)} approved, {len(rejected_queue_ids)} rejected"
                )
                return True

        except Exception as e:
            logger.error(f"Error approving batch items: {e}")
            return False
