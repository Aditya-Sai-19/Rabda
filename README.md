# WhatsApp Status Automation

A robust Windows desktop application to automate uploading images and captions to WhatsApp Status using Playwright and Tkinter.

## 🌟 Features

- **Automated Status Upload**: Uploads images with optional captions to WhatsApp Status.
- **Graphical User Interface (GUI)**: Simple and intuitive interface built with Tkinter.
- **Persistent Session**: Logs in once (via QR code) and saves the session for future use.
- **Smart Selectors**: Uses fallback selectors and retry logic to handle WhatsApp Web's dynamic DOM.
- **Safe Automation**: Implements human-like delays and waits to mimic real user behavior.
- **Detailed Logging**: View real-time automation logs directly in the application.

## 🛠️ Prerequisites

- **OS**: Windows
- **Python**: 3.11 or higher
- **WhatsApp**: An active WhatsApp account on your phone (linked via QR code).

## 🚀 Installation

1.  **Clone the repository** (or ensure you have the project files).

2.  **Create a Virtual Environment** (Recommended):
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```powershell
    pip install -r whatsapp_status_bot/requirements.txt
    ```

4.  **Install Playwright Browsers**:
    ```powershell
    playwright install chromium
    ```

## 📖 Usage

1.  **Run the Application**:
    From the root directory (`STATUS AUTOMATION`), run:
    ```powershell
    python -m whatsapp_status_bot.main
    ```

2.  **First Run (Authentication)**:
    - A Chromium window will open with WhatsApp Web.
    - **Scan the QR code** with your phone (WhatsApp > Settings > Linked Devices > Link a Device).
    - Once logged in, the session will be saved to `whatsapp_status_bot/session/`. Future runs will auto-login.

3.  **Posting a Status**:
    - **Browse**: Select an image file (`.jpg`, `.png`, `.webp`, `.bmp`).
    - **Caption**: (Optional) Enter a text caption.
    - **Post**: Click "Post Status".
    - The bot will navigate to the Status tab, upload the image, add the caption, and post it automatically.

## 📂 Project Structure

```text
STATUS AUTOMATION/
├── whatsapp_status_bot/
│   ├── __init__.py
│   ├── config.py           # Configuration (timeouts, paths, delays)
│   ├── gui.py              # Tkinter GUI implementation
│   ├── logger.py           # Logging utility
│   ├── main.py             # Application entry point
│   ├── requirements.txt    # Python dependencies
│   ├── selectors.py        # CSS/XPath selectors for WhatsApp Web
│   ├── status_uploader.py  # Core Playwright automation logic
│   └── utils.py            # Helper functions
└── README.md
```

## ⚙️ Configuration

You can adjust settings in `whatsapp_status_bot/config.py`:
- `keep_browser_open`: Set to `False` to close the browser after posting (default can be changed here).
- `debug`: Enable/disable debug logging.
- **Timeouts**: Adjust `navigation_timeout_ms` or `action_timeout_ms` for slower connections.

## 🔧 Troubleshooting

- **Stuck on Login**: If the bot waits indefinitely for login, close the app, delete the `whatsapp_status_bot/session` directory, and restart to triggering a fresh QR scan.
- **Selectors/Elements Not Found**: WhatsApp Web updates frequently. If the bot fails to click buttons (like "My status"), check `whatsapp_status_bot/selectors.py`. The project uses a list of fallback selectors, but new updates might require adding new ones.
- **Browser Issues**: If errors occur related to the browser, try running `playwright install --with-deps chromium`.

## ⚠️ Disclaimer

This tool uses UI automation. Use responsibly. WhatsApp may change their user interface at any time, which could break the automation logic until selectors are updated.
