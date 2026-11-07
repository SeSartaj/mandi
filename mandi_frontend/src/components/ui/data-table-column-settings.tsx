import { ArrowDown, ArrowUp, RotateCcw, Settings2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type ColumnOption<Key extends string> = { key: Key; label: string };

type DataTableColumnSettingsProps<Key extends string> = {
  columns: readonly ColumnOption<Key>[];
  visibleColumns: Key[];
  onChange: (columns: Key[]) => void;
  onReset: () => void;
  labels: {
    button: string;
    title: string;
    reset: string;
    moveUp: string;
    moveDown: string;
  };
  idPrefix?: string;
};

export function DataTableColumnSettings<Key extends string>({
  columns,
  visibleColumns,
  onChange,
  onReset,
  labels,
  idPrefix = "table-column",
}: DataTableColumnSettingsProps<Key>) {
  const orderedColumns = [
    ...visibleColumns.map((key) => columns.find((column) => column.key === key)).filter(Boolean),
    ...columns.filter((column) => !visibleColumns.includes(column.key)),
  ] as ColumnOption<Key>[];

  const toggle = (key: Key, checked: boolean) => {
    if (checked) onChange(visibleColumns.includes(key) ? visibleColumns : [...visibleColumns, key]);
    else if (visibleColumns.length > 1) onChange(visibleColumns.filter((item) => item !== key));
  };

  const move = (key: Key, offset: -1 | 1) => {
    const index = visibleColumns.indexOf(key);
    const nextIndex = index + offset;
    if (index < 0 || nextIndex < 0 || nextIndex >= visibleColumns.length) return;
    const next = [...visibleColumns];
    [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
    onChange(next);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" className="gap-2">
          <Settings2 className="size-4" />
          {labels.button}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel>{labels.title}</DropdownMenuLabel>
        <div role="group" aria-label={labels.title}>
          {orderedColumns.map((column) => {
            const checked = visibleColumns.includes(column.key);
            const index = visibleColumns.indexOf(column.key);
            const id = `${idPrefix}-${column.key}`;
            return (
              <div key={column.key} className="flex items-center gap-2 px-2 py-1">
                <label
                  htmlFor={id}
                  className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-sm"
                >
                  <Checkbox
                    id={id}
                    checked={checked}
                    disabled={checked && visibleColumns.length === 1}
                    onCheckedChange={(value) => toggle(column.key, value === true)}
                  />
                  <span className="truncate">{column.label}</span>
                </label>
                {checked && (
                  <div className="flex shrink-0 items-center gap-0.5">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      disabled={index === 0}
                      aria-label={`${labels.moveUp}: ${column.label}`}
                      onClick={() => move(column.key, -1)}
                    >
                      <ArrowUp className="size-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      disabled={index === visibleColumns.length - 1}
                      aria-label={`${labels.moveDown}: ${column.label}`}
                      onClick={() => move(column.key, 1)}
                    >
                      <ArrowDown className="size-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onReset}>
          <RotateCcw className="size-4" />
          {labels.reset}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
