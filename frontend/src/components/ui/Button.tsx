import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type ButtonVariant = "primary" | "secondary";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const base =
  "inline-flex w-fit items-center justify-center gap-2 border-2 border-ink px-4 py-2 font-mono text-sm font-bold uppercase tracking-wide transition-all disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-hard-sm";

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-ink text-paper shadow-hard-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none",
  secondary:
    "bg-paper text-ink shadow-hard-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none",
};

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return <button className={cn(base, variants[variant], className)} {...props} />;
}
