import { FileText, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useMediaUrl } from "@/features/checklists/useMediaUrl";
import { mediaIconKind } from "@/features/checklists/useMediaUrl";
import type { KoboMediaKind } from "@/lib/api";

type SubmissionMediaProps = {
  url: string | null;
  kind: KoboMediaKind | string;
  filename?: string;
  mimetype?: string;
  compact?: boolean;
};

/** Renders one KoBo upload: images inline, audio/video players, files as links. */
export function SubmissionMedia({
  url,
  kind,
  filename,
  mimetype,
  compact = false,
}: SubmissionMediaProps) {
  const { t } = useTranslation();
  const needsAudioConversion = Boolean(
    filename?.toLowerCase().endsWith(".amr") || mimetype?.toLowerCase().startsWith("audio/amr"),
  );
  const playbackUrl =
    url && needsAudioConversion ? `${url}${url.includes("?") ? "&" : "?"}playback=1` : url;
  const media = useMediaUrl(playbackUrl);
  const resolved = needsAudioConversion ? "audio" : mediaIconKind(kind);

  if (!url) {
    return <span className="text-muted-foreground">—</span>;
  }
  if (media.isPending) {
    return (
      <span className="text-muted-foreground inline-flex items-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin" />
        {t("Loading file…")}
      </span>
    );
  }
  if (media.error || !media.data) {
    return (
      <span className="text-destructive inline-flex items-center gap-2 text-sm">
        <FileText className="size-4" />
        {t("File unavailable")}
      </span>
    );
  }

  const label = filename ?? t("Open file");

  if (resolved === "image") {
    return (
      <a href={media.data} target="_blank" rel="noreferrer" title={label}>
        <img
          src={media.data}
          alt={label}
          className={
            compact
              ? "border-border size-14 rounded border object-cover"
              : "border-border max-h-72 rounded-md border object-contain"
          }
        />
      </a>
    );
  }

  if (resolved === "audio") {
    return <audio controls src={media.data} className="w-full max-w-md" />;
  }

  if (resolved === "video") {
    return <video controls src={media.data} className="border-border max-h-72 rounded-md border" />;
  }

  return (
    <a
      className="text-link inline-flex items-center gap-2"
      href={media.data}
      target="_blank"
      rel="noreferrer"
    >
      <FileText className="size-4" />
      {label}
      {mimetype ? <small className="muted">({mimetype})</small> : null}
    </a>
  );
}
