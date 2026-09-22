import sys
import os

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

print("Testing /courses...")
resp = client.get("/courses?q=CPE")
assert resp.status_code == 200, resp.text
data = resp.json()
print("GET /courses =>", data)
assert "items" in data
assert "code" in data["items"][0]

print("\nTesting /courses/{code}/sections...")
resp = client.get("/courses/CPE301/sections")
assert resp.status_code == 200, resp.text
data = resp.json()
print("GET /courses/CPE301/sections =>", data)
assert "items" in data
assert "section_id" in data["items"][0]

print("\nTesting /sections/bulk...")
resp = client.post("/sections/bulk", json={"ids": ["CPE301-01"]})
assert resp.status_code == 200, resp.text
data = resp.json()
print("POST /sections/bulk =>", data)
assert len(data["items"]) == 1

print("\nTesting /courses/search...")
resp = client.post("/courses/search", json={"q": "ข้อมูล"})
assert resp.status_code == 200, resp.text
data = resp.json()
print("POST /courses/search =>", data)
assert len(data["items"]) > 0

print("\nALL TESTS PASSED!")
