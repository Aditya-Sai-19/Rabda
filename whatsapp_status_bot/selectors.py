"""Selector fallback lists.

WhatsApp Web changes DOM frequently, so we keep multiple candidates.
All selectors should be used via fallback logic (never assume one selector).
"""

from __future__ import annotations

# Login ready - detect when WhatsApp Web is fully loaded and logged in
# Using multiple stable indicators that persist across UI updates
LOGIN_READY = [
    # Side panel / chat list indicators (most stable)
    "div[aria-label='Chat list']",
    "div[aria-label='Chats']",
    "[data-icon='chat']",
    "[data-icon='menu']",
    # Search box in sidebar
    "div[aria-label='Search input textbox']",
    "div[title='Search input textbox']",
    "[data-icon='search']",
    # New chat / menu buttons
    "[data-icon='new-chat-outline']",
    "span[data-icon='menu']",
    # Header elements
    "header[data-testid='chatlist-header']",
    "div[data-testid='chat-list']",
    # Fallback: any contenteditable (original selectors)
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true'][data-tab]",
]

# Updates/Status tab entry point
STATUS_TAB_SELECTORS = [
    # Primary selectors for Updates/Status tab
    '[data-icon="status-outline"]',
    '[data-icon="status-v3-outline"]',
    'button[aria-label*="Updates" i]',
    'div[aria-label*="Updates" i]',
    'button[aria-label*="Status" i]',
    'div[aria-label*="Status" i]',
    'div[role="button"][aria-label*="status" i]',
    'div[role="button"][aria-label*="updates" i]',
    # Text-based fallbacks
    'span:has-text("Updates")',
    'span:has-text("Status")',
]

# Backwards-compatible alias
STATUS_TAB = STATUS_TAB_SELECTORS

# The + icon at top-right of Status page (used to add new status when one exists)
ADD_STATUS_PLUS_ICON = [
    "[data-icon='plus']",
    "[data-icon='plus-unread']",
    "[data-testid='status-v3-add']",
    "button[aria-label*='New status' i]",
    "div[aria-label*='New status' i]",
    "[aria-label*='New status' i]",
    "span[data-icon='plus']",
]

# Add / My Status button (used when no status exists yet)
ADD_STATUS_SELECTORS = [
    # Text-based selectors
    "text=My status",
    "text=Add status",
    "text=Add Status",
    # Aria-label based
    "button[aria-label*='Add status' i]",
    "div[aria-label*='My status' i]",
    "div[aria-label*='Add status' i]",
    "[aria-label*='My status' i]",
    # Icon-based
    "[data-icon='status-v3-unread']",
    # Role-based with text
    "div[role='button']:has-text('My status')",
    "div[role='button']:has-text('Add')",
]

# Chooser option after clicking My status (new WhatsApp UI)
MEDIA_STATUS_SELECTORS = [
    "text=Photos & videos",
    "text=Photos and videos",
    "text=Photo & video",
    "text=Photos",
    "text=Image",
    "div[role='button']:has-text('Photos')",
    "div[role='button']:has-text('videos')",
    "div[role='menuitem']:has-text('Photos')",
    "div[role='menuitem']:has-text('Image')",
    "[aria-label*='Photos' i]",
    "[aria-label*='Image' i]",
]

# Backwards-compatible alias
ADD_STATUS_BUTTON = ADD_STATUS_SELECTORS

# File input for status upload
FILE_INPUT = [
    "input[type='file']",
    "input[type='file'][accept*='image' i]",
]

# Preview/caption area for status (must be specific to avoid chat search box)
# These are used as fallbacks; the primary method uses get_by_placeholder
CAPTION_BOX = [
    # Case-insensitive partial matches for aria-label
    "div[aria-label*='caption' i][contenteditable='true']",
    "div[aria-label*='Caption' i][contenteditable='true']",
    # Exact aria-label matches
    "div[aria-label='Add a caption']",
    "div[aria-label='Type a caption']",
    # data-placeholder attribute
    "div[data-placeholder*='caption' i]",
    "div[data-placeholder='Add a caption']",
    # data-testid based
    "div[data-testid='caption-input']",
    "div[data-testid='media-caption-input']",
    "div[data-testid='caption-input-text-container']",
    # title attribute
    "div[title*='caption' i]",
]

# Send/Post button for status
SEND_BUTTON = [
    # Icon-based (most reliable for current WhatsApp Web)
    '[data-icon="send"]',
    'span[data-icon="send"]',
    # Status-specific send/post buttons
    '[data-testid="send"]',
    '[data-testid="compose-btn-send"]',
    # Aria-label based
    "button[aria-label*='Send' i]",
    "button[aria-label*='Post' i]",
    "div[role='button'][aria-label*='Send' i]",
    "div[role='button'][aria-label*='Post' i]",
    # Generic clickable with send icon
    "div[role='button'] [data-icon='send']",
]

# New DOM-based selector set for the current WhatsApp Web UI.
SEND_BUTTON_SELECTORS = [
    # Icon-based send button (preferred - most stable)
    '[data-icon="send"]',
    'span[data-icon="send"]',
    '[data-testid="send"]',
    '[data-testid="compose-btn-send"]',
    # Parent button containing send icon
    'button:has([data-icon="send"])',
    'div[role="button"]:has([data-icon="send"])',
    # Text-based alternatives (fallback)
    'button[aria-label*="Send" i]',
    'button[aria-label*="Post" i]',
    'div[aria-label*="Send" i]',
]

# A rough indicator that the preview composer is open
PREVIEW_READY = [
    # Send button presence indicates preview is ready
    '[data-icon="send"]',
    'span[data-icon="send"]',
    '[data-testid="send"]',
    "button[aria-label*='Send' i]",
    "button[aria-label*='Post' i]",
    # Image preview indicators
    "div[data-testid='media-canvas']",
    "img[draggable='false']",
]
