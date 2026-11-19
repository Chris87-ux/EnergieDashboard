import { Check } from "lucide-react";
import { Checkbox as Primitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function Checkbox({ className, ...props }: ComponentProps<typeof Primitive.Root>) {
  return (
    <Primitive.Root className={cn("grid size-4 shrink-0 place-items-center rounded border border-muted-foreground bg-background data-[state=checked]:border-primary data-[state=checked]:bg-primary focus-visible:ring-2 focus-visible:ring-ring", className)} {...props}>
      <Primitive.Indicator><Check className="size-3" /></Primitive.Indicator>
    </Primitive.Root>
  );
}
