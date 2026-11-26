import React, { useEffect, useState } from 'react';
import { Compass, MapPin, Package, Search } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { NA } from '../lib/format';
import { CredCard } from '../components/ui/primitives';

// No hand-typed fallback lists: data comes only from the API (dataset/reference/*.json).

export default function Reference() {
  const [activeTab, setActiveTab] = useState('ports');
  const [searchQuery, setSearchQuery] = useState('');
  const [portsData, setPortsData] = useState([]);
  const [routesData, setRoutesData] = useState([]);
  const [commoditiesData, setCommoditiesData] = useState([]);
  const [, setLoading] = useState(false);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [pRes, rRes, cRes] = await Promise.all([
          fetch('http://localhost:5001/api/ports').catch(() => null),
          fetch('http://localhost:5001/api/routes').catch(() => null),
          fetch('http://localhost:5001/api/commodities').catch(() => null)
        ]);
        if (!pRes || !pRes.ok) setOffline(true);
        if (pRes && pRes.ok) setPortsData(await pRes.json());
        if (rRes && rRes.ok) setRoutesData(await rRes.json());
        if (cRes && cRes.ok) setCommoditiesData(await cRes.json());
      } catch (e) {
        console.error('Error fetching reference databases', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const q = searchQuery.toLowerCase();
  const filteredPorts = portsData.filter(p => p.name?.toLowerCase().includes(q) || p.country?.toLowerCase().includes(q));
  const filteredRoutes = routesData.filter(r => r.name?.toLowerCase().includes(q) || r.route_id?.toLowerCase().includes(q));
  const filteredCommodities = commoditiesData.filter(c => c.name?.toLowerCase().includes(q) || c.commodity_id?.toLowerCase().includes(q));

  const tabs = [
    { id: 'ports', label: 'World Ports', icon: MapPin, count: portsData.length },
    { id: 'routes', label: 'Shipping Corridors', icon: Compass, count: routesData.length },
    { id: 'commodities', label: 'Commodities', icon: Package, count: commoditiesData.length }
  ];

  return (
    <PageShell
      eyebrow="reference knowledge databases"
      title="The Global"
      accent="Knowledge Bases."
      sub="Structured reference databases containing global container ports, maritime trade corridors, and commodity vulnerability parameters."
      right={
        <div className="relative w-full md:w-80">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
          <input
            type="text"
            placeholder="Search ports, lanes, commodities…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-white/[0.03] border border-[rgba(225,29,72,0.3)] pl-11 pr-5 py-3 text-xs sm:text-sm text-white placeholder:text-neutral-500 focus:border-[rgba(225,29,72,0.7)] focus:outline-none transition-colors"
          />
        </div>
      }
    >
      {offline && (
        <div className="mb-8 border border-neutral-700 bg-neutral-900/60 px-4 py-3 text-xs text-neutral-300">
          API server offline: no reference data shown. Start python3 dev_dashboard/server.py.
        </div>
      )}
      {/* ── 1. Tab Selector ─────────────────────────────────────────────── */}
      <section className="mb-10 flex items-center gap-8 border-b border-[rgba(225,29,72,0.25)] pb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`transition-colors cursor-pointer py-1 font-semibold tracking-wider uppercase text-xs flex items-center gap-2 ${
              activeTab === tab.id
                ? 'text-white border-b-2 border-rose-500'
                : 'text-neutral-500 hover:text-neutral-300'
            }`}
          >
            <span>{tab.label}</span>
            <span className="mono text-[10px] text-neutral-600 font-normal">({tab.count})</span>
          </button>
        ))}
      </section>

      {/* ── 2. Reference Table / List Slabs ──────────────────────────────── */}
      <section className="mb-16">
        <CredCard hover={false} className="p-8 sm:p-10">
          {activeTab === 'ports' && (
            <div className="divide-y divide-[rgba(225,29,72,0.2)]">
              {filteredPorts.slice(0, 20).map((port, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-6 items-center gap-4 py-4 text-xs hover:bg-white/[0.02] px-3 transition-colors"
                >
                  <span className="mono font-bold text-rose-400">{port.port_id || `P${idx + 1}`}</span>
                  <div className="md:col-span-2">
                    <span className="text-sm font-bold text-white block">{port.name}</span>
                    <span className="text-xs text-neutral-500 block">{port.country}</span>
                  </div>
                  <span className="mono text-neutral-400">
                    {port.lat?.toFixed(2)}°, {port.lon?.toFixed(2)}°
                  </span>
                  <span className="mono font-bold text-emerald-400">
                    {port.annual_teu_millions ?? NA} M TEU
                  </span>
                  <div className="flex justify-end">
                    <span className="mono font-bold text-amber-400">
                      {port.vessel_capacity ?? NA} vessels/day cap.
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'routes' && (
            <div className="divide-y divide-[rgba(225,29,72,0.2)]">
              {filteredRoutes.map((route, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 items-center gap-4 py-4 text-xs hover:bg-white/[0.02] px-3 transition-colors"
                >
                  <span className="mono font-bold text-rose-400">{route.route_id}</span>
                  <span className="text-sm font-bold text-white md:col-span-2">{route.name ?? NA}</span>
                  <span className="mono text-neutral-400 truncate">{(route.key_ports || []).join(' · ') || NA}</span>
                  <div className="flex justify-end mono font-bold text-emerald-400">
                    {route.avg_transit_days ?? NA}d normal · {route.alternate_transit_days ?? NA}d alternate
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'commodities' && (
            <div className="divide-y divide-[rgba(225,29,72,0.2)]">
              {filteredCommodities.map((comm, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 items-center gap-4 py-4 text-xs hover:bg-white/[0.02] px-3 transition-colors"
                >
                  <span className="mono font-bold text-rose-400">{comm.commodity_id ?? NA}</span>
                  <span className="text-sm font-bold text-white md:col-span-2">{comm.name ?? NA}</span>
                  <div>
                    <span className="mono text-[11px] font-semibold text-neutral-400">
                      Sensitivity: {comm.supply_chain_sensitivity ?? NA}
                    </span>
                  </div>
                  <div className="flex justify-end mono text-xs text-neutral-300">
                    <span className="text-rose-400 font-bold">{comm.typical_disruption_impact_days ?? NA}d typical impact</span>
                    <span className="mx-2 text-neutral-700">·</span>
                    <span className="text-emerald-400 font-bold">{comm.avg_value_per_container_usd != null ? `$${comm.avg_value_per_container_usd.toLocaleString()}/container` : NA}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CredCard>
      </section>
    </PageShell>
  );
}
