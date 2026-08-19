# Kural AI Voice Assistant v2

**Kural AI** is a voice assistant with live Microsoft Excel automation and bilingual (Tamil & English) speech synthesis powered by Sarvam AI.

---

## 🌟 Key Features

- **🗣️ Natural Voice Interaction**: Interactive voice orb interface with continuous listening, real-time visual feedback, and audio wave animation.
- **🎙️ Tamil & English TTS**: High-quality Indian language text-to-speech powered by Sarvam AI (`bulbul:v1` model, voices like `meera`).
- **📊 Live Microsoft Excel Automation**:
  - Live desktop control via Win32 COM / `win32com.client`.
  - Natural language commands in Tamil, English, and Tamil-English (e.g. *"open excel"*, *"excel open pannu"*, *"write sales data in column A"*).
  - Cell formatting, calculations, charts, styling, and multi-sheet workflows.
  - Safe fallback headless mode via `openpyxl` when Excel desktop is not installed.
- **⚡ Modern Responsive Web UI**: Built with SvelteKit, TypeScript, and FastAPI.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend development)
- Microsoft Excel (optional, for live desktop UI interaction on Windows)

### 1. Environment Configuration

Copy the example environment configuration:
```bash
cp .env.example .env
```

Set your API keys in `.env`:
```ini
SARVAM_API_KEY=your_sarvam_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Run Backend Server

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Launch the assistant
python -m cptr.cli run
```

Access the web interface at `http://localhost:8000`.

---

## 🧪 Testing & Verification

Run the test suite to verify Excel automation and Sarvam TTS integration:

```bash
# Verify Sarvam TTS provider
python -m unittest tests/test_sarvam_tts_provider.py

# Verify live Excel desktop control
python -m unittest tests/test_excel_live_desktop_verification.py
```
