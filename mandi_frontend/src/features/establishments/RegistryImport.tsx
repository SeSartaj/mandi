import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { Can } from "@/components/Can";
import { AppDialog } from "@/components/public/AppDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/features/shared/api";
import { api, errorMessage, type Establishment } from "@/lib/api";
import { notify } from "@/lib/notify";
import { useRegistryCatalog } from "./registry";

type Candidate = { id: string; name: string; details: { province?: string } };
export default function RegistryImport() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("licensing");
  const [kind, setKind] = useState("pharmacy");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const catalog = useRegistryCatalog();
  const client = useQueryClient();
  const navigate = useNavigate();
  const candidates = useApiQuery<{ results: Candidate[]; has_next: boolean }>(
    ["registry-import", source],
    `/sources/${source}/`,
    { kind, search: query, page },
    { enabled: open },
  );
  const mutation = useMutation({
    mutationFn: async (external_id: string) =>
      (await api.post<Establishment>("/registry/import/", { source, kind, external_id })).data,
    onSuccess: (data) => {
      notify.success(t("{{entity}} imported.", { entity: t("Establishment") }));
      client.invalidateQueries();
      setOpen(false);
      navigate(`/establishments/${data.id}`);
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });
  return (
    <Can permission="establishments.change_sourcelink">
      <Button variant="secondary" onClick={() => setOpen(true)}>
        {t("Import from registry")}
      </Button>
      <AppDialog
        open={open}
        onOpenChange={setOpen}
        title={t("Import establishment")}
        description={t(
          "Import a local identity linked to its primary registry. Reimporting the same external ID returns the existing establishment.",
        )}
      >
        <div className="space-y-4">
          <label className="block">
            {t("Source system")}
            <select
              className="block w-full rounded border p-2"
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                setPage(1);
                mutation.reset();
              }}
            >
              {catalog.data?.systems
                .filter((item) => item.searchable !== false)
                .map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.name}
                  </option>
                ))}
            </select>
          </label>
          <label className="block">
            {t("Type")}
            <select
              className="block w-full rounded border p-2"
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                setPage(1);
                mutation.reset();
              }}
            >
              {catalog.data?.types.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setQuery(search);
              setPage(1);
            }}
          >
            <Input
              aria-label={t("Search registry")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("Search registry")}
            />
            <Button type="submit">{t("Search")}</Button>
          </form>
          {candidates.isFetching && <p>{t("Loading registry…")}</p>}
          {candidates.error && <p role="alert">{errorMessage(candidates.error)}</p>}
          {mutation.error && <p role="alert">{errorMessage(mutation.error)}</p>}
          {candidates.data?.results.map((item) => (
            <div className="flex items-center justify-between gap-3 border-b py-2" key={item.id}>
              <span>
                {item.name} · {item.details.province || t("Unknown province")}
                <small className="block">
                  {item.id}
                </small>
              </span>
              <Button
                disabled={mutation.isPending || candidates.isFetching}
                onClick={() => mutation.mutate(item.id)}
              >
                {t("Import")}
              </Button>
            </div>
          ))}
          {candidates.data?.results.length === 0 && <p>{t("No matching records.")}</p>}
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={page === 1 || candidates.isFetching}
              onClick={() => setPage(page - 1)}
            >
              {t("Previous")}
            </Button>
            <Button
              variant="outline"
              disabled={!candidates.data?.has_next || candidates.isFetching}
              onClick={() => setPage(page + 1)}
            >
              {t("Next")}
            </Button>
          </div>
        </div>
      </AppDialog>
    </Can>
  );
}
