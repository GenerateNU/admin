import { PublicClientApplication, type Configuration } from "@azure/msal-browser";

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
    redirectUri: typeof window === "undefined" ? "http://localhost:3000" : window.location.origin,
  },
  cache: { cacheLocation: "sessionStorage" },
};

export const apiRequest = { scopes: [apiScope] };

export const msalInstance = new PublicClientApplication(msalConfig);

export async function getApiToken(): Promise<string | null> {
  const account = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0];
  if (!account) return null;

  try {
    const result = await msalInstance.acquireTokenSilent({ ...apiRequest, account });
    return result.accessToken;
  } catch {
    await msalInstance.acquireTokenRedirect(apiRequest);
    return null;
  }
}
