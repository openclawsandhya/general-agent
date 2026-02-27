/**
 * API Client for SANDHYA.AI Backend
 * 
 * Provides typed functions for interacting with the FastAPI backend.
 * Includes error handling, timeouts, and retry logic.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT = 120000; // 120 seconds — phi-3.1-mini needs up to 10s on first request

// ============================================================================
// Types
// ============================================================================

export interface MessageRequest {
  message: string;
  session_id?: string;
}

export interface MessageResponse {
  reply: string;
  session_id: string;
  mode: string;
}

export interface HealthResponse {
  status: string;
  llm_available: boolean;
  model: string;          // backward compat
  llm_model: string;
  llm_base_url: string;
  model_loaded: boolean;
  orchestrator_ready: boolean;
  browser_ready: boolean;
  timestamp: string;
}

export interface ApiError {
  error: string;
  message: string;
  path?: string;
  timestamp?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Fetch with timeout support
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = DEFAULT_TIMEOUT
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Request timeout");
    }
    throw error;
  }
}

/**
 * Handle API response
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error: "API Error",
        message: `HTTP ${response.status}: ${response.statusText}`,
      };
    }
    throw new Error(errorData.message || errorData.error);
  }

  return response.json();
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Send a message to the agent
 */
export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<MessageResponse> {
  console.log("[API] Sending message:", message.substring(0, 50) + "...");

  const startTime = Date.now();

  try {
    const response = await fetchWithTimeout(
      `${API_BASE}/agent/message`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          session_id: sessionId,
        } as MessageRequest),
      },
      DEFAULT_TIMEOUT
    );

    const data = await handleResponse<MessageResponse>(response);
    const elapsed = Date.now() - startTime;

    console.log(`[API] ✓ Response received in ${elapsed}ms, mode: ${data.mode}`);

    return data;
  } catch (error) {
    const elapsed = Date.now() - startTime;
    console.error(`[API] ✗ Error after ${elapsed}ms:`, error);
    throw error;
  }
}

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await fetchWithTimeout(
      `${API_BASE}/health`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      },
      5000 // 5 second timeout for health checks
    );

    return handleResponse<HealthResponse>(response);
  } catch (error) {
    console.error("[API] Health check failed:", error);
    throw error;
  }
}

/**
 * Test connection to backend
 */
export async function testConnection(): Promise<boolean> {
  try {
    await checkHealth();
    return true;
  } catch {
    return false;
  }
}

/**
 * Retry a function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 2,
  initialDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt < maxRetries) {
        const delay = initialDelay * Math.pow(2, attempt);
        console.log(`[API] Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms...`);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError!;
}

// Export API base URL for debugging
export { API_BASE };
