import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type BannerTone = "info" | "warning" | "error";

const tones: Record<BannerTone, string> = {
  info: "border-ink bg-accent text-paper",
  warning: "border-ink bg-highlight text-ink",
  error: "border-red-600 bg-paper text-red-600",
};

export function Banner({ tone = "info", children }: { tone?: BannerTone; children: ReactNode }) {
  return (
    <div className={cn("border-2 px-4 py-3 text-center font-sans text-sm", tones[tone])}>
      {children}
    </div>
  );
}
