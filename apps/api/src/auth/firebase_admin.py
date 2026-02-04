"""Firebase Admin SDK initialization."""

import firebase_admin
from firebase_admin import credentials

from src.config import get_settings

_initialized = False


def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK.

    This function is idempotent - calling it multiple times has no effect.
    """
    global _initialized
    if _initialized:
        return

    settings = get_settings()

    try:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        _initialized = True
    except FileNotFoundError:
        # In test environment, Firebase may not be configured
        pass
    except ValueError:
        # Already initialized
        _initialized = True
