import { useSearchParams } from "react-router";
import { positiveInteger } from "@/components/public/pagination-state";

/** List state belongs in the URL so opening a record does not lose the user's place. */
export function useListParams() {
  const [params, setParams] = useSearchParams();
  const update = (values: Record<string, string | number>, resetPage = true, replace = false) => {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        for (const [key, value] of Object.entries(values)) {
          if (value === "") next.delete(key);
          else next.set(key, String(value));
        }
        if (resetPage) next.set("page", "1");
        return next;
      },
      { replace },
    );
  };
  return {
    params,
    update,
    page: positiveInteger(params.get("page"), 1),
    setPage: (page: number) => update({ page }, false),
  };
}
