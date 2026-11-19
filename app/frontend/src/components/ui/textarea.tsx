import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn("min-h-20 w-full rounded-md border bg-background p-3 text-sm focus-visible:ring-2 focus-visible:ring-ring", className)} {...props} />;
}
