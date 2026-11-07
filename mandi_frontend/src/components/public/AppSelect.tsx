"use client";

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

interface SelectOption {
  value: string | number;
  label: string;
}

interface AppSelectProps {
  label?: string;
  options: SelectOption[];
  onChange: (value: string | number) => void;
  width?: string;
  value?: string | number;
  defaultValue?: string | number;
  className?: string;
}

export function AppSelect({
  label = "",
  options,
  onChange,
  width = "",
  value,
  defaultValue,
  className,
}: AppSelectProps) {
  const selectProps =
    value !== undefined ? { value: String(value) } : { defaultValue: String(defaultValue ?? "") };

  return (
    <Select
      {...selectProps}
      onValueChange={(val) => {
        const parsed = isNaN(Number(val)) ? val : Number(val);
        onChange(parsed);
      }}
    >
      <SelectTrigger className={cn(width || "w-45", className)}>
        <SelectValue placeholder={label} />
      </SelectTrigger>

      <SelectContent>
        <SelectGroup>
          {options?.map((op) => (
            <SelectItem key={String(op.value)} value={String(op.value)}>
              {op.label}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}
