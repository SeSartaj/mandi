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

/** Resolve a path relative to the API root, e.g. a signed source-document link. */
export function apiUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const base = (api.defaults.baseURL || "/api/v1").replace(/\/$/, "");
  return `${base}/${path.replace(/^\//, "")}`;
}
export type Employee = {
  id: number;
  username: string;
  email: string;
  display_name: string;
  position: string;
  is_active: boolean;
  is_staff: boolean;
  groups: number[];
  restrict_checklist_access: boolean;
  allowed_checklists: number[];
};
export type EmployeeGroupInfo = {
  id: number;
  name: string;
  permissions: string[];
};
export type EmployeeChecklistInfo = {
  id: number;
  code: string;
  name: string;
};
export type EmployeeDetail = Employee & {
  is_superuser: boolean;
  date_joined: string;
  last_login: string | null;
  groups_info: EmployeeGroupInfo[];
  allowed_checklists_info: EmployeeChecklistInfo[];
};
export type GrantSummary = {
  grant_id: number;
  checklist_id: number;
  checklist_name: string;
};
export type CollectorCredential = {
  project_id: number;
  project_name?: string | null;
  remote_id: string;
  checklists: GrantSummary[];
};
export type NewCollectorCredential = CollectorCredential & {
  server_url: string;
  qr?: string;
  message?: string;
};
export type ProvisionResult = {
  credentials: NewCollectorCredential[];
  added: GrantSummary[];
  unchanged: GrantSummary[];
};
export type CollectionProject = {
  id: number;
  name: string;
  archived: boolean;
};
export type CollectionProjectDirectory = {
  available: boolean;
  projects: CollectionProject[];
  error: string;
};
export type Session = { user: Employee; permissions: string[] };
export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export type Establishment = {
  id: string;
  name: string;
  kind: string;
  province: string | null;
  province_name: string | null;
  province_name_local: string | null;
  district: string | null;
  district_name: string | null;
  district_name_local: string | null;
  address: string;
  latitude: number | null;
  longitude: number | null;
  source_links: SourceLink[];
  primary_source?: string | null;
  inspection_stats?: {
    total: number;
    this_year: number;
    last_submitted_at: string | null;
  };
  created_at: string;
  updated_at: string;
};
export type SourceLink = {
  id: number;
  source: string;
  external_id: string;
  details: Record<string, unknown>;
  linked_at: string;
  is_primary?: boolean;
  last_synced_at?: string | null;
};
export type EstablishmentType = {
  code: string;
  name: string;
  is_active: boolean;
};
export type ChecklistQuestion = {
  name: string;
  label: string;
  type: string;
  group: string;
  choices: { value: string; label: string }[];
};
export type SubmissionGroup = {
  checklist_id: number;
  checklist_name: string;
  count: number;
  last_submitted_at: string | null;
  submissions: Submission[];
};
export type OdkProject = {
  id: number;
  name: string;
  description: string;
  archived: boolean;
};
export type Checklist = {
  id: number;
  code: string;
  name: string;
  xlsform: string | null;
  collection: {
    provider: string;
    project_id: number | null;
    form_id: string;
    status: "not_deployed" | "deploying" | "deployed" | "failed";
    error: string;
    deployed_at: string | null;
    url: string | null;
  };
  submission_count?: number;
  created_at: string;
  updated_at: string;
};
export type SubmissionScoreSection = {
  key: string;
  label: string;
  score: number;
  max: number | null;
  percent: number | null;
};
export type SubmissionScores = {
  sections: SubmissionScoreSection[];
  score: number | null;
  max: number | null;
  percent: number | null;
};
export type SubmissionAnswerMedia = {
  index: number;
  filename: string;
  mimetype: string;
  kind: MediaKind;
  url: string | null;
};
export type MediaKind = "image" | "audio" | "video" | "pdf" | "file";
export type SubmissionAttachment = {
  index: number;
  filename: string;
  basename: string;
  mimetype: string;
  kind: MediaKind;
  url: string;
};
export type SubmissionAnswer = {
  name: string;
  label: string;
  value: unknown;
  display: string;
  type: string;
  group: string;
  media: SubmissionAnswerMedia[];
};
export type Submission = {
  id: number;
  asset_uid: string;
  submission_id: string;
  establishment_id: string | null;
  establishment_name: string | null;
  establishment_kind: string | null;
  checklist_id: number | null;
  checklist_name: string | null;
  form_version: string;
  submitted_at: string | null;
  scores: SubmissionScores;
  answers: SubmissionAnswer[];
  attachments: SubmissionAttachment[];
  form_url: string | null;
  data: Record<string, unknown>;
};
