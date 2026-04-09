# Deploy Pest Shield API on Render

## 1) Push to GitHub
- Commit this folder and push to a GitHub repo.

## 2) Create Web Service on Render
- In Render: **New +** -> **Blueprint** (recommended) or **Web Service**
- Select your repo.
- If using Blueprint, Render reads `render.yaml` automatically.

## 3) Set environment variables
- `OPENROUTER_API_KEY` = your key (required)
- `PEST_VISION_MODEL` = `openai/gpt-4o-mini` (optional)

## 4) Verify API
- After deploy, open:
  - `/health`
  - `/docs`
- Example:
  - `https://your-service.onrender.com/health`

## 5) Connect Flutter app
Run the app with API base URL:

```bash
flutter run --dart-define=API_BASE_URL=https://your-service.onrender.com
```

For release APK:

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://your-service.onrender.com
```

## Notes
- If `API_BASE_URL` is not provided, app falls back to demo classifier.
- Render free tier can sleep; first request may be slow.
