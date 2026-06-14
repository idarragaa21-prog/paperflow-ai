"""Push references to a Zotero library via the Zotero Web API.

Optional: needs the user's Zotero API key and numeric user (or group) ID, from
zotero.org/settings/keys. Nothing is stored server-side; credentials are passed
per request. Falls back cleanly with a clear error if Zotero can't be reached.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import uuid

API = "https://api.zotero.org"
LOCAL = "http://127.0.0.1:23119"  # Zotero desktop connector server


def _creators(authors: str) -> list[dict]:
    out = []
    for a in re.split(r"[;,]\s*(?=[A-ZÁÉÍÓÚÑ])", authors or ""):
        a = a.strip()
        if not a:
            continue
        if "," in a:
            last, _, first = a.partition(",")
        else:
            parts = a.split()
            last, first = parts[0], " ".join(parts[1:])
        out.append({"creatorType": "author", "lastName": last.strip(), "firstName": first.strip()})
    return out or [{"creatorType": "author", "name": authors.strip()}] if authors else []


def _item(record: dict, collection_key: str | None = None) -> dict:
    extra = []
    if record.get("pmid"):
        extra.append(f"PMID: {record['pmid']}")
    if record.get("pmcid"):
        extra.append(f"PMCID: {record['pmcid']}")
    item = {
        "itemType": "journalArticle",
        "title": record.get("title", ""),
        "creators": _creators(record.get("authors", "")),
        "publicationTitle": record.get("journal", ""),
        "date": str(record.get("year", "")),
        "DOI": record.get("doi") or "",
        "abstractNote": record.get("abstract", ""),
        "url": record.get("doi_url") or record.get("pdf_url") or "",
        "extra": "\n".join(extra),
    }
    if collection_key:
        item["collections"] = [collection_key]
    return item


def _post(url: str, api_key: str, payload, *, timeout: int = 40) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Zotero-API-Key": api_key, "Zotero-API-Version": "3", "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def push_to_zotero(records: list[dict], api_key: str, user_id: str, *,
                   library_type: str = "user", collection: str | None = None) -> dict:
    if not api_key or not user_id:
        raise ValueError("Faltan la clave de API y el ID de usuario de Zotero.")
    if not records:
        raise ValueError("No hay referencias para enviar.")
    base = f"{API}/{'groups' if library_type == 'group' else 'users'}/{user_id}"

    collection_key = None
    if collection:
        try:
            res = _post(f"{base}/collections", api_key, [{"name": collection}])
            collection_key = (res.get("success") or {}).get("0") or (res.get("successful") or {}).get("0", {}).get("key")
        except Exception:  # noqa: BLE001 — collection optional
            collection_key = None

    created, failed = 0, 0
    try:
        for i in range(0, len(records), 50):
            batch = [_item(r, collection_key) for r in records[i:i + 50]]
            res = _post(f"{base}/items", api_key, batch)
            created += len(res.get("successful") or res.get("success") or {})
            failed += len(res.get("failed") or {})
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        detail = exc.read().decode("utf-8", "ignore")[:200] if hasattr(exc, "read") else str(exc)
        raise ValueError(f"Zotero rechazó la petición ({exc.code}): {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"No se pudo conectar con Zotero: {exc}") from exc

    return {"created": created, "failed": failed, "collection": collection if collection_key else None}


# --- Local connector (Zotero desktop, no API key) ---------------------------
_LOCAL_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "MetaForge",
    "X-Zotero-Connector-API-Version": "3",
    "Zotero-Allowed-Request": "true",
}


def local_available(timeout: int = 2) -> bool:
    """Whether the Zotero desktop connector is running on this machine."""
    try:
        req = urllib.request.Request(f"{LOCAL}/connector/ping", headers=_LOCAL_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def push_local(records: list[dict], *, timeout: int = 25) -> dict:
    """Send items to the running Zotero desktop via its local connector.

    No API key needed — Zotero just has to be open. Items are saved to the
    collection currently selected in Zotero.
    """
    if not records:
        raise ValueError("No hay referencias para enviar.")
    if not local_available():
        raise ValueError("Zotero de escritorio no está abierto (conector local 127.0.0.1:23119 no responde).")
    payload = {
        "sessionID": uuid.uuid4().hex,
        "uri": "http://localhost/metaforge",
        "items": [_item(r) for r in records],
    }
    req = urllib.request.Request(f"{LOCAL}/connector/saveItems",
                                 data=json.dumps(payload).encode("utf-8"),
                                 method="POST", headers=_LOCAL_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:160] if hasattr(exc, "read") else ""
        raise ValueError(f"Zotero local rechazó la petición ({exc.code}). {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"No se pudo conectar con el Zotero local: {exc}") from exc
    return {"created": len(records), "via": "local"}
