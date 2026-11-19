import { Tabs as Primitive } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const Tabs = Primitive.Root;
export const TabsContent = Primitive.Content;

export function TabsList({ className, ...props }: ComponentProps<typeof Primitive.List>) {
  return <Primitive.List className={cn("flex flex-wrap gap-1 rounded-md bg-muted p-1", className)} {...props} />;
}

export function TabsTrigger({ className, ...props }: ComponentProps<typeof Primitive.Trigger>) {
  return <Primitive.Trigger className={cn("flex-1 rounded px-2 py-1.5 text-sm text-muted-foreground data-[state=active]:bg-background data-[state=active]:text-foreground focus-visible:ring-2 focus-visible:ring-ring", className)} {...props} />;
}
