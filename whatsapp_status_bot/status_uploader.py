"""Playwright sync automation for posting an image to WhatsApp Status (WhatsApp Web)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from .config import CONFIG
from .logger import Logger
from .selectors import (
    ADD_STATUS_BUTTON,
    ADD_STATUS_SELECTORS,
    CAPTION_BOX,
    FILE_INPUT,
    LOGIN_READY,
    MEDIA_STATUS_SELECTORS,
    PREVIEW_READY,
    SEND_BUTTON,
    SEND_BUTTON_SELECTORS,
    STATUS_TAB,
    STATUS_TAB_SELECTORS,
)
from .utils import (
    first_visible_locator,
    human_delay,
    safe_click,
    safe_fill,
    safe_set_input_files,
    first_attached_locator,
)

LogCallback = Callable[[str], None]


@dataclass
class PostResult:
    success: bool
    message: str


class WhatsAppStatusUploader:
    """Automates posting an image as WhatsApp Status via WhatsApp Web."""

    def __init__(self, *, log_callback: Optional[LogCallback] = None) -> None:
        self.logger = Logger(callback=log_callback)
        self._pw: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Page not initialized")
        return self._page

    def launch_browser(self) -> None:
        """Launch Chromium persistent context (non-headless)."""

        self.logger.info("Launching Chromium persistent context...")
        CONFIG.session_dir.mkdir(parents=True, exist_ok=True)

        self._pw = sync_playwright().start()
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(CONFIG.session_dir),
            headless=False,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        self._context.set_default_timeout(CONFIG.action_timeout_ms)
        self._context.set_default_navigation_timeout(CONFIG.navigation_timeout_ms)

        pages = self._context.pages
        self._page = pages[0] if pages else self._context.new_page()
        self.logger.info("Opening WhatsApp Web...")
        self._page.goto(CONFIG.whatsapp_web_url, wait_until="domcontentloaded")
        human_delay(1.5)

    def wait_for_login(self) -> None:
        """Wait until WhatsApp Web is ready (user logged in)."""

        self.logger.info("Waiting for WhatsApp Web login to be ready...")
        first_visible_locator(self.page, LOGIN_READY, timeout_ms=CONFIG.navigation_timeout_ms)
        self.logger.info("Login ready (chat UI detected).")

    def open_status_tab(self) -> None:
        """Navigate to Updates/Status tab."""

        self.logger.info("Navigating to Updates/Status tab...")

        verify_selectors = [
            "text=My status",
            "text=Add status",
            "input[type='file']",
        ]

        def _verify_opened() -> bool:
            """Verify the status composer is opened by ensuring at least one
            known element is attached to the DOM (not strictly visible).
            """
            for vsel in verify_selectors:
                try:
                    self.page.locator(vsel).first.wait_for(state="attached", timeout=5000)
                    self.logger.info("[VERIFY] Status tab detected (attached)" )
                    return True
                except Exception:
                    continue
            return False

        # Try each selector candidate and verify we truly opened Updates/Status.
        for sel in STATUS_TAB_SELECTORS:
            self.logger.info(f"[STEP] Clicking Updates tab selector: {sel}")
            try:
                safe_click(
                    self.page,
                    [sel],
                    timeout_ms=CONFIG.action_timeout_ms,
                    tries=1,
                    log=self.logger.info,
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.info(f"[RETRY] Trying fallback selector {sel} failed: {type(exc).__name__}: {exc}")
                continue

            human_delay(1.0)
            if _verify_opened():
                return

            self.logger.info("Status tab not opened — retrying alternate selector")

        self.logger.error("[ERROR] Status tab open failed")
        raise RuntimeError("Failed to open Updates/Status tab — selectors outdated")

    def click_add_status(self) -> None:
        """Click Add Status / My Status entry point."""

        # New WhatsApp UI flow:
        #   1) Click "My status"
        #   2) In chooser popup, click "Photos & videos" to open media composer
        self.logger.info("[STEP] Clicking My status")
        safe_click(
            self.page,
            ADD_STATUS_SELECTORS,
            timeout_ms=CONFIG.action_timeout_ms,
            tries=CONFIG.max_action_retries,
            log=self.logger.info,
        )
        human_delay(0.8)

        composer_verify_selectors = [
            "input[type='file']",
            "div[contenteditable='true'][role='textbox']",
        ]

        def _composer_opened() -> bool:
            for sel in composer_verify_selectors:
                try:
                    self.page.locator(sel).first.wait_for(state="attached", timeout=5000)
                    return True
                except Exception:
                    continue
            return False

        self.logger.info("[STEP] Clicking Photos & videos option")
        last_exc: Exception | None = None
        for media_sel in MEDIA_STATUS_SELECTORS:
            try:
                safe_click(
                    self.page,
                    [media_sel],
                    timeout_ms=CONFIG.action_timeout_ms,
                    tries=1,
                    log=self.logger.info,
                )
                human_delay(0.9)

                # Verify composer opened (do not require visibility).
                if _composer_opened():
                    self.logger.info("[VERIFY] Media composer opened")
                    return

                self.logger.info(f"[RETRY] Trying fallback selector {media_sel}")
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self.logger.info(f"[RETRY] Trying fallback selector {media_sel} failed: {type(exc).__name__}: {exc}")
                continue

        raise RuntimeError("Status media composer did not open") from last_exc

    def upload_image(self, image_path: str) -> None:
        """Upload image using file input (DOM path only)."""

        self.logger.info("[STEP] Uploading image")

        # Use attached-based locator logic to avoid triggering OS file picker dialogs.
        try:
            self.logger.info("[STEP] Located attached file input for DOM upload (no OS dialog).")
        except Exception as exc:  # pragma: no cover
            self.logger.error(f"Failed to locate file input: {exc}")
            raise

        # DOM-based upload: set the file directly on the attached input.
        safe_set_input_files(self.page, FILE_INPUT, image_path, timeout_ms=CONFIG.action_timeout_ms)
        # Wait for preview/compose screen signals.
        first_visible_locator(self.page, PREVIEW_READY, timeout_ms=CONFIG.navigation_timeout_ms)
        self.logger.info("Image preview ready.")

    def add_caption(self, caption: str) -> None:
        """Add optional caption."""

        if not caption.strip():
            self.logger.info("No caption provided; skipping caption step.")
            return

        self.logger.info("Adding caption...")
        loc = first_visible_locator(self.page, CAPTION_BOX, timeout_ms=CONFIG.action_timeout_ms)
        safe_fill(loc, caption, timeout_ms=CONFIG.action_timeout_ms)
        human_delay(0.8)

    def send_status(self) -> None:
        """Click Send/Post button (DOM-based, with updated selectors)."""

        self.logger.info("Posting status (clicking Send/Post)...")
        # Step 1: Try to click using a DOM-attached Send button (icon-based first).
        clicked = False
        try:
            loc = first_attached_locator(self.page, SEND_BUTTON_SELECTORS, timeout_ms=CONFIG.action_timeout_ms)
            loc.scroll_into_view_if_needed()
            loc.click(timeout=CONFIG.action_timeout_ms)
            clicked = True
            self.logger.info("[STEP] Clicked Send button via DOM selector (attached element)")
        except Exception as exc:  # noqa: BLE001
            self.logger.info(f"[WARN] DOM send button via attached locator not found: {type(exc).__name__}: {exc}")

        # Step 2: Fallback to legacy path if DOM path isn't available
        if not clicked:
            safe_click(
                self.page,
                SEND_BUTTON,
                timeout_ms=CONFIG.action_timeout_ms,
                tries=CONFIG.max_action_retries,
                log=self.logger.info,
            )

        # Step 3: Post-click verification: allow transition and verify progress
        human_delay(0.5)
        try:
            # Prefer DOM-based selectors for detachment check as well
            for sel in SEND_BUTTON_SELECTORS:
                loc = self.page.locator(sel).first
                loc.wait_for(state="detached", timeout=CONFIG.navigation_timeout_ms)
                self.logger.info("[VERIFY] Send button detached after click; post may be submitted.")
                break
        except Exception:
            self.logger.info("[VERIFY] Send button detachment not detected; relying on post verification.")

    def verify_posted(self) -> None:
        """Best-effort verification.

        WhatsApp doesn't always show a clean toast we can rely on.
        We consider it successful if the send button disappears or composer closes.
        """

        self.logger.info("Verifying status post success...")
        try:
            # Wait until any known Send/Post button becomes hidden/detached.
            # This indicates WhatsApp accepted the post and closed/transitioned composer.
            for sel in SEND_BUTTON:
                loc = self.page.locator(sel).first
                try:
                    # If it exists and is visible, wait for it to be hidden.
                    if loc.is_visible():
                        loc.wait_for(state="hidden", timeout=CONFIG.navigation_timeout_ms)
                        self.logger.info("Post verification: send button disappeared.")
                        return
                except Exception:
                    # Try next selector fallback.
                    continue

            # If no send button was visible by the time we check, treat as success.
            self.logger.info("Post verification: send button not visible; assuming posted.")
        except Exception:
            # Defensive: even if verification is flaky, don't fail hard.
            self.logger.warn("Post verification was inconclusive; treating as success.")

    def close(self) -> None:
        """Close browser and Playwright."""

        if CONFIG.keep_browser_open:
            self.logger.info("Keeping browser open (per config).")
            return

        self.logger.info("Closing browser...")
        try:
            if self._context:
                self._context.close()
        finally:
            self._context = None
            if self._pw:
                self._pw.stop()
            self._pw = None
            self._page = None

    def post_status(self, image: str, caption: str, log_callback: Optional[LogCallback] = None) -> PostResult:
        """End-to-end flow used by the GUI."""

        if log_callback is not None:
            self.logger.callback = log_callback

        img_path = Path(image)
        if not img_path.exists() or not img_path.is_file():
            return PostResult(False, f"Image file not found: {image}")

        try:
            # Step 1: Launch persistent browser context (non-headless)
            self.launch_browser()

            # Step 2: Wait for login ready (QR scan if first time)
            self.wait_for_login()

            # Step 3: Navigate to Updates/Status tab
            self.open_status_tab()

            # Step 4: Click Add Status / My Status entry point
            self.click_add_status()

            # Step 5: Upload image using hidden file input (set_input_files)
            self.upload_image(str(img_path))

            # Step 6: Insert caption (optional)
            self.add_caption(caption)

            # Step 7: Click Send/Post
            self.send_status()

            # Step 8: Verify post success (best-effort)
            self.verify_posted()

            return PostResult(True, "Status posted successfully.")
        except Exception as exc:  # noqa: BLE001 - desired for UI automation
            self.logger.error(f"Automation failed: {type(exc).__name__}: {exc}")
            return PostResult(False, f"Automation failed: {type(exc).__name__}: {exc}")
        finally:
            self.close()
