import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { RefreshCw, AlertOctagon, ThumbsUp, CheckCircle } from 'lucide-react';
import { fetchAdminHeatmap, updateTicketStatus } from '../api';
import { CivicTicket } from '../types';

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  MEDIUM: '#2563eb',
  LOW: '#0d9488',
};

export default function AdminDashboard() {
  const [token, setToken] = useState('officer-demo-token');
  const [tickets, setTickets] = useState<CivicTicket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  const loadData = async () => {
    setError(null);
    try {
      const list = await fetchAdminHeatmap(token);
      setTickets(list);
    } catch {
      setError('Unauthorized or backend offline. Check officer token and FastAPI server.');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current).setView([12.8231, 80.0442], 15);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map);
      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;
    map.eachLayer((layer) => {
      if (layer instanceof L.Circle || layer instanceof L.CircleMarker) {
        map.removeLayer(layer);
      }
    });

    tickets.forEach((t) => {
      const color = SEVERITY_COLORS[t.severity] || '#2563eb';
      L.circle([t.lat, t.lon], {
        radius: 50,
        color,
        fillColor: color,
        fillOpacity: 0.12,
        weight: 1,
      }).addTo(map);

      L.circleMarker([t.lat, t.lon], {
        radius: 8,
        color: '#ffffff',
        weight: 2,
        fillColor: color,
        fillOpacity: 0.95,
      })
        .bindPopup(
          `<strong>${t.issue_subcategory}</strong> (${t.department_code})<br/>
           Severity: <b>${t.severity}</b> | Status: <b>${t.status}</b><br/>
           Upvotes (Clustered Reports): <b>${t.upvote_count}</b>`
        )
        .addTo(map);
    });
  }, [tickets]);

  const handleStatusChange = async (ticketId: string, status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED') => {
    await updateTicketStatus(token, ticketId, status);
    await loadData();
  };

  const criticalCount = tickets.filter((t) => t.severity === 'CRITICAL' && t.status !== 'RESOLVED').length;
  const totalUpvotes = tickets.reduce((acc, t) => acc + t.upvote_count, 0);

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs text-slate-500 font-medium">Active Master Tickets</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{tickets.length}</div>
        </div>
        <div className="bg-red-50 p-4 rounded-xl border border-red-200 shadow-sm">
          <div className="text-xs text-red-700 font-semibold flex items-center gap-1">
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>Critical Safety Hazards</span>
          </div>
          <div className="text-2xl font-bold text-red-800 mt-1">{criticalCount}</div>
        </div>
        <div className="bg-blue-50 p-4 rounded-xl border border-blue-200 shadow-sm">
          <div className="text-xs text-blue-700 font-semibold flex items-center gap-1">
            <ThumbsUp className="w-3.5 h-3.5" />
            <span>Total Citizen Reports Consolidated</span>
          </div>
          <div className="text-2xl font-bold text-blue-900 mt-1">{totalUpvotes}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <label className="text-[11px] font-semibold text-slate-500">Officer RBAC Bearer Token</label>
          <div className="flex gap-1.5 mt-1">
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg px-2 py-1.5"
            />
            <button
              onClick={loadData}
              className="bg-slate-800 hover:bg-slate-900 text-white px-2.5 py-1.5 rounded-lg text-xs flex items-center"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">{error}</div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-900">
            Live Municipal Ward Heatmap (Circles denote 50m PostGIS Deduplication Radius)
          </h3>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600 inline-block" /> Critical
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-600 inline-block" /> High
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block" /> Medium
            </span>
          </div>
        </div>
        <div ref={mapContainerRef} className="h-72 w-full z-0" />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-100 text-slate-700 border-b border-slate-200">
              <th className="py-3 px-4 font-semibold">Department</th>
              <th className="py-3 px-4 font-semibold">Issue & Description</th>
              <th className="py-3 px-4 font-semibold">Severity</th>
              <th className="py-3 px-4 font-semibold">Upvotes</th>
              <th className="py-3 px-4 font-semibold">Status</th>
              <th className="py-3 px-4 font-semibold">Crew Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {tickets.map((t) => (
              <tr key={t.ticket_id} className="hover:bg-slate-50">
                <td className="py-3 px-4 font-bold text-slate-800">{t.department_code}</td>
                <td className="py-3 px-4">
                  <div className="font-semibold text-slate-900">{t.issue_subcategory}</div>
                  <div className="text-slate-500 mt-0.5">{t.description}</div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">{t.ticket_id}</div>
                </td>
                <td className="py-3 px-4">
                  <span
                    className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                      t.severity === 'CRITICAL'
                        ? 'bg-red-100 text-red-800'
                        : t.severity === 'HIGH'
                        ? 'bg-orange-100 text-orange-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {t.severity}
                  </span>
                </td>
                <td className="py-3 px-4 font-bold text-slate-800">{t.upvote_count}</td>
                <td className="py-3 px-4 font-semibold">{t.status}</td>
                <td className="py-3 px-4">
                  <div className="flex gap-1.5">
                    {t.status !== 'IN_PROGRESS' && t.status !== 'RESOLVED' && (
                      <button
                        onClick={() => handleStatusChange(t.ticket_id, 'IN_PROGRESS')}
                        className="px-2.5 py-1 bg-amber-100 hover:bg-amber-200 text-amber-900 rounded font-semibold"
                      >
                        Dispatch Crew
                      </button>
                    )}
                    {t.status !== 'RESOLVED' && (
                      <button
                        onClick={() => handleStatusChange(t.ticket_id, 'RESOLVED')}
                        className="px-2.5 py-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-900 rounded font-semibold flex items-center gap-1"
                      >
                        <CheckCircle className="w-3 h-3" />
                        <span>Resolve</span>
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
