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
    const body = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      body?.code ?? "http_error",
      body?.message ?? response.statusText,
      body?.details ?? null,
    );
  }

  const data = response.status === 204 ? undefined : await response.json();
  return { data, status: response.status, headers: response.headers } as T;
};
