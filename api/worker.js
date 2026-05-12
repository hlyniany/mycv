/**
 * Cloudflare Worker for CV Analysis with Azure OpenAI
 * 
 * Secure proxy for OpenAI API calls from static GitHub Pages site
 * Uses Azure OpenAI Service (GPT-5.5 model)
 * 
 * SECURITY NOTES:
 * - CORS protection only blocks browsers, not direct API calls
 * - TODO: Add Cloudflare Turnstile bot challenge
 * - TODO: Implement KV-based rate limiting (persistent across worker restarts)
 * - TODO: Add global daily/monthly quota caps
 * - Current in-memory rate limit is per-worker instance only
 */

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
 * Send Telegram notification via tg-mcp service
 * Fires-and-forgets — errors are logged but do not affect the response
 */
async function sendTelegramNotification(message, env) {
  const token = env.TG_MCP_TOKEN;
  const chat = env.TG_CHAT || 'https://t.me/+2t3oMfO0y883NmMy';

  if (!token) {
    console.warn('TG_MCP_TOKEN secret not set — skipping Telegram notification');
    return;
  }

  try {
    const res = await fetch('https://tg-mcp.losskot.xyz/send-message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ username: chat, message })
    });
    if (!res.ok) {
      const text = await res.text();
      console.error('Telegram notification failed:', res.status, text);
    } else {
      console.log('Telegram notification sent OK');
    }
  } catch (err) {
    console.error('Telegram notification error:', err.message || err);
  }
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
      max_completion_tokens: 2000
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
async function handleAnalyze(request, env, ctx) {
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
  
  const { prompt } = body;
  
  // Input validation
  if (!prompt || typeof prompt !== 'string') {
    return new Response(
      JSON.stringify({ error: 'prompt is required and must be a string' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }
  
  if (prompt.length > 50000) {
    return new Response(
      JSON.stringify({ error: 'Prompt too long (maximum 50000 characters)' }),
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
    
    // Build complete prompt with CV data
    const fullPrompt = `${prompt}\n\n**Resume Data (JSON):**\n${JSON.stringify(cvData, null, 2)}`;
    
    // Call Azure OpenAI
    console.log(`Analyzing CV match for IP: ${clientIP}`);
    const analysis = await callAzureOpenAI(fullPrompt, env);

    // Send Telegram notification (awaited so it completes before response)
    const jobSnippet = prompt.slice(0, 300).replace(/\n+/g, ' ').trim();
    const tgMessage = `📋 CV Analysis Request\nIP: ${clientIP}\nTime: ${new Date().toUTCString()}\n\nJob snippet:\n${jobSnippet}${prompt.length > 300 ? '…' : ''}`;
    await sendTelegramNotification(tgMessage, env);

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
  const allowedOrigins = new Set([
    env.ALLOWED_ORIGIN || 'https://hlyniany.github.io',
    'http://localhost:8000' // Development only
  ]);
  
  const headers = {
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400'
  };
  
  // Only set ACAO if origin is in the allowed set (strict equality check)
  if (origin && allowedOrigins.has(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
  }
  
  return headers;
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
      const response = await handleAnalyze(request, env, ctx);
      
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
