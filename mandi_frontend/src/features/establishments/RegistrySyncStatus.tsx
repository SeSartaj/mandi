import { useApiQuery } from "@/features/shared/api";
import { errorMessage } from "@/lib/api";

type SyncStatus = {
  enabled: boolean;
  interval: number;
  states: {
    source_id: string;
    kind_id: string;
    next_page: number;
    last_success_at: string | null;
    last_error: string;
    counts: Record<string, number>;
  }[];
};
export default function RegistrySyncStatus() {
  const query = useApiQuery<SyncStatus>(["registry-sync-status"], "/registry/sync/");
  if (query.error) return <p role="alert">{errorMessage(query.error)}</p>;
  if (!query.data) return null;
  return (
    <details className="rounded border p-3 text-sm">
      <summary>Automatic registration sync: {query.data.enabled ? "enabled" : "disabled"}</summary>
      <p className="text-muted-foreground my-2">
        One page per category, with {query.data.interval} seconds between batches. Existing mappings
        prevent duplicate imports. Only primary registry identities are refreshed.
      </p>
      {query.data.states.length === 0 && <p>No sync attempt recorded yet.</p>}
      {query.data.states.map((state) => (
        <p key={`${state.source_id}:${state.kind_id}`} className="my-2">
          <strong>
            {state.source_id} · {state.kind_id}
          </strong>
          :{" "}
          {state.last_error ||
            (state.last_success_at
              ? `Last page synced ${new Date(state.last_success_at).toLocaleString()}`
              : "Waiting")}
          <span className="text-muted-foreground block">
            Next page {state.next_page} ·{" "}
            {Object.entries(state.counts)
              .map(([key, value]) => `${key}: ${value}`)
              .join(" · ")}
          </span>
        </p>
      ))}
      <button className="text-link" onClick={() => query.refetch()} disabled={query.isFetching}>
        Refresh sync status
      </button>
    </details>
  );
}
