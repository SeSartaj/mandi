import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import type { Checklist } from "@/lib/api";

type DeploymentStatus = Checklist["collection"]["status"];

export function DeploymentBadge({ status }: { status: DeploymentStatus }) {
  const { t } = useTranslation();
  const variants: Record<
    DeploymentStatus,
    "default" | "secondary" | "destructive" | "outline"
  > = {
    not_deployed: "secondary",
    deploying: "outline",
    deployed: "default",
    failed: "destructive",
  };
  const labels: Record<DeploymentStatus, string> = {
    not_deployed: "Not deployed",
    deploying: "Deploying…",
    deployed: "Deployed",
    failed: "Deployment failed",
  };
  return <Badge variant={variants[status]}>{t(labels[status])}</Badge>;
}
