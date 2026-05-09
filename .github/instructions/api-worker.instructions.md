---
description: "Cloudflare Workers API proxy code. Use when: editing worker.js, debugging API calls, adding endpoints, configuring CORS, implementing rate limiting, or troubleshooting Azure OpenAI integration."
applyTo:
  - "api/**/*.js"
  - "api/wrangler.toml"
---

# Cloudflare Workers API Instructions

## Core Principles

### 1. Keep Worker Code Clean
- **ONLY** API proxy logic in worker
- **NO** embedded prompts, templates, or CV data
- Fetch all data from external URLs
- Accept prompts from frontend via request body

### 2. Azure OpenAI GPT-5.5 Compatibility
When making Azure OpenAI API calls:
```javascript
// ✅ Correct
body: JSON.stringify({
  messages: [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: prompt }
  ],
  max_completion_tokens: 2000
})

// ❌ Wrong - these parameters are NOT supported in GPT-5.5
body: JSON.stringify({
  messages: [...],
  max_tokens: 2000,        // Use max_completion_tokens instead
  temperature: 0.7,        // Not configurable in GPT-5.5
  top_p: 0.95             // Not configurable in GPT-5.5
})
```

### 3. Error Handling Pattern
Always wrap API calls and provide detailed error responses:
```javascript
try {
  const response = await fetch(azureEndpoint, options);
  
  if (!response.ok) {
    const error = await response.text();
    return jsonResponse({
      success: false,
      error: `Azure API error: ${response.status}`,
      details: error
    }, response.status);
  }
  
  const data = await response.json();
  return jsonResponse({
    success: true,
    analysis: data.choices[0].message.content
  });
} catch (error) {
  return jsonResponse({
    success: false,
    error: error.message
  }, 500);
}
```

### 4. CORS Configuration
Always include CORS headers for GitHub Pages origin:
```javascript
function corsHeaders(origin) {
  const allowedOrigin = env.ALLOWED_ORIGIN || 'https://hlyniany.github.io';
  
  return {
    'Access-Control-Allow-Origin': origin === allowedOrigin ? origin : allowedOrigin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

// Handle OPTIONS preflight
if (request.method === 'OPTIONS') {
  return new Response(null, { headers: corsHeaders(request.headers.get('Origin')) });
}
```

### 5. Rate Limiting Implementation
Use in-memory cache for rate limiting:
```javascript
const rateLimitCache = new Map();

function checkRateLimit(ip) {
  const now = Date.now();
  const windowMs = 60 * 60 * 1000; // 1 hour
  const maxRequests = 10;
  
  if (!rateLimitCache.has(ip)) {
    rateLimitCache.set(ip, { count: 1, resetTime: now + windowMs });
    return true;
  }
  
  const record = rateLimitCache.get(ip);
  
  if (now > record.resetTime) {
    rateLimitCache.set(ip, { count: 1, resetTime: now + windowMs });
    return true;
  }
  
  if (record.count >= maxRequests) {
    return false;
  }
  
  record.count++;
  return true;
}
```

## Environment Variables

### wrangler.toml
Use `[vars]` section for non-sensitive config:
```toml
[vars]
CV_JSON_URL = "https://hlyniany.github.io/mycv/cv.resume.json"
ALLOWED_ORIGIN = "https://hlyniany.github.io/mycv"
```

### Cloudflare Secrets
Set via Wrangler CLI (never in code):
```bash
wrangler secret put AZURE_OPENAI_ENDPOINT
wrangler secret put AZURE_OPENAI_KEY
wrangler secret put AZURE_OPENAI_DEPLOYMENT
```

Access in worker:
```javascript
const endpoint = env.AZURE_OPENAI_ENDPOINT;
const apiKey = env.AZURE_OPENAI_KEY;
const deployment = env.AZURE_OPENAI_DEPLOYMENT;
```

## API Endpoints Structure

### Health Check
```javascript
if (url.pathname === '/health') {
  return jsonResponse({
    status: 'ok',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
}
```

### Main API Endpoint
```javascript
if (url.pathname === '/api/analyze' && request.method === 'POST') {
  return handleAnalyze(request, env);
}
```

## Common Debugging Steps

### 1. Test Health Endpoint
```bash
curl https://your-worker.workers.dev/health
```

### 2. Test API with Minimal Prompt
```bash
curl -X POST https://your-worker.workers.dev/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, respond with: API is working"}'
```

### 3. Check Deployment Status
```bash
wrangler deployments list
```

### 4. View Live Logs
```bash
wrangler tail
```

## Error Messages to Check For

- `max_tokens is not supported` → Use `max_completion_tokens`
- `temperature does not support` → Remove temperature parameter
- `401 Unauthorized` → Check AZURE_OPENAI_KEY secret
- `404 Not Found` → Verify AZURE_OPENAI_DEPLOYMENT name
- `Failed to fetch CV JSON` → Check CV_JSON_URL is accessible
- `Rate limit exceeded` → Implement exponential backoff or increase limits

## Testing Locally

Start local development server:
```bash
cd api/
wrangler dev
```

Test against local server:
```bash
curl -X POST http://localhost:8787/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test prompt"}'
```

## Deployment Checklist

Before deploying:
- [ ] All secrets set via `wrangler secret put`
- [ ] `wrangler.toml` has correct `CV_JSON_URL` and `ALLOWED_ORIGIN`
- [ ] Worker uses `max_completion_tokens` (not `max_tokens`)
- [ ] No `temperature` or `top_p` parameters in API call
- [ ] CORS headers configured for GitHub Pages origin
- [ ] Rate limiting implemented
- [ ] Error handling includes detailed error messages

Deploy command:
```bash
cd api/
wrangler deploy
```

Verify deployment:
```bash
curl https://your-worker.workers.dev/health
```
