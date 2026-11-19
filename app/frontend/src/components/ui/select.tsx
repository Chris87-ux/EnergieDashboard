import { Check, ChevronDown } from "lucide-react";
import { Select as Primitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const Select = Primitive.Root;
export const SelectValue = Primitive.Value;

export function SelectTrigger({ className, children, ...props }: ComponentProps<typeof Primitive.Trigger>) {
  return (
    <Primitive.Trigger className={cn("flex h-9 w-full items-center justify-between gap-2 rounded-md border bg-background px-3 text-left text-sm focus-visible:ring-2 focus-visible:ring-ring", className)} {...props}>
      {children}
      <Primitive.Icon asChild><ChevronDown className="size-4 shrink-0 text-muted-foreground" /></Primitive.Icon>
    </Primitive.Trigger>
  );
}

export function SelectContent({ className, children, ...props }: ComponentProps<typeof Primitive.Content>) {
  return (
    <Primitive.Portal>
      <Primitive.Content position="popper" sideOffset={4} className={cn("z-[60] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border bg-popover text-sm shadow-lg", className)} {...props}>
        <Primitive.Viewport className="max-h-[var(--radix-select-content-available-height)] p-1">{children}</Primitive.Viewport>
      </Primitive.Content>
    </Primitive.Portal>
  );
}

export function SelectItem({ className, children, ...props }: ComponentProps<typeof Primitive.Item>) {
  return (
    <Primitive.Item className={cn("relative cursor-default rounded py-1.5 pr-3 pl-8 outline-none data-highlighted:bg-accent", className)} {...props}>
      <Primitive.ItemIndicator className="absolute top-2 left-2"><Check className="size-4" /></Primitive.ItemIndicator>
      <Primitive.ItemText>{children}</Primitive.ItemText>
    </Primitive.Item>
  );
}
