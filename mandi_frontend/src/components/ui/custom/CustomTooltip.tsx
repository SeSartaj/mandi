import type { ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface CustomTooltipProps {
  children: ReactNode;
  className?: string;
  title: string;
}

export function CustomTooltip({ children, title, className }: CustomTooltipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent className={className}>{title}</TooltipContent>
    </Tooltip>
  );
}
