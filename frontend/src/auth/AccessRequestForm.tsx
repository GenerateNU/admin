"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getReadSessionQueryKey, useRequestAccess } from "@generatenu/api";
import type { Identity } from "@generatenu/api";
import { Button, Heading, Textarea } from "@/components/ui";

export function AccessRequestForm({ identity }: { identity: Identity }) {
  const [message, setMessage] = useState("");
  const queryClient = useQueryClient();

  const mutation = useRequestAccess({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getReadSessionQueryKey() }),
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Heading level={2}>Request access</Heading>
        <p className="text-sm text-muted">
          Signed in as {identity.email}. You haven&apos;t been invited to Generate Admin yet. Send
          a request and an admin will review it.
        </p>
      </div>

      <Textarea
        placeholder="Optional message for the reviewer"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        disabled={mutation.isPending}
      />

      <Button
        onClick={() => mutation.mutate({ data: { message: message.trim() || undefined } })}
        disabled={mutation.isPending}
      >
        {mutation.isPending ? "Sending…" : "Request access"}
      </Button>

      {mutation.isError && (
        <p className="text-sm text-red-600">
          {mutation.error instanceof Error ? mutation.error.message : "Something went wrong."}
        </p>
      )}
    </div>
  );
}
