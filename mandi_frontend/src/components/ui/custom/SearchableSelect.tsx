import { startTransition, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Check, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { toEnglishDigits } from "@/lib/utils";

export interface SearchableSelectOption {
  value: string;
  label: string;
  labelSuffix?: string;
  parentLabel?: string;
  searchText?: string;
}

interface SearchableSelectProps {
  id?: string;
  className?: string;
  options: SearchableSelectOption[];
  value: string | null;
  onValueChange: (value: string | null) => void;
  placeholder: string;
  searchPlaceholder: string;
  allLabel?: string;
  showAllOption?: boolean;
  showAllOptionWhenEmpty?: boolean;
  allowClear?: boolean;
  clearLabel?: string;
  searching?: boolean;
  emptyLabel?: string;
  emptyContent?: ReactNode;
  footerContent?: ReactNode;
  onSearchChange?: (query: string) => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function SearchableSelect({
  id,
  className,
  options,
  value,
  onValueChange,
  placeholder,
  searchPlaceholder,
  allLabel = "Show all",
  showAllOption = true,
  showAllOptionWhenEmpty = true,
  allowClear = true,
  clearLabel = "Clear selection",
  searching = false,
  emptyLabel = "No options found.",
  emptyContent,
  footerContent,
  onSearchChange,
  open: controlledOpen,
  onOpenChange: onControlledOpenChange,
}: SearchableSelectProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [portalContainer, setPortalContainer] = useState<HTMLElement | undefined>();
  const allOptionRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const open = controlledOpen ?? internalOpen;
  // Dialog's scroll lock allows wheel/touch scrolling only within its content.
  // Keep the dropdown in that DOM subtree instead of portaling to document.body.
  useEffect(() => {
    if (open) {
      setPortalContainer(triggerRef.current?.closest<HTMLElement>('[role="dialog"]') ?? undefined);
    }
  }, [open]);
  const selected = options.find((option) => option.value === value);
  const normalizedQuery = toEnglishDigits(query).toLocaleLowerCase();

  useEffect(() => {
    if (controlledOpen === false) {
      setQuery("");
      onSearchChange?.("");
    }
  }, [controlledOpen, onSearchChange]);
  const filteredOptions = useMemo(
    () =>
      options.filter((option) =>
        toEnglishDigits(option.searchText ?? option.label)
          .toLocaleLowerCase()
          .includes(normalizedQuery),
      ),
    [options, normalizedQuery],
  );
  const showAll = showAllOption && (value || showAllOptionWhenEmpty);
  const optionCount = filteredOptions.length + (showAll ? 1 : 0);

  useEffect(() => {
    if (activeIndex >= optionCount) setActiveIndex(optionCount - 1);
  }, [activeIndex, optionCount]);

  useEffect(() => {
    if (activeIndex === 0 && showAll) allOptionRef.current?.scrollIntoView({ block: "nearest" });
    else optionRefs.current[activeIndex - (showAll ? 1 : 0)]?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, showAll]);

  const setOpen = (nextOpen: boolean) => {
    if (nextOpen) {
      setPortalContainer(triggerRef.current?.closest<HTMLElement>('[role="dialog"]') ?? undefined);
    }
    if (controlledOpen === undefined) setInternalOpen(nextOpen);
    if (!nextOpen) {
      setQuery("");
      setActiveIndex(-1);
      onSearchChange?.("");
    }
    onControlledOpenChange?.(nextOpen);
  };

  const handleTriggerKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== "ArrowDown" || event.altKey || event.ctrlKey || event.metaKey) return;
    event.preventDefault();
    setActiveIndex(0);
    setOpen(true);
  };

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (optionCount ? (current + 1 + optionCount) % optionCount : -1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) =>
        optionCount ? (current <= 0 ? optionCount - 1 : current - 1) : -1,
      );
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      if (showAll && activeIndex === 0) onValueChange(null);
      else onValueChange(filteredOptions[activeIndex - (showAll ? 1 : 0)]?.value ?? null);
      setOpen(false);
    }
  };

  return (
    <Popover modal={false} open={open} onOpenChange={setOpen}>
      <div className={cn("relative w-fit max-w-full min-w-0", className)}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            ref={triggerRef}
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            onKeyDown={handleTriggerKeyDown}
            className={cn(
              "bg-input-bg dark:bg-input-bg hover:bg-input-bg w-56 max-w-full min-w-0 justify-between gap-2 overflow-hidden",
              value && "pe-8",
              className,
            )}
          >
            <span className="flex min-w-0 items-center gap-2 overflow-hidden">
              <Search className="text-muted-foreground size-4 shrink-0" aria-hidden="true" />
              <span className="flex min-w-0 flex-col truncate text-start">
                {selected?.parentLabel && (
                  <span className="text-muted-foreground truncate text-[10px] leading-3">
                    {selected.parentLabel}
                  </span>
                )}
                <span className="truncate">
                  {selected?.label ?? placeholder}
                  {selected?.labelSuffix && (
                    <span className="text-muted-foreground text-xs"> {selected.labelSuffix}</span>
                  )}
                </span>
              </span>
            </span>
          </Button>
        </PopoverTrigger>
        {value && allowClear && (
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground absolute end-2 top-1/2 z-10 -translate-y-1/2 rounded-sm p-1"
            aria-label={clearLabel}
            title={clearLabel}
            onClick={() => {
              onValueChange(null);
              setQuery("");
              setOpen(false);
            }}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        )}
        <PopoverContent container={portalContainer} className="w-64 p-2" align="start">
          <div className="relative mb-2">
            <Search
              className="text-muted-foreground absolute start-3 top-1/2 size-4 -translate-y-1/2"
              aria-hidden="true"
            />
            <Input
              autoFocus
              value={query}
              role="combobox"
              aria-expanded="true"
              aria-autocomplete="list"
              onKeyDown={handleInputKeyDown}
              onChange={(event) => {
                const nextQuery = event.target.value;
                setQuery(nextQuery);
                setActiveIndex(-1);
                if (onSearchChange) {
                  startTransition(() => onSearchChange(nextQuery));
                }
              }}
              placeholder={searchPlaceholder}
              className="ps-9"
            />
          </div>
          <div className="max-h-60 overflow-y-auto overscroll-contain" role="listbox">
            {showAll && (
              <button
                ref={allOptionRef}
                type="button"
                role="option"
                aria-selected={!value}
                className={cn(
                  "hover:bg-muted flex w-full items-center gap-2 rounded px-2 py-1.5 text-start text-sm",
                  !value && "bg-primary/10 text-primary",
                  activeIndex === 0 && "bg-muted",
                )}
                onMouseMove={() => setActiveIndex(0)}
                onClick={() => {
                  onValueChange(null);
                  setOpen(false);
                }}
              >
                <span className="min-w-0 flex-1 truncate">{allLabel}</span>
                {!value && <Check className="size-4 shrink-0" aria-hidden="true" />}
              </button>
            )}
            {searching ? (
              <p className="text-muted-foreground px-2 py-2 text-sm">Searching...</p>
            ) : filteredOptions.length > 0 ? (
              filteredOptions.map((option, index) => (
                <button
                  ref={(element) => {
                    optionRefs.current[index] = element;
                  }}
                  type="button"
                  key={option.value}
                  role="option"
                  aria-selected={option.value === value}
                  className={cn(
                    "hover:bg-muted flex w-full items-center gap-2 rounded px-2 py-1.5 text-start text-sm break-words whitespace-normal",
                    option.value === value && "bg-primary/10 text-primary",
                    activeIndex === index + (showAll ? 1 : 0) && "bg-muted",
                  )}
                  onMouseMove={() => setActiveIndex(index + (showAll ? 1 : 0))}
                  onClick={() => {
                    onValueChange(option.value);
                    setOpen(false);
                  }}
                >
                  <span className="flex min-w-0 flex-1 flex-col">
                    {option.parentLabel && (
                      <span className="text-muted-foreground text-[10px] leading-3">
                        {option.parentLabel}
                      </span>
                    )}
                    <span>
                      {option.label}
                      {option.labelSuffix && (
                        <span className="text-muted-foreground text-xs"> {option.labelSuffix}</span>
                      )}
                    </span>
                  </span>
                  {option.value === value && (
                    <Check className="size-4 shrink-0" aria-hidden="true" />
                  )}
                </button>
              ))
            ) : (
              (emptyContent ?? (
                <p className="text-muted-foreground px-2 py-2 text-sm">{emptyLabel}</p>
              ))
            )}
          </div>
          {footerContent}
        </PopoverContent>
      </div>
    </Popover>
  );
}
