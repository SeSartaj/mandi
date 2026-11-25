import { MoreVertical } from "lucide-react";
import { Fragment, type ComponentType } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export type ActionsMenuItem = {
  id: string;
  label: string;
  icon?: ComponentType<{ className?: string }>;
  onSelect?: () => void;
  disabled?: boolean;
  hidden?: boolean;
  separatorBefore?: boolean;
  variant?: "default" | "destructive";
};

export function ActionsMenu({
  items,
  label,
  align = "end",
  className,
  contentClassName,
}: {
  items: ActionsMenuItem[];
  label: string;
  align?: "start" | "center" | "end";
  className?: string;
  contentClassName?: string;
}) {
  const { t } = useTranslation();
  const visible = items.filter((item) => !item.hidden);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={cn("print:hidden", className)}
          aria-label={label}
          title={label}
        >
          <MoreVertical className="size-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align} className={cn("w-56", contentClassName)}>
        {visible.map((item) => {
          const Icon = item.icon;
          return (
            <Fragment key={item.id}>
              {item.separatorBefore ? <DropdownMenuSeparator /> : null}
              <DropdownMenuItem
                variant={item.variant}
                disabled={item.disabled}
                onSelect={item.onSelect}
              >
                {Icon ? <Icon className="size-4" /> : null}
                <span>{item.label}</span>
              </DropdownMenuItem>
            </Fragment>
          );
        })}
        {visible.length === 0 ? (
          <p className="text-muted-foreground px-2 py-1.5 text-sm">{t("No actions available.")}</p>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
