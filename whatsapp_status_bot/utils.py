"""Automation utility helpers (retries, fallback selectors, safe actions)."""

from __future__ import annotations

import random
import time
from typing import Callable, Iterable, Optional, TypeVar

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from .config import CONFIG

T = TypeVar("T")


def human_delay(multiplier: float = 1.0) -> None:
    """Sleep a short random time to mimic human pacing."""

    low = CONFIG.min_human_delay_s * multiplier
    high = CONFIG.max_human_delay_s * multiplier
    time.sleep(random.uniform(low, high))


def retry(fn: Callable[[], T], *, tries: int, on_retry: Optional[Callable[[int, Exception], None]] = None) -> T:
    """Retry wrapper with exponential-ish backoff."""

    last_exc: Optional[Exception] = None
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentional for automation stability
            last_exc = exc
            if attempt >= tries:
                break
            if on_retry:
                on_retry(attempt, exc)
            backoff = CONFIG.retry_backoff_base_s * attempt
            time.sleep(backoff)
    assert last_exc is not None
    raise last_exc


def first_visible_locator(page: Page, selectors: Iterable[str], *, timeout_ms: int) -> Locator:
    """Return a locator for the first visible element matching any of the selectors."""

    # Join selectors with commas to create an OR selector.
    # This allows Playwright to find whichever one appears first efficiently.
    joined_selector = ", ".join(selectors)
    
    loc = page.locator(joined_selector).first
    loc.wait_for(state="visible", timeout=timeout_ms)
    return loc


def first_attached_locator(page: Page, selectors: Iterable[str], *, timeout_ms: int) -> Locator:
    """Return a locator for the first element attached to the DOM matching any of the selectors."""

    joined_selector = ", ".join(selectors)
    
    loc = page.locator(joined_selector).first
    loc.wait_for(state="attached", timeout=timeout_ms)
    return loc


def safe_click(page: Page, selectors: Iterable[str], *, timeout_ms: int, tries: int, log: Callable[[str], None]) -> None:
    """Click an element using selector fallbacks + retries."""

    selector_list = list(selectors)
    last_exc: Optional[Exception] = None

    for attempt in range(1, tries + 1):
        for sel in selector_list:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=timeout_ms)

                # Ensure interactable.
                try:
                    if not loc.is_enabled():
                        raise RuntimeError("Element not enabled")
                except Exception:
                    # Some nodes may not support enabled state; proceed defensively.
                    pass

                loc.scroll_into_view_if_needed()
                human_delay()

                # Debug: which selector is being attempted.
                log(f"[STEP] Clicking selector: {sel}")
                loc.click(timeout=timeout_ms)
                log(f"[OK] Clicked selector: {sel}")
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                continue

        if attempt < tries:
            log(
                f"[RETRY] Click attempt {attempt + 1}/{tries} after failing all selectors. "
                f"Last error: {type(last_exc).__name__ if last_exc else 'Unknown'}: {last_exc}"
            )
            human_delay(1.5)

    raise last_exc or RuntimeError("safe_click failed with unknown error")


def safe_fill(locator: Locator, text: str, *, timeout_ms: int) -> None:
    """Fill text in an input/contenteditable safely."""

    locator.wait_for(state="visible", timeout=timeout_ms)
    locator.scroll_into_view_if_needed()
    human_delay()
    try:
        locator.fill(text, timeout=timeout_ms)
    except PlaywrightTimeoutError:
        locator.click(timeout=timeout_ms)
        human_delay()
        locator.press_sequentially(text, delay=20)


def safe_set_input_files(page: Page, selectors: Iterable[str], file_path: str, *, timeout_ms: int) -> None:
    """Find an attached file input and set files.

    Prefer an element that is attached to the DOM (even if not visible) to
    avoid triggering OS file picker dialogs. This aligns with a DOM-based
    upload path.
    """

    # Use the attached-locator helper to find a file input that is present in the DOM.
    loc = first_attached_locator(page, selectors, timeout_ms=timeout_ms)
    loc.set_input_files(file_path, timeout=timeout_ms)
    human_delay(1.2)
