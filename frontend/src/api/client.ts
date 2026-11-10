const API_BASE = "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function extractDetail(payload: unknown): string | null {
  if (typeof payload !== "object" || payload === null) {
    return null;
  }

  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "object" && item !== null) {
          const msg = (item as { msg?: unknown }).msg;
          if (typeof msg === "string") {
            return msg;
          }
        }
        return null;
      })
      .filter((msg): msg is string => msg !== null);

    if (messages.length > 0) {
      return messages.join(". ");
    }
  }

  return null;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!response.ok) {
    let message = `Error ${response.status} al comunicarse con el servidor.`;
    try {
      const payload: unknown = await response.json();
      message = extractDetail(payload) ?? message;
    } catch {
      // Conserva el mensaje por defecto si la respuesta no es JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}