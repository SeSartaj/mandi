import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { MediaKind } from "@/lib/api";

/**
 * Fetch a collection attachment through the API (which adds the token) and expose it
 * as an object URL so `<img>`, `<audio>` and `<video>` can render it.
 */
export function useMediaUrl(path: string | null | undefined) {
  const [objectUrl, setObjectUrl] = useState<string>();
  const query = useQuery({
    queryKey: ["media", path],
    enabled: Boolean(path),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    queryFn: async () => {
      const response = await api.get(path as string, { responseType: "blob" });
      return response.data as Blob;
    },
  });

  useEffect(() => {
    if (!query.data) {
      setObjectUrl(undefined);
      return;
    }
    const url = URL.createObjectURL(query.data);
    setObjectUrl(url);
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [query.data]);

  return { ...query, data: objectUrl };
}

export function mediaIconKind(kind: MediaKind | string): MediaKind {
  if (kind === "image" || kind === "audio" || kind === "video" || kind === "pdf") {
    return kind;
  }
  return "file";
}
