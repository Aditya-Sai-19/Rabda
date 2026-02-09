"""Central configuration for the WhatsApp Status automation app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Runtime configuration.

    Values are intentionally conservative because WhatsApp Web UI is dynamic.
    """

    # Persistent browser session folder for WhatsApp Web login.
    # This allows you to scan QR once and reuse the session.
    session_dir: Path = Path(__file__).resolve().parent / "session"

    # Base URL
    whatsapp_web_url: str = "https://web.whatsapp.com/"

    # Whether to keep the browser open after posting.
    keep_browser_open: bool = True

    # Playwright + UI timeouts (ms)
    navigation_timeout_ms: int = 60_000
    action_timeout_ms: int = 20_000

    # Retries
    max_action_retries: int = 4
    retry_backoff_base_s: float = 0.7

    # Human-like delays (seconds)
    min_human_delay_s: float = 0.15
    max_human_delay_s: float = 0.45

    # Debug logging
    debug: bool = True

    # Default paths
    default_csv_path: Path = Path("data/status_queue.csv")
    default_images_folder: Path = Path("images/")


CONFIG = Config()
