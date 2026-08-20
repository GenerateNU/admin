import type { TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-24 border-2 border-ink bg-paper px-3 py-2 font-sans text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
