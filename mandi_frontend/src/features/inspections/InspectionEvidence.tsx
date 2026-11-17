import { SourceValue } from "@/features/establishments/SourceDetails";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Can } from "@/components/Can";
import { PageSection } from "@/components/PageSection";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/features/shared/api";
import { api, errorMessage, type Establishment, type Inspection } from "@/lib/api";

type Field = { id: string; label: string; value: unknown; section?: string };
type Evidence = {
  id: number;
  source: string;
  external_id: string;
  fields: Field[];
  captured_at: string;
};
function EvidenceCapture({ inspection, source }: { inspection: Inspection; source: string }) {
  const [selected, setSelected] = useState<string[]>([]);
  const client = useQueryClient();
  const detail = useApiQuery<{ sections: { title: string; fields: Field[] }[] }>(
    ["evidence-source", inspection.id, source],
    `/establishments/${inspection.establishment_id}/sources/${source}/?purpose=evidence`,
  );
  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/inspections/${inspection.id}/evidence/`, { source, selected_fields: selected }),
    onSuccess: () => {
      setSelected([]);
      client.invalidateQueries();
    },
  });
  return (
    <div className="space-y-3 rounded border p-3">
      <strong>{source}</strong>
      {detail.isPending && <p>Loading current source details…</p>}
      {detail.error && <p role="alert">{errorMessage(detail.error)}</p>}
      {detail.data?.sections.map((section, i) => (
        <fieldset key={i} className="space-y-2">
          <legend>{section.title}</legend>
          {section.fields.map((field, j) => (
            <label key={j} className="flex gap-2 text-sm">
              <input
                type="checkbox"
                checked={selected.includes(field.id)}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, field.id]
                      : selected.filter((key) => key !== field.id),
                  )
                }
              />
              <span>
                {field.label}: <SourceValue value={field.value} />
              </span>
            </label>
          ))}
        </fieldset>
      ))}
      {mutation.error && <p role="alert">{errorMessage(mutation.error)}</p>}
      <Button
        disabled={!selected.length || mutation.isPending || detail.isFetching}
        onClick={() => mutation.mutate()}
      >
        Save selected evidence
      </Button>
    </div>
  );
}
export default function InspectionEvidence({ inspection }: { inspection: Inspection }) {
  const [capturing, setCapturing] = useState(false);
  const evidence = useApiQuery<Evidence[]>(
    ["inspection-evidence", inspection.id],
    `/inspections/${inspection.id}/evidence/`,
  );
  const establishment = useApiQuery<Establishment>(
    ["evidence-establishment", inspection.establishment_id],
    `/establishments/${inspection.establishment_id}/`,
    {},
    { enabled: capturing },
  );
  return (
    <PageSection title="Historical identity and evidence" contentClassName="space-y-4 pt-4">
      <p className="text-muted-foreground text-sm">
        Identity was captured when Mandi first received this inspection. Source evidence records the
        time it was fetched. Adding evidence clears approval for review.
      </p>
      {inspection.establishment_snapshot &&
      Object.keys(inspection.establishment_snapshot).length > 0 ? (
        <dl className="info-grid">
          {["name", "kind", "province", "district", "address", "license_number", "captured_at"].map(
            (key) => (
              <div key={key}>
                <dt>{key.replaceAll("_", " ")}</dt>
                <dd>{String(inspection.establishment_snapshot?.[key] || "—")}</dd>
              </div>
            ),
          )}
        </dl>
      ) : (
        <p>No historical identity was captured for this earlier inspection.</p>
      )}
      {evidence.error && <p role="alert">{errorMessage(evidence.error)}</p>}
      {evidence.data?.map((item) => (
        <div key={item.id} className="rounded border p-3">
          <p>
            {item.source} · {item.external_id} · {new Date(item.captured_at).toLocaleString()}
          </p>
          <dl>
            {item.fields.map((field, i) => (
              <div key={i} className="text-sm">
                <dt>
                  {field.section} · {field.label}
                </dt>
                <dd>
                  <SourceValue value={field.value} />
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
      <Can permission="inspections.change_inspection">
        <Can permission="establishments.view_sourcelink">
          <Button variant="secondary" onClick={() => setCapturing(!capturing)}>
            {capturing ? "Close source selection" : "Capture current source evidence"}
          </Button>
          {capturing && establishment.error && (
            <p role="alert">{errorMessage(establishment.error)}</p>
          )}
          {capturing &&
            establishment.data?.source_links.map((link) => (
              <EvidenceCapture key={link.source} inspection={inspection} source={link.source} />
            ))}
          {capturing && establishment.data?.source_links.length === 0 && (
            <p>Connect a source on the establishment first.</p>
          )}
        </Can>
      </Can>
    </PageSection>
  );
}
