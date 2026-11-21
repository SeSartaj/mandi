import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Can } from "@/components/Can";
import { Button } from "@/components/ui/button";
import { api, errorMessage, type Establishment } from "@/lib/api";

export default function RegistryOwnership({ establishment }: { establishment: Establishment }) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ action, source }: { action: string; source?: string | null }) =>
      api.post(
        `/establishments/${establishment.id}/${action}/`,
        action === "ownership" ? { source } : {},
      ),
    onSuccess: () => {
      client.invalidateQueries();
    },
  });
  return (
    <div className="space-y-3 rounded border p-4">
      <p>
        Identity managed by:{" "}
        <strong>
          {establishment.primary_source === "registration"
            ? "Licensing"
            : establishment.primary_source || "Mandi"}
        </strong>
      </p>
      <Can permission="establishments.change_establishment">
        {establishment.primary_source && (
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ action: "refresh" })}
          >
            Refresh registry identity
          </Button>
        )}
        <Can permission="establishments.change_sourcelink">
          {establishment.primary_source ? (
            <Button
              variant="secondary"
              disabled={mutation.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    "Transfer identity ownership to Mandi? Local identity fields will become editable.",
                  )
                )
                  mutation.mutate({ action: "ownership", source: null });
              }}
            >
              Transfer ownership to Mandi
            </Button>
          ) : (
            establishment.source_links.map((link) => (
              <Button
                key={link.source}
                variant="secondary"
                disabled={mutation.isPending}
                onClick={() => {
                  if (
                    window.confirm(
                      `Make ${link.source} the primary registry? Its identity will replace local identity fields.`,
                    )
                  )
                    mutation.mutate({ action: "ownership", source: link.source });
                }}
              >
                Use {link.source} as primary registry
              </Button>
            ))
          )}
        </Can>
      </Can>
      {mutation.error && <p role="alert">{errorMessage(mutation.error)}</p>}
      {establishment.primary_source && (
        <p className="text-muted-foreground text-sm">
          The local identity remains available during registry outages. Refresh requires the
          registry to be online.
        </p>
      )}
    </div>
  );
}
