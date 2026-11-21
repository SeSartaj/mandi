import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

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

export function DeferredMap({ location }: { location: { latitude: number; longitude: number } }) {
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
          <LocationMap {...location} />
        </Suspense>
      ) : (
        placeholder
      )}
    </div>
  );
}

function label(key: string) {
  return (
    (
      { name_fa: "Dari name", name_en: "English name", name_ps: "Pashto name" } as Record<
        string,
        string
      >
    )[key] || key.replaceAll("_", " ")
  );
}
export function SourceValue({ value }: { value: unknown }) {
  const { t, i18n } = useTranslation();
  if (value === null || value === undefined || value === "")
    return <span className="text-muted-foreground">—</span>;
  if (typeof value === "boolean") return <span>{t(value ? "Yes" : "No")}</span>;
  if (Array.isArray(value))
    return value.length ? (
      <div className="space-y-3">
        {value.map((item, i) => (
          <div key={i} className="rounded border p-3">
            <SourceValue value={item} />
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
              <dt className="text-muted-foreground text-xs capitalize">{t(label(key))}</dt>
              <dd className="mt-1 break-words whitespace-pre-wrap">
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
    morning: "Morning",
    evening: "Evening",
    night: "Night",
    bachelor: "Bachelor",
    master: "Master",
    pharmacy: "Pharmacy",
    factory: "Factory",
    wholesale: "Wholesaler",
    company: "Importer",
  };
  if (/^https?:\/\//i.test(text))
    return (
      <a className="text-link break-all" href={text} target="_blank" rel="noopener noreferrer">
        {t("Open document")}
      </a>
    );
  return (
    <span dir="auto" className="break-words whitespace-pre-wrap">
      {statuses[text] ? t(statuses[text]) : text}
    </span>
  );
}
function SectionFields({ section }: { section: SourceDetail["sections"][number] }) {
  const { t } = useTranslation();
  return (
    <>
      <dl className="grid min-w-0 gap-x-8 gap-y-5 sm:grid-cols-2">
        {section.fields.map((field, i) => (
          <div
            key={i}
            className={
              typeof field.value === "object" && field.value !== null
                ? "min-w-0 sm:col-span-2"
                : "min-w-0"
            }
          >
            <dt
              className={
                typeof field.value === "object" && field.value !== null
                  ? "mb-2 text-sm font-semibold"
                  : "text-muted-foreground mb-1 text-sm"
              }
            >
              {t(field.label)}
            </dt>
            <dd
              className={
                typeof field.value === "object" && field.value !== null
                  ? "bg-muted/10 rounded-lg border p-4 text-sm"
                  : "text-sm"
              }
            >
              <SourceValue value={field.value} />
            </dd>
          </div>
        ))}
      </dl>
      {section.location && <DeferredMap location={section.location} />}
    </>
  );
}

export default function SourceDetails({
  data,
  stacked = false,
}: {
  data: SourceDetail;
  stacked?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-5">
      {data.notice && <p className="text-muted-foreground text-sm">{t(data.notice)}</p>}
      {!!data.sections.length &&
        (stacked ? (
          <div className="space-y-6">
            {data.sections.map((section, index) => (
              <section key={index} className="space-y-3">
                <h3 className="font-semibold">{t(section.title)}</h3>
                <SectionFields section={section} />
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
              <TabsContent key={index} value={`section-${index}`} className="space-y-3 pt-3">
                <h3 className="font-semibold">{t(section.title)}</h3>
                <SectionFields section={section} />
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
