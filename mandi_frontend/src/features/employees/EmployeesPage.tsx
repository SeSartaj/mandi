import { useState } from "react";
import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { AppDialog } from "@/components/public/AppDialog";
import { AppErrorState } from "@/components/public/AppErrorState";
import { AppLoader } from "@/components/public/AppLoader";
import AppTable from "@/components/public/AppTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import EmployeeForm from "@/features/employees/EmployeeForm";
import { useApiQuery } from "@/features/shared/api";
import { pageCount } from "@/features/shared/labels";
import { useTablePageSize } from "@/hooks/useTablePageSize";
import type { Employee, Page } from "@/lib/api";
import { errorMessage } from "@/lib/api";

export default function EmployeesPage() {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTablePageSize();
  const [open, setOpen] = useState(false);
  const data = useApiQuery<Page<Employee>>(["employees"], "/employees/", {
    page,
    page_size: pageSize,
  });

  const rows = data.data?.results ?? [];
  const count = data.data?.count ?? 0;

  return (
    <div className="space-y-6">
      <PageSection
        title={t("Employees")}
        description={t("Employee directory")}
        actions={
          <Can permission="accounts.add_user">
            <Button onClick={() => setOpen(true)}>
              <Plus />
              {t("Add employee")}
            </Button>
          </Can>
        }
      >
        {data.isPending ? (
          <AppLoader label={t("Loading…")} className="py-10" />
        ) : data.error ? (
          <AppErrorState message={errorMessage(data.error)} onRetry={() => data.refetch()} />
        ) : (
          <AppTable
            className="min-w-[720px]"
            pagination={{
              page,
              pageSize,
              totalPages: pageCount(count, pageSize),
              totalItems: count,
              onPageChange: setPage,
              onPageSizeChange: (size) => {
                setPageSize(size);
                setPage(1);
              },
            }}
          >
            <TableHeader>
              <TableRow>
                <TableHead>{t("Full name")}</TableHead>
                <TableHead>{t("Username")}</TableHead>
                <TableHead>{t("Position")}</TableHead>
                <TableHead>{t("Status")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((employee) => (
                <TableRow key={employee.id}>
                  <TableCell>{employee.display_name || employee.username}</TableCell>
                  <TableCell>{employee.username}</TableCell>
                  <TableCell>{employee.position || "—"}</TableCell>
                  <TableCell>
                    <Badge variant={employee.is_active ? "default" : "secondary"}>
                      {t(employee.is_active ? "Active" : "Inactive")}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-muted-foreground py-8 text-center">
                    {t("No records found.")}
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </AppTable>
        )}
      </PageSection>

      <AppDialog
        open={open}
        onOpenChange={setOpen}
        title={t("Add employee")}
        size="md"
        contentClassName="max-h-[90vh] overflow-y-auto"
      >
        <EmployeeForm onClose={() => setOpen(false)} />
      </AppDialog>
    </div>
  );
}
