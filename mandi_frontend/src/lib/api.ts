import axios from "axios";
import i18next from "i18next";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
});
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("mandi-token");
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const token = sessionStorage.getItem("mandi-token");
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      token &&
      error.config?.headers.Authorization === `Token ${token}`
    ) {
      sessionStorage.removeItem("mandi-token");
      window.dispatchEvent(new Event("mandi-session-expired"));
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response)
      return i18next.t("Cannot reach Mandi. Check your connection and try again.");
    if (error.response.status >= 500)
      return i18next.t("Mandi is temporarily unavailable. Please try again shortly.");
    if (error.response.status === 404)
      return i18next.t("This record could not be found. It may have been removed.");
    const data = error.response.data;
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data === "string") return data;
    if (Array.isArray(data)) {
      const messages = data.filter((item) => typeof item === "string");
      if (messages.length) return messages.join(" · ");
    }
    if (data && typeof data === "object" && !Array.isArray(data)) {
      const messages = Object.entries(data).flatMap(([key, value]) => {
        const items = Array.isArray(value) ? value : [value];
        const text = items.filter((item) => typeof item === "string").join(", ");
        if (!text) return [];
        return key === "non_field_errors"
          ? [text]
          : [`${i18next.t(key.replaceAll("_", " "))}: ${text}`];
      });
      if (messages.length) return messages.join(" · ");
    }
  }
  return i18next.t("Something went wrong. Please try again.");
}

export function fileUrl(path: string | null | undefined): string {
  if (!path) return "";
  try {
    return new URL(path, new URL(api.defaults.baseURL ?? "/", window.location.origin)).toString();
  } catch {
    return path;
  }
}
export type Employee = {
  id: number;
  username: string;
  display_name: string;
  position: string;
  is_active: boolean;
  is_staff: boolean;
  groups: number[];
  restrict_checklist_access: boolean;
  allowed_checklists: number[];
};
export type Session = { user: Employee; permissions: string[] };
export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export type Establishment = {
  id: string;
  name: string;
  kind: string;
  subtype: string;
  province: string;
  district: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  phone: string;
  source_links: SourceLink[];
  primary_source?: string | null;
  attributes?: Record<string, unknown>;
  license_number?: string;
  status?: string;
};
export type SourceLink = {
  id: number;
  source: string;
  external_id: string;
  details: Record<string, unknown>;
  is_demo: boolean;
  linked_at: string;
  is_primary?: boolean;
  last_synced_at?: string | null;
};
export type Inspection = {
  id: number;
  establishment_id: string;
  establishment_name: string;
  establishment_snapshot?: Record<string, unknown>;
  inspected_on: string;
  kind: string;
  checklist: { id: number; name: string; version: string };
  team: Employee[];
  provider: string;
  submission_id: string;
  mapping_version: string;
  summary: {
    overall_percent?: number;
    sections?: { name: string; earned: number; possible: number }[];
    findings?: { issue: string; action: string; deadline: string }[];
  };
  approved: boolean;
  approved_by: Employee | null;
  approved_at: string | null;
  is_demo: boolean;
};
export type Coverage = {
  establishments: number;
  inspected: number;
  uninspected: number;
  visits: number;
  approved: number;
  unapproved: number;
  coverage_percent: number;
};
export type Checklist = {
  id: number;
  code: string;
  name: string;
  version: string;
  establishment_kind: string;
  xlsform: string | null;
  collection: {
    provider: string;
    form_id: string;
    status: "not_deployed" | "deploying" | "deployed" | "failed";
    error: string;
    deployed_at: string | null;
    url: string | null;
  };
  kobo_asset_uid: string;
  kobo_project_url?: string | null;
  kobo_deployment_status: "not_deployed" | "deploying" | "deployed" | "failed";
  kobo_deployment_error: string;
  kobo_deployed_at: string | null;
  submission_count?: number;
  created_at: string;
  updated_at: string;
};
export type KoboScoreSection = {
  key: string;
  label: string;
  score: number;
  max: number | null;
  percent: number | null;
};
export type KoboSubmissionScores = {
  sections: KoboScoreSection[];
  score: number | null;
  max: number | null;
  percent: number | null;
};
export type KoboAnswerMedia = {
  index: number;
  filename: string;
  mimetype: string;
  kind: KoboMediaKind;
  url: string | null;
};
export type KoboMediaKind = "image" | "audio" | "video" | "pdf" | "file";
export type KoboAttachment = {
  index: number;
  filename: string;
  basename: string;
  mimetype: string;
  kind: KoboMediaKind;
  url: string;
};
export type KoboAnswer = {
  name: string;
  label: string;
  value: unknown;
  display: string;
  type: string;
  group: string;
  media: KoboAnswerMedia[];
};
export type KoboSubmission = {
  id: number;
  asset_uid: string;
  submission_id: string;
  establishment_id: string;
  establishment_name: string | null;
  checklist_id: number | null;
  checklist_name: string | null;
  checklist_version: string | null;
  submitted_at: string | null;
  scores: KoboSubmissionScores;
  answers: KoboAnswer[];
  attachments: KoboAttachment[];
  kobo_url: string | null;
  data: Record<string, unknown>;
};
