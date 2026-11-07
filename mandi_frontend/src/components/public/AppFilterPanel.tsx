import { useCallback, useId, useState, type ReactNode } from "react";
import { FilterX, SlidersHorizontal, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useTranslations } from "@/i18n/useTranslations";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export type ActiveFilter = {
  key: string;
  label: string;
  value: string;
};

type AppFilterPanelProps = {
  children: ReactNode;
  /** Frequently used controls rendered directly in the top filter row. */
  alwaysVisible?: ReactNode;
  advancedLabel?: string;
  activeFilters?: ActiveFilter[];
  onRemoveFilter?: (key: string) => void;
  onClearAll?: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  hideTrigger?: boolean;
  hideChips?: boolean;
  hideClearAll?: boolean;
  trigger?: ReactNode;
  className?: string;
  filtersClassName?: string;
};

function FilterChip({
  filter,
  onRemove,
  removeLabel,
}: {
  filter: ActiveFilter;
  onRemove?: () => void;
  removeLabel: string;
}) {
  return (
    <span className="border-primary/20 bg-primary/5 inline-flex h-7 items-center gap-1 rounded-full border px-2.5 text-xs">
      <span className="text-muted-foreground">{filter.label}:</span>
      <span className="text-primary max-w-32 truncate font-semibold">{filter.value}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus-visible:ring-ring rounded-full p-0.5 focus-visible:ring-2 focus-visible:outline-none"
          aria-label={`${removeLabel} ${filter.label}`}
        >
          <X className="size-3" aria-hidden="true" />
        </button>
      )}
    </span>
  );
}

export default function AppFilterPanel({
  children,
  alwaysVisible,
  advancedLabel,
  activeFilters = [],
  onRemoveFilter,
  onClearAll,
  open: controlledOpen,
  onOpenChange,
  hideTrigger = false,
  hideChips = false,
  hideClearAll = false,
  trigger,
  className,
  filtersClassName,
}: AppFilterPanelProps) {
  const t = useTranslations("FilterPanel");
  const contentId = useId();
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = controlledOpen ?? internalOpen;
  const hasActiveFilters = activeFilters.length > 0;

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (controlledOpen === undefined) setInternalOpen(nextOpen);
      onOpenChange?.(nextOpen);
    },
    [controlledOpen, onOpenChange],
  );

  const defaultTrigger = (
    <Button
      type="button"
      variant={isOpen ? "secondary" : "outline"}
      size="icon-sm"
      aria-expanded={isOpen}
      aria-controls={contentId}
      aria-label={advancedLabel ?? t("label")}
      className="relative"
    >
      <SlidersHorizontal className="size-3.5" aria-hidden="true" />
      {hasActiveFilters && (
        <span className="bg-primary text-primary-foreground absolute -end-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px]">
          {activeFilters.length}
        </span>
      )}
    </Button>
  );

  return (
    <div
      className={cn(
        "border-border bg-card min-w-0 flex-1 overflow-hidden rounded-xl border shadow-xs",
        className,
      )}
    >
      <Collapsible open={isOpen} onOpenChange={handleOpenChange}>
        <div className="flex flex-wrap items-center gap-2 p-3">
          {alwaysVisible}
          {hasActiveFilters && onClearAll && !hideClearAll && (
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={onClearAll}
              className="text-muted-foreground hover:text-destructive h-7 gap-1 px-2 text-xs"
            >
              <FilterX className="size-3" aria-hidden="true" />
              {t("clear_all")}
            </Button>
          )}
          {!hideTrigger && (
            <div className="ms-auto">
              <Tooltip>
                <TooltipTrigger asChild>
                  <CollapsibleTrigger asChild>{trigger ?? defaultTrigger}</CollapsibleTrigger>
                </TooltipTrigger>
                <TooltipContent>{advancedLabel ?? t("label")}</TooltipContent>
              </Tooltip>
            </div>
          )}
          {hasActiveFilters && !hideChips && (
            <div className="flex min-w-full flex-wrap items-center gap-1.5">
              {activeFilters.map((filter) => (
                <FilterChip
                  key={filter.key}
                  filter={filter}
                  onRemove={onRemoveFilter ? () => onRemoveFilter(filter.key) : undefined}
                  removeLabel={t("remove_filter")}
                />
              ))}
            </div>
          )}
        </div>

        <CollapsibleContent id={contentId}>
          <div className={cn("border-border border-t", filtersClassName)}>
            <div className="flex flex-wrap items-end gap-3 overflow-auto p-4">{children}</div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
