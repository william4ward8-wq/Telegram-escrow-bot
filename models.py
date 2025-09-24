"""
Database models for the Telegram Escrow Bot
"""
import os
from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class DealStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    FUNDED = "funded"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class DisputeStatus(Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TransactionType(Enum):
    DEPOSIT = "deposit"
    ESCROW_HOLD = "escrow_hold"
    ESCROW_RELEASE = "escrow_release"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"


class WithdrawalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"


class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(20), unique=True, nullable=False)
    username = Column(String(50), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)  # First user (ID 1) will be auto-admin
    is_arbitrator = Column(Boolean, default=False)
    balance = Column(Float, default=0.0)
    escrowed_amount = Column(Float, default=0.0)  # Amount currently held in escrow
    
    # Relationships
    deals_as_buyer = relationship("Deal", foreign_keys="Deal.buyer_id", back_populates="buyer")
    deals_as_seller = relationship("Deal", foreign_keys="Deal.seller_id", back_populates="seller")
    transactions = relationship("Transaction", back_populates="user")
    
    def __repr__(self):
        username = self.username if self.username is not None else self.first_name
        return f'<User {username}>'
    
    @property
    def available_balance(self):
        """Available balance excluding escrowed amount"""
        return self.balance - self.escrowed_amount
    
    @property
    def display_name(self):
        """Display name for user"""
        if self.username is not None:
            return f"@{self.username}"
        last_name = self.last_name if self.last_name is not None else ''
        return f"{self.first_name} {last_name}".strip()


class Deal(db.Model):
    __tablename__ = 'deals'
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(String(20), unique=True, nullable=False)  # Short readable ID
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default=DealStatus.PENDING.value)
    
    # User IDs
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    arbitrator_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    funded_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    disputed_at = Column(DateTime, nullable=True)
    
    # Dispute information
    dispute_reason = Column(Text, nullable=True)
    
    # Relationships
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="deals_as_buyer")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="deals_as_seller")
    arbitrator = relationship("User", foreign_keys=[arbitrator_id])
    transactions = relationship("Transaction", back_populates="deal")
    dispute = relationship("Dispute", back_populates="deal", uselist=False)
    
    def __repr__(self):
        return f'<Deal {self.deal_id}: {self.title}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20), nullable=False)
    status = Column(String(20), default='pending')
    description = Column(String(500), nullable=True)
    
    # Stripe integration
    stripe_payment_intent_id = Column(String(100), nullable=True)
    stripe_charge_id = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    deal = relationship("Deal", back_populates="transactions")
    
    def __repr__(self):
        return f'<Transaction {self.transaction_id}: {self.transaction_type} ${self.amount}>'


class Dispute(db.Model):
    __tablename__ = 'disputes'
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=False)
    raised_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    arbitrator_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    reason = Column(Text, nullable=False)
    status = Column(String(20), default=DisputeStatus.OPEN.value)
    resolution = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    deal = relationship("Deal", back_populates="dispute")
    raised_by = relationship("User", foreign_keys=[raised_by_id])
    arbitrator = relationship("User", foreign_keys=[arbitrator_id])
    
    def __repr__(self):
        return f'<Dispute for Deal {self.deal_id}: {self.status}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    deal_id = Column(Integer, ForeignKey('deals.id'), nullable=True)
    
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    deal = relationship("Deal")
    
    def __repr__(self):
        return f'<Notification {self.title} for {self.user_id}>'


class WithdrawalRequest(db.Model):
    __tablename__ = 'withdrawal_requests'
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(20), unique=True, nullable=False)  # Short readable ID
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    amount = Column(Float, nullable=False)
    wallet_address = Column(String(200), nullable=False)
    crypto_type = Column(String(20), nullable=True)  # BTC, LTC, USDT
    status = Column(String(20), default=WithdrawalStatus.PENDING.value)
    
    # Admin fields
    processed_by_id = Column(BigInteger, nullable=True)  # Admin Telegram ID, not FK
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    # processed_by_id stores admin Telegram ID directly, not a User FK
    
    def __repr__(self):
        return f'<WithdrawalRequest {self.request_id}: ${self.amount} for {self.user_id}>'