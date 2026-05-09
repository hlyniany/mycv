## EXECUTION DISCIPLINE

- **Do only what was asked** — Execute the requested task. Do not invent
  additional steps (creating new scripts, refactoring related files) unless asked.
- **"Run X" means run X** — Not: find X, read X, plan how to run X, create a
  helper for X, then run it. Just run it with needed prerequisites.
- Reading files for context needed to complete the requested action is permitted.

## ERROR AND OBSTACLE HANDLING

When an action fails or hits an obstacle:
- You MAY attempt to fix the error within the current strategy (retry, adjust
  parameters, install a missing dependency to unblock the original command).
- You MUST NOT switch to a different strategy, tool, or approach without asking
  the user first.
- If the fix attempt also fails, STOP and report what happened. Let the user
  decide the next step.

Forbidden:
- Silently switching to a fallback or alternative strategy after a failure
- Choosing a different tool, command, or workflow on your own
- Expanding scope (e.g., error in one file → refactoring three files)
- "Recovering" by doing something the user did not request

---

## PROJECT ARCHITECTURE

This project uses a **serverless edge computing** architecture:
- **Frontend**: Static GitHub Pages site (`docs/` folder)
- **Backend**: Cloudflare Workers as API proxy
- **AI**: Azure OpenAI Service (GPT-5.5)

## SECURITY PRINCIPLES

### API Key Protection
- **NEVER** commit API keys, tokens, or secrets to the repository
- Store all secrets as Cloudflare Worker secrets (not environment variables)
- Frontend code should NEVER contain API keys or direct Azure OpenAI calls
- Use `.gitignore` to exclude `.env` files

### CORS Configuration
- Configure explicit origin whitelist in worker (no wildcards)
- Set proper CORS headers: `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`
- Validate origin on every request

### Rate Limiting
- Implement per-IP rate limiting in worker (default: 10 requests/hour)
- Use in-memory cache for production, consider Durable Objects for persistence
- Return `429 Too Many Requests` when limit exceeded

## CLOUDFLARE WORKERS PATTERNS

### Clean Code Principle
**Workers should contain ONLY logic, NOT data:**
- ❌ No embedded prompts, templates, or content strings
- ❌ No hardcoded CV data or resume information
- ✅ Fetch data from external URLs (GitHub Pages)
- ✅ Accept prompts from frontend via request body
- ✅ Pure API proxy logic only

### Code Structure
```javascript
// Good: Clean worker with fetched data
async function handleAnalyze(request, env) {
  const { prompt } = await request.json();
  const cvData = await fetch(env.CV_JSON_URL).then(r => r.json());
  const fullPrompt = `${prompt}\n${JSON.stringify(cvData)}`;
  return callAzureOpenAI(fullPrompt, env);
}

// Bad: Embedded data
const PROMPT_TEMPLATE = "Long multiline prompt..."; // ❌ Keep in frontend!
const CV_DATA = { name: "..." }; // ❌ Fetch from URL!
```

### Environment Variables
Use `wrangler.toml` for non-sensitive config:
```toml
[vars]
CV_JSON_URL = "https://username.github.io/repo/cv.resume.json"
ALLOWED_ORIGIN = "https://username.github.io/repo"
```

Use secrets for sensitive data (set via CLI):
```bash
wrangler secret put AZURE_OPENAI_KEY
wrangler secret put AZURE_OPENAI_ENDPOINT
wrangler secret put AZURE_OPENAI_DEPLOYMENT
```

## AZURE OPENAI GPT-5.5 API

### API Requirements
GPT-5.5 has **different parameters** than GPT-4:

**Required:**
- `messages`: Array of {role, content} objects
- `max_completion_tokens`: Token limit (replaces `max_tokens`)

**NOT SUPPORTED:**
- ❌ `temperature` (uses default value only, cannot customize)
- ❌ `top_p` (not configurable in GPT-5.5)
- ❌ `max_tokens` (use `max_completion_tokens` instead)

### Correct API Call
```javascript
const response = await fetch(
  `${env.AZURE_OPENAI_ENDPOINT}/openai/deployments/${env.AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version=2024-02-15-preview`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-key': env.AZURE_OPENAI_KEY
    },
    body: JSON.stringify({
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: prompt }
      ],
      max_completion_tokens: 2000
      // ❌ Do NOT include: temperature, top_p, max_tokens
    })
  }
);
```

### Error Handling
Always check for Azure-specific errors:
- `max_tokens is not supported` → Use `max_completion_tokens`
- `temperature does not support X` → Remove temperature parameter
- `401 Unauthorized` → Check API key secret
- `404 Not Found` → Verify deployment name and endpoint URL

## FRONTEND INTEGRATION

### Prompt Placement
- **Prompts belong in HTML/JavaScript files**, not in worker
- Use `const PROMPT = "..."` in frontend
- Send complete prompt to worker via POST body
- Worker should NOT modify or construct prompts

### API Call Pattern
```javascript
// frontend.js
const PROMPT = `...full prompt template...`; // Stored in frontend

async function analyzeJob() {
  const jobDescription = document.getElementById('input').value;
  const fullPrompt = `${PROMPT}\n${jobDescription}`;
  
  const response = await fetch(workerUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: fullPrompt })
  });
  
  const { success, analysis } = await response.json();
  // Display analysis...
}
```

## DEPLOYMENT WORKFLOW

### Testing Locally
```bash
cd api/
wrangler dev  # Test locally on http://localhost:8787
```

### Deploying to Production
```bash
cd api/
wrangler deploy  # Deploys to *.workers.dev
```

### Verify Deployment
```bash
# Health check
curl https://your-worker.workers.dev/health

# Test API (with test prompt)
curl -X POST https://your-worker.workers.dev/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test prompt"}'
```

## COMMON ISSUES

### Empty API Response
If worker returns `{"success":true,"analysis":""}`:
- Verify complete prompt is sent (not just "test")
- Check CV JSON is accessible at CV_JSON_URL
- Confirm GPT-5.5 deployment is active in Azure

### CORS Errors
- Verify `ALLOWED_ORIGIN` matches GitHub Pages URL exactly
- Check for trailing slashes (should match)
- Confirm worker returns CORS headers in OPTIONS and POST responses

### Rate Limit Issues
- Check if IP is hitting 10 requests/hour limit
- Consider increasing limit or using authentication
- Monitor Cloudflare Workers analytics for usage patterns
