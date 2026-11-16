import type { ComponentProps } from "react";
import { LoaderCircle, Pencil, Plus, Save, Trash2, Undo2, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const actions = {
  create: { icon: Plus, label: "Create", pending: "Creating…", variant: "primary", type: "button" },
  edit: { icon: Pencil, label: "Edit", pending: "Loading…", variant: "secondary", type: "button" },
  save: { icon: Save, label: "Save", pending: "Saving…", variant: "primary", type: "submit" },
  cancel: { icon: X, label: "Cancel", pending: "Cancel", variant: "secondary", type: "button" },
  delete: {
    icon: Trash2,
    label: "Delete",
    pending: "Deleting…",
    variant: "primary",
    type: "button",
  },
  discard: {
    icon: Undo2,
    label: "Discard changes",
    pending: "Discard changes",
    variant: "secondary",
    type: "button",
  },
} as const;

export type ActionButtonProps = Omit<
  ComponentProps<typeof Button>,
  "children" | "variant" | "size" | "asChild"
> & {
  action: keyof typeof actions;
  /** Emphasis is separate from meaning; delete remains destructive in either variant. */
  variant?: "primary" | "secondary";
  size?: "xs" | "sm" | "default" | "lg";
  label?: string;
  iconOnly?: boolean;
  loading?: boolean;
  loadingLabel?: string;
};

export function ActionButton({
  action,
  variant,
  size = "default",
  label,
  iconOnly = false,
  loading = false,
  loadingLabel,
  disabled,
  type,
  className,
  ...props
}: ActionButtonProps) {
  const { t } = useTranslation();
  const config = actions[action];
  const emphasis = variant ?? config.variant;
  const destructive = action === "delete" || action === "discard";
  const text = label ?? t(config.label);
  const visibleText = loading ? (loadingLabel ?? t(config.pending)) : text;
  const Icon = loading ? LoaderCircle : config.icon;
  const iconSizes = { xs: "icon-xs", sm: "icon-sm", default: "icon", lg: "icon-lg" } as const;

  return (
    <Button
      {...props}
      type={type ?? config.type}
      variant={emphasis === "secondary" ? "outline" : destructive ? "destructive" : "default"}
      size={iconOnly ? iconSizes[size] : size}
      disabled={disabled || loading}
      aria-label={props["aria-label"] ?? (iconOnly ? visibleText : undefined)}
      aria-busy={loading || undefined}
      title={props.title ?? (iconOnly ? visibleText : undefined)}
      data-action={action}
      data-emphasis={emphasis}
      className={cn(
        destructive &&
          emphasis === "secondary" &&
          "text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive",
        className,
      )}
    >
      <Icon aria-hidden="true" className={cn("size-4", loading && "animate-spin")} />
      {!iconOnly && <span>{visibleText}</span>}
    </Button>
  );
}

type SemanticButtonProps = Omit<ActionButtonProps, "action">;
export function CreateButton(props: SemanticButtonProps) {
  return <ActionButton {...props} action="create" />;
}
export function EditButton(props: SemanticButtonProps) {
  return <ActionButton {...props} action="edit" />;
}
export function SaveButton(props: SemanticButtonProps) {
  return <ActionButton {...props} action="save" />;
}
export function CancelButton(props: SemanticButtonProps) {
  return <ActionButton {...props} action="cancel" />;
}
export function DeleteButton(props: SemanticButtonProps) {
  return <ActionButton {...props} action="delete" />;
}
export function DiscardButton(props: SemanticButtonProps) {
  return <ActionButton {...props} action="discard" />;
}
