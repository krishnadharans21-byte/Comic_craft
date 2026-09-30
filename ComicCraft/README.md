# ComicCraft — AI Comic Story Creator

ComicCraft is a small, beginner-friendly FastAPI project that turns a creative brief into an illustrated **five-panel comic** and a downloadable PDF. It uses Jinja2, HTML, CSS, and vanilla JavaScript for the interface. Google Gemini and Hugging Face are optional online services; the app is still fully demonstrable without keys or a powerful GPU.

## What it does

- Collects a story prompt, main character name, setting, tone, and art style.
- Generates a connected five-beat outline (setup, conflict, development, climax, resolution), then expands it into captions, narration, and short dialogue.
- Generates one landscape illustration per panel through the Hugging Face Inference Providers client when configured.
- Creates an attractive Pillow placeholder with the visible message **“Image generation unavailable”** and the panel number if image generation is not configured or fails.
- Shows a five-panel preview and exports a multi-page PDF with FPDF2.
- Offers form-based pages, a JSON comic API, an image-test route, and FastAPI's interactive `/docs`.
- Falls back to deterministic sample story content whenever Gemini is not configured or cannot be reached.

## Requirements

- Windows 10/11 and Python **3.11 or newer**
- VS Code (recommended) with its Python extension
- Internet access for the first package installation and for optional online AI generation

Local Diffusers, PyTorch, and a GPU are **not required**. A Hugging Face token can generate art through their hosted Inference Providers service. If you choose to add API credentials, they remain in your local `.env` file and are never committed.

## Quick start on Windows

1. Download/extract the project folder and open that folder in VS Code.
2. In File Explorer, double-click `run.bat`, or open the VS Code terminal in the project root and run:

   ```powershell
   .\run.bat
   ```

   The launcher creates `.venv`, copies `.env.example` to `.env` if needed, installs requirements, and starts Uvicorn.
3. Open <http://127.0.0.1:8000>.
4. To stop the server, focus the terminal and press **Ctrl+C**.

### Manual setup in the VS Code terminal

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks virtual-environment activation, you can skip activation and use `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then `.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`.

## Optional AI configuration

The application starts in **demo mode without any API key**. The story and placeholder artwork still render, and PDF export works. For original AI content, open `.env` in VS Code and add:

```dotenv
GEMINI_API_KEY=your_google_ai_studio_key
HUGGINGFACE_API_KEY=your_hugging_face_token
```

- Create a Gemini key through [Google AI Studio](https://aistudio.google.com/app/apikey). The default outline model is `gemini-3.8-flash` and the narration model is `gemini-3.1-pro-preview`; these are current Gemini API model IDs at the time this project was built. Set `GEMINI_OUTLINE_MODEL` or `GEMINI_STORY_MODEL` to a model enabled for your account if availability changes. Gemini model access can vary by account and region.
- Create a Hugging Face token with **Inference Providers** permission in [Hugging Face token settings](https://huggingface.co/settings/tokens). The default image model is `stabilityai/stable-diffusion-3-medium-diffusers`. Model/provider access may vary. The hosted provider may have its own usage limits or charges.
- You can configure only Gemini or only Hugging Face. Missing or failing services degrade gracefully to the demo story or panel placeholders respectively.
- After changing `.env`, restart the server to load the new settings.
- Never share an API token or put one in source code. `.env` is excluded by `.gitignore`.

All supported settings are in `.env.example`. In particular, `IMAGE_TIMEOUT` controls the provider timeout and `PDF_FONT_PATH` may point at a TrueType font such as `C:/Windows/Fonts/arial.ttf` when you need broader PDF character support.

## Generate a comic through the API

Interactive documentation is at <http://127.0.0.1:8000/docs>. Example JSON request:

```json
{
  "story_prompt": "A curious fox finds a glowing compass that points toward whatever needs help.",
  "character_name": "Pip",
  "setting": "an enchanted forest",
  "tone": "Adventurous",
  "art_style": "Classic comic book"
}
```

Send it to `POST /generate-comic/json`. The response includes five panel objects, the AI/demo status, and a `pdf_url` such as `/static/exports/comiccraft_comic_<id>.pdf`.

Other useful routes:

| Route | Purpose |
|---|---|
| `GET /` | Story creation page |
| `POST /generate` | Create a comic from the browser form |
| `GET /preview/{comic_id}` | Reopen a comic from the current running session |
| `POST /export/{comic_id}` | Generate a PDF and redirect to the export confirmation |
| `GET /export-success` | PDF export success page |
| `POST /generate-comic/json` | JSON comic generation API |
| `POST /test-image` | Generate one image or a Pillow fallback for testing |
| `GET /api/status` | Check whether optional services are configured (never returns secret values) |
| `GET /health` | Basic health check |
| `GET /docs` | FastAPI Swagger UI |
| `GET /manus-routes.json` | Page-route manifest |

Comics are kept in process memory for preview/export navigation; files are written to `static/panels/` and `static/exports/`. Restarting the local development server clears the in-memory comic index. Back up any PDFs you want to keep.

## Run tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

The tests use local fallback fixtures and do not call Gemini or Hugging Face or require API keys.

## Project structure

```text
ComicCraft/
├── app/
│   ├── main.py                 # FastAPI app, static files, and startup
│   ├── routes.py               # Browser, JSON, test-image, and export routes
│   ├── models.py               # Pydantic input and story contracts
│   ├── config.py               # Environment settings and local paths
│   ├── services/
│   │   ├── gemini_flash.py     # Structured five-panel outline
│   │   ├── gemini_pro.py       # Narration and dialogue
│   │   ├── demo_generator.py   # Deterministic no-key story fallback
│   │   ├── image_generator.py  # Hosted images and Pillow placeholders
│   │   ├── layout_builder.py   # Panel/image/story assembly
│   │   └── exporters.py        # FPDF2 export
│   └── utils/helpers.py        # Safe filenames, directories, and JSON parsing
├── templates/                  # Jinja2 pages
├── static/css/style.css        # Responsive Panel Pop design
├── static/js/app.js            # Character counter and loading state
├── static/img/                 # Local ComicCraft mark and favicon
├── static/panels/              # Generated panel images
├── static/exports/             # Exported PDFs
├── tests/                      # Offline route and service tests
├── .env.example
├── requirements.txt
├── run.bat
└── README.md
```

## Troubleshooting

- **No Python 3.11 runtime installed:** in the VS Code terminal run `py install 3.11` (for the Windows Python Install Manager), or install Python 3.11+ from [python.org](https://www.python.org/downloads/), then reopen VS Code and run `run.bat` again. The launcher checks for an installed Python 3.11+ runtime before creating `.venv`.
- **`python` or `py` command not found:** install Python 3.11+ from [python.org](https://www.python.org/downloads/) and enable its PATH option; reopen VS Code afterward.
- **AI story is in demo mode:** check that the key is in the root `.env`, has no quotes or extra spaces, the model is enabled for your account, and restart Uvicorn. Demo mode is an intentional fallback, not a startup failure.
- **AI art is unavailable:** check the Hugging Face token's Inference Providers permission, selected model availability, network access, and provider limits. Pillow placeholders preserve the preview/PDF flow.
- **PDF fonts or non-English characters:** set `PDF_FONT_PATH` to a suitable `.ttf` on your computer and restart. If no Unicode font is available, text is normalized for FPDF's built-in font support.
- **Port 8000 is busy:** stop the other application or change the `--port 8000` argument in `run.bat` and README commands to another free port.

## Technology notes

The project uses the current official `google-genai` package and Gemini structured response schemas; it intentionally does not use the deprecated `google-generativeai` package. Image generation uses `huggingface_hub.InferenceClient`, not locally installed Diffusers, so the project stays lightweight enough for a standard student laptop.
