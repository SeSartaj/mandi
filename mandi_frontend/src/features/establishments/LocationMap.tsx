import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AttributionControl,
  Map,
  Marker,
  NavigationControl,
  Popup,
} from "maplibre-gl";
import { useApiQuery } from "@/features/shared/api";
import { localizeAddress, pharmacyTypeLabel } from "@/features/shared/labels";
import { useDistrictName } from "@/features/establishments/registry";
import { useParams } from "react-router";
import "maplibre-gl/dist/maplibre-gl.css";

type PopupItem = {
  name: string;
  address?: string | null;
  province?: string | null;
  district?: string | null;
  house_number?: string | null;
  floor?: string | null;
  market?: string | null;
  landmark?: string | null;
  pharmacy_type?: string | number | null;
  href?: string;
};

type NearbyRow = PopupItem & { id: string; latitude: number; longitude: number };

export default function LocationMap({
  latitude,
  longitude,
  name,
  address,
}: {
  latitude: number;
  longitude: number;
  name?: string;
  address?: string | null;
}) {
  const { t, i18n } = useTranslation();
  const districtName = useDistrictName();
  const { id } = useParams();
  const nearby = useApiQuery<{ results: NearbyRow[]; count: number }>(
    ["nearby-establishments"],
    "/establishments/nearby/",
    { latitude, longitude },
  );
  const mapRef = useRef<Map | null>(null);
  const currentMarkerRef = useRef<Marker | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const buildPopup = useCallback(
    (item: PopupItem) => {
      const content = document.createElement("div");
      content.dir = "auto";
      content.className = "min-w-56 overflow-hidden text-sm text-slate-900";
      const title = document.createElement(item.href ? "a" : "span");
      title.textContent = item.name || t("Establishment");
      if (item.href && title instanceof HTMLAnchorElement) {
        title.href = item.href;
        title.className = "font-semibold text-sky-700 hover:underline";
      } else {
        title.className = "font-semibold";
      }
      const addressText = document.createElement("span");
      const addressParts = [
        item.house_number,
        item.floor,
        item.market,
        item.landmark,
      ].filter(Boolean) as string[];
      const separator = i18n.language === "en" ? ", " : "، ";
      addressText.textContent =
        (addressParts.length ? addressParts.join(separator) : localizeAddress(item.address)) || "—";
      const rows: { label: string; value: string | HTMLElement }[] = [
        { label: t("Name"), value: title },
        { label: t("Province"), value: item.province || "—" },
        { label: t("District"), value: districtName(item.district) || "—" },
        { label: t("House number"), value: item.house_number || "—" },
        { label: t("Floor"), value: item.floor || "—" },
        { label: t("Market"), value: item.market || "—" },
        { label: t("Address"), value: addressText },
        {
          label: t("Pharmacy type"),
          value: pharmacyTypeLabel(item.pharmacy_type) || "—",
        },
      ];
      for (const [index, lineItem] of rows.entries()) {
        const line = document.createElement("div");
        line.className = `grid grid-cols-[minmax(4.5rem,auto)_minmax(0,1fr)] items-start gap-3 px-3 py-2 ${
          index % 2 === 0 ? "bg-slate-50" : "bg-white"
        } ${index > 0 ? "border-t border-slate-200" : ""}`;
        const label = document.createElement("span");
        label.className = "text-xs leading-5 text-slate-500";
        label.textContent = lineItem.label;
        const value = document.createElement("span");
        value.className = "font-semibold leading-5 break-words text-slate-900";
        value.append(lineItem.value);
        line.append(label, value);
        content.append(line);
      }
      const popup = new Popup({
        offset: 25,
        className: "establishment-map-popup",
      }).setDOMContent(content);
      popup.on("open", () => {
        const popupElement = popup.getElement();
        if (popupElement) popupElement.style.zIndex = "20";
      });
      return popup;
    },
    [districtName, i18n.language, t],
  );
  useEffect(() => {
    if (!container.current) return;
    let map: Map | undefined;
    let observer: ResizeObserver | undefined;
    try {
      map = new Map({
        container: container.current,
        center: [longitude, latitude],
        zoom: 17,
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
      const currentMarker = new Marker({ color: "#1e4976" }).setLngLat([
        longitude,
        latitude,
      ]);
      currentMarkerRef.current = currentMarker;
      if (name || address) {
        currentMarker.setPopup(
          buildPopup({ name: name || t("Establishment"), address }),
        );
      }
      currentMarker.addTo(map);
      // The selected establishment must stay visible when nearby pins overlap it.
      const currentElement = currentMarker.getElement();
      currentElement.style.zIndex = "5";
      currentElement.setAttribute("data-current-establishment", "true");
      map.addControl(new NavigationControl({ showCompass: false }), "top-right");
      map.on("error", () => setFailed(true));
      observer = new ResizeObserver(() => map?.resize());
      observer.observe(container.current);
    } catch {
      setFailed(true);
    }
    return () => {
      observer?.disconnect();
      currentMarkerRef.current = null;
      mapRef.current = null;
      map?.remove();
    };
  }, [address, buildPopup, latitude, longitude, name, t]);
  const currentRow = nearby.data?.results.find((row) => row.id === id);
  useEffect(() => {
    const marker = currentMarkerRef.current;
    if (!marker) return;
    if (currentRow) {
      marker.setPopup(buildPopup({ ...currentRow, href: undefined }));
    } else if (name || address) {
      marker.setPopup(buildPopup({ name: name || t("Establishment"), address }));
    }
  }, [address, buildPopup, currentRow, name, t]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const markers = (nearby.data?.results ?? [])
      .filter((row) => row.id !== id)
      .map((row) => {
        const marker = new Marker({ color: "#d97706", scale: 0.8 })
          .setLngLat([row.longitude, row.latitude])
          .setPopup(
            buildPopup({
              name: row.name,
              address: row.address,
              href: `/establishments/${encodeURIComponent(row.id)}`,
            }),
          )
          .addTo(map);
        const element = marker.getElement();
        element.style.zIndex = "1";
        element.setAttribute("aria-label", row.name);
        return marker;
      });
    return () => markers.forEach((marker) => marker.remove());
  }, [nearby.data, id, latitude, longitude, buildPopup]);
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
        {t("Blue: selected establishment. Orange: nearby establishments within 1 km.")}
      </p>
      {failed && (
        <p role="status" className="text-muted-foreground mt-2 text-sm">
          {t("The map could not load. Check your connection.")}
        </p>
      )}
    </div>
  );
}
