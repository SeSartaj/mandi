import type { ReactNode } from "react";

import { useSession } from "@/lib/session";
import { useTranslation } from "react-i18next";

type CanProps = {
  /** Django permission name, for example `tickets.add_ticket`. */
  permission?: string;
  /** Permissions to combine when one or more permissions are required. */
  permissions?: string[];
  /** Defaults to `or` when `permissions` is provided. */
  operator?: "or" | "and";
  children: ReactNode;
  /** Optional content to render when permission is missing. */
  fallback?: ReactNode;
  /** Some backend permission checks also require the account to be staff. */
  staffOnly?: boolean;
};

/** Render children only when the current user has the requested permission. */
export function Can({
  permission,
  permissions,
  operator = "or",
  children,
  fallback = null,
  staffOnly = false,
}: CanProps) {
  const requiredPermissions = permissions ?? (permission ? [permission] : []);
  const session = useSession();
  const hasPermission =
    requiredPermissions.length > 0 &&
    (operator === "and"
      ? requiredPermissions.every((item) => session.permissions.includes(item))
      : requiredPermissions.some((item) => session.permissions.includes(item)));
  const allowed = hasPermission && (!staffOnly || Boolean(session.user.is_staff));
  return allowed ? <>{children}</> : <>{fallback}</>;
}

type CanAnyProps = {
  permissions: string[];
  children: ReactNode;
  fallback?: ReactNode;
};

/** Render children when the current user has at least one permission. */
export function CanAny({ permissions, children, fallback = null }: CanAnyProps) {
  return (
    <Can permissions={permissions} operator="or" fallback={fallback}>
      {children}
    </Can>
  );
}

/** Small route fallback that does not expose any protected page content. */
export function PermissionDenied() {
  const { t } = useTranslation();
  return (
    <div className="text-muted-foreground flex min-h-60 items-center justify-center text-sm">
      {t("Access denied.")}
    </div>
  );
}
