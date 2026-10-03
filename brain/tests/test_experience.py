import os
import uuid
import pytest
import psycopg2
from datetime import datetime, timezone
from pydantic import ValidationError

from models import ExperienceCreate
from experience import save_experience, get_experience

# Use environment variables for connection parameters, default to standard local setup
DB_USER = os.getenv("DB_USER", "malakul-tech")
DB_NAME = os.getenv("DB_NAME", "digital_self")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "5432")

@pytest.fixture(scope="function")
def db_connection():
    """Provides a database connection and rolls back after each test."""
    conn = psycopg2.connect(
        user=DB_USER,
        dbname=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )
    # Ensure any failure doesn't persist
    yield conn
    conn.rollback()
    conn.close()

def test_save_valid_experience(db_connection):
    exp_in = ExperienceCreate(
        raw_text="This is a test experience.",
        metadata={"source": "test"}
    )
    
    saved_exp = save_experience(db_connection, exp_in)
    
    assert saved_exp.id is not None
    assert saved_exp.raw_text == "This is a test experience."
    assert saved_exp.occurred_at is None
    assert saved_exp.created_at is not None
    assert saved_exp.metadata == {"source": "test"}
    
    # Retrieve it back
    retrieved = get_experience(db_connection, saved_exp.id)
    assert retrieved is not None
    assert retrieved.id == saved_exp.id
    assert retrieved.raw_text == saved_exp.raw_text
    assert retrieved.created_at == saved_exp.created_at
    assert retrieved.metadata == saved_exp.metadata

def test_save_experience_with_occurred_at(db_connection):
    past_time = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    exp_in = ExperienceCreate(
        raw_text="Happened in the past",
        occurred_at=past_time
    )
    
    saved_exp = save_experience(db_connection, exp_in)
    assert saved_exp.occurred_at == past_time

def test_blank_raw_text_rejected_by_model():
    with pytest.raises(ValidationError):
        ExperienceCreate(raw_text="   ")

def test_blank_raw_text_rejected_by_function(db_connection):
    # Bypassing pydantic validation for testing the function validation
    class MockExp:
        raw_text = "   "
        occurred_at = None
        metadata = {}
        
    with pytest.raises(ValueError, match="raw_text must not be blank"):
        save_experience(db_connection, MockExp())
        
def test_database_error_rollback(db_connection):
    # Try inserting directly violating DB constraint
    with pytest.raises(psycopg2.errors.CheckViolation):
        with db_connection.cursor() as cur:
            cur.execute("INSERT INTO experiences (raw_text) VALUES ('   ')")

def test_raw_text_identical(db_connection):
    complex_text = "I went to the store... \n and I bought 3 apples! 🍎"
    exp_in = ExperienceCreate(raw_text=complex_text)
    
    saved_exp = save_experience(db_connection, exp_in)
    
    # Should be perfectly identical
    assert saved_exp.raw_text == complex_text
