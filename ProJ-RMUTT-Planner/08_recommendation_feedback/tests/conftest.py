import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["INTERNAL_API_TOKEN"] = "test-token"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from src.core.database import Base, SessionLocal, engine
from src.main import app
from src.models import EventLog, FeedbackEvent, Notification, ReviewItem


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_tables():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for model in (ReviewItem, FeedbackEvent, Notification, EventLog):
            db.execute(delete(model))
        db.commit()
    yield
