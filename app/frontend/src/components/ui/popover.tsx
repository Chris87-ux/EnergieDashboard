import { Popover as Primitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const Popover = Primitive.Root;
export const PopoverTrigger = Primitive.Trigger;

export function PopoverContent({ className, ...props }: ComponentProps<typeof Primitive.Content>) {
  return (
    <Primitive.Portal>
      <Primitive.Content sideOffset={6} className={cn("z-50 max-w-[calc(100vw-1rem)] rounded-md border bg-popover shadow-xl", className)} {...props} />
    </Primitive.Portal>
  );
}
