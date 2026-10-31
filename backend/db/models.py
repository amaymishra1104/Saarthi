import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Case(Base):
    __tablename__ = "cases"

    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), nullable=False, index=True)
    txn_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="OPEN") 
    # OPEN, INVESTIGATING, PENDING_APPROVAL, RESOLVED, ESCALATED, AWAITING_STATUS_CHANGE, CLOSED
    outcome = Column(String(64), nullable=True)
    complaint_text = Column(Text, nullable=False)
    customer_language = Column(String(16), default="en")
    case_brief = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    steps = relationship("CaseStep", back_populates="case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")

class CaseStep(Base):
    __tablename__ = "case_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), ForeignKey("cases.id"), nullable=False, index=True)
    step_name = Column(String(32), nullable=False)
    # UNDERSTAND, INVESTIGATE, DECIDE, GATE, ACT, VERIFY, INFORM, ESCALATE, DONE
    status = Column(String(32), default="SUCCESS")  # SUCCESS, FAILED, SKIPPED, PAUSED
    state_data = Column(Text, nullable=True)  # JSON payload
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="steps")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    case_id = Column(String(64), ForeignKey("cases.id"), nullable=True, index=True)
    txn_id = Column(String(64), nullable=True, index=True)
    actor = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    input_payload = Column(Text, nullable=True)  # Masked JSON
    output_payload = Column(Text, nullable=True)  # Masked JSON
    decision_reason = Column(Text, nullable=True)
    policy_citations = Column(Text, nullable=True)  # JSON array

    case = relationship("Case", back_populates="audit_logs")

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    idempotency_key = Column(String(128), primary_key=True)
    action_type = Column(String(64), nullable=False)
    txn_id = Column(String(64), nullable=False, index=True)
    case_id = Column(String(64), nullable=False)
    status = Column(String(32), default="EXECUTED")  # EXECUTED, LOCKED, FAILED
    response_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("action_type", "txn_id", name="uq_action_txn"),
    )

class HumanApprovalQueue(Base):
    __tablename__ = "human_approval_queue"

    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("cases.id"), nullable=False, index=True)
    txn_id = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    action_proposed = Column(String(64), nullable=False)
    gate_reason = Column(Text, nullable=False)
    case_brief = Column(Text, nullable=True)
    status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String(64), nullable=True)
    supervisor_notes = Column(Text, nullable=True)

