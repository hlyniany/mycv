/**
 * Cloudflare Worker for CV Analysis with Azure OpenAI
 * 
 * Provides secure proxy for OpenAI API calls from static GitHub Pages site
 * Uses Azure OpenAI Service (GPT-55 model)
 */

// Embedded prompt templates from data/hrprompt.md
const PROMPTS = {
  en: `You are an expert technical recruiter assistant and resume analyst.

I will provide you with:
1. A JSON Resume (fetched from URL below)
2. A job description (I will paste it after this prompt)

**Resume JSON URL:** https://hlyniany.github.io/mycv/cv.resume.json

**Your task:**
1. Fetch and parse the JSON Resume from the URL above
2. Read the job description I paste below
3. Analyze the match between the candidate's profile and the role
4. Output a structured report:

---
## Match Analysis

### ✅ Strong matches
[Skills, experience, keywords that directly align]

### ⚠️ Partial matches
[Areas where candidate has adjacent but not exact experience]

### ❌ Gaps
[Requirements not covered by the resume]

### 🏆 Overall fit score
[X/10 with one-sentence rationale]

### 💬 Suggested talking points for screening call
[3–5 specific questions based on gaps or ambiguities]

---

**Job description:**`,

  ua: `Ти — експерт з технічного рекрутингу та аналізу резюме.

Я надам тобі:
1. JSON Resume (за URL нижче)
2. Опис вакансії (вставлю після цього промту)

**URL резюме у форматі JSON:** https://hlyniany.github.io/mycv/cv.resume.json

**Твоє завдання:**
1. Завантажити та розпарсити JSON Resume за вказаним URL
2. Прочитати опис вакансії, який я вставлю нижче
3. Проаналізувати відповідність профілю кандидата та вимог ролі
4. Сформувати структурований звіт:

---
## Аналіз відповідності

### ✅ Сильні збіги
[Навички, досвід, ключові слова, які прямо відповідають вимогам]

### ⚠️ Часткові збіги
[Сфери, де кандидат має суміжний, але не точний досвід]

### ❌ Прогалини
[Вимоги, які не покриті резюме]

### 🏆 Загальна оцінка відповідності
[X/10 з одним реченням обґрунтування]

### 💬 Рекомендовані питання для скринінгового дзвінка
[3–5 конкретних питань на основі прогалин або неоднозначностей]

---

**Опис вакансії:**`
};

// Simple in-memory rate limiting
// Note: Resets on worker restart, but good enough for MVP
const rateLimitCache = new Map();
const RATE_LIMIT = 10; // requests per hour per IP
const RATE_WINDOW = 3600000; // 1 hour in milliseconds

/**
 * Check if IP has exceeded rate limit
 */
function checkRateLimit(ip) {
  const now = Date.now();
  const record = rateLimitCache.get(ip) || { count: 0, resetTime: now + RATE_WINDOW };
  
  // Reset if window expired
  if (now > record.resetTime) {
    record.count = 0;
    record.resetTime = now + RATE_WINDOW;
  }
  
  // Check limit
  if (record.count >= RATE_LIMIT) {
    return { allowed: false, resetTime: record.resetTime };
  }
  
  // Increment counter
  record.count++;
  rateLimitCache.set(ip, record);
  return { allowed: true };
}

/**
 * Call Azure OpenAI API
 */
async function callAzureOpenAI(prompt, env) {
  const endpoint = env.AZURE_OPENAI_ENDPOINT;
  const apiKey = env.AZURE_OPENAI_KEY;
  const deployment = env.AZURE_OPENAI_DEPLOYMENT;
  
  if (!endpoint || !apiKey || !deployment) {
    throw new Error('Azure OpenAI credentials not configured. Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, and AZURE_OPENAI_DEPLOYMENT secrets.');
  }
  
  // Build Azure OpenAI API URL
  const url = `${endpoint}/openai/deployments/${deployment}/chat/completions?api-version=2024-02-15-preview`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-key': apiKey
    },
    body: JSON.stringify({
      messages: [
        { role: 'system', content: 'You are a helpful technical recruiter assistant.' },
        { role: 'user', content: prompt }
      ],
      max_tokens: 2000,
      temperature: 0.7,
      top_p: 0.95
    })
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    console.error('Azure OpenAI API error:', response.status, errorText);
    throw new Error(`Azure OpenAI API error: ${response.status} - ${errorText}`);
  }
  
  const data = await response.json();
  return data.choices[0].message.content;
}

/**
 * Handle /api/analyze endpoint
 */
async function handleAnalyze(request, env) {
  const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
  
  // Rate limiting check
  const rateCheck = checkRateLimit(clientIP);
  if (!rateCheck.allowed) {
    const resetDate = new Date(rateCheck.resetTime);
    return new Response(
      JSON.stringify({ 
        error: 'Rate limit exceeded', 
        message: `Too many requests. Please try again after ${resetDate.toLocaleTimeString()}`,
        retryAfter: Math.ceil((rateCheck.resetTime - Date.now()) / 1000)
      }),
      { 
        status: 429,
        headers: { 
          'Content-Type': 'application/json',
          'Retry-After': Math.ceil((rateCheck.resetTime - Date.now()) / 1000).toString()
        }
      }
    );
  }
  
  // Parse request body
  let body;
  try {
    body = await request.json();
  } catch (error) {
    return new Response(
      JSON.stringify({ error: 'Invalid JSON body' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }
  
  const { jobDescription } = body;
  
  // Input validation
  if (!jobDescription || typeof jobDescription !== 'string') {
    return new Response(
      JSON.stringify({ error: 'jobDescription is required and must be a string' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }
  
  if (jobDescription.trim().length < 50) {
    return new Response(
      JSON.stringify({ error: 'Job description too short (minimum 50 characters)' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }
  
  if (jobDescription.length > 10000) {
    return new Response(
      JSON.stringify({ error: 'Job description too long (maximum 10000 characters)' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }
  
  try {
    // Fetch CV JSON from GitHub Pages
    const cvResponse = await fetch(env.CV_JSON_URL);
    if (!cvResponse.ok) {
      throw new Error(`Failed to fetch CV: ${cvResponse.status}`);
    }
    const cvData = await cvResponse.json();
    
    // Build complete prompt
    const fullPrompt = `${PROMPT_TEMPLATE}\n${jobDescription}\n\n**Resume Data (JSON):**\n${JSON.stringify(cvData, null, 2)}`;
    
    // Call Azure OpenAI
    console.log(`Analyzing job description for IP: ${clientIP}`);
    const analysis = await callAzureOpenAI(fullPrompt, env);
    
    return new Response(
      JSON.stringify({ 
        success: true, 
        analysis
      }),
      { 
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );
    
  } catch (error) {
    console.error('Analysis error:', error);
    return new Response(
      JSON.stringify({ 
        error: 'Analysis failed', 
        message: error.message,
        details: 'Please try again later or contact the site administrator.'
      }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Get CORS headers
 */
function getCORSHeaders(request, env) {
  const origin = request.headers.get('Origin');
  const allowedOrigin = env.ALLOWED_ORIGIN || 'https://hlyniany.github.io';
  
  return {
    'Access-Control-Allow-Origin': origin && origin.startsWith(allowedOrigin) ? origin : allowedOrigin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400'
  };
}

/**
 * Main worker fetch handler
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const corsHeaders = getCORSHeaders(request, env);
    
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { 
        status: 204,
        headers: corsHeaders 
      });
    }
    
    // Route: POST /api/analyze
    if (url.pathname === '/api/analyze' && request.method === 'POST') {
      const response = await handleAnalyze(request, env);
      
      // Add CORS headers to response
      Object.entries(corsHeaders).forEach(([key, value]) => {
        response.headers.set(key, value);
      });
      
      return response;
    }
    
    // Route: GET /health (health check)
    if (url.pathname === '/health') {
      return new Response(
        JSON.stringify({ 
          status: 'ok', 
          version: '1.0.0',
          timestamp: new Date().toISOString()
        }), 
        {
          status: 200,
          headers: { 
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        }
      );
    }
    
    // 404 for all other routes
    return new Response(
      JSON.stringify({ error: 'Not found' }), 
      { 
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
};
