"use client";

import type { ReactNode } from "react";
import { useMsal } from "@azure/msal-react";
import { AccessState, useReadSession } from "@generatenu/api";

import { apiRequest } from "@/auth/msal";
import { AcceptInviteForm } from "@/auth/AcceptInviteForm";
import { AccessRequestForm } from "@/auth/AccessRequestForm";
import { SessionProvider } from "@/auth/session-context";
import { Banner, Button, Card, Heading } from "@/components/ui";

function Centered({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-screen w-full items-center justify-center p-6">
      <Card className="w-full max-w-md">{children}</Card>
    </main>
  );
}

export function SessionGate({ children }: { children: ReactNode }) {
  const { instance, accounts } = useMsal();
  const signedIn = accounts.length > 0;

  const { data, error, isLoading } = useReadSession({ query: { enabled: signedIn } });

  if (!signedIn) {
    return (
      <Centered>
        <div className="flex flex-col gap-4">
          <div>
            <Heading level={1}>Generate Admin</Heading>
          </div>
          <Button onClick={() => instance.loginRedirect(apiRequest)}>
            Sign in with Northeastern email
          </Button>
        </div>
      </Centered>
    );
  }

  if (isLoading) {
    return (
      <Centered>
        <p className="text-sm text-muted">Loading…</p>
      </Centered>
    );
  }

  if (error || !data) {
    return (
      <Centered>
        <Banner tone="error">
          {error instanceof Error ? error.message : "Couldn't reach the API."}
        </Banner>
      </Centered>
    );
  }

  const session = data.data;

  if (session.access_state === AccessState.active || session.access_state === AccessState.no_roles) {
    return (
      <SessionProvider value={session}>
        <div className="flex min-h-screen flex-col">
          <header className="flex items-center justify-between border-b-2 border-ink p-4">
            <span className="font-mono text-sm font-bold uppercase">{session.identity.email}</span>
            <Button variant="secondary" onClick={() => instance.logoutRedirect()}>
              Sign out
            </Button>
          </header>

          {session.access_state === AccessState.no_roles && (
            <Banner tone="warning">
              You don&apos;t have any roles assigned yet. An admin needs to grant you one before
              most features are available.
            </Banner>
          )}

          {children}
        </div>
      </SessionProvider>
    );
  }

  if (session.access_state === AccessState.invited) {
    return (
      <Centered>
        <AcceptInviteForm identity={session.identity} />
      </Centered>
    );
  }

  if (session.access_state === AccessState.no_access) {
    return (
      <Centered>
        <AccessRequestForm identity={session.identity} />
      </Centered>
    );
  }

  if (session.access_state === AccessState.pending) {
    return (
      <Centered>
        <div className="flex flex-col gap-2">
          <Heading level={2}>Request pending</Heading>
          <p className="text-sm text-muted">
            Your access request is awaiting review. You&apos;ll be able to sign in once an admin
            approves it.
          </p>
        </div>
      </Centered>
    );
  }

  if (session.access_state === AccessState.denied) {
    return (
      <Centered>
        <div className="flex flex-col gap-2">
          <Heading level={2}>Access denied</Heading>
          <p className="text-sm text-muted">
            Your request for access was denied. Contact an admin if you think this is a mistake.
          </p>
        </div>
      </Centered>
    );
  }

  if (session.access_state === AccessState.suspended) {
    return (
      <Centered>
        <div className="flex flex-col gap-2">
          <Heading level={2}>Account suspended</Heading>
          <p className="text-sm text-muted">
            Your account has been suspended. Contact an admin for details.
          </p>
        </div>
      </Centered>
    );
  }

  return (
    <Centered>
      <Banner tone="error">Unrecognized access state: {session.access_state}</Banner>
    </Centered>
  );
}
