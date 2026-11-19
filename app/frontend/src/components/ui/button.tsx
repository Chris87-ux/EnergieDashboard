import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const variants = {
  default: "bg-primary text-primary-foreground hover:bg-primary/85",
  outline: "border border-border bg-background hover:bg-accent",
  ghost: "hover:bg-accent",
  destructive: "bg-red-700 text-white hover:bg-red-600",
};
const sizes = { default: "h-9 px-4", sm: "h-8 px-3", lg: "h-11 px-5", "icon-sm": "size-8" };

interface Appearance {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  className?: string;
}

export function buttonVariants({ variant = "default", size = "default", className }: Appearance = {}) {
  return cn(
    "inline-flex shrink-0 items-center justify-center gap-2 rounded-md text-sm font-medium",
    "focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
    variants[variant], sizes[size], className,
  );
}

export function Button({ variant, size, className, type = "button", ...props }: ComponentProps<"button"> & Appearance) {
  return <button type={type} className={buttonVariants({ variant, size, className })} {...props} />;
}
