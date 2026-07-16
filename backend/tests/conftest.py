import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import engine, get_db
from app.main import app
from app.models.clinic import Clinic
from app.models.user import User, UserRole


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    return TestClient(app)


@pytest.fixture()
def clinic(db_session):
    obj = Clinic(name="Test Clinic")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def user(db_session, clinic):
    obj = User(
        clinic_id=clinic.id,
        email="vet@example.com",
        hashed_password=hash_password("hunter2"),
        full_name="Dr. Vet",
        role=UserRole.VET,
    )
    db_session.add(obj)
    db_session.flush()
    return obj
