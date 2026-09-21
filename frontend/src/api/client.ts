const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

if (!API_BASE_URL) {
  // Fail loudly in development rather than silently hitting a relative path.
  // eslint-disable-next-line no-console
  console.error(
    "VITE_API_BASE_URL is not set. Copy frontend/.env.example to frontend/.env."
  );
}

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(status: number, message: string, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  401: "Your session has expired. Please sign in again.",
  404: "We couldn't find what you were looking for.",
  422: "Some of the submitted data isn't valid.",
  500: "Something went wrong on our end. Please try again.",
  502: "The server is temporarily unreachable. Please try again shortly.",
  503: "The service is temporarily unavailable. Please try again shortly.",
};

async function parseErrorBody(response: Response): Promise<{ message?: string; code?: string; details?: unknown }> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return {};
  }
  try {
    const body = await response.json();
    if (typeof body === "object" && body !== null) {
      const message =
        typeof body.message === "string"
          ? body.message
          : typeof body.detail === "string"
            ? body.detail
            : undefined;
      return { message, code: body.code, details: body.detail ?? body.errors };
    }
    return {};
  } catch {
    return {};
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | undefined | null>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const base = (API_BASE_URL ?? "").replace(/\/+$/, "");
  const url = new URL(`${base}${path.startsWith("/") ? path : `/${path}`}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, query, signal } = options;

  const headers: Record<string, string> = {};
  let requestBody: BodyInit | undefined;

  if (formData) {
    // Never set Content-Type manually for FormData: the browser needs to
    // attach its own multipart boundary.
    requestBody = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: requestBody,
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new ApiError(0, "Couldn't reach the server. Check your connection and try again.");
  }

  if (!response.ok) {
    const parsed = await parseErrorBody(response);
    const fallback = STATUS_MESSAGES[response.status] ?? `Request failed (${response.status}).`;
    throw new ApiError(response.status, parsed.message ?? fallback, parsed.code, parsed.details);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const apiClient = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) =>
    request<T>(path, { method: "GET", query, signal }),
  post: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", body, signal }),
  postForm: <T>(path: string, formData: FormData, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", formData, signal }),
  patch: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "PATCH", body, signal }),
  delete: <T>(path: string, signal?: AbortSignal) => request<T>(path, { method: "DELETE", signal }),
};

export async function checkHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    await request("/health", { signal });
    return true;
  } catch {
    return false;
  }
}
