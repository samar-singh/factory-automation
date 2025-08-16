"""Database models for factory automation system."""

from datetime import datetime

from sqlalchemy import (
    DECIMAL,
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    company = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    status = Column(String(50), default="pending")
    total_amount = Column(DECIMAL(10, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    email_thread_id = Column(String(255))
    email_message_id = Column(String(255))

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="order")
    approvals = relationship("ApprovalQueue", back_populates="order")
    email_logs = relationship("EmailLog", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    tag_code = Column(String(50))
    description = Column(Text)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2))
    total_price = Column(DECIMAL(10, 2))
    matched_inventory_id = Column(String(100))
    similarity_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    payment_type = Column(String(50))  # 'utr', 'cheque', 'cash'
    payment_reference = Column(String(255))
    amount = Column(DECIMAL(10, 2))
    status = Column(String(50), default="pending")
    payment_date = Column(Date)
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="payments")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True)
    message_id = Column(String(255), unique=True)
    thread_id = Column(String(255))
    from_email = Column(String(255))
    subject = Column(Text)
    received_at = Column(DateTime)
    processed_at = Column(DateTime)
    status = Column(String(50))
    order_id = Column(Integer, ForeignKey("orders.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="email_logs")


class ApprovalQueue(Base):
    __tablename__ = "approval_queue"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    approval_type = Column(String(50))  # 'new_design', 'price_change', 'quantity'
    details = Column(JSON)
    status = Column(String(50), default="pending")
    approved_by = Column(String(255))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="approvals")


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    tag_code = Column(String(50))
    snapshot_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(Integer, primary_key=True)
    review_id = Column(
        String(50), unique=True, nullable=False
    )  # REV-YYYYMMDD-HHMMSS-XXXX
    order_id = Column(Integer, ForeignKey("orders.id"))
    email_id = Column(String(255))
    customer_email = Column(String(255), nullable=False)
    subject = Column(Text)
    confidence_score = Column(Float)

    # Review details
    items = Column(JSON)  # List of requested items
    search_results = Column(JSON)  # Search results shown

    # Decision details
    decision = Column(
        String(50), nullable=False
    )  # approve/reject/clarify/alternative/defer
    status = Column(
        String(50), nullable=False
    )  # approved/rejected/needs_clarification/etc
    review_notes = Column(Text)
    alternative_items = Column(JSON)  # If alternatives suggested

    # Reviewer info
    reviewed_by = Column(String(255), default="human_reviewer")
    reviewed_at = Column(DateTime, nullable=False)
    review_duration_seconds = Column(Float)

    # Priority and timestamps
    priority = Column(String(20))  # urgent/high/medium/low
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", backref="review_decisions")


class EmailPattern(Base):
    """Store email sender patterns for intelligent routing"""

    __tablename__ = "email_patterns"

    id = Column(Integer, primary_key=True)
    sender_email = Column(String(255), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=False)
    recipient_description = Column(Text)  # Store the email's purpose/description
    intent_type = Column(
        String(50), nullable=False
    )  # NEW_ORDER, PAYMENT, INQUIRY, etc.
    count = Column(Integer, default=1)
    confidence = Column(Float, default=0.5)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Additional learning fields
    subject_keywords = Column(Text)  # JSON string of common keywords
    avg_response_time = Column(Float)  # Track response patterns
    auto_approved_count = Column(Integer, default=0)
    manual_review_count = Column(Integer, default=0)

    __table_args__ = (
        Index(
            "idx_sender_recipient_intent",
            "sender_email",
            "recipient_email",
            "intent_type",
        ),
        UniqueConstraint(
            "sender_email",
            "recipient_email",
            "intent_type",
            name="uq_sender_recipient_intent",
        ),
    )
