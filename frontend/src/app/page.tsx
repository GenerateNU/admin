"use client";

import { useMsal } from "@azure/msal-react";
import { useReadSession } from "@generate-admin/api";

import { apiRequest } from "@/auth/msal";

export default function Home() {
  const { instance, accounts } = useMsal();
  const signedIn = accounts.length > 0;

  const { data, error, isLoading } = useReadSession({ query: { enabled: signedIn } });

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-10">
      <div>
        <h1 className="text-2xl font-semibold">Generate Admin</h1>
        <p className="text-sm text-neutral-500">Northeastern Entra ID sign-in</p>
      </div>

      {!signedIn ? (
        <button
          onClick={() => instance.loginRedirect(apiRequest)}
          className="w-fit rounded bg-neutral-900 px-4 py-2 text-sm text-white hover:bg-neutral-700"
        >
          Sign in with Northeastern
        </button>
      ) : (
        <div className="flex items-center gap-4">
          <span className="text-sm">{accounts[0].username}</span>
          <button
            onClick={() => instance.logoutRedirect()}
            className="rounded border px-3 py-1.5 text-sm hover:bg-neutral-100"
          >
            Sign out
          </button>
        </div>
      )}

      {signedIn && (
        <section className="rounded border p-4">
          <h2 className="mb-2 text-sm font-medium">GET /api/v1/session</h2>
          {isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
          {error ? (
            <pre className="overflow-auto text-xs text-red-600">
              {error instanceof Error ? error.message : String(error)}
            </pre>
          ) : null}
          {data && (
            <pre className="overflow-auto text-xs">{JSON.stringify(data.data, null, 2)}</pre>
          )}
        </section>
      )}
    </main>
  );
}
