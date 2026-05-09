# CV Analysis API - Cloudflare Worker

Secure serverless API for analyzing job descriptions against the CV using Azure OpenAI.

## Features

- **Secure**: API keys stored as Cloudflare secrets (never exposed to browser)
- **Fast**: Cloudflare edge network, no cold starts
- **Rate Limited**: 10 requests per hour per IP
- **CORS Enabled**: Allows calls from GitHub Pages site
- **Azure OpenAI**: Uses GPT-55 model for intelligent analysis
- **Bilingual**: Supports English and Ukrainian prompts

## Setup

### 1. Configure Secrets

```bash
# Set Azure OpenAI API key
wrangler secret put AZURE_OPENAI_KEY
# Enter your Azure OpenAI API key when prompted

# Set Azure OpenAI endpoint URL
wrangler secret put AZURE_OPENAI_ENDPOINT
# Enter: https://YOUR-RESOURCE.openai.azure.com

# Set deployment name
wrangler secret put AZURE_OPENAI_DEPLOYMENT
# Enter: gpt-55
```

### 2. Test Locally

```bash
# Start development server
wrangler dev

# In another terminal, test the API
curl -X POST http://localhost:8787/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "jobDescription": "Looking for Senior Python Developer with 5+ years experience in FastAPI and async programming",
    "language": "en"
  }'
```

### 3. Deploy to Production

```bash
# Deploy to Cloudflare Workers
wrangler deploy

# Your API will be available at:
# https://mycv-api.YOUR-SUBDOMAIN.workers.dev
```

## API Endpoints

### POST /api/analyze

Analyzes job description match against the CV.

**Request:**
```json
{
  "jobDescription": "Job requirements text...",
  "language": "en"  // or "ua"
}
```

**Response (Success):**
```json
{
  "success": true,
  "analysis": "## Match Analysis\n\n### ✅ Strong matches...",
  "language": "en"
}
```

**Response (Error):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again after...",
  "retryAfter": 3456
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-05-10T12:00:00.000Z"
}
```

## Rate Limiting

- **Limit**: 10 requests per hour per IP address
- **Scope**: Per-worker instance (resets on redeployment)
- **Status Code**: 429 (Too Many Requests)
- **Header**: `Retry-After` indicates seconds until reset

## Architecture

```
GitHub Pages (Static Site)
         ↓
    JavaScript fetch()
         ↓
Cloudflare Worker (This API)
  ├─ Validates input
  ├─ Checks rate limit
  ├─ Fetches CV JSON
  ├─ Builds prompt with hrprompt.md template
  └─ Calls Azure OpenAI API
         ↓
Azure OpenAI Service (GPT-55)
```

## Security Features

1. **API Key Protection**: Stored as Cloudflare secrets, never exposed in code or browser
2. **CORS Restriction**: Only allows requests from `https://hlyniany.github.io`
3. **Rate Limiting**: Prevents abuse and controls costs
4. **Input Validation**: Job description length limits (50-10000 chars)
5. **Error Handling**: Generic error messages, detailed logs server-side only

## Configuration

Edit `wrangler.toml` to change:

- `CV_JSON_URL`: URL of the CV JSON file
- `ALLOWED_ORIGIN`: GitHub Pages domain for CORS

## Troubleshooting

### "Azure OpenAI credentials not configured"
Run the secret configuration commands above.

### "Rate limit exceeded"
Wait until the retry-after time or use a different IP address.

### "Failed to fetch CV"
Check that `CV_JSON_URL` in `wrangler.toml` is correct and accessible.

### CORS errors in browser
Ensure `ALLOWED_ORIGIN` matches your GitHub Pages domain.

## Development

```bash
# View logs
wrangler tail

# View deployments
wrangler deployments list

# Delete a deployment
wrangler delete
```

## Cost Estimation

**Cloudflare Workers Free Tier:**
- 100,000 requests per day
- 10ms CPU time per request
- This API well within free limits

**Azure OpenAI Costs:**
- GPT-55: ~$0.01-0.03 per analysis
- 100 analyses ≈ $1-3
- Set budget alerts in Azure portal

## License

Same as parent repository (mycv).
