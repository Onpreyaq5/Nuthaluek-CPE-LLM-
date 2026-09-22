import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "04_course_data_services"}

def test_list_courses():
    response = client.get("/courses?q=CPE")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "next_cursor" in data
    assert len(data["items"]) > 0
    
    # Assert schema shape
    course = data["items"][0]
    assert "code" in course
    assert "name_th" in course
    assert "credits" in course

def test_list_sections():
    response = client.get("/courses/CPE301/sections")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    
    # Assert schema shape
    section = data["items"][0]
    assert "section_id" in section
    assert "course_code" in section
    assert "meetings" in section
    assert isinstance(section["meetings"], list)

def test_sections_bulk():
    response = client.post("/sections/bulk", json={"ids": ["CPE301-01"]})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["section_id"] == "CPE301-01"

def test_search_courses_for_03():
    response = client.post("/courses/search", json={"q": "ข้อมูล", "term": "1/2569"})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["items"][0]["code"] == "CPE301"
