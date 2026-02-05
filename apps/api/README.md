# TogeNuki API

Backend API service for TogeNuki - Email voice playback service.

## Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start development server
uvicorn src.main:app --reload
```

## Cloud Run Deployment

### Prerequisites

1. Firebase service account JSON file at `secrets/firebase-service-account.json`
2. Environment variables set:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`
   - `DATABASE_URL`

### Deploy

```bash
# Set environment variables
export PROJECT_ID="your-project-id"
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="https://your-frontend-url/auth/gmail/callback"
export DATABASE_URL="postgresql+asyncpg://user:password@/togenuki?host=/cloudsql/PROJECT:REGION:INSTANCE"

# Run deployment script
./deploy.sh
```

### Manual Deploy (without script)

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/togenuki-api

# Deploy to Cloud Run
gcloud run deploy togenuki-api \
    --image gcr.io/PROJECT_ID/togenuki-api \
    --platform managed \
    --region asia-northeast1 \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=..." \
    --set-env-vars "GOOGLE_CLIENT_ID=..." \
    --set-env-vars "GOOGLE_CLIENT_SECRET=..." \
    --set-env-vars "GOOGLE_REDIRECT_URI=..."
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Application info |
| GET | `/health` | Health check |
| GET | `/api/auth/gmail/url` | Get Gmail OAuth URL |
| POST | `/api/auth/gmail/callback` | Gmail OAuth callback |
| GET | `/api/auth/gmail/status` | Gmail connection status |
| POST | `/api/webhook/gmail` | Gmail Pub/Sub webhook |
