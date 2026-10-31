import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.models import Base
from backend.mock_payments.service import mock_payments_service

@pytest.fixture
def db_session():
    # Use SQLite in-memory for fast, isolated tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    mock_payments_service.reset()
    try:
        yield session
    finally:
        session.close()
        mock_payments_service.reset()

