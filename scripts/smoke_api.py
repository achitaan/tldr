"""Exercise a running local API and worker using a temporary, original course.

Run with backend/.venv/Scripts/python.exe scripts/smoke_api.py.
No model request is submitted. Only the course created here is deleted.
"""
from __future__ import annotations

import io
import time
import uuid
import zipfile

import requests
from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    session = requests.Session()
    session.trust_env = False
    base = "http://127.0.0.1:8765/api"

    def request(method: str, path: str, expected: int = 200, **kwargs):
        response = session.request(method, base + path, timeout=30, **kwargs)
        assert response.status_code == expected, (path, response.status_code, response.text[:300])
        return response

    status = request("GET", "/status/").json()
    assert status["worker"]["running"], "Start the local study worker first."
    course = request("POST", "/courses/", 201, json={"name": "Verification " + uuid.uuid4().hex[:8]}).json()
    course_id = course["id"]
    try:
        source = request("POST", "/sources/", 201, json={
            "course": course_id, "title": "Original bus-read notes",
            "text": "A teaching bus places address 16 on the address lines. Read request stays high until data is valid. The processor then samples 42. This is a simplified handshake, not a named processor protocol.",
        }).json()

        def wait_source(source_id):
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                value = request("GET", f"/sources/{source_id}/").json()
                if value["status"] == "ready":
                    return value
                assert value["status"] != "error", value["error"]
                time.sleep(0.3)
            raise AssertionError("Source ingestion did not finish within 60 seconds")

        source = wait_source(source["id"])
        page = source["pages"][0]
        corrected = page["text"] + " Keep the address stable until sampling."
        page = request("PATCH", f"/pages/{page['id']}/", json={"text": corrected}).json()
        assert page["corrected"] and page["original_text"] != page["text"]

        picture = Image.new("RGB", (1000, 420), "white")
        draw = ImageDraw.Draw(picture)
        draw.rectangle((60, 130, 300, 290), outline="black", width=5)
        draw.rectangle((700, 130, 940, 290), outline="black", width=5)
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 30)
        draw.text((70, 40), "PROCESSOR sends requests to MEMORY", fill="black", font=font)
        draw.text((80, 180), "PROCESSOR", fill="black", font=font)
        draw.text((725, 180), "MEMORY", fill="black", font=font)
        draw.line((300, 170, 700, 170), fill="black", width=5)
        draw.line((700, 250, 300, 250), fill="black", width=5)
        image_file = io.BytesIO()
        picture.save(image_file, format="PNG")
        image_file.seek(0)
        image_source = request("POST", "/sources/", 201,
                               data={"course": str(course_id), "title": "Original bus sketch"},
                               files={"file": ("bus.png", image_file, "image/png")}).json()
        image_source = wait_source(image_source["id"])
        image_page = image_source["pages"][0]
        assert image_page["image_url"] and image_page["width"] > 0
        image_url = image_page["image_url"]
        if status["ocr_available"]:
            assert all(word in image_page["text"].upper() for word in ('PROCESSOR', 'MEMORY')), image_page["text"]
        region = request("POST", "/regions/", 201, json={
            "page": image_page["id"], "label": "Processor", "x": 0.06, "y": 0.3,
            "width": 0.24, "height": 0.4, "text": "Processor", "confirmed": True,
        }).json()
        region = request("PATCH", f"/regions/{region['id']}/", json={"width": 0.25}).json()
        assert region["width"] == 0.25
        conversation = request("POST", "/conversations/", 201,
                               json={"course": course_id, "title": "Read handshake"}).json()
        assert request("GET", f"/conversations/{conversation['id']}/messages/").json() == []
        card = request("POST", "/study-items/", 201, json={
            "course": course_id, "kind": "flashcard", "title": "When should data be sampled?",
            "body": "Read handshake", "data": {"answer": "After data valid."},
        }).json()
        request("PATCH", f"/study-items/{card['id']}/", json={"completed": True})
        assert request("GET", f"/study-items/?course={course_id}").json()[0]["completed"]
        exported = request("GET", f"/courses/{course_id}/export/")
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            assert any(name.endswith(".json") for name in archive.namelist())
            assert len(archive.namelist()) >= 3
        print("PASS: text/image ingestion, OCR correction, region edit, conversation storage, study item persistence and ZIP export")
        print(f"OCR available: {status['ocr_available']}; no cloud generation requested")
    finally:
        request("DELETE", f"/courses/{course_id}/", 204)
    request("GET", f"/courses/{course_id}/", 404)
    if image_url.startswith('/media/'):
        assert session.get('http://127.0.0.1:8765' + image_url, timeout=10).status_code == 404
    print("PASS: temporary course and associated records deleted")


if __name__ == "__main__":
    main()
