import type { ReactNode } from "react";
import { LoaderCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type AppLoaderProps = {
  label?: ReactNode;
  className?: string;
  spinnerClassName?: string;
};

export function AppLoader({ label, className, spinnerClassName }: AppLoaderProps) {
  return (
    <div
      className={cn("text-muted-foreground flex items-center justify-center gap-2", className)}
      role="status"
      aria-live="polite"
      aria-label={typeof label === "string" ? label : "Loading"}
    >
      <LoaderCircle
        className={cn("text-primary size-5 animate-spin", spinnerClassName)}
        aria-hidden="true"
      />
      {label && <span>{label}</span>}
    </div>
  );
}
