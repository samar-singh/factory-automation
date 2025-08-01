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
    Integer,
    String,
    Text,
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
