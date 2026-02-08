"""Selector fallback lists.

WhatsApp Web changes DOM frequently, so we keep multiple candidates.
All selectors should be used via fallback logic (never assume one selector).
"""

from __future__ import annotations

# Login ready (chat textbox)
LOGIN_READY = [
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true'][data-tab]",
    "div[role='textbox'][contenteditable='true']",
]

# Updates/Status tab entry point
STATUS_TAB_SELECTORS = [
    'button[aria-label*="Updates"]',
    'div[aria-label*="Updates"]',
    'button[aria-label*="Status"]',
    '[data-icon="status-outline"]',
    'div[role="button"][aria-label*="status"]',
]

# Backwards-compatible alias
STATUS_TAB = STATUS_TAB_SELECTORS

# Add / My Status button
ADD_STATUS_SELECTORS = [
    "text=My status",
    "text=Add status",
    "button[aria-label*='Add status' i]",
    "div[aria-label*='My status' i]",
]

# Chooser option after clicking My status (new WhatsApp UI)
MEDIA_STATUS_SELECTORS = [
    "text=Photos & videos",
    "text=Photos and videos",
    "text=Photos",
    "div[role='button']:has-text('Photos')",
    "div[role='button']:has-text('videos')",
]

# Backwards-compatible alias
ADD_STATUS_BUTTON = ADD_STATUS_SELECTORS

# File input for status upload
FILE_INPUT = [
    "input[type='file']",
    "input[type='file'][accept*='image' i]",
]

# Preview/caption area (often contenteditable)
CAPTION_BOX = [
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true'][data-tab]",
    "footer div[contenteditable='true']",
]

# Send/Post button
SEND_BUTTON = [
    "button[aria-label*='Send' i]",
    "button[aria-label*='Post' i]",
    "div[role='button'][aria-label*='Send' i]",
    "div[role='button'][aria-label*='Post' i]",
]

# New DOM-based selector set for the current WhatsApp Web UI.
SEND_BUTTON_SELECTORS = [
    # Icon-based send button (preferred)
    'span[data-icon="send"]',
    'button span[data-icon="send"]',
    'div[role="button"] span[data-icon="send"]',
    # Text-based alternatives (fallback)
    'button[aria-label*="Send"]',
    'button[aria-label*="send"]',
]

# A rough indicator that the preview composer is open
PREVIEW_READY = [
    "input[type='file']",
    "button[aria-label*='Send' i]",
    "button[aria-label*='Post' i]",
]
