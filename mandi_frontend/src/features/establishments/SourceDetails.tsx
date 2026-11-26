import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { pharmacyTypeLabel } from "@/features/shared/labels";
import { apiUrl } from "@/lib/api";

export type SourceDetail = {
  name: string;
  application_id: string;
  notice?: string;
  via?: string;
  sections: {
    title: string;
    location?: { latitude: number; longitude: number };
    fields: { id?: string; label: string; value: unknown }[];
  }[];
};

const LocationMap = lazy(() => import("./LocationMap"));

export function DeferredMap({
  location,
  name,
  address,
}: {
  location: { latitude: number; longitude: number };
  name?: string;
  address?: string | null;
}) {
  const { t } = useTranslation();
  const container = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!container.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "150px" },
    );
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  if (
    !Number.isFinite(location.latitude) ||
    !Number.isFinite(location.longitude) ||
    Math.abs(location.latitude) > 90 ||
    Math.abs(location.longitude) > 180
  )
    return null;
  const placeholder = <p className="text-muted-foreground p-4 text-sm">{t("Loading map…")}</p>;
  return (
    <div ref={container} className="min-h-64">
      {visible ? (
        <Suspense fallback={placeholder}>
          <LocationMap {...location} name={name} address={address} />
        </Suspense>
      ) : (
        placeholder
      )}
    </div>
  );
}

/**
 * Source documents are proxied by Mandi: the server attaches the upstream
 * `X-API-KEY`, so the browser only ever receives a signed Mandi link.
 */
const DOCUMENT_LINK = /^sources\/[a-z0-9_-]+\/document\/\?/i;

function isDocumentLink(value: string) {
  return DOCUMENT_LINK.test(value) || /^https?:\/\//i.test(value);
}

function label(key: string) {
  const mapped: Record<string, string> = {
    name_fa: "Dari name",
    name_en: "English name",
    name_ps: "Pashto name",
    "land mark": "Landmark",
    "land mark fa": "Landmark",
    "village name": "Village",
    "village name fa": "Village",
    "neighborhood fa": "Neighborhood",
    "house number": "House number",
    not_precise_address: "Address",
  };
  if (mapped[key]) return mapped[key];
  const words = key.replaceAll("_", " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}
export function SourceValue({ value }: { value: unknown }) {
  const { t, i18n } = useTranslation();
  if (value === null || value === undefined || value === "")
    return <span className="text-muted-foreground">—</span>;
  if (typeof value === "boolean") return <span>{t(value ? "Yes" : "No")}</span>;
  if (Array.isArray(value))
    return value.length ? (
      <div className="space-y-4">
        {value.map((item, i) => (
          <div key={i} className="flex gap-3">
            <span className="text-muted-foreground mt-0.5 text-xs tabular-nums">{i + 1}.</span>
            <div className="min-w-0 flex-1">
              <SourceValue value={item} />
            </div>
          </div>
        ))}
      </div>
    ) : (
      <span>—</span>
    );
  if (typeof value === "object" && !Array.isArray(value)) {
    const names = value as Record<string, unknown>;
    if (
      ["name_fa", "name_en", "name_ps"].some((key) => typeof names[key] === "string" && names[key])
    ) {
      const locale = (i18n.resolvedLanguage || i18n.language || "en").split("-")[0];
      const preferred = names[`name_${locale}`] || names.name_fa || names.name_en || names.name_ps;
      return <span dir="auto">{String(preferred)}</span>;
    }
  }
  if (typeof value === "object")
    return (
      <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
        {Object.entries(value)
          .filter(
            ([key, item]) =>
              !["id", "upload_id", "code", "long_lat"].includes(key) &&
              item !== null &&
              item !== "",
          )
          .map(([key, item]) => (
            <div
              key={key}
              className={typeof item === "object" ? "min-w-0 sm:col-span-2" : "min-w-0"}
            >
              <dt className="text-muted-foreground text-sm">{t(label(key))}</dt>
              <dd className="mt-1 text-base break-words whitespace-pre-wrap">
                <SourceValue value={item} />
              </dd>
            </div>
          ))}
      </dl>
    );
  const text = String(value);
  const statuses: Record<string, string> = {
    ongoing: "Ongoing",
    completed: "Completed",
    active: "Active",
    inactive: "Inactive",
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
    new: "New",
    renewal: "Renewal",
    re_register: "Re-registration",
    new_company: "New company",
    register: "Register",
    renew: "Renewal",
    morning: "Morning",
    evening: "Evening",
    night: "Night",
    day: "Day",
    bachelor: "Bachelor",
    bachelor_degree: "Bachelor's degree",
    master: "Master",
    master_degree: "Master's degree",
    pharmacy: "Pharmacy",
    factory: "Factory",
    wholesale: "Wholesaler",
    wholesaler: "Wholesaler",
    company: "Importer",
    yes: "Yes",
    no: "No",
  };
  if (isDocumentLink(text))
    return (
      <a
        className="text-link break-all"
        href={apiUrl(text)}
        target="_blank"
        rel="noopener noreferrer"
      >
        {t("Open document")}
      </a>
    );
  // Upstream sends machine codes such as `new_factory`; show them as words.
  const display = statuses[text]
    ? t(statuses[text])
    : /^[a-z][a-z0-9]*(_[a-z0-9]+)+$/.test(text)
      ? t(text.charAt(0).toUpperCase() + text.replaceAll("_", " ").slice(1))
      : text;
  return (
    <span dir="auto" className="break-words whitespace-pre-wrap">
      {display}
    </span>
  );
}
function SectionFields({
  section,
  showLocationMap,
}: {
  section: SourceDetail["sections"][number];
  showLocationMap: boolean;
}) {
  const { t } = useTranslation();
  return (
    <>
      <dl className="grid min-w-0 gap-x-8 gap-y-6 sm:grid-cols-2">
        {section.fields.map((field, i) => {
          const nested = typeof field.value === "object" && field.value !== null;
          return (
            <div key={i} className={nested ? "min-w-0 sm:col-span-2" : "min-w-0"}>
              <dt
                className={
                  nested
                    ? "mb-2 text-sm font-semibold"
                    : "text-muted-foreground mb-1 text-sm"
                }
              >
                {t(field.label)}
              </dt>
              <dd className="text-base leading-relaxed">
                <SourceValue
                  value={
                    field.label === "Pharmacy type"
                      ? pharmacyTypeLabel(field.value as string | number | null) || field.value
                      : field.value
                  }
                />
              </dd>
            </div>
          );
        })}
      </dl>
      {section.location && showLocationMap && (
        <div className="mt-5">
          <DeferredMap location={section.location} />
        </div>
      )}
    </>
  );
}

export default function SourceDetails({
  data,
  stacked = false,
  showLocationMap = true,
}: {
  data: SourceDetail;
  stacked?: boolean;
  showLocationMap?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-5">
      {data.notice && <p className="text-muted-foreground text-sm">{t(data.notice)}</p>}
      {!!data.sections.length &&
        (stacked ? (
          <div className="divide-border divide-y">
            {data.sections.map((section, index) => (
              <section key={index} className="space-y-4 py-5 first:pt-0 last:pb-0">
                <h3 className="text-lg font-semibold">{t(section.title)}</h3>
                <SectionFields section={section} showLocationMap={showLocationMap} />
              </section>
            ))}
          </div>
        ) : (
          <Tabs key={data.application_id} defaultValue="section-0">
            <TabsList aria-label={t("Source details")}>
              {data.sections.map((section, index) => (
                <TabsTrigger key={index} value={`section-${index}`}>
                  {t(section.title)}
                </TabsTrigger>
              ))}
            </TabsList>
            {data.sections.map((section, index) => (
              <TabsContent key={index} value={`section-${index}`} className="space-y-4 pt-4">
                <h3 className="text-lg font-semibold">{t(section.title)}</h3>
                <SectionFields section={section} showLocationMap={showLocationMap} />
              </TabsContent>
            ))}
          </Tabs>
        ))}
      {!data.sections.length && !data.notice && (
        <p className="text-muted-foreground">{t("No details returned by this source.")}</p>
      )}
    </div>
  );
}
