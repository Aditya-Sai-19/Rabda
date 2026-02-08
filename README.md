# WhatsApp Status Bot (Playwright + Tkinter)

Windows desktop Python app that posts an **image** as a WhatsApp Status using **WhatsApp Web UI automation** (not API-based).

## Requirements

- Python 3.11+
- Windows
- WhatsApp account

## Install

1. Create/activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:

```bash
playwright install chromium
```

## Run

From the folder that contains `whatsapp_status_bot/`:

```bash
python -m whatsapp_status_bot.main
```

## First-time login (QR)

- The app uses a **Chromium persistent context** with a saved session folder at:
  - `whatsapp_status_bot/session/`
- The first time you run it, WhatsApp Web will ask you to scan the QR code.
- After a successful scan, future runs should reuse the session.

## Usage

- Click **Browse Image...** and select an image.
- Optionally type a caption.
- Click **Post Status**.

The UI stays responsive because automation runs in a background thread.

## Important notes (Selector fragility)

WhatsApp Web changes its DOM frequently. This project uses:

- Selector fallback lists (multiple candidates per element)
- Retry logic for clicks
- Wait-for-visible before actions

Even with these strategies, selectors may break in the future.

## Troubleshooting

- If it keeps waiting for login:
  - Make sure you completed the QR scan in the opened browser window.
  - Try deleting `whatsapp_status_bot/session/` to force a fresh login.
- If upload/click steps fail:
  - WhatsApp UI changed; update `selectors.py` with new selector fallbacks.
- If Playwright is missing browsers:
  - Run `playwright install chromium`

## Disclaimer

This is UI automation. Use responsibly and be aware that WhatsApp may change UI behavior or apply limitations.
