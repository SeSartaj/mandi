import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { Can } from "@/components/Can";
import { AppDialog } from "@/components/public/AppDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/features/shared/api";
import { api, errorMessage, type Establishment } from "@/lib/api";
import { useRegistryCatalog } from "./registry";

type Candidate = { id: string; name: string; details: { province?: string } };
export default function RegistryImport() {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("registration");
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
      client.invalidateQueries();
      setOpen(false);
      navigate(`/establishments/${data.id}`);
    },
  });
  return (
    <Can permission="establishments.change_sourcelink">
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Import from registry
      </Button>
      <AppDialog
        open={open}
        onOpenChange={setOpen}
        title="Import establishment"
        description="Import a local identity linked to its primary registry. Reimporting the same external ID returns the existing establishment."
      >
        <div className="space-y-4">
          <label className="block">
            Source system
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
            Type
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
              aria-label="Search registry"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search registry"
            />
            <Button type="submit">Search</Button>
          </form>
          {candidates.isFetching && <p>Loading registry…</p>}
          {candidates.error && <p role="alert">{errorMessage(candidates.error)}</p>}
          {mutation.error && <p role="alert">{errorMessage(mutation.error)}</p>}
          {candidates.data?.results.map((item) => (
            <div className="flex items-center justify-between gap-3 border-b py-2" key={item.id}>
              <span>
                {item.name} · {item.details.province || "Unknown province"}
                <small className="block">
                  {item.id}
                </small>
              </span>
              <Button
                disabled={mutation.isPending || candidates.isFetching}
                onClick={() => mutation.mutate(item.id)}
              >
                Import
              </Button>
            </div>
          ))}
          {candidates.data?.results.length === 0 && <p>No matching records.</p>}
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={page === 1 || candidates.isFetching}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={!candidates.data?.has_next || candidates.isFetching}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </AppDialog>
    </Can>
  );
}
