const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

interface UploadResponse {
  success: boolean;
  summary: string;
  stats: Record<string, unknown>;
  rows_processed: number;
}

interface SendResponse {
  success: boolean;
  message: string;
  email_id: string | null;
}

interface SSEEvent {
  stage: string;
  status: string;
  data?: Record<string, unknown>;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "X-API-Key": API_KEY,
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function uploadAndAnalyze(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<UploadResponse>("/api/v1/upload", {
    method: "POST",
    body: formData,
  });
}

export async function sendSummaryEmail(
  toEmail: string,
  summary: string,
  subject: string,
): Promise<SendResponse> {
  return apiRequest<SendResponse>("/api/v1/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      to_email: toEmail,
      summary,
      subject,
    }),
  });
}

export function streamPipeline(
  file: File,
  toEmail: string,
  subject: string,
  onEvent: (event: SSEEvent) => void,
  onError: (error: string) => void,
  onDone: () => void,
): () => void {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("to_email", toEmail);
  formData.append("subject", subject);

  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/stream`, {
        method: "POST",
        headers: { "X-API-Key": API_KEY },
        body: formData,
        signal: controller.signal,
      });

      if (!response.ok) {
        const err = await response
          .json()
          .catch(() => ({ detail: "Stream failed" }));
        onError(err.detail || `HTTP ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError("No response stream");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const cleaned = line.replace(/^data: /, "").trim();
          if (!cleaned) continue;
          try {
            const event: SSEEvent = JSON.parse(cleaned);
            onEvent(event);
            if (event.stage === "done") {
              onDone();
              return;
            }
          } catch {
            // skip malformed events
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        onError(err.message);
      }
    }
  })();

  return () => controller.abort();
}

export type { UploadResponse, SendResponse, SSEEvent };
