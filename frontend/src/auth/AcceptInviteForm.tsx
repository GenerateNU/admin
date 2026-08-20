"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getReadSessionQueryKey, useAcceptInvitation } from "@generatenu/api";
import type { Identity } from "@generatenu/api";
import { Button, Heading, Input } from "@/components/ui";
import { clearPendingInviteToken, peekPendingInviteToken } from "@/auth/invite-token";

export function AcceptInviteForm({ identity }: { identity: Identity }) {
  const [token, setToken] = useState(() => peekPendingInviteToken());
  const queryClient = useQueryClient();
  const autoSubmitted = useRef(false);

  const mutation = useAcceptInvitation({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getReadSessionQueryKey() }),
    },
  });

  useEffect(() => {
    if (autoSubmitted.current || !token) return;
    autoSubmitted.current = true;
    clearPendingInviteToken();
    mutation.mutate({ data: { token } });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Heading level={2}>Accept your invitation</Heading>
        <p className="text-sm text-muted">
          Signed in as {identity.email}. Enter the invitation code you were sent.
        </p>
      </div>

      <Input
        placeholder="Invitation code"
        value={token}
        onChange={(event) => setToken(event.target.value)}
        disabled={mutation.isPending}
      />

      <Button
        onClick={() => mutation.mutate({ data: { token: token.trim() } })}
        disabled={mutation.isPending || !token.trim()}
      >
        {mutation.isPending ? "Accepting…" : "Accept invitation"}
      </Button>

      {mutation.isError && (
        <p className="text-sm text-red-600">
          {mutation.error instanceof Error ? mutation.error.message : "Something went wrong."}
        </p>
      )}
    </div>
  );
}
