import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AttributionControl,
  LngLatBounds,
  Map,
  Marker,
  NavigationControl,
  Popup,
} from "maplibre-gl";
import { useApiQuery } from "@/features/shared/api";
import { useParams } from "react-router";
import "maplibre-gl/dist/maplibre-gl.css";

export default function LocationMap({
  latitude,
  longitude,
}: {
  latitude: number;
  longitude: number;
}) {
  const { t } = useTranslation();
  const { id } = useParams();
  const nearby = useApiQuery<{
    results: { id: string; name: string; address: string; latitude: number; longitude: number }[];
    count: number;
  }>(["nearby-establishments"], "/establishments/nearby/", { latitude, longitude });
  const mapRef = useRef<Map | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!container.current) return;
    let map: Map | undefined;
    let observer: ResizeObserver | undefined;
    try {
      map = new Map({
        container: container.current,
        center: [longitude, latitude],
        zoom: 15,
        scrollZoom: false,
        attributionControl: false,
        style: {
          version: 8,
          sources: {
            streets: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              maxzoom: 19,
              attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>',
            },
          },
          layers: [{ id: "streets", type: "raster", source: "streets" }],
        },
      });
      mapRef.current = map;
      map.addControl(new AttributionControl({ compact: false }));
      new Marker({ color: "#1e4976" }).setLngLat([longitude, latitude]).addTo(map);
      map.addControl(new NavigationControl({ showCompass: false }), "top-right");
      map.on("error", () => setFailed(true));
      observer = new ResizeObserver(() => map?.resize());
      observer.observe(container.current);
    } catch {
      setFailed(true);
    }
    return () => {
      observer?.disconnect();
      mapRef.current = null;
      map?.remove();
    };
  }, [latitude, longitude]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const markers = (nearby.data?.results ?? [])
      .filter((row) => row.id !== id)
      .map((row) => {
        const content = document.createElement("div");
        content.dir = "auto";
        const link = document.createElement("a");
        link.href = `/establishments/${encodeURIComponent(row.id)}`;
        link.textContent = row.name;
        link.className = "text-link font-semibold";
        const address = document.createElement("p");
        address.textContent = row.address;
        content.append(link, address);
        const marker = new Marker({ color: "#d97706", scale: 0.8 })
          .setLngLat([row.longitude, row.latitude])
          .setPopup(new Popup({ offset: 25 }).setDOMContent(content))
          .addTo(map);
        marker.getElement().setAttribute("aria-label", row.name);
        return marker;
      });
    const bounds = new LngLatBounds([longitude, latitude], [longitude, latitude]);
    for (const row of nearby.data?.results ?? []) bounds.extend([row.longitude, row.latitude]);
    if (markers.length) map.fitBounds(bounds, { padding: 45, maxZoom: 15, duration: 0 });
    return () => markers.forEach((marker) => marker.remove());
  }, [nearby.data, id, latitude, longitude]);
  return (
    <div>
      <div
        ref={container}
        role="region"
        aria-label={t("Establishment location")}
        className="h-64 w-full overflow-hidden rounded-lg border"
        dir="ltr"
      />
      <p className="text-muted-foreground mt-2 text-sm">
        {t("Blue: selected establishment. Orange: nearby establishments within 5 km.")}
      </p>
      {failed && (
        <p role="status" className="text-muted-foreground mt-2 text-sm">
          {t("The map could not load. Check your connection.")}
        </p>
      )}
    </div>
  );
}
