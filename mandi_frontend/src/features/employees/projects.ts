import type { CollectionProjectDirectory } from "@/lib/api";

export function projectNameMap(directory?: CollectionProjectDirectory) {
  return new Map((directory?.projects ?? []).map((project) => [project.id, project.name] as const));
}

export function projectLabel(
  projectId: number | null | undefined,
  names: Map<number, string>,
  fallbackId: string,
) {
  if (projectId === null || projectId === undefined) return fallbackId;
  return names.get(projectId) ?? fallbackId;
}
