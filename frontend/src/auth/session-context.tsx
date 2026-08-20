"use client";

import { createContext, useContext } from "react";
import type { Session } from "@generatenu/api";

const SessionContext = createContext<Session | null>(null);

export const SessionProvider = SessionContext.Provider;

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) {
    throw new Error("useSession() must be called within <SessionGate>");
  }
  return session;
}
