import { PublicClientApplication, type Configuration } from "@azure/msal-browser";

// These must be written out statically. Next replaces `process.env.NEXT_PUBLIC_FOO` by literal
// string substitution at build time, so a dynamic `process.env[name]` is never substituted and
// reads as undefined in the browser.
const required = (name: string, value: string | undefined): string => {
  if (!value) throw new Error(`${name} is not set; copy .env.example to .env.local`);
  return value;
};

const tenantId = required("NEXT_PUBLIC_ENTRA_TENANT_ID", process.env.NEXT_PUBLIC_ENTRA_TENANT_ID);
const clientId = required("NEXT_PUBLIC_ENTRA_CLIENT_ID", process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID);
const apiScope = required("NEXT_PUBLIC_API_SCOPE", process.env.NEXT_PUBLIC_API_SCOPE);

export const msalConfig: Configuration = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    // Must exactly match a redirectUri on the app registration's SPA platform.
    redirectUri: typeof window === "undefined" ? "http://localhost:3000" : window.location.origin,
  },
  cache: { cacheLocation: "sessionStorage" },
};

/**
 * The API scope, not Graph. This is what makes Entra mint a token with
 * aud = the API's client id, which is what the FastAPI verifier checks.
 */
export const apiRequest = { scopes: [apiScope] };

export const msalInstance = new PublicClientApplication(msalConfig);

export async function getApiToken(): Promise<string | null> {
  const account = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0];
  if (!account) return null;

  try {
    const result = await msalInstance.acquireTokenSilent({ ...apiRequest, account });
    return result.accessToken;
  } catch {
    // Silent renewal fails when the refresh token is gone or consent is needed;
    // a redirect is the only way back, and it never returns.
    await msalInstance.acquireTokenRedirect(apiRequest);
    return null;
  }
}
