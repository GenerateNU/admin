import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

const sizes = {
  1: "text-3xl",
  2: "text-xl",
} as const;

export function Heading({
  level = 1,
  children,
  className,
}: {
  level?: 1 | 2;
  children: ReactNode;
  className?: string;
}) {
  const Tag = level === 1 ? "h1" : "h2";
  return (
    <Tag className={cn("font-mono font-bold uppercase tracking-tight text-ink", sizes[level], className)}>
      {children}
    </Tag>
  );
}
