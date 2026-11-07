import {
  useCallback,
  useId,
  type Ref,
  type FocusEventHandler,
  startTransition,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { FieldValues, Path, PathValue, RegisterOptions, UseFormReturn } from "react-hook-form";
import { Check, ChevronsUpDown, Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { api } from "@/lib/api";
import { cn, toEnglishDigits } from "@/lib/utils";
import { changeFieldValue, type ClearFieldItem } from "@/utils/form-utils";

import { FormInputLayout, SimpleInputLayout } from "./InputLayout";

export interface CustomSearchSelectorOption {
  value: string;
  label: ReactNode;
  parentLabel?: ReactNode;
  searchText?: string;
  data?: unknown;
}

export type SelectedOptionPayload =
  CustomSearchSelectorOption | CustomSearchSelectorOption[] | null;

type StaticSearchProps = {
  items: CustomSearchSelectorOption[];
  endpoint?: never;
  queryKey?: never;
  mapDataToOptions?: never;
  searchParamName?: never;
  parseData?: never;
};

type AsyncSearchProps<TData = unknown> = {
  endpoint: string;
  queryKey: string | readonly unknown[];
  mapDataToOptions: (item: TData) => CustomSearchSelectorOption;
  searchParamName?: string;
  items?: never;
  parseData?: (response: unknown) => TData[];
  extraParams?: Record<string, unknown>;
};

type SharedProps = {
  label?: ReactNode;
  placeholder?: string;
  searchPlaceholder?: string;
  noOptionsText?: string;
  clearLabel?: string;
  disabled?: boolean;
  required?: boolean;
  reserveErrorSpace?: boolean;
  containerClassName?: string;
  labelClassName?: string;
  triggerClassName?: string;
  popoverContentClassName?: string;
  searching?: boolean;
  searchingLabel?: string;
  emptyContent?: ReactNode;
  footerContent?: ReactNode;
  onSearchChange?: (query: string) => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  multichoice?: boolean;
  keepSelectedOnSearch?: boolean;
  leftAddon?: ReactNode;
  rightAddon?: ReactNode;
  addonClassName?: string;
  renderHoverContent?: (item: CustomSearchSelectorOption) => ReactNode;
  defaultOptions?: CustomSearchSelectorOption[];
  debounceMs?: number;
};

export type CustomSearchSelectorProps<
  TFieldValues extends FieldValues,
  TData = unknown,
> = SharedProps & {
  form: UseFormReturn<TFieldValues>;
  name: Path<TFieldValues>;
  rules?: RegisterOptions<TFieldValues, Path<TFieldValues>>;
  clearFieldsOnChange?: ClearFieldItem<TFieldValues>[];
  defaultClearValue?: PathValue<TFieldValues, Path<TFieldValues>> | string | null;
  onValueChange?: (value: string | string[], selected: SelectedOptionPayload) => void;
} & (StaticSearchProps | AsyncSearchProps<TData>);

export type SimpleSearchSelectorProps<TData = unknown> = SharedProps &
  (StaticSearchProps | AsyncSearchProps<TData>) & {
    value?: string | string[];
    onChange: (value: string | string[]) => void;
    onValueChange?: (value: string | string[], selected: SelectedOptionPayload) => void;
    error?: string;
  };

function normalizeValues(value?: string | string[]) {
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
}

function optionText(option: CustomSearchSelectorOption) {
  const label = typeof option.label === "string" ? option.label : "";
  return toEnglishDigits(option.searchText ?? `${label} ${option.value}`).toLocaleLowerCase();
}

function uniqueByValue(items: CustomSearchSelectorOption[]) {
  return [...new Map(items.map((item) => [item.value, item])).values()];
}

function resolveSelectedOptions(
  value: string | string[],
  items: CustomSearchSelectorOption[],
): CustomSearchSelectorOption[] {
  const itemByValue = new Map(items.map((item) => [item.value, item]));
  return normalizeValues(value).map(
    (itemValue) => itemByValue.get(itemValue) ?? { value: itemValue, label: itemValue },
  );
}

function selectedPayload(items: CustomSearchSelectorOption[]): SelectedOptionPayload {
  if (items.length === 0) return null;
  return items.length === 1 ? items[0] : items;
}

function useDebouncedValue<T>(value: T, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedValue(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);
  return debouncedValue;
}

function useAsyncOptions<TData>(
  props: AsyncSearchProps<TData> | undefined,
  query: string,
  enabled: boolean,
  debounceMs: number,
) {
  const debouncedQuery = useDebouncedValue(query, debounceMs);
  const [data, setData] = useState<TData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const endpoint = props?.endpoint;
  const queryKey = props?.queryKey;
  const extraParamsKey = JSON.stringify(props?.extraParams ?? {});
  const searchParamName = props?.searchParamName ?? "search";
  const parseData = props?.parseData;

  useEffect(() => {
    if (!enabled || !props || !endpoint) {
      setIsLoading(false);
      setIsFetching(false);
      return;
    }

    let active = true;
    const cacheKey = JSON.stringify([queryKey, endpoint, debouncedQuery, extraParamsKey]);
    const cached = asyncOptionsCache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) {
      setData(cached.data as TData[]);
      setError(null);
      setIsLoading(false);
      setIsFetching(false);
      return () => {
        active = false;
      };
    }

    setIsLoading(true);
    setIsFetching(true);
    setError(null);
    const params = {
      ...(props.extraParams ?? {}),
      [searchParamName]: debouncedQuery,
    };
    void api
      .get<unknown>(endpoint, { params })
      .then(({ data: response }) => {
        let parsed: TData[];
        if (parseData) parsed = parseData(response);
        else if (Array.isArray(response)) parsed = response as TData[];
        else if (typeof response === "object" && response !== null && "results" in response) {
          parsed = (response as { results?: TData[] }).results ?? [];
        } else parsed = [];
        if (!active) return;
        setData(parsed);
        asyncOptionsCache.set(cacheKey, { data: parsed, expiresAt: Date.now() + 60_000 });
      })
      .catch((requestError: unknown) => {
        if (active) setError(requestError);
      })
      .finally(() => {
        if (!active) return;
        setIsLoading(false);
        setIsFetching(false);
      });

    return () => {
      active = false;
    };
    // Keep previous results while the next debounced query is loading.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, enabled, endpoint, extraParamsKey, parseData, queryKey, searchParamName]);

  return { data, isLoading, isFetching, error };
}

const asyncOptionsCache = new Map<string, { data: unknown[]; expiresAt: number }>();

function SearchSelector({
  id,
  ref,
  onBlur,
  "aria-describedby": describedBy,
  value,
  items,
  placeholder,
  searchPlaceholder,
  noOptionsText,
  clearLabel,
  searching = false,
  searchingLabel = "Searching...",
  emptyContent,
  footerContent,
  onSearchChange,
  open: controlledOpen,
  onOpenChange: onControlledOpenChange,
  disabled = false,
  hasError = false,
  triggerClassName,
  popoverContentClassName,
  multichoice = false,
  keepSelectedOnSearch = true,
  leftAddon,
  rightAddon,
  addonClassName,
  renderHoverContent,
  onChange,
}: {
  id?: string;
  ref?: Ref<HTMLButtonElement>;
  onBlur?: FocusEventHandler<HTMLButtonElement>;
  "aria-describedby"?: string;
  value?: string | string[];
  items: CustomSearchSelectorOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  noOptionsText?: string;
  clearLabel?: string;
  searching?: boolean;
  searchingLabel?: string;
  emptyContent?: ReactNode;
  footerContent?: ReactNode;
  onSearchChange?: (query: string) => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  disabled?: boolean;
  hasError?: boolean;
  triggerClassName?: string;
  popoverContentClassName?: string;
  multichoice?: boolean;
  keepSelectedOnSearch?: boolean;
  leftAddon?: ReactNode;
  rightAddon?: ReactNode;
  addonClassName?: string;
  renderHoverContent?: (item: CustomSearchSelectorOption) => ReactNode;
  onChange: (value: string | string[]) => void;
}) {
  const generatedId = useId();
  const formItemId = id ?? generatedId;
  const listboxId = `${formItemId}-options`;
  const searchInputRef = useRef<HTMLInputElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [internalOpen, setInternalOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const open = controlledOpen ?? internalOpen;
  const values = normalizeValues(value);
  const selectedOptions = resolveSelectedOptions(value ?? "", items);
  const selected = selectedOptions[0];
  const normalizedQuery = toEnglishDigits(query).trim().toLocaleLowerCase();

  const matchingItems = useMemo(
    () =>
      items.filter(
        (item) => onSearchChange || !normalizedQuery || optionText(item).includes(normalizedQuery),
      ),
    [items, normalizedQuery, onSearchChange],
  );
  const visibleItems = useMemo(
    () =>
      normalizedQuery && keepSelectedOnSearch
        ? uniqueByValue([...selectedOptions, ...matchingItems])
        : matchingItems,
    [keepSelectedOnSearch, matchingItems, normalizedQuery, selectedOptions],
  );

  const setOpen = (nextOpen: boolean) => {
    if (controlledOpen === undefined) setInternalOpen(nextOpen);
    if (!nextOpen) {
      setQuery("");
      setActiveIndex(-1);
      onSearchChange?.("");
    }
    onControlledOpenChange?.(nextOpen);
  };

  const handleTriggerKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (disabled || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex(0);
      setOpen(true);
      return;
    }
    if (event.key.length === 1) {
      event.preventDefault();
      setQuery(event.key);
      onSearchChange?.(event.key);
      setOpen(true);
    }
  };

  useEffect(() => {
    if (controlledOpen === false) {
      setQuery("");
      setActiveIndex(-1);
      onSearchChange?.("");
    }
  }, [controlledOpen, onSearchChange]);

  useEffect(() => {
    if (activeIndex >= visibleItems.length) setActiveIndex(visibleItems.length - 1);
  }, [activeIndex, visibleItems.length]);

  useEffect(() => {
    optionRefs.current[activeIndex]?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const close = () => setOpen(false);
  const selectOption = (selectedValue: string) => {
    if (multichoice) {
      const next = values.includes(selectedValue)
        ? values.filter((itemValue) => itemValue !== selectedValue)
        : [...values, selectedValue];
      onChange(next);
      return;
    }
    onChange(values[0] === selectedValue ? "" : selectedValue);
    close();
  };

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (visibleItems.length ? (current + 1) % visibleItems.length : -1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) =>
        visibleItems.length ? (current <= 0 ? visibleItems.length - 1 : current - 1) : -1,
      );
    } else if (event.key === "Enter" && visibleItems.length) {
      event.preventDefault();
      const index = activeIndex >= 0 ? activeIndex : visibleItems.length === 1 ? 0 : -1;
      if (index >= 0) selectOption(visibleItems[index].value);
    }
  };

  const preview = multichoice ? (
    selectedOptions.length <= 2 ? (
      selectedOptions
        .map((item) => item.label)
        .reduce<ReactNode[]>((acc, label, index) => [...acc, ...(index ? [", "] : []), label], [])
    ) : (
      <>
        {selectedOptions[0]?.label}, {selectedOptions[1]?.label} +{selectedOptions.length - 2}
      </>
    )
  ) : (
    selected?.label
  );

  return (
    <div className="relative w-full min-w-0">
      <Popover
        modal={false}
        open={open}
        onOpenChange={(nextOpen) => {
          setOpen(nextOpen);
          if (!nextOpen) setQuery("");
        }}
      >
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            id={formItemId}
            ref={ref}
            onBlur={onBlur}
            aria-describedby={describedBy}
            aria-controls={open ? listboxId : undefined}
            disabled={disabled}
            aria-expanded={open}
            aria-invalid={hasError}
            onKeyDown={handleTriggerKeyDown}
            className={cn(
              "bg-input-bg dark:bg-input-bg hover:bg-input-bg relative w-full justify-between gap-2 pe-9",
              !values.length && "text-muted-foreground",
              hasError && "border-destructive text-destructive",
              triggerClassName,
            )}
          >
            <span className="flex min-w-0 flex-1 items-center gap-2 truncate text-start">
              {leftAddon ? (
                <span className={cn("shrink-0", addonClassName)}>{leftAddon}</span>
              ) : (
                <Search className="text-muted-foreground size-4 shrink-0" aria-hidden="true" />
              )}
              <span className="min-w-0 flex-1 truncate">{preview ?? placeholder}</span>
              {rightAddon && <span className={cn("shrink-0", addonClassName)}>{rightAddon}</span>}
            </span>
            {!values.length && (
              <ChevronsUpDown
                className="absolute end-2 top-1/2 size-4 -translate-y-1/2 opacity-50"
                aria-hidden="true"
              />
            )}
          </Button>
        </PopoverTrigger>

        <PopoverContent
          align="start"
          className={cn(
            "max-h-[var(--radix-popover-content-available-height)] w-[min(var(--radix-popover-trigger-width),calc(100vw-1rem))] min-w-0 overflow-hidden p-2",
            popoverContentClassName,
          )}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            requestAnimationFrame(() => searchInputRef.current?.focus());
          }}
        >
          <Input
            ref={searchInputRef}
            autoFocus
            value={query}
            placeholder={searchPlaceholder}
            role="combobox"
            aria-expanded="true"
            aria-autocomplete="list"
            aria-label={searchPlaceholder ?? placeholder}
            aria-controls={listboxId}
            aria-activedescendant={
              activeIndex >= 0 && !searching && visibleItems[activeIndex]
                ? `${listboxId}-${activeIndex}`
                : undefined
            }
            onChange={(event) => {
              const nextQuery = event.target.value;
              setQuery(nextQuery);
              setActiveIndex(-1);
              if (onSearchChange) startTransition(() => onSearchChange(nextQuery));
            }}
            onKeyDown={onInputKeyDown}
            className="mb-2"
          />
          <div
            className="max-h-[min(15rem,calc(var(--radix-popover-content-available-height)-3.5rem))] touch-pan-y overflow-y-auto overscroll-y-contain"
            role="listbox"
            id={listboxId}
            aria-label={placeholder}
            aria-multiselectable={multichoice || undefined}
          >
            {searching ? (
              <p className="text-muted-foreground px-2 py-2 text-sm">{searchingLabel}</p>
            ) : visibleItems.length ? (
              visibleItems.map((item, index) => {
                const isSelected = values.includes(item.value);
                const option = (
                  <button
                    key={item.value}
                    ref={(element) => {
                      optionRefs.current[index] = element;
                    }}
                    type="button"
                    role="option"
                    id={`${listboxId}-${index}`}
                    tabIndex={-1}
                    aria-selected={isSelected}
                    className={cn(
                      "hover:bg-muted flex w-full items-center gap-2 rounded px-2 py-1.5 text-start text-sm",
                      activeIndex === index && "bg-muted",
                    )}
                    onMouseMove={() => setActiveIndex(index)}
                    onClick={() => selectOption(item.value)}
                  >
                    <span className="min-w-0 flex-1 break-words">
                      {item.parentLabel && (
                        <span className="text-muted-foreground block text-[10px] leading-3">
                          {item.parentLabel}
                        </span>
                      )}
                      {item.label}
                    </span>
                    <Check
                      className={cn("size-4 shrink-0", isSelected ? "opacity-100" : "opacity-0")}
                      aria-hidden="true"
                    />
                  </button>
                );
                return renderHoverContent ? (
                  <HoverCard key={item.value} openDelay={200} closeDelay={0}>
                    <HoverCardTrigger asChild>
                      <div className="w-full">{option}</div>
                    </HoverCardTrigger>
                    <HoverCardContent align="start" className="z-50 max-w-100 min-w-64">
                      {renderHoverContent(item)}
                    </HoverCardContent>
                  </HoverCard>
                ) : (
                  option
                );
              })
            ) : (
              (emptyContent ?? (
                <p className="text-muted-foreground px-2 py-3 text-center text-sm">
                  {noOptionsText || "No options found."}
                </p>
              ))
            )}
          </div>
          {footerContent}
        </PopoverContent>
      </Popover>

      {values.length > 0 && !multichoice && (
        <button
          type="button"
          aria-label={clearLabel ?? "Clear selection"}
          title={clearLabel}
          disabled={disabled}
          className="text-muted-foreground hover:text-foreground absolute end-2 top-1/2 z-10 -translate-y-1/2 rounded-sm p-1 disabled:pointer-events-none disabled:opacity-50"
          onClick={() => {
            onChange("");
            close();
          }}
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

function useOptions<TData>(
  props: SharedProps & (StaticSearchProps | AsyncSearchProps<TData>),
  open: boolean,
  query: string,
  debounceMs: number,
) {
  const asyncProps = "endpoint" in props ? (props as AsyncSearchProps<TData>) : undefined;
  const { data, isLoading, isFetching } = useAsyncOptions(asyncProps, query, open, debounceMs);
  const items = useMemo(() => {
    if (!asyncProps)
      return uniqueByValue([...(props.defaultOptions ?? []), ...(props.items ?? [])]);
    return uniqueByValue([
      ...(props.defaultOptions ?? []),
      ...data.map((item) => asyncProps.mapDataToOptions(item)),
    ]);
  }, [asyncProps, data, props]);
  return { items, isLoading, isFetching };
}

export function CustomSearchSelector<TFieldValues extends FieldValues, TData = unknown>(
  props: CustomSearchSelectorProps<TFieldValues, TData>,
) {
  const {
    form,
    name,
    rules,
    clearFieldsOnChange = [],
    defaultClearValue = "",
    onValueChange,
    label,
    required = false,
    reserveErrorSpace = false,
    containerClassName,
    labelClassName,
    defaultOptions: _defaultOptions = [],
    debounceMs = 500,
    ...sharedProps
  } = props;
  const [openInternal, setOpenInternal] = useState(false);
  const [query, setQuery] = useState("");
  const open = sharedProps.open ?? openInternal;
  const { items, isLoading, isFetching } = useOptions(props, open, query, debounceMs);
  const async = "endpoint" in props;
  const onSearchChange = sharedProps.onSearchChange;
  const handleSearchChange = useCallback(
    (term: string) => {
      setQuery(term);
      onSearchChange?.(term);
    },
    [onSearchChange],
  );
  const searchChangeHandler = async || sharedProps.onSearchChange ? handleSearchChange : undefined;

  return (
    <FormField
      control={form.control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => (
        <FormInputLayout
          label={label}
          required={required}
          reserveErrorSpace={reserveErrorSpace}
          labelClassName={labelClassName}
          containerClassName={containerClassName}
        >
          <SearchSelector
            {...sharedProps}
            ref={field.ref}
            onBlur={field.onBlur}
            value={field.value as string | string[] | undefined}
            items={items}
            open={open}
            onOpenChange={(nextOpen) => {
              if (sharedProps.open === undefined) setOpenInternal(nextOpen);
              sharedProps.onOpenChange?.(nextOpen);
            }}
            searching={sharedProps.searching ?? (async && (isLoading || isFetching))}
            hasError={!!fieldState.error}
            onSearchChange={searchChangeHandler}
            onChange={(value) => {
              field.onChange(value);
              if (clearFieldsOnChange.length) {
                changeFieldValue(form, clearFieldsOnChange, defaultClearValue, {
                  shouldDirty: true,
                });
              }
              onValueChange?.(value, selectedPayload(resolveSelectedOptions(value, items)));
            }}
          />
        </FormInputLayout>
      )}
    />
  );
}

export function SimpleSearchSelector<TData = unknown>(props: SimpleSearchSelectorProps<TData>) {
  const {
    value,
    onChange,
    onValueChange,
    error,
    label,
    required,
    containerClassName,
    labelClassName,
    defaultOptions: _defaultOptions = [],
    debounceMs = 500,
    ...sharedProps
  } = props;
  const fieldId = useId();
  const [internalOpen, setOpen] = useState(false);
  const open = sharedProps.open ?? internalOpen;
  const [query, setQuery] = useState("");
  const { items, isLoading, isFetching } = useOptions(props, open, query, debounceMs);
  const async = "endpoint" in props;
  const onSearchChange = sharedProps.onSearchChange;
  const handleSearchChange = useCallback(
    (term: string) => {
      setQuery(term);
      onSearchChange?.(term);
    },
    [onSearchChange],
  );
  const searchChangeHandler = async || sharedProps.onSearchChange ? handleSearchChange : undefined;

  return (
    <SimpleInputLayout
      id={fieldId}
      containerClassName={containerClassName}
      labelClassName={labelClassName}
      label={label as string | undefined}
      error={error}
      required={required}
    >
      <SearchSelector
        {...sharedProps}
        id={fieldId}
        aria-describedby={error ? `${fieldId}-error` : undefined}
        value={value}
        items={items}
        open={open}
        onOpenChange={(nextOpen) => {
          if (sharedProps.open === undefined) setOpen(nextOpen);
          sharedProps.onOpenChange?.(nextOpen);
        }}
        searching={sharedProps.searching ?? (async && (isLoading || isFetching))}
        hasError={!!error}
        onSearchChange={searchChangeHandler}
        onChange={(nextValue) => {
          onChange(nextValue);
          onValueChange?.(nextValue, selectedPayload(resolveSelectedOptions(nextValue, items)));
        }}
      />
    </SimpleInputLayout>
  );
}

export default CustomSearchSelector;
