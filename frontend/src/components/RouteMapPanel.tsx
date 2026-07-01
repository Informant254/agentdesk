"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  MapPin, Navigation, Clock, GripVertical, Sun, Trash2,
  ChevronLeft, ChevronRight, Loader, AlertCircle, Layers,
} from "lucide-react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { getRouteMap, reorderRoute } from "@/lib/api";
import type { RouteJob, RouteData, RouteMapResponse } from "@/types";

import "leaflet/dist/leaflet.css";

function decodePolyline(encoded: string): [number, number][] {
  const points: [number, number][] = [];
  let index = 0, lat = 0, lng = 0;
  while (index < encoded.length) {
    let b, shift = 0, result = 0;
    do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; }
    while (b >= 0x20);
    lat += (result & 1 ? ~(result >> 1) : result >> 1);
    shift = 0; result = 0;
    do { b = encoded.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; }
    while (b >= 0x20);
    lng += (result & 1 ? ~(result >> 1) : result >> 1);
    points.push([lat * 1e-5, lng * 1e-5]);
  }
  return points;
}

function createMarkerIcon(color: string) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="24" height="36">
    <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24C24 5.4 18.6 0 12 0z" fill="${color}" stroke="white" stroke-width="2"/>
    <circle cx="12" cy="12" r="4" fill="white"/>
  </svg>`;
  return L.divIcon({
    html: svg,
    iconSize: [24, 36],
    iconAnchor: [12, 36],
    popupAnchor: [0, -36],
    className: "bg-transparent",
  });
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: "#3b82f6",
  in_progress: "#eab308",
  completed: "#22c55e",
  cancelled: "#ef4444",
};

function FitBounds({ jobs, route }: { jobs: RouteJob[]; route?: RouteData | null }) {
  const map = useMap();
  useEffect(() => {
    const points: [number, number][] = [];
    if (route) {
      for (const leg of route.legs) {
        points.push([leg.start_lat, leg.start_lng]);
        points.push([leg.end_lat, leg.end_lng]);
      }
    } else {
      for (const j of jobs) {
        if (j.lat != null && j.lng != null) points.push([j.lat, j.lng]);
      }
    }
    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [jobs, route, map]);
  return null;
}

export function RouteMapPanel() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState<RouteMapResponse | null>(null);
  const [startingLocation, setStartingLocation] = useState("");
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [mapLayer, setMapLayer] = useState<"street" | "satellite">("street");
  const jobListRef = useRef<HTMLDivElement>(null);

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });

  const dateStr = (d: Date) => d.toISOString().split("T")[0];

  const navigateDate = (offset: number) => {
    setSelectedDate(prev => { const n = new Date(prev); n.setDate(n.getDate() + offset); return n; });
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await getRouteMap(dateStr(selectedDate), startingLocation) as RouteMapResponse;
      setData(result);
      if (result.error) setError(result.error);
      if (result.note) setError(result.note);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load route map");
    } finally {
      setLoading(false);
    }
  }, [selectedDate, startingLocation]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const jobs = data?.optimized_order && data.optimized_order.length > 0
    ? data.optimized_order
    : data?.jobs || [];
  const route = data?.route;
  const routePoints = route ? decodePolyline(route.polyline) : [];

  const handleDragStart = (idx: number) => setDraggedIdx(idx);

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (draggedIdx === null || draggedIdx === idx) return;
    const reordered = [...jobs];
    const [item] = reordered.splice(draggedIdx, 1);
    reordered.splice(idx, 0, item);
    setDraggedIdx(idx);
    setData(prev => prev ? { ...prev, optimized_order: reordered } : prev);
  };

  const handleDragEnd = async () => {
    setDraggedIdx(null);
    if (!data?.optimized_order) return;
    const order = data.optimized_order.map(j => j.id);
    try {
      const result = await reorderRoute(dateStr(selectedDate), order, startingLocation) as { success: boolean; route?: RouteData };
      if (result.route) {
        setData(prev => prev ? { ...prev, route: result.route! } : prev);
      }
    } catch {
      await fetchData();
    }
  };

  const tileUrl = mapLayer === "street"
    ? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    : "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

  const tileAttr = mapLayer === "street"
    ? "&copy; OpenStreetMap contributors"
    : "&copy; Esri";

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Navigation size={20} className="text-blue-600" />
            Live Route Map
          </h2>
          <p className="text-sm text-slate-500">{formatDate(selectedDate)}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMapLayer(l => l === "street" ? "satellite" : "street")}
            className="p-2 hover:bg-slate-100 rounded-lg text-slate-500"
            title={`Switch to ${mapLayer === "street" ? "satellite" : "street"} view`}
          >
            <Layers size={18} />
          </button>
          <button onClick={() => navigateDate(-1)} className="p-2 hover:bg-slate-100 rounded-lg">
            <ChevronLeft size={20} />
          </button>
          <button onClick={() => setSelectedDate(new Date())} className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 rounded-lg">
            Today
          </button>
          <button onClick={() => navigateDate(1)} className="p-2 hover:bg-slate-100 rounded-lg">
            <ChevronRight size={20} />
          </button>
          <button
            onClick={fetchData}
            className="ml-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-1.5"
          >
            <MapPin size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Starting location input */}
      <div className="px-4 py-2 bg-white border-b border-slate-100 flex items-center gap-3">
        <Sun size={16} className="text-slate-400 flex-shrink-0" />
        <input
          type="text"
          value={startingLocation}
          onChange={e => setStartingLocation(e.target.value)}
          placeholder="Starting location (e.g. office address or 'Shop')"
          className="flex-1 text-sm px-3 py-1.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Job list sidebar */}
        <div
          ref={jobListRef}
          className="w-72 border-r border-slate-200 bg-white overflow-y-auto flex-shrink-0"
        >
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader size={24} className="animate-spin text-blue-500" />
            </div>
          )}

          {error && !loading && (
            <div className="p-4">
              <div className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            </div>
          )}

          {!loading && !error && jobs.length === 0 && (
            <div className="text-center py-12 px-4">
              <MapPin size={32} className="mx-auto text-slate-300 mb-3" />
              <p className="text-sm text-slate-500">No jobs scheduled for this day</p>
            </div>
          )}

          {!loading && jobs.length > 0 && (
            <div className="p-2 space-y-1.5">
              <div className="px-2 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Route Order
              </div>
              {jobs.map((job, idx) => (
                <div
                  key={job.id}
                  draggable
                  onDragStart={() => handleDragStart(idx)}
                  onDragOver={e => handleDragOver(e, idx)}
                  onDragEnd={handleDragEnd}
                  className={`flex items-start gap-2 p-2.5 rounded-lg border cursor-grab active:cursor-grabbing transition-colors ${
                    draggedIdx === idx
                      ? "border-blue-400 bg-blue-50 shadow-md"
                      : "border-slate-200 hover:border-blue-300 hover:bg-blue-50/50"
                  }`}
                >
                  <GripVertical size={14} className="text-slate-300 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                        {idx + 1}
                      </span>
                      <span className="font-medium text-sm text-slate-900 truncate">{job.title}</span>
                    </div>
                    <p className="text-xs text-slate-500 truncate ml-7">{job.client_name}</p>
                    <p className="text-xs text-slate-400 truncate ml-7">{job.address}</p>
                    <div className="flex items-center gap-2 mt-1 ml-7">
                      <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded-full ${
                        job.status === "completed" ? "bg-green-100 text-green-700"
                          : job.status === "in_progress" ? "bg-yellow-100 text-yellow-700"
                            : "bg-blue-100 text-blue-700"
                      }`}>
                        {job.status.replace("_", " ")}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        <Clock size={10} className="inline mr-0.5" />
                        {Math.round(job.estimated_duration_minutes / 60)}h
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Map */}
        <div className="flex-1 relative">
          {loading && (
            <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-white/60">
              <Loader size={32} className="animate-spin text-blue-500" />
            </div>
          )}

          {data && (
            <MapContainer
              center={[39.8283, -98.5795]}
              zoom={4}
              className="h-full w-full"
              zoomControl={true}
            >
              <TileLayer url={tileUrl} attribution={tileAttr} />
              <FitBounds jobs={jobs} route={route} />

              {jobs.map((job, idx) => {
                if (job.lat == null || job.lng == null) return null;
                const color = STATUS_COLORS[job.status] || "#3b82f6";
                return (
                  <Marker
                    key={job.id}
                    position={[job.lat, job.lng]}
                    icon={createMarkerIcon(color)}
                  >
                    <Popup>
                      <div className="min-w-[200px]">
                        <div className="font-semibold text-sm mb-1">{job.title}</div>
                        <div className="text-xs text-slate-500 space-y-0.5">
                          <p><span className="font-medium">Client:</span> {job.client_name}</p>
                          <p><span className="font-medium">Address:</span> {job.address}</p>
                          <p>
                            <span className="font-medium">Order:</span> Stop #{idx + 1}
                          </p>
                          <p>
                            <span className="font-medium">Duration:</span>{" "}
                            {Math.round(job.estimated_duration_minutes / 60)}h{" "}
                            {job.estimated_duration_minutes % 60}m
                          </p>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}

              {route && routePoints.length > 0 && (
                <Polyline
                  positions={routePoints}
                  pathOptions={{
                    color: "#3b82f6",
                    weight: 4,
                    opacity: 0.7,
                    dashArray: "10, 10",
                  }}
                />
              )}
            </MapContainer>
          )}
        </div>
      </div>

      {/* Summary footer */}
      <div className="p-3 border-t border-slate-200 bg-white flex items-center gap-6 text-sm flex-shrink-0">
        <div className="flex items-center gap-1.5 text-slate-600">
          <MapPin size={14} className="text-blue-500" />
          <span className="font-semibold">{data?.total_jobs ?? jobs.length}</span>
          <span className="text-slate-400">jobs</span>
        </div>
        {route && (
          <>
            <div className="flex items-center gap-1.5 text-slate-600">
              <Navigation size={14} className="text-green-500" />
              <span className="font-semibold">{route.total_distance_km} km</span>
              <span className="text-slate-400">total</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-600">
              <Clock size={14} className="text-amber-500" />
              <span className="font-semibold">{Math.round(route.total_duration_min)} min</span>
              <span className="text-slate-400">drive time</span>
            </div>
          </>
        )}
        {data?.starting_location && (
          <div className="flex items-center gap-1.5 text-slate-500 ml-auto text-xs">
            <Sun size={12} />
            <span className="truncate max-w-[200px]">From: {data.starting_location}</span>
          </div>
        )}
      </div>
    </div>
  );
}
