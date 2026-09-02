# FoodBridge — Week 1–2

FoodBridge is a presentation-ready local food-rescue inventory application. This milestone covers food intake, stock management, expiry prioritisation, CSV import, barcode/QR lookup, dashboard reporting, seeded demo data, and a desktop launcher. It intentionally does not include the planned Weeks 3–8 NGO matching, pickup routing, impact analytics, notifications, or authentication work.

## Architecture

```
React + Vite UI  ──HTTP──>  FastAPI API  ──> SQLite (backend/foodbridge.db)
       │
       └── pywebview launcher (desktop/main.py)
```

The scanner view accepts a USB scanner as keyboard input, manual code entry, and has a camera-scanner foundation powered by ZXing. Seeded codes `FB-1001` through `FB-1006` can be used in the demo.

## Run locally

Prerequisites: Python 3.13+ and Node.js 20+.

Install API dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

Install and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

In a second PowerShell window, start the backend:

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --port 8010
```

Open `http://127.0.0.1:5174`. The API documentation is at `http://127.0.0.1:8010/docs`.

To run it as a desktop shell (with the dependencies installed and `npm install` completed):

```powershell
python desktop/main.py
```

## Verification

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -q -p no:cacheprovider
cd frontend
npm run build
```

## CSV format

Use [docs/sample-inventory.csv](docs/sample-inventory.csv) as a template. Required columns are `name`, `category`, `quantity`, `unit`, `expiry_date` (ISO `YYYY-MM-DD`), and `donor`. `barcode` and `notes` are optional.

## Data notes

SQLite is automatically created at `backend/foodbridge.db` when the API first starts. It is seeded only when empty. To reset the demo data, stop the API and remove that database file; it will be re-created and seeded on next start.
