import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.entities import Base
from app.providers.affiliate.base import AffiliateProvider, AffiliateLinkResult
from unittest.mock import Mock


@pytest.fixture(scope="session")
def db_engine():
    """Provides a SQLAlchemy engine for an in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provides a transactional database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def mock_affiliate_provider():
    """Provides a mock AffiliateProvider for testing."""
    mock_provider = Mock(spec=AffiliateProvider)
    mock_provider.generate_affiliate_link.return_value = AffiliateLinkResult(
        affiliate_url="https://affiliate.test/generated_link?sub_id={tracking_id}",
        platform="shopee",
    )
    return mock_provider
