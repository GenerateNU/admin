/**
 * The single seam every generated hook goes through.
 *
 * Auth is injected rather than baked in, so the same generated client serves both
 * the admin UI (which supplies an MSAL token) and the public website (which does not).
 */

type TokenProvider = () => Promise<string | null>;

let baseUrl = "";
let getToken: TokenProvider | null = null;

export function configureApi(options: { baseUrl: string; getToken?: TokenProvider }): void {
  baseUrl = options.baseUrl.replace(/\/$/, "");
  getToken = options.getToken ?? null;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const apiFetch = async <T>(url: string, options: RequestInit = {}): Promise<T> => {
  const headers = new Headers(options.headers);

  if (getToken) {
    const token = await getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${baseUrl}${url}`, { ...options, headers });

  if (!response.ok) {
    // The backend's DomainError handler returns {code, message, details}; fall back for
    // anything that doesn't (502s from a proxy, FastAPI's own validation errors).
    const body = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      body?.code ?? "http_error",
      body?.message ?? response.statusText,
      body?.details ?? null,
    );
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
};
