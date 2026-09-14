"""Read device tokens out of a Mi Home app backup, without the cloud.

python-miio already ships the readers for both database formats; this only
wraps them so the config flow can hand over an uploaded file. Everything in
here blocks and belongs in an executor job.
"""
# pylint: disable=import-error
import logging
import tempfile
from pathlib import Path
from typing import Optional

from miio.extract_tokens import BackupDatabaseReader

_LOGGER = logging.getLogger(__name__)

# Where the Mi Home app keeps its device database inside an Android backup.
ANDROID_DB_PATH = "apps/com.xiaomi.smarthome/db/miio2.db"


class TokenBackupException(Exception):
    """Raised when a backup cannot be read."""


def extract_devices(path: str, password: Optional[str] = None) -> list[dict]:
    """Return every device found in a Mi Home backup.

    Accepts an Android backup (.ab) or an already extracted sqlite database,
    which is also what an iOS backup yields. Blocking - call from an executor.
    """
    reader = BackupDatabaseReader()

    if str(path).endswith(".ab"):
        devices = _read_android_backup(reader, path, password)
    else:
        try:
            devices = list(reader.read_tokens(str(path)))
        except Exception as ex:  # noqa: BLE001 - sqlite3 raises several types
            raise TokenBackupException(
                f"Could not read the backup as a device database: {ex}"
            ) from ex

    # Shape the result like the cloud device list so the config flow can treat
    # both sources identically.
    return [
        {
            "name": device.name,
            "model": device.model,
            "localip": device.ip,
            "mac": device.mac,
            "token": device.token,
        }
        for device in devices
        if device.token
    ]


def _read_android_backup(
    reader: BackupDatabaseReader, path: str, password: Optional[str]
) -> list:
    """Unpack an .ab backup and read the Mi Home database out of it."""
    try:
        from android_backup import AndroidBackup
    except ModuleNotFoundError as ex:
        raise TokenBackupException(
            "Reading Android backups needs the android_backup package"
        ) from ex

    try:
        with AndroidBackup(str(path), stream=False) as backup:
            tar = backup.read_data(password)

            try:
                database = tar.extractfile(ANDROID_DB_PATH)
            except KeyError as ex:
                raise TokenBackupException(
                    "The backup contains no Mi Home database. Make sure it was "
                    "created for com.xiaomi.smarthome."
                ) from ex

            with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
                tmp.write(database.read())
                tmp.flush()
                return list(reader.read_tokens(tmp.name))
    except TokenBackupException:
        raise
    except Exception as ex:  # noqa: BLE001 - the backup reader raises broadly
        raise TokenBackupException(f"Could not read the Android backup: {ex}") from ex


def looks_like_backup(path: str) -> bool:
    """Cheap sanity check so obvious mistakes get a clear message."""
    candidate = Path(path)
    if not candidate.is_file():
        return False
    return candidate.stat().st_size > 0
