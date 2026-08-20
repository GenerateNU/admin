const STORAGE_KEY = "generate-admin:pending-invite-token";

export function captureInviteTokenFromUrl(): void {
  if (typeof window === "undefined") return;

  const params = new URLSearchParams(window.location.search);
  const token = params.get("invite_token");
  if (!token) return;

  sessionStorage.setItem(STORAGE_KEY, token);
  params.delete("invite_token");
  const query = params.toString();
  const url = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  window.history.replaceState(null, "", url);
}

export function peekPendingInviteToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(STORAGE_KEY) ?? "";
}

export function clearPendingInviteToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
}
