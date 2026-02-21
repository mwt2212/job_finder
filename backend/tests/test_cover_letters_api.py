import json
from pathlib import Path


def _insert_job(app):
    return app.upsert_job(
        {
            "url": "https://example.com/job/cover",
            "title": "Operations Analyst / Reporting",
            "company": "Ruan",
            "location": "Des Moines, IA",
            "workplace": "hybrid",
            "posted": "1 day ago",
            "description": "x" * 600,
            "source": "Des Moines",
        }
    )


def test_cover_letter_template_crud_contract(app_ctx):
    listing0 = app_ctx.client.get("/cover-letter-templates")
    assert listing0.status_code == 200
    assert listing0.json()["items"] == []

    created = app_ctx.client.post("/cover-letter-templates", json={"text": "Dear Hiring Manager,\n\nBody 1\n\nBody 2\n\nBody 3\n\nSincerely,\nMe"})
    assert created.status_code == 200
    template_id = created.json()["item"]["id"]

    updated = app_ctx.client.put(f"/cover-letter-templates/{template_id}", json={"text": "Updated template"})
    assert updated.status_code == 200
    assert updated.json()["item"]["text"] == "Updated template"

    listing1 = app_ctx.client.get("/cover-letter-templates")
    assert len(listing1.json()["items"]) == 1

    deleted = app_ctx.client.delete(f"/cover-letter-templates/{template_id}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

    missing_delete = app_ctx.client.delete(f"/cover-letter-templates/{template_id}")
    assert missing_delete.status_code == 404


def test_cover_letter_generate_save_list_export_txt(app_ctx, monkeypatch):
    job_id = _insert_job(app_ctx.app)
    monkeypatch.setattr(
        app_ctx.app,
        "_call_model",
        lambda prompt, model: {
            "text": json.dumps({"paragraphs": ["Opening paragraph.", "Body paragraph.", "Closing paragraph."]}),
            "usage": {"input_tokens": 100, "output_tokens": 120, "cached_input_tokens": 10},
        },
    )

    create = app_ctx.client.post(
        "/cover-letters/generate",
        json={
            "job_id": job_id,
            "feedback": "Keep it concise",
            "model": "gpt-4.1",
            "draft": "Dear Hiring Manager,\n\nSeed 1\n\nSeed 2\n\nSeed 3\n\nSincerely,\nCandidate",
            "locked_indices": [1],
        },
    )
    assert create.status_code == 200
    cover_id = create.json()["id"]

    listing = app_ctx.client.get(f"/cover-letters/{job_id}")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["id"] == cover_id

    save = app_ctx.client.post("/cover-letters/save", json={"id": cover_id, "content": "Edited body", "feedback": "v2"})
    assert save.status_code == 200
    assert save.json()["ok"] is True

    exported = app_ctx.client.get(f"/cover-letters/export/{cover_id}?format=txt")
    assert exported.status_code == 200
    export_path = Path(exported.json()["path"])
    assert export_path.exists()
    assert "Edited body" in export_path.read_text(encoding="utf-8")


def test_cover_letter_generate_error_edges(app_ctx, monkeypatch):
    missing_job = app_ctx.client.post("/cover-letters/generate", json={"job_id": 999999, "feedback": ""})
    assert missing_job.status_code == 404

    job_id = _insert_job(app_ctx.app)
    bad_template = app_ctx.client.post(
        "/cover-letters/generate",
        json={"job_id": job_id, "template_id": "missing", "feedback": ""},
    )
    assert bad_template.status_code == 404

    monkeypatch.setattr(app_ctx.app, "_call_model", lambda prompt, model: {"text": "", "usage": {}})
    empty_model_output = app_ctx.client.post("/cover-letters/generate", json={"job_id": job_id, "feedback": ""})
    assert empty_model_output.status_code == 500


def test_cover_letter_export_errors(app_ctx):
    missing = app_ctx.client.get("/cover-letters/export/99999?format=txt")
    assert missing.status_code == 404

    job_id = _insert_job(app_ctx.app)
    cover_id = app_ctx.app.insert_cover_letter(job_id, "Hello", "", "gpt-4.1")
    unsupported = app_ctx.client.get(f"/cover-letters/export/{cover_id}?format=rtf")
    assert unsupported.status_code == 400
