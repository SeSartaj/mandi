import * as React from "react";

import AppTable from "@/components/public/AppTable";

type DataTableProps = React.ComponentProps<typeof AppTable>;

/**
 * Shared table surface with responsive horizontal scrolling and wrapped cells.
 * Use the regular table primitives inside it for headers, rows, and cells.
 */
function DataTable({ className, ...props }: DataTableProps) {
  return <AppTable className={className} {...props} />;
}

export { DataTable };
