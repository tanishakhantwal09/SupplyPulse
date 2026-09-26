import React, { useEffect, useState } from 'react';
import { Compass, MapPin, Package, Search } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { CredCard } from '../components/ui/primitives';

const DEFAULT_PORTS = [
  { port_id: 'P01', name: 'Port of Shanghai', country: 'China', lat: 31.2304, lon: 121.4737, container_throughput_mteu: 47.3, max_draft_m: 16.0 },
  { port_id: 'P02', name: 'Port of Singapore', country: 'Singapore', lat: 1.3521, lon: 103.8198, container_throughput_mteu: 37.5, max_draft_m: 18.0 },
  { port_id: 'P03', name: 'Port of Rotterdam', country: 'Netherlands', lat: 51.9244, lon: 4.4777, container_throughput_mteu: 15.3, max_draft_m: 24.0 },
  { port_id: 'P04', name: 'Ningbo-Zhoushan', country: 'China', lat: 29.8683, lon: 121.5440, container_throughput_mteu: 31.0, max_draft_m: 17.5 },
  { port_id: 'P05', name: 'Port of Suez', country: 'Egypt', lat: 29.9668, lon: 32.5498, container_throughput_mteu: 6.5, max_draft_m: 20.1 }
];

const DEFAULT_ROUTES = [
  { route_id: 'R01', name: 'Trans-Pacific Express', origin: 'Shanghai', destination: 'Los Angeles', distance_nm: 5700, avg_transit_days: 14 },
  { route_id: 'R02', name: 'Asia-Europe Mainline', origin: 'Singapore', destination: 'Rotterdam', distance_nm: 8400, avg_transit_days: 26 },
  { route_id: 'R03', name: 'Suez Transit Corridor', origin: 'Port Said', destination: 'Port of Suez', distance_nm: 101, avg_transit_days: 1 }
];

const DEFAULT_COMMODITIES = [
  { commodity_id: 'C01', name: 'Semiconductors & Electronics', tier: 1, critical_stockout_days: 5, safety_buffer_days: 10 },
  { commodity_id: 'C02', name: 'Crude Oil & LNG', tier: 1, critical_stockout_days: 7, safety_buffer_days: 14 },
  { commodity_id: 'C03', name: 'Automotive Components', tier: 2, critical_stockout_days: 4, safety_buffer_days: 7 }
];

export default function Reference() {
  const [activeTab, setActiveTab] = useState('ports');
  const [searchQuery, setSearchQuery] = useState('');
  const [portsData, setPortsData] = useState(DEFAULT_PORTS);
  const [routesData, setRoutesData] = useState(DEFAULT_ROUTES);
  const [commoditiesData, setCommoditiesData] = useState(DEFAULT_COMMODITIES);
  const [, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [pRes, rRes, cRes] = await Promise.all([
          fetch('http://localhost:5001/api/ports').catch(() => null),
          fetch('http://localhost:5001/api/routes').catch(() => null),
          fetch('http://localhost:5001/api/commodities').catch(() => null)
        ]);
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
                    {port.container_throughput_mteu || port.annual_teu_millions || '15.0'} M TEU
                  </span>
                  <div className="flex justify-end">
                    <span className="mono font-bold text-amber-400">
                      {port.max_draft_m || '16.0'}m Draft
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
                  <span className="text-sm font-bold text-white md:col-span-2">{route.name || route.route_name}</span>
                  <span className="mono text-neutral-400">{route.origin} ➔ {route.destination}</span>
                  <div className="flex justify-end mono font-bold text-emerald-400">
                    {route.distance_nm?.toLocaleString()} NM · {route.avg_transit_days}d
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
                  <span className="mono font-bold text-rose-400">{comm.commodity_id || `C${idx + 1}`}</span>
                  <span className="text-sm font-bold text-white md:col-span-2">{comm.name || comm.commodity}</span>
                  <div>
                    <span className="mono text-[11px] font-semibold text-neutral-400">
                      Tier {comm.tier || 1}
                    </span>
                  </div>
                  <div className="flex justify-end mono text-xs text-neutral-300">
                    <span className="text-rose-400 font-bold">{comm.critical_stockout_days || 5}d Stockout</span>
                    <span className="mx-2 text-neutral-700">·</span>
                    <span className="text-emerald-400 font-bold">{comm.safety_buffer_days || 10}d Buffer</span>
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
