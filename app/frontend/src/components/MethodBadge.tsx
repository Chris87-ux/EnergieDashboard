import { Badge } from "@/components/ui/badge";
import { METHOD_LABELS } from "@/lib/format";
import type { Method } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<Method, string> = {
  run_estimate: "bg-[#78350F] text-[#FDE68A] border-[#92400E]",
  counter_delta: "bg-[#064E3B] text-[#A7F3D0] border-[#065F46]",
  phase_sum: "bg-[#1E3A8A] text-[#BFDBFE] border-[#1E40AF]",
  power_integral: "bg-[#78350F] text-[#FDE68A] border-[#92400E]",
  unavailable: "bg-[#450A0A] text-[#FECACA] border-[#7F1D1D]",
  not_applicable: "bg-transparent text-[#8EA8C3] border-[var(--border)]",
};

export default function MethodBadge({ method, testid, className }: { method: Method; testid?: string; className?: string }) {
  return (
    <Badge data-testid={testid} className={cn("h-5 rounded-md px-1.5 text-[10px] font-semibold", STYLES[method], className)}>
      {METHOD_LABELS[method]}
    </Badge>
  );
}
