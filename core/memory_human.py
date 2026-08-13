"""core/memory_human.py — Human-like persistent memory backed by Google Drive.

Architecture
------------
JARVIS_MEMORY (Drive root folder)
├── ACTIVE_MEMORY/          sessions for the moving 4-day detailed window
├── SUMMARISED_MEMORY/      daily/ weekly/ monthly permanent summaries
├── IMPORTANT_MEMORY/       explicit user-saved memories (never compressed)
├── ERROR_CORRECTION_MEMORY/ user corrections (high retrieval priority)
├── KNOWLEDGE_MEMORY/       durable knowledge extracted from conversations
└── INDEX/                  memory_index.json, important_index.json,
                            session_index.json (incremental, no full scans)

Every write is mirrored locally first (atomic), then synchronised to Drive.
If Drive is down the memory stays local and is retried (pending sync).
Only retrieved, ranked, budget-bounded memory is ever injected into prompts.

Design rules honoured here:
- Never dump the whole store into the LLM (hard token budget).
- Never block request latency on Drive uploads (buffered flushes).
- Never silently discard memory on network failure.
- Never mutate or drop an explicitly saved memory without history.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, time as datetime_time
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.memory import extract_memory_intent

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

MEMORY_MAX_CONTEXT_TOKENS = int(os.getenv("MEMORY_MAX_CONTEXT_TOKENS", "4000"))


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class MemoryConfig:
    """Memory subsystem configuration (all values overridable via env)."""

    root_name: str = os.getenv("JARVIS_MEMORY_ROOT", "JARVIS_MEMORY")
    active_days: int = int(os.getenv("MEMORY_ACTIVE_DAYS", "4"))
    max_context_tokens: int = int(os.getenv("MEMORY_MAX_CONTEXT_TOKENS", "4000"))
    summary_enabled: bool = _env_bool("MEMORY_SUMMARY_ENABLED", True)
    drive_enabled: bool = _env_bool("MEMORY_DRIVE_ENABLED", True)
    local_fallback: bool = _env_bool("MEMORY_LOCAL_FALLBACK", True)
    auto_promotion: bool = _env_bool("MEMORY_AUTO_PROMOTION", True)
    correction_enabled: bool = _env_bool("MEMORY_CORRECTION_ENABLED", True)
    index_enabled: bool = _env_bool("MEMORY_INDEX_ENABLED", True)

    local_root: str = os.getenv(
        "MEMORY_LOCAL_ROOT",
        str(Path(__file__).resolve().parent.parent / "data" / "memory_human"),
    )
    credentials_file: str = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "")
    token_file: str = os.getenv("GOOGLE_DRIVE_TOKEN_FILE", "")

    summarizer_max_messages: int = int(os.getenv("MEMORY_SUMMARY_MAX_MESSAGES", "240"))
    resumable_threshold_bytes: int = int(os.getenv("MEMORY_RESUMABLE_THRESHOLD", str(5 * 1024 * 1024)))
    summary_retention_days: int = int(os.getenv("MEMORY_SUMMARY_RETENTION_DAYS", "20"))


# ---------------------------------------------------------------------------
# FOLDER LAYOUT
# ---------------------------------------------------------------------------

ROOT_FOLDER = "JARVIS_MEMORY"

FOLDERS = {
    "active": "ACTIVE_MEMORY",
    "summary": "SUMMARISED_MEMORY",
    "summary_daily": "SUMMARISED_MEMORY/daily",
    "summary_weekly": "SUMMARISED_MEMORY/weekly",
    "summary_monthly": "SUMMARISED_MEMORY/monthly",
    "important": "IMPORTANT_MEMORY",
    "correction": "ERROR_CORRECTION_MEMORY",
    "knowledge": "KNOWLEDGE_MEMORY",
    "index": "INDEX",
}

INDEX_FILES = ("memory_index.json", "important_index.json", "session_index.json")


# ---------------------------------------------------------------------------
# PERSISTENCE HELPERS
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _local_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> datetime.date:
    return datetime.now().date()


def _date_to_str(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")


def _session_stamp() -> str:
    return datetime.now().strftime("%d-%m-%Y_%H-%M-%S")


def _content_hash(text: str) -> str:
    return hashlib.sha1(
        " ".join(str(text or "").lower().split()).encode("utf-8")
    ).hexdigest()[:16]


_STOP = frozenset(
    "a an the is are was were be been being am what which who whom whose my mine "
    "your yours our ours i me we us you it its this that these those to of for on "
    "in at by with from up down out off over under do does did have has had not no "
    "and or but if then so because as here there when where why how all any both "
    "each few more most other some such only own same too very can will just "
    "should would could may might must about than into please s re ve d ll don t "
    "dont remember recall saved save stored store memorize forget know want need "
    "used use using say said tell told ask asked go get me about your our".split()
)


def _tokens(text: str) -> List[str]:
    return [
        t
        for t in re.findall(r"[a-z0-9']+", str(text or "").lower())
        if len(t) > 1 and t not in _STOP
    ]


def _keywords(content: str, extra: Optional[List[str]] = None, limit: int = 12) -> List[str]:
    from collections import Counter

    tokens = _tokens(content) + [t.lower().strip() for t in (extra or []) if t]
    counter = Counter(tokens)
    return [w for w, _ in counter.most_common(limit)]


def _estimate_tokens(text: str) -> int:
    return max(1, len(str(text)) // 4)


# ---------------------------------------------------------------------------
# DRIVE API ABSTRACTION
# ---------------------------------------------------------------------------


class GoogleDriveApi:
    """Thin wrapper over Google Drive API v3.

    Only created when googleapiclient/google-auth are installed and
    credentials are configured. Everything else flows through the same
    narrow interface used by tests (FakeDrive).
    """

    FIELDS = "id,name,mimeType,parents,size,modifiedTime,trashed"

    def __init__(
        self,
        credentials_file: str = "",
        token_file: str = "",
        client_secret: Optional[Dict[str, Any]] = None,
        token_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google.oauth2.service_account import Credentials as SACredentials
        from googleapiclient.discovery import build

        self._service = None
        creds = None

        if isinstance(client_secret, dict) and isinstance(token_info, dict):
            creds = Credentials(
                token=token_info.get("token", ""),
                refresh_token=token_info.get("refresh_token"),
                token_uri=client_secret.get("token_uri"),
                client_id=client_secret.get("client_id"),
                client_secret=client_secret.get("client_secret"),
            )
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
            return

        if credentials_file:
            try:
                with open(credentials_file, "r", encoding="utf-8") as f:
                    client_secret = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("DRIVE_CONFIG client_secret unreadable: %s", exc)

        if client_secret and client_secret.get("type") == "service_account":
            creds = SACredentials.from_service_account_info(
                client_secret, scopes=["https://www.googleapis.com/auth/drive"]
            )
        elif token_file and os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(
                token_file,
                ["https://www.googleapis.com/auth/drive"],
            )
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(token_file, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                except Exception as exc:
                    logger.error("DRIVE_AUTH token refresh failed: %s", exc)
        elif client_secret:
            raise RuntimeError(
                "DRIVE_AUTH: OAuth token missing. Run the one-time "
                "authorization flow to produce the token file, then set "
                "GOOGLE_DRIVE_TOKEN_FILE."
            )
        else:
            raise RuntimeError(
                "DRIVE_AUTH: no credentials. Set GOOGLE_DRIVE_CREDENTIALS_FILE "
                "and GOOGLE_DRIVE_TOKEN_FILE."
            )

        self._service = build(
            "drive", "v3", credentials=creds, cache_discovery=False
        )

    # -- narrow interface (mirrored by FakeDrive in tests) -------------

    def create_file(
        self,
        parent_id: str,
        name: str,
        mime_type: str = "application/json",
        media_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        body = {
            "name": name,
            "parents": [parent_id],
            "mimeType": mime_type,
        }
        return self._do_upload(body, media_bytes)

    def update_file(
        self,
        file_id: str,
        name: Optional[str] = None,
        mime_type: Optional[str] = None,
        media_bytes: Optional[bytes] = None,
        trashed: Optional[bool] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if mime_type is not None:
            body["mimeType"] = mime_type
        if trashed is not None:
            body["trashed"] = trashed
        return self._do_upload(body, media_bytes, file_id=file_id)

    def _do_upload(
        self,
        body: Dict[str, Any],
        media_bytes: Optional[bytes],
        file_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        from googleapiclient.http import MediaIoBaseUpload

        import io

        media = None
        if media_bytes is not None:
            media = MediaIoBaseUpload(
                io.BytesIO(media_bytes),
                mimetype=body.get("mimeType", "application/json"),
                chunksize=262144,
                resumable=len(media_bytes)
                >= int(os.getenv("MEMORY_RESUMABLE_THRESHOLD", str(5 * 1024 * 1024))),
            )
        try:
            if file_id:
                request = self._service.files().update(
                    fileId=file_id, body=body, media_body=media, fields=self.FIELDS
                )
            else:
                request = self._service.files().create(
                    body=body, media_body=media, fields=self.FIELDS
                )
            if media is not None and getattr(media, "resumable", False):
                response = None
                while response is None:
                    status, response = request.next_chunk()
            else:
                response = request.execute()
            return response or {}
        except Exception as exc:
            logger.error("DRIVE_UPLOAD_FAILED name=%s error=%s", body.get("name"), exc)
            raise

    def get_file(self, file_id: str) -> Dict[str, Any]:
        return self._service.files().get(fileId=file_id, fields=self.FIELDS).execute()

    def search_files(
        self,
        query: str,
        page_size: int = 500,
    ) -> List[Dict[str, Any]]:
        results = (
            self._service.files()
            .list(q=query, fields=f"files({self.FIELDS})", pageSize=page_size, includeItemsFromAllDrives=True, supportsAllDrives=True)
            .execute()
        )
        return results.get("files", [])

    def list_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        return self.search_files(f"'{folder_id}' in parents and trashed=false")

    def download(self, file_id: str) -> bytes:
        import io

        data = io.BytesIO()
        request = self._service.files().get_media(fileId=file_id)
        from googleapiclient.http import MediaIoBaseDownload

        downloader = MediaIoBaseDownload(data, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return data.getvalue()

    def delete_file(self, file_id: str) -> None:
        self._service.files().delete(fileId=file_id).execute()

    def update_parents(self, file_id: str, parents: List[str]) -> None:
        self._service.files().update(
            fileId=file_id, addParents=",".join(parents), removeParents=","
        ).execute()


# ---------------------------------------------------------------------------
# DRIVE MEMORY STORE
# ---------------------------------------------------------------------------


class GoogleDriveMemoryStore:
    """Dedicated Drive layer. Everything else talks through this store.

    Supports create/read/update/search/delete/move/list plus a local mirror
    and a pending-sync journal so Drive outages never lose memory.
    """

    def __init__(
        self,
        api: Any = None,
        config: Optional[MemoryConfig] = None,
        local_root: Optional[str] = None,
    ) -> None:
        self.config = config or MemoryConfig()
        self.api = api
        self.local_root = Path(
            local_root or self.config.local_root
        )
        self.local_root.mkdir(parents=True, exist_ok=True)

        self._hierarchy: Dict[str, str] = {}
        self._pending: List[Dict[str, Any]] = []
        self._pending_path = self.local_root / "pending_sync.json"
        self._hierarchy_path = self.local_root / "hierarchy.json"
        self._lock = threading.Lock()

        self._load_hierarchy()
        self._load_pending()

    # -- hierarchy -----------------------------------------------------

    def ensure_hierarchy(self) -> bool:
        """Create JARVIS_MEMORY and all subfolders if missing.

        Never creates duplicates: folders are located by name under the
        root and stored IDs are cached in hierarchy.json.
        """
        if not self.api:
            return False

        try:
            root_id = self._hierarchy.get("root")

            if not root_id:
                found = self.api.search_files(
                    f"name='{self.config.root_name}' and "
                    f"mimeType='application/vnd.google-apps.folder' and "
                    f"trashed=false"
                )
                root_id = found[0]["id"] if found else None

            if not root_id:
                created = self.api.create_file(
                    parent_id="root",
                    name=self.config.root_name,
                    mime_type="application/vnd.google-apps.folder",
                )
                root_id = created["id"]
                logger.info(
                    "DRIVE_ROOT created id=%s name=%s",
                    root_id,
                    self.config.root_name,
                )
            else:
                logger.info(
                    "DRIVE_ROOT found id=%s name=%s",
                    root_id,
                    self.config.root_name,
                )

            self._hierarchy["root"] = root_id

            for key, sub in (
                ("active", FOLDERS["active"]),
                ("summary", FOLDERS["summary"]),
                ("summary_daily", FOLDERS["summary_daily"]),
                ("summary_weekly", FOLDERS["summary_weekly"]),
                ("summary_monthly", FOLDERS["summary_monthly"]),
                ("important", FOLDERS["important"]),
                ("correction", FOLDERS["correction"]),
                ("knowledge", FOLDERS["knowledge"]),
                ("index", FOLDERS["index"]),
            ):
                self._ensure_folder(root_id, key, sub)

            self._save_hierarchy()
            return True
        except Exception as exc:
            logger.error("DRIVE_HIERARCHY_FAILED error=%s", exc)
            return False

    def _ensure_folder(self, parent_id: str, key: str, name: str) -> None:
        existing = self._hierarchy.get(key)
        if existing:
            return
        try:
            found = self.api.search_files(
                f"name='{name}' and "
                f"'{parent_id}' in parents and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"trashed=false"
            )
            folder_id = found[0]["id"] if found else None
            if not folder_id:
                created = self.api.create_file(
                    parent_id=parent_id,
                    name=name,
                    mime_type="application/vnd.google-apps.folder",
                )
                folder_id = created["id"]
            self._hierarchy[key] = folder_id
        except Exception as exc:
            logger.error(
                "DRIVE_FOLDER_FAILED name=%s error=%s", name, exc
            )
            raise

    def _load_hierarchy(self) -> None:
        try:
            if self._hierarchy_path.exists():
                with open(self._hierarchy_path, "r", encoding="utf-8") as f:
                    self._hierarchy = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._hierarchy = {}

    def _save_hierarchy(self) -> None:
        try:
            tmp = self._hierarchy_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._hierarchy, f, indent=2)
            os.replace(tmp, self._hierarchy_path)
        except OSError as exc:
            logger.error("HIERARCHY_CACHE_SAVE_FAILED error=%s", exc)

    def folder_id(self, key: str) -> Optional[str]:
        return self._hierarchy.get(key)

    # -- local mirror ---------------------------------------------------

    def _local_path(self, folder_key: str, name: str) -> Path:
        safe = str(name).replace("/", "_").replace("\\", "_")
        path = self.local_root / folder_key / safe
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _write_local_atomic(self, path: Path, data: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    # -- pending sync journal -------------------------------------------

    def _load_pending(self) -> None:
        try:
            if self._pending_path.exists():
                with open(self._pending_path, "r", encoding="utf-8") as f:
                    self._pending = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._pending = []
        if not isinstance(self._pending, list):
            self._pending = []

    def _save_pending(self) -> None:
        try:
            self._write_local_atomic(
                self._pending_path, json.dumps(self._pending, indent=2)
            )
        except OSError as exc:
            logger.error("PENDING_SYNC_SAVE_FAILED error=%s", exc)

    def pending_count(self) -> int:
        return len(self._pending)

    def _drop_pending(self, folder_key: str, name: str) -> None:
        self._pending = [
            p
            for p in self._pending
            if not (p.get("folder") == folder_key and p.get("name") == name)
        ]
        self._save_pending()

    # -- file operations ------------------------------------------------

    def save_file(
        self,
        folder_key: str,
        name: str,
        data: Any,
    ) -> Dict[str, Any]:
        """Persist data locally (atomic), then synchronise to Drive.

        Returns {"synced": bool, "file_id": str|None, "local": path}.
        A Drive failure marks the entry pending and keeps the local copy.
        """
        path = self._local_path(folder_key, name)
        payload = json.dumps(data, indent=2, ensure_ascii=False)
        self._write_local_atomic(path, payload)

        with self._lock:
            existing = next(
                (
                    p
                    for p in self._pending
                    if p.get("folder") == folder_key and p.get("name") == name
                ),
                None,
            )
            if existing:
                existing.pop("error", None)
                existing["attempts"] = 0
            else:
                self._pending.append({
                    "folder": folder_key,
                    "name": name,
                    "attempts": 0,
                    "error": None,
                })
            self._save_pending()

        file_id = self._hierarchy.get(f"file:{folder_key}:{name}")
        synced = self._sync_one(folder_key, name, payload, file_id)

        if synced:
            return {
                "synced": True,
                "file_id": self._hierarchy.get(f"file:{folder_key}:{name}"),
                "local": str(path),
                "pending": False,
            }
        return {
            "synced": False,
            "file_id": None,
            "local": str(path),
            "pending": True,
        }

    def _sync_one(
        self,
        folder_key: str,
        name: str,
        payload: Optional[str],
        known_file_id: Optional[str],
    ) -> bool:
        if not self.api:
            return False

        folder_id = self._hierarchy.get(
            "summary_daily" if folder_key == "summary_daily"
            else "summary_weekly" if folder_key == "summary_weekly"
            else "summary_monthly" if folder_key == "summary_monthly"
            else folder_key
        )
        if not folder_id and folder_key not in (
            "summary_daily",
            "summary_weekly",
            "summary_monthly",
            "summary",
        ):
            return False

        if folder_key in ("summary_daily", "summary_weekly", "summary_monthly"):
            folder_id = self._hierarchy.get(folder_key) or self._hierarchy.get("summary")
        if folder_key == "summary":
            folder_id = self._hierarchy.get("summary")

        try:
            payload = payload or self._local_path(folder_key, name).read_text(
                encoding="utf-8"
            )
            media = payload.encode("utf-8")

            if known_file_id:
                self.api.update_file(
                    known_file_id, name=name, media_bytes=media
                )
            else:
                found = self.api.search_files(
                    f"name='{name}' and "
                    f"'{folder_id}' in parents and trashed=false"
                )
                file_id = found[0]["id"] if found else None
                if file_id:
                    self.api.update_file(file_id, name=name, media_bytes=media)
                else:
                    created = self.api.create_file(
                        parent_id=folder_id, name=name, media_bytes=media
                    )
                    file_id = created["id"]
                self._hierarchy[f"file:{folder_key}:{name}"] = file_id

            self._save_hierarchy()
            logger.info(
                "DRIVE_SYNC status=success folder=%s name=%s",
                folder_key,
                name,
            )
            return True
        except Exception as exc:
            logger.warning(
                "DRIVE_SYNC_FAILED folder=%s name=%s error=%s",
                folder_key,
                name,
                exc,
            )
            return False

    def sync_pending(self, max_attempts: int = 5) -> Tuple[int, int]:
        """Replay the pending journal; returns (synced, still_pending)."""
        if not self.api or not self._pending:
            return 0, len(self._pending)

        synced = 0
        still: List[Dict[str, Any]] = []
        for entry in self._pending:
            folder_key = entry.get("folder", "")
            name = entry.get("name", "")
            attempts = int(entry.get("attempts", 0))
            if attempts >= max_attempts:
                logger.warning(
                    "DRIVE_SYNC_GAVE_UP folder=%s name=%s attempts=%d",
                    folder_key,
                    name,
                    attempts,
                )
                still.append(entry)
                continue

            payload = None
            try:
                payload = self._local_path(folder_key, name).read_text(
                    encoding="utf-8"
                )
            except OSError:
                payload = None

            known = self._hierarchy.get(f"file:{folder_key}:{name}")
            if self._sync_one(folder_key, name, payload, known):
                synced += 1
                logger.info("DRIVE_SYNC retry_success folder=%s name=%s", folder_key, name)
            else:
                entry["attempts"] = attempts + 1
                entry["error"] = "sync retry failed"
                still.append(entry)

        self._pending = still
        self._save_pending()
        return synced, len(still)

    def read_file(self, folder_key: str, name: str) -> Optional[Dict[str, Any]]:
        """Read a stored memory file (local mirror first, Drive fallback)."""
        path = self._local_path(folder_key, name)
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

        if not self.api:
            return None
        file_id = self._hierarchy.get(f"file:{folder_key}:{name}")
        if not file_id:
            return None
        try:
            raw = self.api.download(file_id)
            return json.loads(raw.decode("utf-8"))
        except (Exception,) as exc:
            logger.warning("DRIVE_READ_FAILED name=%s error=%s", name, exc)
            return None

    def search_drive(self, query: str) -> List[Dict[str, Any]]:
        if not self.api:
            return []
        return self.api.search_files(query)

    def delete_file(
        self,
        folder_key: str,
        name: str,
        file_id: Optional[str] = None,
    ) -> bool:
        deleted_local = False
        path = self._local_path(folder_key, name)
        try:
            if path.exists():
                path.unlink()
                deleted_local = True
        except OSError:
            pass

        file_id = file_id or self._hierarchy.get(f"file:{folder_key}:{name}")
        if file_id and self.api:
            try:
                self.api.delete_file(file_id)
            except Exception as exc:
                logger.warning("DRIVE_DELETE_FAILED id=%s error=%s", file_id, exc)
        self._hierarchy.pop(f"file:{folder_key}:{name}", None)
        self._save_hierarchy()
        self._drop_pending(folder_key, name)
        return deleted_local or bool(file_id)

    def list_local(self, folder_key: str) -> List[Path]:
        root = self.local_root / folder_key
        if not root.exists():
            return []
        return sorted(
            p for p in root.iterdir() if p.is_file() and not p.name.endswith(".tmp")
        )


# ---------------------------------------------------------------------------
# HUMAN-LIKE MEMORY ORCHESTRATOR
# ---------------------------------------------------------------------------


class HumanLikeMemory:
    """Session, window, summarisation, important/correction/knowledge and
    retrieval orchestration for the Drive-backed memory system."""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        store: Optional[GoogleDriveMemoryStore] = None,
        summarizer: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
    ) -> None:
        self.config = config or MemoryConfig()
        self.store = store or GoogleDriveMemoryStore(config=self.config)
        self.summarizer = summarizer

        self._started = False
        self._drive_ready = False
        self._session: Optional[Dict[str, Any]] = None
        self._session_drive_file_id: Optional[str] = None
        self._session_path: Optional[Path] = None
        self._flush_lock = threading.Lock()
        self._last_flush = 0.0
        self._buffered = 0
        self._index: Dict[str, Any] = {}
        self._important_index: Dict[str, Any] = {}
        self._session_index: Dict[str, Any] = {}
        self._index_flushed_at = 0.0

        if self.store.api:
            logger.info(
                "MEMORY_INIT drive=enabled root=%s local=%s",
                self.config.root_name,
                self.config.local_root,
            )
        else:
            logger.info(
                "MEMORY_INIT drive=disabled(root=%s, api=None) local=%s "
                "fallback=%s",
                self.config.root_name,
                self.config.local_root,
                self.config.local_fallback,
            )

    # ------------------------------------------------------------------
    # STARTUP / SHUTDOWN
    # ------------------------------------------------------------------

    def startup(self) -> Dict[str, Any]:
        """Lightweight startup: hierarchy, indexes, repairs, rollover, cleanup."""
        if self._started:
            return {"started": True, "drive_ready": self._drive_ready}

        started = time.perf_counter()

        if self.config.drive_enabled and self.store.api:
            self._drive_ready = self.store.ensure_hierarchy()
        elif self.config.drive_enabled:
            logger.warning(
                "MEMORY_DRIVE_UNAVAILABLE google_libs_or_credentials_missing "
                "-> local fallback active"
            )
        else:
            logger.info("MEMORY_DRIVE disabled by configuration")

        if self.config.index_enabled:
            self._load_indexes()

        synced, pending = self.store.sync_pending()
        if synced or pending:
            logger.info(
                "DRIVE_SYNC startup synced=%d still_pending=%d", synced, pending
            )

        self._rollover_due_days()
        
        # NEW: 20-day summary cleanup
        if self.config.summary_enabled:
            self._cleanup_expired_summaries()

        self._recover_session()

        self._started = True
        logger.info(
            "MEMORY_STARTUP drive_ready=%s active_days=%d "
            "sessions_active=%d latency_ms=%.1f",
            self._drive_ready,
            self.config.active_days,
            len(self._active_session_files()),
            (time.perf_counter() - started) * 1000,
        )
        return {
            "started": True,
            "drive_ready": self._drive_ready,
            "pending_sync": self.store.pending_count(),
        }

    def is_started(self) -> bool:
        return self._started

    def shutdown(self) -> Dict[str, Any]:
        """Finalize the session and flush buffered state."""
        if self._session:
            self._finalize_session(ended=True)
        synced, pending = self.store.sync_pending()
        self._started = False
        logger.info(
            "MEMORY_SHUTDOWN session_finalized sync=%d pending=%d",
            synced,
            pending,
        )
        return {"session_finalized": True, "pending_sync": pending}

    # ------------------------------------------------------------------
    # SESSIONS
    # ------------------------------------------------------------------

    def _recover_session(self) -> None:
        active = self.store.local_root / "active_session.json"
        if active.exists():
            try:
                pointer = json.loads(active.read_text(encoding="utf-8"))
                name = pointer.get("session_file", "")
                path = self.store.local_root / "active" / name.replace("/", "_")
                if path.exists():
                    try:
                        session = json.loads(path.read_text(encoding="utf-8"))
                        session["recovered"] = True
                        self._write_session_local(session)
                        logger.info(
                            "MEMORY_SESSION_RECOVERED id=%s file=%s",
                            session.get("session_id"),
                            name,
                        )
                    except (OSError, json.JSONDecodeError):
                        logger.warning("MEMORY_SESSION_RECOVERY_FAILED file=%s", name)
            except (OSError, json.JSONDecodeError):
                pass
            try:
                active.unlink()
            except OSError:
                pass

        self._start_session(recovered=True)

    def _start_session(self, recovered: bool = False) -> None:
        session_id = f"session-{_content_hash(_session_stamp())}"
        now = _now_iso()
        self._session = {
            "session_id": session_id,
            "started_at": now,
            "ended_at": None,
            "timezone": time.strftime("%Z"),
            "recovered": recovered,
            "status": "active",
            "messages": [],
        }
        self._session_path = self.store._local_path(
            "active", f"{_session_stamp()}.json"
        )
        self._session_drive_file_id = None
        self._write_session_local(self._session)

        pointer = self.store.local_root / "active_session.json"
        pointer.write_text(
            json.dumps({
                "session_id": session_id,
                "session_file": self._session_path.name,
            }),
            encoding="utf-8",
        )
        self._flush_session()
        logger.info("MEMORY_SESSION_START id=%s", session_id)

    def _finalize_session(self, ended: bool = True) -> None:
        if not self._session:
            return
        self._session["ended_at"] = _now_iso()
        self._session["status"] = "ended"
        self._write_session_local(self._session)
        self._flush_session()
        pointer = self.store.local_root / "active_session.json"
        try:
            if pointer.exists():
                pointer.unlink()
        except OSError:
            pass
        self._index_session(self._session)
        self._session = None

    def on_user_message(self, text: str) -> None:
        if not self._started or not text:
            return
        if self._session is None:
            self._start_session()
        assert self._session is not None
        self._session["messages"].append({
            "timestamp": _now_iso(),
            "role": "user",
            "content": str(text),
        })
        self._bump_session()

    def on_assistant_message(self, text: str) -> None:
        if not self._started or not text:
            return
        if self._session is None:
            return
        self._session["messages"].append({
            "timestamp": _now_iso(),
            "role": "assistant",
            "content": str(text),
        })
        self._bump_session()

    def _bump_session(self) -> None:
        self._buffered += 1
        self._write_session_local(self._session)
        now = time.time()
        # Debounced: flush at most every 2s OR when buffer is large.
        if self._buffered >= 20 or (now - self._last_flush) >= 2.0:
            self._flush_session()

    def _write_session_local(self, session: Dict[str, Any]) -> None:
        if not self._session_path:
            return
        self.store._write_local_atomic(
            self._session_path, json.dumps(session, indent=2, ensure_ascii=False)
        )

    def _flush_session(self) -> None:
        if not self._session or not self._session_path:
            return
        with self._flush_lock:
            if not self._session_path.exists():
                return
            data = self._session_path.read_text(encoding="utf-8")
            session = json.loads(data)
            self._session_drive_file_id = self.store._hierarchy.get(
                f"file:active:{self._session_path.name}"
            )
            result = self.store.save_file(
                "active", self._session_path.name, session
            )
            if result.get("synced"):
                self._session_drive_file_id = result.get("file_id")
            self._last_flush = time.time()
            self._buffered = 0

    def _active_session_files(self) -> List[Path]:
        return self.store.list_local("active")

    def _sessions_for_day(self, day: datetime.date) -> List[Dict[str, Any]]:
        """Load local session files whose session date matches `day`."""
        out: List[Dict[str, Any]] = []
        prefix = day.strftime("%d-%m-%Y")
        for path in self._active_session_files():
            if not path.name.startswith(prefix):
                continue
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return out

    # ------------------------------------------------------------------
    # FOUR-DAY WINDOW + ROLLOVER
    # ------------------------------------------------------------------

    def window_start_date(self, today: Optional[datetime.date] = None) -> datetime.date:
        today = today or _today()
        return today - timedelta(days=max(1, self.config.active_days) - 1)

    def _rollover_due_days(self) -> int:
        """Summarize every day that has crossed the active window."""
        if not self.config.summary_enabled:
            return 0
        processed = 0
        today = _today()
        window_start = self.window_start_date(today)
        for path in self._active_session_files():
            try:
                session_date = datetime.strptime(
                    path.name[:10], "%d-%m-%Y"
                ).date()
            except ValueError:
                continue
            if session_date >= window_start:
                continue
            if self._day_summarized(session_date):
                continue
            if self._summarize_day(session_date):
                processed += 1
        return processed

    def _day_summarized(self, day: datetime.date) -> bool:
        name = f"{day.strftime('%d-%m-%Y')}.json"
        summary = self.store.read_file("summary_daily", name)
        return summary is not None and summary.get("status") == "completed"

    def _summarize_day(self, day: datetime.date) -> bool:
        name = f"{day.strftime('%d-%m-%Y')}.json"
        sessions = self._sessions_for_day(day)
        if not sessions:
            # No sessions that day but files exist without parsable date.
            return False

        logger.info(
            "MEMORY_SUMMARY start day=%s sessions=%d",
            day,
            len(sessions),
        )

        messages: List[Dict[str, Any]] = []
        for session in sessions:
            messages.extend(session.get("messages", []))

        summary = self._build_summary(
            messages, day, granularity="daily"
        )

        saved = self.store.save_file("summary_daily", name, summary)
        if not saved.get("synced") and not self.config.drive_enabled:
            # Local-only mode still counts as persisted when fallback enabled.
            pass

        if not self.store.read_file("summary_daily", name):
            logger.error("MEMORY_SUMMARY failed day=%s (no local file)", day)
            return False

        # Mark the day's sessions historical (originals are retained).
        for session in sessions:
            session["status"] = "historical"
            session["summary_file"] = f"daily/{name}"
            self._write_session_local(session)
            self._index_session(session)

        self._index_entry(
            {
                "memory_id": _content_hash(name + "|" + day.strftime("%Y-%m-%d")),
                "file_id": saved.get("file_id"),
                "type": "summary",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "tags": [*summary.get("topics", []), *summary.get("keywords", [])],
                "keywords": summary.get("keywords", []),
                "summary": summary.get("summary", ""),
                "importance": 0.35,
                "folder": "summary_daily",
                "granularity": "daily",
                "day": day.strftime("%Y-%m-%d"),
            }
        )
        self._flush_index()

        if self.config.auto_promotion:
            for fact in summary.get("important_facts", [])[:5]:
                self.save_knowledge(fact, tags=summary.get("topics", [])[:4])

        logger.info(
            "MEMORY_SUMMARY done day=%s messages=%d",
            day,
            len(messages),
        )
        return True

    def _build_summary(
        self,
        messages: List[Dict[str, Any]],
        day: datetime.date,
        granularity: str,
    ) -> Dict[str, Any]:
        """Summarize messages using the injected/LLM summarizer.

        Falls back to a deterministic extractor when no summarizer is
        configured or the LLM path fails, so rollover is never blocked.
        """
        bounded = messages[-(self.config.summarizer_max_messages):]

        if self.summarizer is not None:
            try:
                result = self.summarizer(bounded)
                if isinstance(result, dict) and result.get("summary"):
                    return self._normalize_summary(result, day, granularity)
            except Exception as exc:
                logger.warning(
                    "MEMORY_SUMMARY provider_error=%s (falling back)", exc
                )
        elif self.config.drive_enabled:
            try:
                llm = self._llm_summary(bounded)
                if llm and llm.get("summary"):
                    return self._normalize_summary(llm, day, granularity)
            except Exception as exc:
                logger.warning(
                    "MEMORY_SUMMARY llm_error=%s (falling back)", exc
                )

        return self._normalize_summary(
            self._deterministic_summary(bounded), day, granularity
        )

    def _llm_summary(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        from core.brain_adapter import BrainAdapter

        transcript = "\n".join(
            f"{m.get('role', '?')}: {m.get('content', '')}" for m in messages
        )[:14000]
        prompt = (
            "Extract a durable memory summary from this conversation. "
            "Return JSON ONLY with keys: summary, topics[], decisions[], "
            "user_preferences[], important_facts[], projects[], "
            "unresolved_problems[], completed_tasks[], mistakes_and_corrections[], "
            "relevant_technical_details[], key_questions[]. "
            "Do not include transient small talk. "
            f"\n\nCONVERSATION:\n{transcript}"
        )
        msgs = [
            {"role": "system", "content": "You are a memory extraction engine."},
            {"role": "user", "content": prompt},
        ]

        async def _run():
            adapter = BrainAdapter()
            result = await adapter.chat_with_tools(
                messages=msgs, tools=[], temperature=0.1, max_tokens=1500
            )
            return (result.content or "").strip()

        try:
            loop = asyncio.new_event_loop()
            try:
                text = loop.run_until_complete(_run())
            finally:
                loop.close()
            if not text:
                return None
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            return json.loads(match.group(0))
        except Exception as exc:
            logger.warning("MEMORY_SUMMARY llm failure: %s", exc)
            return None

    def _normalize_summary(
        self,
        raw: Dict[str, Any],
        day: datetime.date,
        granularity: str,
    ) -> Dict[str, Any]:
        def _as_list(value: Any) -> List[str]:
            if isinstance(value, list):
                return [str(v) for v in value if str(v).strip()]
            if isinstance(value, str) and value.strip():
                return [value.strip()]
            return []

        topics = _as_list(raw.get("topics"))
        if not topics:
            topics = _keywords(raw.get("summary", "") , None, 8)
        
        # Calculate expiration date based on memory_date (the actual conversation date)
        memory_date = day.strftime("%Y-%m-%d")
        created_at = _now_iso()
        retention_days = self.config.summary_retention_days
        
        # expires_at is calculated from memory_date, not created_at
        expires_date = datetime.strptime(memory_date, "%Y-%m-%d") + timedelta(days=retention_days)
        expires_at = expires_date.isoformat(timespec="seconds")
        
        return {
            "memory_type": "summarised",
            "memory_date": memory_date,
            "day": memory_date,
            "granularity": granularity,
            "created_at": created_at,
            "updated_at": created_at,
            "expires_at": expires_at,
            "retention_days": retention_days,
            "status": "completed",
            "summary": str(raw.get("summary") or "")[:3000],
            "topics": topics[:12],
            "decisions": _as_list(raw.get("decisions"))[:10],
            "user_preferences": _as_list(raw.get("user_preferences"))[:10],
            "important_facts": _as_list(raw.get("important_facts"))[:10],
            "projects": _as_list(raw.get("projects"))[:10],
            "unresolved_problems": _as_list(raw.get("unresolved_problems"))[:10],
            "completed_tasks": _as_list(raw.get("completed_tasks"))[:15],
            "mistakes_and_corrections": _as_list(raw.get("mistakes_and_corrections"))[:10],
            "relevant_technical_details": _as_list(raw.get("relevant_technical_details"))[:10],
            "key_questions": _as_list(raw.get("key_questions"))[:10],
            "keywords": _keywords(
                json.dumps(raw, default=str), None, 20
            ),
        }

    @staticmethod
    def _deterministic_summary(
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        text = " ".join(str(m.get("content", "")) for m in messages)[:20000]
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

        signal_words = (
            "decided", "decision", "prefer", "preference", "favorite",
            "my name", "my project", "my backend", "my port", "uses ",
            "is running on", "remember", "important", "always", "never",
            "rule", "instruction",
        )
        fact_sentences = [
            s for s in sentences[:200]
            if any(w in s.lower() for w in signal_words)
        ][:8]

        completed = [
            s for s in sentences[:200]
            if re.match(r"^\s*(done|completed|finished|fixed|resolved)", s, re.I)
        ][:8]
        unresolved = [
            s for s in sentences[:200]
            if re.search(r"\b(todo|pending|still|not working|broken|issue|bug)\b", s, re.I)
        ][:8]
        corrections = [
            s for s in sentences[:200]
            if re.search(r"^\s*(no|actually|correction|wrong)", s, re.I)
        ][:8]
        questions = [
            s for s in sentences[:200] if re.search(r"\?", s)
        ][:8]

        topics = _keywords(" ".join(sentences), None, 10)
        compact = " ".join(
            (fact_sentences + completed + unresolved + corrections)[:12]
        )[:800]

        return {
            "summary": compact or text[:400],
            "topics": topics,
            "decisions": [],
            "user_preferences": fact_sentences,
            "important_facts": fact_sentences,
            "projects": [],
            "unresolved_problems": unresolved,
            "completed_tasks": completed,
            "mistakes_and_corrections": corrections,
            "relevant_technical_details": [],
            "key_questions": questions,
        }

    def _compact_summaries(self) -> None:
        """Compress finished daily summaries into weekly/monthly files."""
        if not self.config.summary_enabled:
            return

        today = _today()
        month = today.strftime("%Y-%m")
        week = today.strftime("%Y-W%V")

        month_summaries = [
            self.store.read_file("summary_daily", p.name)
            for p in self.store.list_local("summary_daily")
            if p.name.startswith(today.strftime("%d-%m-%Y")) is False
        ]
        # Fall back to scanning folder for the current month's days.
        month_files = [
            p
            for p in self.store.list_local("summary_daily")
            if self._file_day(p.name).strftime("%Y-%m") == month
        ]
        month_summaries = [
            self.store.read_file("summary_daily", p.name)
            for p in month_files
        ]
        month_summaries = [s for s in month_summaries if s]

        if len(month_summaries) >= 7:
            weekly_name = f"{week}.json"
            if not self.store.read_file("summary_weekly", weekly_name):
                combined = "\n".join(
                    f"- {s.get('summary', '')}" for s in month_summaries
                )
                weekly = {
                    "week": week,
                    "created_at": _now_iso(),
                    "status": "completed",
                    "granularity": "weekly",
                    "topics": _keywords(combined, None, 15),
                    "summary": combined[:4000],
                    "sources": [f"daily/{p.name}" for p in month_files],
                    "keywords": _keywords(combined, None, 20),
                }
                saved = self.store.save_file("summary_weekly", weekly_name, weekly)
                self._index_entry({
                    "memory_id": _content_hash("weekly|" + week),
                    "file_id": saved.get("file_id"),
                    "type": "summary",
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                    "tags": weekly["topics"],
                    "keywords": weekly["keywords"],
                    "summary": weekly["summary"],
                    "importance": 0.4,
                    "folder": "summary_weekly",
                    "granularity": "weekly",
                    "day": week,
                })
                self._flush_index()

        if len(month_summaries) >= 28:
            monthly_name = f"{month}.json"
            if not self.store.read_file("summary_monthly", monthly_name):
                combined = "\n".join(
                    f"- {s.get('summary', '')}" for s in month_summaries
                )
                monthly = {
                    "month": month,
                    "created_at": _now_iso(),
                    "status": "completed",
                    "granularity": "monthly",
                    "topics": _keywords(combined, None, 18),
                    "summary": combined[:6000],
                    "sources": [f"daily/{p.name}" for p in month_files],
                    "keywords": _keywords(combined, None, 22),
                }
                saved = self.store.save_file("summary_monthly", monthly_name, monthly)
                self._index_entry({
                    "memory_id": _content_hash("monthly|" + month),
                    "file_id": saved.get("file_id"),
                    "type": "summary",
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                    "tags": monthly["topics"],
                    "keywords": monthly["keywords"],
                    "summary": monthly["summary"],
                    "importance": 0.45,
                    "folder": "summary_monthly",
                    "granularity": "monthly",
                    "day": month,
                })
                self._flush_index()

    @staticmethod
    def _file_day(name: str) -> datetime.date:
        try:
            return datetime.strptime(name[:10], "%d-%m-%Y").date()
        except ValueError:
            return _today()

    # ------------------------------------------------------------------
    # 20-DAY SUMMARY CLEANUP
    # ------------------------------------------------------------------

    def _cleanup_expired_summaries(self) -> Dict[str, Any]:
        """Scan and trash summaries older than retention period.
        
        Safety rules:
        - Only operates on SUMMARISED_MEMORY
        - Uses expires_at metadata (not filename)
        - Falls back to memory_date if expires_at missing
        - Skips deletion if both missing (logs warning)
        - Moves to Drive Trash (not permanent delete)
        - Updates index to mark entries as expired/trashed
        - Idempotent (safe to run multiple times)
        """
        if not self.store.api:
            logger.info("[MEMORY] Drive unavailable - skipping summary cleanup")
            return {"cleaned": 0, "skipped": "drive_unavailable"}
        
        try:
            logger.info("[MEMORY] Starting 20-day summary cleanup")
            
            # Get all summary files from Drive
            summary_folder_id = self.store.folder_id("summary_daily")
            if not summary_folder_id:
                logger.warning("[MEMORY] Summary folder not found - skipping cleanup")
                return {"cleaned": 0, "skipped": "folder_not_found"}
            
            # List local summary files first (for local fallback)
            local_summaries = self.store.list_local("summary_daily")
            logger.info(f"[MEMORY] Local summaries scanned: {len(local_summaries)} files")
            
            cleaned_count = 0
            metadata_missing_count = 0
            already_trashed_count = 0
            current_date = _today()
            
            for path in local_summaries:
                try:
                    summary = self.store.read_file("summary_daily", path.name)
                    if not summary:
                        continue
                    
                    # Safety: skip if not a summary
                    if summary.get("memory_type") != "summarised":
                        continue
                    
                    # Check if already trashed in index
                    memory_id = _content_hash(f"summary|{path.name}")
                    index_entry = self._index.get(memory_id) or self._index.get(_content_hash(f"summary|{summary.get('day', '')}"))
                    if index_entry and index_entry.get("trashed"):
                        already_trashed_count += 1
                        continue
                    
                    # Get expiration metadata
                    expires_at = summary.get("expires_at")
                    memory_date_str = summary.get("memory_date")  # Only use memory_date, not day
                    
                    if not expires_at and not memory_date_str:
                        logger.warning(
                            f"[MEMORY][WARNING] Retention metadata missing for {path.name} - skipping cleanup"
                        )
                        metadata_missing_count += 1
                        # Mark as retention_metadata_missing in index
                        if index_entry:
                            index_entry["status"] = "retention_metadata_missing"
                        continue
                    
                    # Calculate expiration if expires_at missing
                    if not expires_at and memory_date_str:
                        try:
                            memory_date = datetime.strptime(memory_date_str, "%Y-%m-%d").date()
                            expires_datetime = datetime.combine(memory_date + timedelta(days=self.config.summary_retention_days), datetime_time.min)
                            expires_at = expires_datetime.isoformat(timespec="seconds")
                        except ValueError:
                            logger.warning(f"[MEMORY][WARNING] Invalid memory_date format in {path.name}")
                            continue
                    
                    # Check if expired
                    try:
                        expires_date = datetime.fromisoformat(expires_at).date()
                        if current_date <= expires_date:
                            continue  # Not expired yet
                    except ValueError:
                        logger.warning(f"[MEMORY][WARNING] Invalid expires_at format in {path.name}")
                        continue
                    
                    # Summary is expired - move to trash
                    file_id = self.store._hierarchy.get(f"file:summary_daily:{path.name}")
                    if file_id:
                        try:
                            # Move to Drive Trash
                            self.store.api.update_file(file_id, trashed=True)
                            logger.info(f"[MEMORY] Trashed expired summary: {path.name}")
                            cleaned_count += 1
                            
                            # Update index
                            if index_entry:
                                index_entry["status"] = "expired"
                                index_entry["expired_at"] = _now_iso()
                                index_entry["trashed"] = True
                            else:
                                # Create index entry for tracking
                                self._index_entry({
                                    "memory_id": memory_id,
                                    "file_id": file_id,
                                    "type": "summary",
                                    "created_at": summary.get("created_at", _now_iso()),
                                    "updated_at": _now_iso(),
                                    "tags": summary.get("topics", []),
                                    "keywords": summary.get("keywords", []),
                                    "summary": summary.get("summary", "")[:300],
                                    "importance": 0.35,
                                    "folder": "summary_daily",
                                    "status": "expired",
                                    "expired_at": _now_iso(),
                                    "trashed": True,
                                    "memory_date": memory_date_str,
                                })
                            
                        except Exception as exc:
                            logger.error(f"[MEMORY][ERROR] Failed to trash {path.name}: {exc}")
                    else:
                        logger.warning(f"[MEMORY] No Drive file_id for {path.name} - skipping trash")
                        
                except Exception as exc:
                    logger.error(f"[MEMORY][ERROR] Error processing {path.name}: {exc}")
            
            # Flush index updates
            if cleaned_count > 0:
                self._flush_index()
            
            logger.info(
                f"[MEMORY] Cleanup complete: cleaned={cleaned_count}, "
                f"metadata_missing={metadata_missing_count}, "
                f"already_trashed={already_trashed_count}"
            )
            
            return {
                "cleaned": cleaned_count,
                "metadata_missing": metadata_missing_count,
                "already_trashed": already_trashed_count,
            }
            
        except Exception as exc:
            logger.error(f"[MEMORY][ERROR] Summary cleanup failed: {exc}")
            return {"cleaned": 0, "error": str(exc)}

    # ------------------------------------------------------------------
    # IMPORTANT / CORRECTION / KNOWLEDGE
    # ------------------------------------------------------------------

    def save_important(
        self,
        content: str,
        source: str = "user_explicit_save",
        tags: Optional[List[str]] = None,
        key: Optional[str] = None,
        value: Any = None,
        memory_type: str = "fact",
    ) -> Dict[str, Any]:
        """Create or update an explicit IMPORTANT_MEMORY entry."""
        content = " ".join(str(content or "").split())
        if not content:
            return {"success": False, "error": "empty_content"}

        memory_id = _content_hash(content)
        now = _now_iso()

        existing = None
        for entry in self._important_index.values():
            if entry.get("memory_id") == memory_id:
                existing = entry
                break
        if existing is None and key:
            for entry in self._important_index.values():
                if (entry.get("key") or "").lower() == key.lower() and entry.get(
                    "active", True
                ):
                    existing = entry
                    break

        if existing:
            old_id = existing["memory_id"]
            # Historical record: mark the old value superseded.
            old_name = f"important_{old_id}.json"
            old_rec = self.store.read_file("important", old_name) or {}
            old_rec["status"] = "superseded"
            old_rec["superseded_by"] = memory_id
            old_rec["updated_at"] = now
            self.store.save_file("important", old_name, old_rec)
            self._record_if_indexed("important", old_rec)
            memory_id = _content_hash(f"{content}|{now}")
            logger.info("MEMORY_UPDATE superseded=%s new=%s", old_id, memory_id)

        record = {
            "memory_id": memory_id,
            "created_at": now,
            "updated_at": now,
            "importance": "explicit",
            "source": source,
            "content": content,
            "type": memory_type,
            "key": key,
            "value": value,
            "tags": list(tags or [])[:10],
            "status": "active",
        }
        name = f"important_{memory_id}.json"
        saved = self.store.save_file("important", name, record)

        # verify: file exists locally AND (drive synced OR drive disabled)
        verified = self.store.read_file("important", name) is not None
        synced = saved.get("synced") or not self.store.api

        if self.config.index_enabled:
            self._important_index[memory_id] = {
                "memory_id": memory_id,
                "file_id": saved.get("file_id"),
                "type": "important",
                "created_at": now,
                "updated_at": now,
                "tags": record["tags"],
                "keywords": _keywords(content, tags),
                "summary": content[:300],
                "importance": 1.0,
                "folder": "important",
                "key": key,
                "active": True,
            }
            if self._index_flushed_at and time.time() - self._index_flushed_at > 10:
                self._flush_index()

        if verified:
            logger.info(
                "MEMORY_SAVE type=important id=%s synced=%s",
                memory_id,
                synced,
            )
        else:
            logger.error(
                "MEMORY_SAVE type=important id=%s VERIFICATION_FAILED", memory_id
            )

        return {
            "success": verified,
            "stored": verified,
            "memory_id": memory_id,
            "synced": synced,
            "action": "superseded" if existing else "created",
        }

    def save_correction(
        self,
        wrong_information: str = "",
        correct_information: str = "",
        source: str = "user_correction",
    ) -> Dict[str, Any]:
        """Store a user correction with high retrieval priority."""
        if not self.config.correction_enabled:
            return {"success": False, "error": "corrections_disabled", "stored": False}
        correct = " ".join(str(correct_information or "").split())
        if not correct:
            return {"success": False, "error": "empty_correction", "stored": False}

        memory_id = _content_hash(f"correction|{correct}")
        now = _now_iso()
        tags = _keywords(correct, None, 6)
        record = {
            "type": "correction",
            "memory_id": memory_id,
            "wrong_information": wrong_information,
            "correct_information": correct,
            "source": source,
            "created_at": now,
            "updated_at": now,
            "confidence": "high",
            "status": "active",
            "tags": tags,
        }
        name = f"correction_{memory_id}.json"
        saved = self.store.save_file("correction", name, record)
        verified = self.store.read_file("correction", name) is not None
        synced = saved.get("synced") or not self.store.api

        if self.config.index_enabled:
            self._index_entry({
                "memory_id": memory_id,
                "file_id": saved.get("file_id"),
                "type": "correction",
                "created_at": now,
                "updated_at": now,
                "tags": tags,
                "keywords": _keywords(correct, tags),
                "summary": correct[:300],
                "importance": 0.9,
                "folder": "correction",
                "active": True,
            })

        logger.info(
            "MEMORY_CORRECTION id=%s verified=%s synced=%s",
            memory_id,
            verified,
            synced,
        )
        return {
            "success": verified,
            "stored": verified,
            "memory_id": memory_id,
            "synced": synced,
            "action": "created",
        }

    def save_knowledge(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        source: str = "conversation_extraction",
    ) -> Dict[str, Any]:
        """Store durable knowledge (deduplicated by content fingerprint)."""
        content = " ".join(str(content or "").split())
        if not content:
            return {"success": False, "error": "empty_content", "stored": False}

        memory_id = _content_hash(f"knowledge|{content}")
        now = _now_iso()
        existing = self.store.read_file("knowledge", f"knowledge_{memory_id}.json")
        if existing:
            logger.info("MEMORY_DEDUP type=knowledge id=%s (update only)", memory_id)
            existing["updated_at"] = now
            saved = self.store.save_file("knowledge", f"knowledge_{memory_id}.json", existing)
            return {
                "success": True,
                "stored": True,
                "memory_id": memory_id,
                "synced": saved.get("synced"),
                "action": "updated",
            }

        record = {
            "type": "knowledge",
            "memory_id": memory_id,
            "content": content,
            "source": source,
            "created_at": now,
            "updated_at": now,
            "tags": list(tags or [])[:10],
            "status": "active",
        }
        name = f"knowledge_{memory_id}.json"
        saved = self.store.save_file("knowledge", name, record)
        verified = self.store.read_file("knowledge", name) is not None
        synced = saved.get("synced") or not self.store.api

        if self.config.index_enabled:
            self._index_entry({
                "memory_id": memory_id,
                "file_id": saved.get("file_id"),
                "type": "knowledge",
                "created_at": now,
                "updated_at": now,
                "tags": record["tags"],
                "keywords": _keywords(content, tags),
                "summary": content[:300],
                "importance": 0.55,
                "folder": "knowledge",
                "active": True,
            })

        logger.info(
            "MEMORY_SAVE type=knowledge id=%s verified=%s synced=%s",
            memory_id,
            verified,
            synced,
        )
        return {
            "success": verified,
            "stored": verified,
            "memory_id": memory_id,
            "synced": synced,
            "action": "created",
        }

    def forget(self, text: Optional[str] = None, memory_id: Optional[str] = None) -> Dict[str, Any]:
        """Retire an explicitly saved memory (preserves audit history)."""
        target = None
        if memory_id:
            target = self._important_index.get(memory_id)
        elif text:
            tokens = set(_tokens(text))
            best = None
            best_score = 0.0
            for entry in self._important_index.values():
                if not entry.get("active", True):
                    continue
                kw = set(entry.get("keywords", []))
                score = len(tokens & kw)
                if score > best_score:
                    best_score = score
                    best = entry
            target = best

        if not target:
            return {"success": False, "stored": False, "error": "not_found"}

        memory_id = target["memory_id"]
        name = f"important_{memory_id}.json"
        record = self.store.read_file("important", name) or {}
        record["status"] = "retired"
        record["retired_at"] = _now_iso()
        self.store.save_file("important", name, record)
        if memory_id in self._important_index:
            self._important_index[memory_id]["active"] = False
            self._flush_index()
        logger.info("MEMORY_DELETE type=important id=%s (retired, history kept)", memory_id)
        return {"success": True, "stored": True, "memory_id": memory_id, "action": "retired"}

    # ------------------------------------------------------------------
    # INDEX
    # ------------------------------------------------------------------

    def _load_indexes(self) -> None:
        self._index = self.store.read_file("index", "memory_index.json") or {}
        if not isinstance(self._index, dict):
            self._index = {}
        self._important_index = (
            self.store.read_file("index", "important_index.json") or self._index
            if False
            else self.store.read_file("index", "important_index.json") or {}
        )
        if not isinstance(self._important_index, dict):
            self._important_index = {}
        self._session_index = (
            self.store.read_file("index", "session_index.json") or {}
        )
        if not isinstance(self._session_index, dict):
            self._session_index = {}
        logger.info(
            "MEMORY_INDEX_LOAD memory=%d important=%d sessions=%d",
            len(self._index),
            len(self._important_index),
            len(self._session_index),
        )

    def _index_entry(self, entry: Dict[str, Any]) -> None:
        if not self.config.index_enabled:
            return
        self._index[entry.get("memory_id", _content_hash(str(entry)))] = entry

    def _record_if_indexed(self, old_name: str, record: Dict[str, Any]) -> None:
        memory_id = record.get("memory_id")
        if memory_id and memory_id in self._important_index:
            self._important_index[memory_id]["active"] = False
            self._important_index[memory_id]["superseded_by"] = record.get("superseded_by")

    def _index_session(self, session: Dict[str, Any]) -> None:
        if not self.config.index_enabled:
            return
        session_id = session.get("session_id", "")
        if not session_id:
            return
        text = " ".join(
            str(m.get("content", "")) for m in session.get("messages", [])
        )
        start_day = (session.get("started_at") or "")[:10]
        self._session_index[session_id] = {
            "memory_id": session_id,
            "file_id": None,
            "type": "session",
            "created_at": session.get("started_at"),
            "updated_at": session.get("ended_at") or session.get("started_at"),
            "tags": _keywords(text, None, 10),
            "keywords": _keywords(text, None, 16),
            "summary": text[:300],
            "importance": 0.2,
            "folder": "active",
            "status": session.get("status", "active"),
            "day": start_day,
        }

    def _flush_index(self) -> None:
        if not self.config.index_enabled:
            return
        self.store.save_file("index", "memory_index.json", self._index)
        self.store.save_file("index", "important_index.json", self._important_index)
        self.store.save_file("index", "session_index.json", self._session_index)
        self._index_flushed_at = time.time()
        logger.info("MEMORY_INDEX_UPDATE entries=%d", len(self._index))

    def _record_if_indexed(self, old_name: str, record: Dict[str, Any]) -> None:  # noqa: F811
        memory_id = record.get("memory_id")
        if memory_id and memory_id in self._important_index:
            self._important_index[memory_id]["status"] = record.get("status")
            self._important_index[memory_id]["active"] = False

    # ------------------------------------------------------------------
    # RETRIEVAL (bounded, ranked, priority ordered)
    # ------------------------------------------------------------------

    def _priority(self, entry: Dict[str, Any]) -> int:
        mem_type = entry.get("type", "")
        if mem_type == "important":
            return 1
        if mem_type == "correction":
            return 2
        if mem_type == "active":
            return 4
        if mem_type == "knowledge":
            return 5
        if mem_type == "summary":
            granularity = entry.get("granularity", "daily")
            return 8 if granularity == "daily" else 9
        return 10

    def _match_score(self, query_tokens: set, entry: Dict[str, Any]) -> float:
        keywords = entry.get("keywords", []) or []
        summary_text = f"{entry.get('summary', '')} {' '.join(entry.get('tags', []) or [])}"
        entry_tokens = set(keywords) | set(_tokens(summary_text))
        if not entry_tokens:
            return 0.0
        overlap = len(query_tokens & entry_tokens)
        if overlap == 0:
            return 0.0
        return 1.0 + 0.25 * overlap

    def _retrieve_candidates(self, query: str, active_sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        q_tokens = set(_tokens(query))
        candidates: List[Tuple[float, int, Dict[str, Any]]] = []

        # 1. Explicit important memories (highest priority).
        for entry in self._important_index.values():
            if not entry.get("active", True):
                continue
            score = self._match_score(q_tokens, entry)
            if score or not q_tokens:
                candidates.append((score, self._priority(entry), entry))

        # 2. Corrections.
        if self.config.correction_enabled:
            for entry in self._index.values():
                if entry.get("type") != "correction" or not entry.get("active", True):
                    continue
                score = self._match_score(q_tokens, entry)
                if score:
                    candidates.append((score, self._priority(entry), entry))

        if not q_tokens:
            candidates = [(s, p, e) for s, p, e in candidates if s]
            candidates.sort(key=lambda t: (t[1], t[0]), reverse=True)
            return [e for _, _, e in candidates[:10]]

        # 3. Active sessions (bounded, date-aware).
        for session in active_sessions:
            if session.get("status") not in ("active", "ended"):
                continue
            text = " ".join(str(m.get("content", "")) for m in session.get("messages", []))
            session_tokens = set(_tokens(text))
            overlap = len(q_tokens & session_tokens)
            if overlap:
                score = 1.0 + 0.2 * overlap + 0.15 * self._session_index.get(
                    session.get("session_id"), {}
                ).get("importance", 0.2)
                candidates.append((score, 3 + 1 / (overlap + 1), {
                    "type": "active",
                    "memory_id": session.get("session_id", ""),
                    "summary": text[:600],
                    "keywords": _keywords(text, None, 14),
                    "session_id": session.get("session_id"),
                    "tier": "active",
                }))

        # 4. Knowledge + summaries from the index.
        for entry in self._index.values():
            mem_type = entry.get("type", "")
            if mem_type not in ("knowledge", "summary"):
                continue
            if not entry.get("active", True) and entry.get("status") == "retired":
                continue
            score = self._match_score(q_tokens, entry)
            if score:
                candidates.append((score, self._priority(entry), entry))

        # 5. Older historical summaries (files not yet indexed).
        for path in self.store.list_local("summary_daily"):
            name = path.name
            if not self._day_summarized_file(name):
                continue
            summary = self.store.read_file("summary_daily", name)
            if not summary:
                continue
            entry = {
                "type": "summary",
                "memory_id": _content_hash("summary|" + name),
                "summary": summary.get("summary", ""),
                "keywords": summary.get("keywords", []),
                "granularity": "daily",
                "folder": "summary_daily",
                "tier": "historical",
            }
            score = self._match_score(q_tokens, entry)
            if score:
                candidates.append((score, 9, entry))

        candidates.sort(key=lambda t: (t[1], t[0]), reverse=True)
        return [e for _, _, e in candidates]

    @staticmethod
    def _day_summarized_file(name: str) -> bool:
        return bool(name)

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        budget_tokens: Optional[int] = None,
        include_active: bool = True,
    ) -> List[Dict[str, Any]]:
        """Ranked, priority-ordered, budget-bounded memory retrieval."""
        budget = budget_tokens or self.config.max_context_tokens
        budget = max(64, min(int(budget), 16000))

        active_sessions = []
        if include_active:
            active_sessions = self._load_active_sessions()

        candidates = self._retrieve_candidates(query, active_sessions)
        if not candidates:
            logger.info('MEMORY_SEARCH query="%s" candidates=0 selected=0', query[:80] or "-")
            return []

        selected: List[Dict[str, Any]] = []
        seen: set = set()
        tokens_used = 0

        for entry in candidates:
            dedupe_key = _content_hash(
                f"{entry.get('type')}|{entry.get('memory_id')}|{entry.get('summary')}"
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            text = str(entry.get("summary") or entry.get("content") or "")
            est = _estimate_tokens(text)
            if tokens_used + est > budget and selected:
                break
            tokens_used += est
            selected.append(entry)
            if len(selected) >= top_k:
                break

        logger.info(
            'MEMORY_SEARCH query="%s" candidates=%d selected=%d budget_tokens=%d',
            query[:80] or "-",
            len(candidates),
            len(selected),
            budget,
        )
        for entry in selected[:3]:
            logger.info(
                "MEMORY_HIT type=%s score_rank=%d",
                entry.get("type"),
                selected.index(entry) + 1,
            )
        if not selected:
            logger.info("MEMORY_MISS query=%s", query[:80] or "-")
        return selected

    def _load_active_sessions(self) -> List[Dict[str, Any]]:
        """Load only sessions inside the active window (bounded set)."""
        window_start = self.window_start_date()
        out: List[Dict[str, Any]] = []
        for path in self._active_session_files():
            try:
                day = datetime.strptime(path.name[:10], "%d-%m-%Y").date()
            except ValueError:
                continue
            if day < window_start:
                continue
            try:
                session = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if session.get("messages"):
                out.append(session)
        return out[:20]

    def context_for(self, query: str, budget_tokens: Optional[int] = None) -> str:
        """Compact <MEMORY_CONTEXT> block for the LLM, or '' when empty."""
        if not self._started:
            return ""
        if not query or not str(query).strip():
            return ""
        results = self.retrieve(query, top_k=8, budget_tokens=budget_tokens)
        if not results:
            return ""

        sections: Dict[str, List[str]] = {
            "Important": [],
            "Corrections": [],
            "Recent": [],
            "Knowledge": [],
            "Historical": [],
        }
        for entry in results:
            mem_type = entry.get("type", "")
            text = str(entry.get("summary") or "").strip()[:300]
            if not text:
                continue
            if mem_type == "important":
                sections["Important"].append(text)
            elif mem_type == "correction":
                sections["Corrections"].append(f"Correction: {text}")
            elif mem_type == "active":
                sections["Recent"].append(text)
            elif mem_type == "knowledge":
                sections["Knowledge"].append(text)
            else:
                sections["Historical"].append(text)

        lines = ["<MEMORY_CONTEXT>"]
        for label, items in sections.items():
            if items:
                lines.append(f"{label}:")
                for item in items[:4]:
                    lines.append(f"* {item}")
        lines.append("</MEMORY_CONTEXT>")

        block = "\n".join(lines)
        if _estimate_tokens(block) > (budget_tokens or self.config.max_context_tokens):
            return ""
        logger.info(
            "MEMORY_CONTEXT injected=%d tokens=%d",
            len(results),
            _estimate_tokens(block),
        )
        return block

    # ------------------------------------------------------------------
    # COMMAND ROUTING (deterministic; no model dependency)
    # ------------------------------------------------------------------

    def route_command(self, text: str) -> Optional[Dict[str, Any]]:
        """Handle explicit memory commands; returns an outcome dict or None.

        Outcome: {"kind": str, "text": str, "success": bool, ...}
        Honest persistence: "text" only claims success when verified.
        """
        original = " ".join(str(text or "").split())
        low = original.lower()

        # --- RECALL ---------------------------------------------------
        recall_match = re.search(
            r"\bwhat do you (?:remember|know|recall)\s+(?:about|of)\s+(.+)$",
            original,
            re.IGNORECASE,
        ) or re.search(
            r"\b(?:what did we|what have we)\s+(?:discuss|talk|say|decide)"
            r"(?:ed|d)?\s+about\s+(.+)$",
            original,
            re.IGNORECASE,
        )
        if recall_match or re.search(r"\bwhat do you (?:remember|know) about me\b", low):
            subject = (recall_match.group(1) if recall_match else "me").strip()
            if subject.lower() in {"me", "i", "myself"}:
                subject = "me " + _local_now()
            results = self.retrieve(subject, top_k=10)
            if not results:
                return {
                    "kind": "recall",
                    "success": True,
                    "text": (
                        "I don't have enough remembered context about that yet."
                    ),
                }
            bullets = []
            for entry in results[:10]:
                label = entry.get("type", "").capitalize()
                text = str(entry.get("summary") or "")[:160]
                if text:
                    bullets.append(f"- [{label}] {text}")
            return {
                "kind": "recall",
                "success": True,
                "text": "Here's what I remember:\n" + "\n".join(bullets),
                "hits": len(results),
            }

        # --- FORGET ---------------------------------------------------
        forget_match = re.search(
            r"\b(?:forget|remove|erase|delete)\s+(?:that|this|the)?\s*(?:memory|remember)?\b"
            r"\s*(.*)$",
            original,
            re.IGNORECASE,
        )
        if forget_match and len(forget_match.group(0).strip().split()) <= 10:
            target_text = forget_match.group(1).strip()
            outcome = self.forget(text=target_text or None)
            if outcome.get("success"):
                return {
                    "kind": "forget",
                    "success": True,
                    "memory_id": outcome.get("memory_id"),
                    "text": "That memory has been removed (history preserved).",
                }
            return {
                "kind": "forget",
                "success": False,
                "text": "I couldn't find a matching memory to remove.",
            }

        # --- CORRECTION (explicit) --------------------------------------
        correction = self._detect_correction(original)
        if correction:
            outcome = self.save_correction(
                wrong_information=correction["wrong"],
                correct_information=correction["correct"],
            )
            if outcome.get("success"):
                return {
                    "kind": "correction",
                    "success": True,
                    "memory_id": outcome.get("memory_id"),
                    "text": "Correction stored — I'll use that going forward.",
                }
            return {
                "kind": "correction",
                "success": False,
                "text": "I couldn't store that correction.",
            }

        # --- EXPLICIT IMPORTANT SAVE -------------------------------------
        important = self._detect_important_save(original)
        if important:
            outcome = self.save_important(
                content=important["content"],
                key=important.get("key"),
                value=important.get("value"),
                tags=important.get("tags"),
            )
            if outcome.get("success"):
                return {
                    "kind": "saved",
                    "success": True,
                    "memory_id": outcome.get("memory_id"),
                    "text": (
                        "Saved to permanent memory"
                        + (" (Drive sync pending)." if not outcome.get("synced") else ".")
                    ),
                }
            return {
                "kind": "saved",
                "success": False,
                "text": "I couldn't save that to permanent memory.",
            }

        return None

    # -- command detectors ------------------------------------------------

    @staticmethod
    def _detect_important_save(text: str) -> Optional[Dict[str, Any]]:
        """remember/save/don't forget/keep permanently/this is important..."""
        preserved = re.match(
            r"^(?:please\s+)?(?:keep\s+(?:this|that)\s+(?:permanently|in\s+memory)|"
            r"this\s+is\s+important\s*:?\s*|"
            r"save\s+this\s*:?\s*|"
            r"remember\s+(?:this\s+|that\s+|it\s+)?permanently\s*:?\s*)"
            r"\s*(.+)$",
            text,
            re.IGNORECASE,
        )
        if preserved:
            content = " ".join(preserved.group(1).split())
            if content:
                return {"content": content, "tags": ["explicit"]}

        intent = extract_memory_intent(text)
        if intent:
            return {
                "content": intent["content"],
                "key": intent.get("key"),
                "value": intent.get("value"),
                "tags": ["explicit"],
            }
        return None

    @staticmethod
    def _detect_correction(text: str) -> Optional[Dict[str, Any]]:
        """Corrections: 'no, my backend uses port 8001', 'X is wrong, it's Y',
        'correct this: ...', 'actually ...'."""
        rest = re.match(
            r"^(?:no|actually|wait|correction|that'?s\s+(?:wrong|not\s+right)|"
            r"that\s+was\s+wrong)\b[,.:]?\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if rest:
            content = rest.group(1).strip()
            if content and re.search(r"\b(my|i|we|it|is|use|port|name|file|model)\b", content, re.I):
                return {"wrong": "", "correct": content}

        structured = re.match(
            r"^(.+?)\s+(?:is|was)\s+wrong[,.]?\s+(?:it'?s|it\s+is|the\s+real\s+answer\s+is|"
            r"actually\s+(?:it'?s|it\s+is)?)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if structured:
            return {
                "wrong": structured.group(1).strip(),
                "correct": structured.group(2).strip(),
            }

        corrected = re.match(
            r"^correct\s+(?:this|that|it|the\s+(?:memory|fact))[:,]?\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if corrected:
            return {"wrong": "", "correct": corrected.group(1).strip()}

        return None


human_memory = HumanLikeMemory()


__all__ = [
    "HumanLikeMemory",
    "MemoryConfig",
    "GoogleDriveMemoryStore",
    "GoogleDriveApi",
    "human_memory",
]