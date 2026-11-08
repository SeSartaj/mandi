import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8001/api/v1",
});
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("mandi-token");
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return "Cannot reach Mandi. Check that the backend is running.";
    const data = error.response.data;
    if (typeof data?.detail === "string") return data.detail;
    if (data && typeof data === "object")
      return Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`)
        .join(" · ");
  }
  return "Something went wrong. Please try again.";
}
export function fileUrl(path: string | null | undefined): string {
  if (!path) return "";
  try {
    return new URL(path, api.defaults.baseURL ?? window.location.origin).toString();
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
  phone: string;
  source_links: SourceLink[];
};
export type SourceLink = {
  id: number;
  source: string;
  external_id: string;
  details: Record<string, unknown>;
  is_demo: boolean;
  linked_at: string;
};
export type Inspection = {
  id: number;
  establishment_id: string;
  establishment_name: string;
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
  kobo_asset_uid: string;
  kobo_project_url?: string | null;
  kobo_deployment_status: "not_deployed" | "deploying" | "deployed" | "failed";
  kobo_deployment_error: string;
  kobo_deployed_at: string | null;
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
export type KoboAnswer = {
  name: string;
  label: string;
  value: unknown;
  display: string;
};
export type KoboSubmission = {
  id: number;
  asset_uid: string;
  submission_id: string;
  establishment_id: string;
  checklist_name: string | null;
  checklist_version: string | null;
  submitted_at: string | null;
  scores: KoboSubmissionScores;
  answers: KoboAnswer[];
  kobo_url: string | null;
  data: Record<string, unknown>;
};
