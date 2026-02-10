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
    ADD_STATUS_PLUS_ICON,
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
from .csv_handler import CsvHandler, HEADER_STATUS

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
        
        # Try to find any login-ready indicator (attached to DOM is sufficient)
        # Some elements may not be visible but indicate login is complete
        try:
            first_attached_locator(self.page, LOGIN_READY, timeout_ms=CONFIG.navigation_timeout_ms)
            self.logger.info("Login ready (chat UI detected).")
            return
        except Exception as exc:
            self.logger.info(f"Primary login detection failed: {exc}")
        
        # Fallback: wait for any element that indicates the main app is loaded
        fallback_selectors = [
            "div[id='app']",
            "div[id='main']",
            "#side",
            "div[data-testid='chat-list']",
        ]
        try:
            first_attached_locator(self.page, fallback_selectors, timeout_ms=CONFIG.navigation_timeout_ms)
            self.logger.info("Login ready (fallback detection).")
        except Exception as exc:
            self.logger.error(f"Login detection failed: {exc}")
            raise RuntimeError("Failed to detect WhatsApp Web login - please ensure you are logged in")

    def open_status_tab(self) -> None:
        """Navigate to Updates/Status tab."""

        self.logger.info("Navigating to Updates/Status tab...")

        verify_selectors = [
            "text=My status",
            "text=Add status",
            "text=Add Status",
            "input[type='file']",
            "[data-icon='status-v3-unread']",
            "div[aria-label*='My status' i]",
            "div[aria-label*='Add status' i]",
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
        """Click Add Status / My Status entry point.
        
        When a status already exists, clicking 'My status' opens the viewer.
        Instead, we must click the + icon at the top-right of the Status page.
        We try the + icon first, then fall back to 'My status' / 'Add status'.
        """

        # Step 1: Try the + icon first (works when a status already exists)
        self.logger.info("[STEP] Looking for + icon to add new status...")
        for sel in ADD_STATUS_PLUS_ICON:
            try:
                loc = self.page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    self.logger.info(f"[OK] Found + icon: {sel}")
                    loc.click()
                    human_delay(0.8)
                    return
            except Exception:
                continue

        # Step 2: Fall back to 'My status' / 'Add status' (when no status exists yet)
        self.logger.info("[STEP] + icon not found; clicking My status / Add status...")
        safe_click(
            self.page,
            ADD_STATUS_SELECTORS,
            timeout_ms=CONFIG.action_timeout_ms,
            tries=CONFIG.max_action_retries,
            log=self.logger.info,
        )
        human_delay(0.8)

    def upload_image(self, image_path: str) -> None:
        """Upload image. Click 'Photos & videos' if present, handling file chooser."""

        self.logger.info("[STEP] Uploading image")
        
        # 1. Try to find/click 'Photos & videos' with file chooser handling
        media_btn_clicked = False
        try:
            # Check if any media selector is visible
            for media_sel in MEDIA_STATUS_SELECTORS:
                # We use a short timeout check to see if the menu is open
                loc = self.page.locator(media_sel).first
                if loc.is_visible(timeout=2000):
                    self.logger.info(f"[STEP] Found media button '{media_sel}'. Clicking with file chooser.")
                    
                    with self.page.expect_file_chooser(timeout=CONFIG.action_timeout_ms) as fc_info:
                        loc.click()
                    
                    file_chooser = fc_info.value
                    file_chooser.set_files(image_path)
                    media_btn_clicked = True
                    self.logger.info("File chooser handled successfully.")
                    break
        except Exception as exc:
            self.logger.info(f"Media button click/chooser failed or not found: {exc}")

        # 2. If we didn't click the media button (maybe Old UI or different state),
        # try strictly DOM-based upload on the input element.
        if not media_btn_clicked:
            self.logger.info("Media button not clicked; attempting direct DOM upload.")
            try:
                # Use attached-based locator logic
                safe_set_input_files(self.page, FILE_INPUT, image_path, timeout_ms=CONFIG.action_timeout_ms)
            except Exception as exc:
                self.logger.error(f"Direct DOM upload failed: {exc}")
                raise

        # Wait for preview/compose screen signals.
        first_visible_locator(self.page, PREVIEW_READY, timeout_ms=CONFIG.navigation_timeout_ms)
        self.logger.info("Image preview ready.")


    def add_caption(self, caption: str) -> None:
        """Add optional caption in the status preview screen."""

        if not caption.strip():
            self.logger.info("No caption provided; skipping caption step.")
            return

        self.logger.info("Adding caption...")
        human_delay(1.0)
        
        caption_added = False

        # Method 1: Playwright get_by_placeholder (most reliable)
        for placeholder_text in ["Add a caption", "Type a caption", "Caption"]:
            try:
                loc = self.page.get_by_placeholder(placeholder_text).first
                if loc.is_visible(timeout=3000):
                    self.logger.info(f"[STEP] Found caption via placeholder: '{placeholder_text}'")
                    loc.click()
                    human_delay(0.3)
                    self.page.keyboard.type(caption, delay=30)
                    human_delay(0.5)
                    self.logger.info("Caption typed via placeholder.")
                    caption_added = True
                    break
            except Exception:
                continue

        # Method 2: CSS selector fallbacks from CAPTION_BOX
        if not caption_added:
            for sel in CAPTION_BOX:
                try:
                    loc = self.page.locator(sel).first
                    if loc.is_visible(timeout=2000):
                        self.logger.info(f"[STEP] Found caption box: {sel}")
                        loc.click()
                        human_delay(0.3)
                        self.page.keyboard.type(caption, delay=30)
                        human_delay(0.5)
                        self.logger.info("Caption typed via selector.")
                        caption_added = True
                        break
                except Exception:
                    continue

        # Method 3: JavaScript-based detection — find the contenteditable
        # that is inside the status image editor overlay (not the main chat)
        if not caption_added:
            self.logger.info("[STEP] Trying JS-based caption detection...")
            try:
                found = self.page.evaluate("""() => {
                    // Find all contenteditable divs
                    const editables = document.querySelectorAll('div[contenteditable="true"]');
                    for (const el of editables) {
                        const rect = el.getBoundingClientRect();
                        // Caption field is at the bottom of the viewport, narrow height
                        // and must be visible (not zero size)
                        if (rect.width > 100 && rect.height > 10 && rect.height < 150
                            && rect.bottom > window.innerHeight * 0.8) {
                            el.click();
                            el.focus();
                            return true;
                        }
                    }
                    return false;
                }""")
                if found:
                    human_delay(0.3)
                    self.page.keyboard.type(caption, delay=30)
                    human_delay(0.5)
                    self.logger.info("Caption typed via JS detection.")
                    caption_added = True
            except Exception as exc:
                self.logger.info(f"JS caption detection failed: {exc}")

        if not caption_added:
            self.logger.warn("Caption box not found; proceeding without caption.")

    def send_status(self) -> None:
        """Click Send/Post button (DOM-based, with updated selectors)."""

        self.logger.info("Posting status (clicking Send/Post)...")
        clicked = False
        
        # Step 1: Try clicking each send button selector individually
        for sel in SEND_BUTTON_SELECTORS:
            try:
                loc = self.page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    self.logger.info(f"[STEP] Found send button: {sel}")
                    loc.scroll_into_view_if_needed()
                    human_delay(0.3)
                    loc.click(timeout=CONFIG.action_timeout_ms)
                    clicked = True
                    self.logger.info(f"[OK] Clicked send button: {sel}")
                    break
            except Exception:
                continue
        
        # Step 2: Try clicking parent element of send icon
        if not clicked:
            try:
                # Find the send icon and click its parent
                send_icon = self.page.locator('[data-icon="send"]').first
                if send_icon.is_visible(timeout=3000):
                    # Click the parent button/div
                    parent = send_icon.locator('xpath=..')
                    parent.click(timeout=CONFIG.action_timeout_ms)
                    clicked = True
                    self.logger.info("[OK] Clicked parent of send icon")
            except Exception as exc:
                self.logger.info(f"[WARN] Parent click failed: {exc}")
        
        # Step 3: Fallback - use Enter key to send (most reliable)
        if not clicked:
            self.logger.info("[STEP] Using Enter key to send status...")
            try:
                human_delay(0.5)
                self.page.keyboard.press("Enter")
                clicked = True
                self.logger.info("[OK] Pressed Enter to send")
            except Exception as exc:
                self.logger.info(f"[WARN] Enter key failed: {exc}")
        
        # Step 4: Last resort - safe_click with all selectors
        if not clicked:
            self.logger.info("[STEP] Trying safe_click fallback...")
            safe_click(
                self.page,
                SEND_BUTTON,
                timeout_ms=CONFIG.action_timeout_ms,
                tries=CONFIG.max_action_retries,
                log=self.logger.info,
            )

        # Post-click: wait for transition
        human_delay(1.0)
        self.logger.info("[STEP] Status send initiated, waiting for completion...")

    def verify_posted(self) -> None:
        """Best-effort verification.

        WhatsApp doesn't always show a clean toast we can rely on.
        We consider it successful if the send button disappears or composer closes.
        """

        self.logger.info("Verifying status post success...")
        human_delay(2.0)  # Give WhatsApp time to process
        
        # Check if send button is gone (indicates success)
        try:
            send_icon = self.page.locator('[data-icon="send"]').first
            if not send_icon.is_visible(timeout=3000):
                self.logger.info("Post verification: send button not visible; status posted successfully.")
        except Exception:
            pass
        
        self.logger.info("Post verification complete.")
        
        # Dismiss any post-send dialogs (e.g. "Select chats" share dialog)
        self._dismiss_post_send_dialogs()

    def _dismiss_post_send_dialogs(self) -> None:
        """Dismiss any dialogs that appear after posting status.
        
        WhatsApp often shows a 'Select chats' dialog after posting a status,
        asking if you want to share to specific chats. We need to dismiss it.
        """
        human_delay(1.0)
        
        # Method 1: Press Escape to dismiss any overlay/dialog
        try:
            self.page.keyboard.press("Escape")
            self.logger.info("[STEP] Pressed Escape to dismiss post-send dialog.")
            human_delay(0.5)
        except Exception:
            pass

        # Method 2: Click X button on "Select chats" dialog if still visible
        close_selectors = [
            "button[aria-label='Close']",
            "button[aria-label='close']",
            "[data-icon='x']",
            "[data-icon='close']",
            "span[data-icon='x']",
            "span[data-icon='x-viewer']",
        ]
        for sel in close_selectors:
            try:
                loc = self.page.locator(sel).first
                if loc.is_visible(timeout=1500):
                    loc.click()
                    self.logger.info(f"[OK] Dismissed dialog via: {sel}")
                    human_delay(0.5)
                    break
            except Exception:
                continue
        
        # Method 3: Press Escape again in case first one didn't work
        try:
            self.page.keyboard.press("Escape")
            human_delay(0.5)
        except Exception:
            pass

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

    def batch_upload(
        self,
        csv_path: str,
        images_dir: str,
        resume_mode: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> PostResult:
        """Process the CSV queue in batch mode."""

        if progress_callback:
            self.logger.callback = progress_callback

        handler = CsvHandler(csv_path)
        valid_msg = handler.validate()
        if valid_msg:
            return PostResult(False, f"CSV Validation Error: {valid_msg}")

        # 1. Reset if START (not resume), else filter for RESUME
        if not resume_mode:
            self.logger.info("Resetting all statuses to 'No' (START mode).")
            handler.reset_all_statuses()
            items = handler.read_queue()  # Read all
        else:
            self.logger.info("Resuming pending uploads (RESUME mode).")
            items = handler.read_queue(filter_status="No")

        if not items:
            return PostResult(True, "No pending items to upload.")

        total = len(items)
        success_count = 0
        skip_count = 0

        self.logger.info(f"Starting batch upload for {total} items...")

        try:
            # Step 1: Launch browser ONCE for the whole batch
            self.launch_browser()
            self.wait_for_login()

            for i, item in enumerate(items, start=1):
                self.logger.info(f"Processing {i}/{total}: {item.image_name}")
                
                # Build image path
                full_path = Path(images_dir) / item.image_name

                # Check existence
                if not full_path.exists():
                    self.logger.warn(f"Image not found: {full_path} - Skipping.")
                    handler.update_status(item.row_index, "No (Missing Image)")
                    skip_count += 1
                    continue

                # Upload
                try:
                    self.open_status_tab()
                    self.click_add_status()
                    self.upload_image(str(full_path))
                    self.add_caption(item.caption)
                    self.send_status()
                    self.verify_posted()
                    
                    # Update status on success
                    handler.update_status(item.row_index, "Yes")
                    success_count += 1
                    self.logger.info(f"Successfully uploaded: {item.image_name}")

                except Exception as exc:
                    self.logger.error(f"Failed to upload {item.image_name}: {exc}")
                    # Keep as No, or maybe mark as "Error"? 
                    # User said: "Upload failure: Keep status as "No" for retry"
                    # But verifying if it was a critical error vs transient is hard.
                    # We will continue to next item unless it is a browser crash.
                    
                    # If browser crashed, we might need to relaunch?
                    # For now, we propagate critical errors but log item errors.
                    if not self._page or self._page.is_closed():
                        raise exc
                    
                    # If just this item failed, update UI but keep status No
                    continue
                
                human_delay(2.0)

            summary = f"Batch Complete. Uploaded: {success_count} | Skipped: {skip_count} | Total: {total}"
            self.logger.info(summary)
            return PostResult(True, summary)

        except Exception as exc:
            self.logger.error(f"Batch processing stopped: {exc}")
            return PostResult(False, f"Batch failed: {exc}")
        finally:
            self.close()
