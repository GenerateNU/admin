import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "border-2 border-ink bg-paper px-2 py-0.5 font-mono text-xs font-bold uppercase text-ink",
        className,
      )}
    >
      {children}
    </span>
  );
}
