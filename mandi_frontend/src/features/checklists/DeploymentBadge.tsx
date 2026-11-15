import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import type { Checklist } from "@/lib/api";

export function DeploymentBadge({ status }: { status: Checklist["kobo_deployment_status"] }) {
  const { t } = useTranslation();
  const variants: Record<
    Checklist["kobo_deployment_status"],
    "default" | "secondary" | "destructive" | "outline"
  > = {
    not_deployed: "secondary",
    deploying: "outline",
    deployed: "default",
    failed: "destructive",
  };
  const labels: Record<Checklist["kobo_deployment_status"], string> = {
    not_deployed: "Not deployed",
    deploying: "Deploying…",
    deployed: "Deployed",
    failed: "Deployment failed",
  };
  return <Badge variant={variants[status]}>{t(labels[status])}</Badge>;
}
