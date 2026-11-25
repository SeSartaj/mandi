import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Can } from "@/components/Can";
import { Button } from "@/components/ui/button";
import { api, errorMessage, type Establishment } from "@/lib/api";
import { notify } from "@/lib/notify";

export default function RegistryOwnership({ establishment }: { establishment: Establishment }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ action, source }: { action: string; source?: string | null }) =>
      api.post(
        `/establishments/${establishment.id}/${action}/`,
        action === "ownership" ? { source } : {},
      ),
    onSuccess: (_data, variables) => {
      notify.success(
        variables.action === "refresh"
          ? t("{{entity}} refreshed.", { entity: t("Registry identity") })
          : t("Registry ownership updated."),
      );
      client.invalidateQueries();
    },
    onError: (error) =>
      notify.error(t("Could not complete the action."), {
        description: errorMessage(error),
      }),
  });
  return (
    <div className="space-y-4">
      <p className="text-sm">
        {t("Identity managed by:")}{" "}
        <strong dir="auto">
          {establishment.primary_source === "licensing"
            ? "Licensing"
            : establishment.primary_source || "Mandi"}
        </strong>
      </p>
      <Can permission="establishments.change_establishment">
        <div className="flex flex-wrap gap-2">
          {establishment.primary_source && (
            <Button
              disabled={mutation.isPending}
              onClick={() => mutation.mutate({ action: "refresh" })}
            >
              {t("Refresh registry identity")}
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
                      t(
                        "Transfer identity ownership to Mandi? Local identity fields will become editable.",
                      ),
                    )
                  )
                    mutation.mutate({ action: "ownership", source: null });
                }}
              >
                {t("Transfer ownership to Mandi")}
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
                        t(
                          "Make {{source}} the primary registry? Its identity will replace local identity fields.",
                          { source: link.source },
                        ),
                      )
                    )
                      mutation.mutate({ action: "ownership", source: link.source });
                  }}
                >
                  {t("Use {{source}} as primary registry", { source: link.source })}
                </Button>
              ))
            )}
          </Can>
        </div>
      </Can>
      {mutation.error && <p role="alert">{errorMessage(mutation.error)}</p>}
    </div>
  );
}
