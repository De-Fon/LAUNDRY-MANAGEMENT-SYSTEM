import os
import pytest
import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure the test database exists before initializing SQLAlchemy
try:
    conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/postgres", autocommit=True)
    conn.execute("CREATE DATABASE laundry_management_test")
    conn.close()
except Exception:
    pass

# Set the environment variable to use the test database
TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/laundry_management_test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Import app and database configuration AFTER setting the environment variable
from app.main import app
from app.core.database import Base, get_db
from app.apps.users.models import RoleEnum, User
from app.core.security import create_access_token

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables before tests run and drop them after."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Yield a database session wrapped in a transaction that rolls back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Return a TestClient with the database dependency overridden."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_student(db_session):
    user = User(
        name="Test Student",
        phone="0700000001",
        email="student@test.com",
        student_id="STD-001",
        role=RoleEnum.student,
        password_hash="fakehash",
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user

@pytest.fixture
def student_token_headers(test_student):
    token = create_access_token(str(test_student.id), {"role": test_student.role.value})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_vendor(db_session):
    user = User(
        name="Test Vendor",
        phone="0700000002",
        email="vendor@test.com",
        student_id=None,
        role=RoleEnum.vendor,
        password_hash="fakehash",
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user

@pytest.fixture
def vendor_token_headers(test_vendor):
    token = create_access_token(str(test_vendor.id), {"role": test_vendor.role.value})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_admin(db_session):
    user = User(
        name="Test Admin",
        phone="0700000003",
        email="admin@test.com",
        student_id=None,
        role=RoleEnum.admin,
        password_hash="fakehash",
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user

@pytest.fixture
def admin_token_headers(test_admin):
    token = create_access_token(str(test_admin.id), {"role": test_admin.role.value})
    return {"Authorization": f"Bearer {token}"}
