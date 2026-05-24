import pytest
from unittest.mock import patch, MagicMock
from lib import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_register(client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("lib.get_db", return_value=mock_conn):
        response = client.post("/register", json={
            "username": "testuser",
            "password": "testpass"
        })
    assert response.status_code == 200
