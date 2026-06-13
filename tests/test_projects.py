import pytest
from fastapi.testclient import TestClient

from metaforge import projects as P
from metaforge.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def tmp_data(monkeypatch, tmp_path):
    monkeypatch.setenv("METAFORGE_DATA", str(tmp_path))


def test_save_list_load_delete():
    rec = P.save_project({"topic": "café", "measure": "OR"}, "Revisión café")
    assert rec["id"].startswith("revisi-n-caf") or "revisi" in rec["id"]
    listed = P.list_projects()
    assert any(p["id"] == rec["id"] for p in listed)
    loaded = P.load_project(rec["id"])
    assert loaded["state"]["topic"] == "café"
    assert P.delete_project(rec["id"]) is True
    with pytest.raises(ValueError):
        P.load_project(rec["id"])


def test_resave_keeps_id_and_created():
    rec = P.save_project({"a": 1}, "X")
    rec2 = P.save_project({"a": 2}, "X", rec["id"])
    assert rec2["id"] == rec["id"]
    assert P.load_project(rec["id"])["state"]["a"] == 2


def test_invalid_id_rejected():
    with pytest.raises(ValueError):
        P.load_project("../etc/passwd")


def test_api_projects_roundtrip():
    save = client.post("/projects", json={"name": "API proj", "state": {"step": 3}})
    assert save.status_code == 200
    pid = save.json()["id"]
    assert any(p["id"] == pid for p in client.get("/projects").json()["projects"])
    assert client.get("/projects/" + pid).json()["state"]["step"] == 3
    assert client.delete("/projects/" + pid).json()["deleted"] is True
    assert client.get("/projects/" + pid).status_code == 404
