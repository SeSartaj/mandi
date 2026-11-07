import { Check, ClipboardCheck } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import AppTable from "@/components/public/AppTable";
import { SystemDateTime } from "@/components/public/SystemDateTime";
import { Badge } from "@/components/ui/badge";
import { TableCell } from "@/components/ui/table";
import { choiceLabel } from "@/features/shared/labels";
import type { Inspection } from "@/lib/api";

export function InspectionStatus({ approved }: { approved: boolean }) {
  const { t } = useTranslation();
  return (
    <Badge variant={approved ? "default" : "secondary"}>
      {approved ? <Check size={12} /> : null} {t(approved ? "Approved" : "Unapproved")}
    </Badge>
  );
}

type InspectionTableProps = {
  rows: Inspection[];
  loading?: boolean;
  page?: number;
  pageSize: number;
  totalItems?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  title?: string;
  description?: string;
  headerAction?: ReactNode;
  emptyMessage?: string;
};

/** Copied CMS AppTable in data mode, bound to Mandi inspection fields. */
export default function InspectionTable({
  rows,
  loading = false,
  page = 1,
  pageSize,
  totalItems,
  totalPages,
  onPageChange,
  onPageSizeChange,
  title,
  description,
  headerAction,
  emptyMessage,
}: InspectionTableProps) {
  const { t } = useTranslation();
  return (
    <AppTable
      title={title ?? t("Inspections")}
      description={description}
      headerAction={headerAction}
      titleIcon={<ClipboardCheck className="size-5" />}
      headers={[
        { id: "establishment", label: t("Establishments") },
        { id: "date", label: t("Date") },
        { id: "kind", label: t("Type") },
        { id: "team", label: t("Team") },
        { id: "status", label: t("Status") },
        { id: "details", label: t("Details") },
      ]}
      data={rows}
      loading={loading}
      emptyMessage={emptyMessage ?? t("No inspections in this selection.")}
      keyExtractor={(inspection) => inspection.id}
      renderRow={(inspection) => (
        <>
          <TableCell>
            <Link className="entity-link" to={`/inspections/${inspection.id}`}>
              {inspection.establishment_name}
            </Link>
            {inspection.is_demo ? (
              <small className="table-subtitle">{t("Demonstration data")}</small>
            ) : null}
          </TableCell>
          <TableCell className="nowrap" dir="ltr">
            <SystemDateTime value={inspection.inspected_on} />
          </TableCell>
          <TableCell>{t(choiceLabel(inspection.kind))}</TableCell>
          <TableCell>
            {inspection.team.map((member) => member.display_name || member.username).join(", ")}
          </TableCell>
          <TableCell>
            <InspectionStatus approved={inspection.approved} />
          </TableCell>
          <TableCell>
            <Link to={`/inspections/${inspection.id}`} className="text-link">
              {t("View")}
            </Link>
          </TableCell>
        </>
      )}
      pagination={
        onPageChange
          ? {
              page,
              pageSize,
              totalPages: totalPages ?? 1,
              totalItems: totalItems ?? rows.length,
              onPageChange,
              onPageSizeChange: onPageSizeChange ?? (() => undefined),
            }
          : undefined
      }
    />
  );
}
