import { CircleHelp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { AppDialog } from "@/components/public/AppDialog";
import { Button } from "@/components/ui/button";

export default function WorkspaceHelp() {
  const { t } = useTranslation();
  const sections = [
    [
      "Establishments",
      "Search the registry before adding an establishment. Open a record to review its details, linked sources, and inspection history.",
    ],
    [
      "Inspections",
      "Use Filters to narrow inspection records. Open an inspection and review its findings before approving it.",
    ],
    [
      "Checklists",
      "Uploading saves a form in Mandi. Deploy publishes it to KoBo. Sync retrieves submitted responses. Open a checklist to browse its submissions.",
    ],
    [
      "Coverage",
      "Coverage counts distinct establishments separately from inspection visits. Use filters to choose the scope of the report.",
    ],
  ];
  return (
    <AppDialog
      title={t("Using Mandi")}
      description={t("Available actions depend on your account permissions.")}
      trigger={
        <Button variant="ghost" size="icon" aria-label={t("Help")} title={t("Help")}>
          <CircleHelp className="size-4" />
        </Button>
      }
    >
      <div className="space-y-5">
        {sections.map(([title, description]) => (
          <section key={title} className="space-y-1">
            <h3 className="font-semibold">{t(title)}</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">{t(description)}</p>
          </section>
        ))}
      </div>
    </AppDialog>
  );
}
