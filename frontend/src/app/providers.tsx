"use client";

import { useEffect, useState } from "react";
import { MsalProvider } from "@azure/msal-react";
import { EventType, type AuthenticationResult } from "@azure/msal-browser";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { configureApi } from "@generate-admin/api";

import { getApiToken, msalInstance } from "@/auth/msal";

configureApi({
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  getToken: getApiToken,
});

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // MSAL v5 requires an explicit initialize() before any other call.
    msalInstance
      .initialize()
      .then(() => msalInstance.handleRedirectPromise())
      .then((result) => {
        if (result?.account) msalInstance.setActiveAccount(result.account);
        else if (!msalInstance.getActiveAccount()) {
          const [first] = msalInstance.getAllAccounts();
          if (first) msalInstance.setActiveAccount(first);
        }
        setReady(true);
      });

    // addEventCallback returns an id, not a teardown function.
    const callbackId = msalInstance.addEventCallback((event) => {
      if (event.eventType === EventType.LOGIN_SUCCESS) {
        msalInstance.setActiveAccount((event.payload as AuthenticationResult).account);
      }
    });

    return () => {
      if (callbackId) msalInstance.removeEventCallback(callbackId);
    };
  }, []);

  if (!ready) return <main className="p-8 text-sm text-neutral-500">Loading…</main>;

  return (
    <MsalProvider instance={msalInstance}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MsalProvider>
  );
}
