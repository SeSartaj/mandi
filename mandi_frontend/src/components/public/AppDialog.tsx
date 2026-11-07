"use client";

import * as React from "react";
import { XIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { useLocale } from "@/i18n/useTranslations";
import { isRTL } from "@/config/languages";

import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";

type DialogSize = "sm" | "md" | "lg" | "xl" | "2xl" | "3xl";

const sizeClasses: Record<DialogSize, string> = {
  sm: "sm:max-w-sm",
  md: "sm:max-w-lg",
  lg: "sm:max-w-2xl",
  xl: "sm:max-w-4xl",
  "2xl": "sm:max-w-6xl",
  "3xl": "sm:max-w-7xl",
};

export type AppDialogRenderApi = {
  open: boolean;
  close: () => void;
  setOpen: (v: boolean) => void;
};

export type AppDialogProps = Omit<React.ComponentProps<typeof Dialog>, "children"> & {
  /** If you don't pass a trigger, the dialog must be controlled via open/onOpenChange */
  trigger?: React.ReactNode;
  triggerAsChild?: boolean;
  triggerProps?: Omit<React.ComponentProps<typeof DialogTrigger>, "asChild" | "children">;

  title?: React.ReactNode;
  description?: React.ReactNode;

  /**
   * children can be a ReactNode
   * or a render-prop function that receives { open, close, setOpen }
   */
  children?: React.ReactNode | ((api: AppDialogRenderApi) => React.ReactNode);

  /** Footer content (buttons/actions). Can also be a render-prop. */
  footer?: React.ReactNode | ((api: AppDialogRenderApi) => React.ReactNode);

  showCloseButton?: boolean;
  closeLabel?: string;

  size?: DialogSize;

  contentClassName?: string;
  headerClassName?: string;
  footerClassName?: string;
  titleClassName?: string;
  descriptionClassName?: string;

  /** If false, clicking the overlay/outside won't close the dialog */
  closeOnOverlayClick?: boolean;

  /**
   * Extra props for DialogContent wrapper (Radix Content props under the hood).
   * NOTE: We intentionally do NOT omit "onInteractOutside" so we can merge it.
   */
  contentProps?: Omit<
    React.ComponentProps<typeof DialogContent>,
    "children" | "className" | "showCloseButton"
  >;
};

export function AppDialog({
  trigger,
  triggerAsChild = true,
  triggerProps,

  title,
  description,

  children,
  footer,

  showCloseButton = true,
  closeLabel,

  size = "md",

  contentClassName,
  headerClassName,
  footerClassName,
  titleClassName,
  descriptionClassName,

  closeOnOverlayClick = true,
  contentProps,

  // Root props
  open: openProp,
  defaultOpen,
  onOpenChange,
  ...rootProps
}: AppDialogProps) {
  const locale = useLocale();
  const { t } = useTranslation();
  const resolvedCloseLabel = closeLabel ?? t("Close");

  // Controlled vs uncontrolled logic
  const isControlled = openProp !== undefined;

  const [internalOpen, setInternalOpen] = React.useState<boolean>(defaultOpen ?? false);

  const open = isControlled ? (openProp as boolean) : internalOpen;

  // setOpen updates internal state (when uncontrolled) and calls onOpenChange either way
  const setOpen = React.useCallback(
    (v: boolean) => {
      if (!isControlled) setInternalOpen(v);
      onOpenChange?.(v);
    },
    [isControlled, onOpenChange],
  );

  // Convenience close method for render-props
  const close = React.useCallback(() => setOpen(false), [setOpen]);

  const api = React.useMemo<AppDialogRenderApi>(
    () => ({ open, close, setOpen }),
    [open, close, setOpen],
  );

  const resolvedChildren = typeof children === "function" ? children(api) : children;

  const resolvedFooter = typeof footer === "function" ? footer(api) : footer;

  // Extract user's onInteractOutside so we can merge it with our own logic.
  const { onInteractOutside: userOnInteractOutside, ...restContentProps } = contentProps ?? {};

  return (
    <Dialog open={open} onOpenChange={setOpen} {...rootProps}>
      {trigger ? (
        <DialogTrigger
          onClick={(e) => {
            e.stopPropagation();
          }}
          {...triggerProps}
          asChild={triggerAsChild}
        >
          {trigger}
        </DialogTrigger>
      ) : null}

      <DialogContent
        onClick={(e) => {
          e.stopPropagation();
        }}
        {...restContentProps}
        // We disable the built-in close button from your DialogContent wrapper
        // because it is hardcoded (right-4, "Close"). We'll render our own below
        // to support RTL and custom closeLabel.
        showCloseButton={false}
        onInteractOutside={(e) => {
          // Prevent closing when closeOnOverlayClick is false
          if (!closeOnOverlayClick) e.preventDefault();

          // Call user's handler if provided
          userOnInteractOutside?.(e);
        }}
        className={cn("max-h-[90vh] overflow-y-auto", sizeClasses[size], contentClassName)}
      >
        {(title || description) && (
          <DialogHeader className={cn(headerClassName)}>
            {title ? (
              <DialogTitle className={cn("text-start", titleClassName)}>{title}</DialogTitle>
            ) : null}

            {description ? (
              <DialogDescription className={cn("text-start", descriptionClassName)}>
                {description}
              </DialogDescription>
            ) : null}
          </DialogHeader>
        )}

        {resolvedChildren}

        {resolvedFooter ? (
          <DialogFooter className={cn(footerClassName)}>{resolvedFooter}</DialogFooter>
        ) : null}

        {showCloseButton && (
          <DialogClose
            aria-label={resolvedCloseLabel}
            className={cn(
              "absolute top-4 rounded-xs opacity-70 transition-opacity hover:opacity-100",
              "focus:ring-ring ring-offset-background focus:ring-2 focus:ring-offset-2 focus:outline-hidden",
              "disabled:pointer-events-none",
              isRTL(locale) ? "left-4" : "right-4",
            )}
          >
            <XIcon className="size-4" />
            <span className="sr-only">{resolvedCloseLabel}</span>
          </DialogClose>
        )}
      </DialogContent>
    </Dialog>
  );
}
