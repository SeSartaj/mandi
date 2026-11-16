import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

type FieldSupportProps = Omit<ComponentProps<"p">, "children"> & {
  error?: ReactNode;
  description?: ReactNode;
};

/** A permanent two-line slot. Longer messages scroll instead of moving controls. */
export function FieldSupport({ error, description, className, ...props }: FieldSupportProps) {
  const content = error || description;
  return (
    <p
      {...props}
      data-slot="field-support"
      data-error={Boolean(error)}
      role={error ? "alert" : undefined}
      aria-hidden={content ? undefined : true}
      tabIndex={content ? 0 : undefined}
      className={cn(
        "field-support text-muted-foreground data-[error=true]:text-destructive",
        className,
      )}
    >
      {content || "\u00a0"}
    </p>
  );
}
