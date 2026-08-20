import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("border-2 border-ink bg-paper p-6 shadow-hard", className)}>{children}</div>;
}
