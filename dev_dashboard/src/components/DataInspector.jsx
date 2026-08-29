import React, { useState, useEffect } from 'react';
import { Database, Search, MapPin, Compass, Package, Filter, CheckCircle, Server } from 'lucide-react';

export default function DataInspector() {
  const [activeTab, setActiveTab] = useState('ports');
  const [searchQuery, setSearchQuery] = useState('');
  const [portsData, setPortsData] = useState([]);
  const [routesData, setRoutesData] = useState([]);
  const [commoditiesData, setCommoditiesData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch reference data from local API server or load default fallback JSONs
    const fetchData = async () => {
      setLoading(true);
      try {
        const [pRes, rRes, cRes] = await Promise.all([
          fetch('http://localhost:5001/api/ports').catch(() => null),
          fetch('http://localhost:5001/api/routes').catch(() => null),
          fetch('http://localhost:5001/api/commodities').catch(() => null)
        ]);

        if (pRes && pRes.ok) setPortsData(await pRes.json());
        else setPortsData(defaultPorts);

        if (rRes && rRes.ok) setRoutesData(await rRes.json());
        else setRoutesData(defaultRoutes);

        if (cRes && cRes.ok) setCommoditiesData(await cRes.json());
        else setCommoditiesData(defaultCommodities);

      } catch (e) {
        console.error("Error fetching reference databases", e);
        setPortsData(defaultPorts);
        setRoutesData(defaultRoutes);
        setCommoditiesData(defaultCommodities);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const defaultPorts = [
    { port_id: 'P01', name: 'Port of Shanghai', country: 'China', lat: 31.2304, lon: 121.4737, container_throughput_mteu: 47.3, max_draft_m: 16.0 },
    { port_id: 'P02', name: 'Port of Singapore', country: 'Singapore', lat: 1.3521, lon: 103.8198, container_throughput_mteu: 37.5, max_draft_m: 18.0 },
    { port_id: 'P03', name: 'Port of Rotterdam', country: 'Netherlands', lat: 51.9244, lon: 4.4777, container_throughput_mteu: 15.3, max_draft_m: 24.0 },
    { port_id: 'P04', name: 'Ningbo-Zhoushan', country: 'China', lat: 29.8683, lon: 121.5440, container_throughput_mteu: 31.0, max_draft_m: 17.5 },
    { port_id: 'P05', name: 'Port of Suez', country: 'Egypt', lat: 29.9668, lon: 32.5498, container_throughput_mteu: 6.5, max_draft_m: 20.1 }
  ];

  const defaultRoutes = [
    { route_id: 'R01', name: 'Trans-Pacific Express', origin: 'Shanghai', destination: 'Los Angeles', distance_nm: 5700, avg_transit_days: 14 },
    { route_id: 'R02', name: 'Asia-Europe Mainline', origin: 'Singapore', destination: 'Rotterdam', distance_nm: 8400, avg_transit_days: 26 },
    { route_id: 'R03', name: 'Suez Transit Corridor', origin: 'Port Said', destination: 'Port of Suez', distance_nm: 101, avg_transit_days: 1 }
  ];

  const defaultCommodities = [
    { commodity_id: 'C01', name: 'Semiconductors & Electronics', tier: 1, critical_stockout_days: 5, safety_buffer_days: 10 },
    { commodity_id: 'C02', name: 'Crude Oil', tier: 1, critical_stockout_days: 7, safety_buffer_days: 14 },
    { commodity_id: 'C03', name: 'Automotive Components', tier: 2, critical_stockout_days: 4, safety_buffer_days: 7 }
  ];

  const filteredPorts = portsData.filter(p => 
    p.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    p.country?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredRoutes = routesData.filter(r => 
    r.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    r.route_id?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredCommodities = commoditiesData.filter(c => 
    c.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    c.commodity_id?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      
      {/* Top Banner */}
      <div className="glass-panel p-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white font-mono">SUPPLYPULSE REFERENCE DB INSPECTOR</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Browse structured reference databases loaded in <code className="text-cyan-400">dataset/reference/</code>
            </p>
          </div>

          {/* Search Input */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search ports, routes, commodities..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Database Selector Tabs */}
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-800 font-mono text-xs">
          <button
            onClick={() => setActiveTab('ports')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 ${
              activeTab === 'ports' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-white bg-slate-900'
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            World Ports ({portsData.length})
          </button>
          <button
            onClick={() => setActiveTab('routes')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 ${
              activeTab === 'routes' ? 'bg-indigo-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-white bg-slate-900'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            Shipping Lanes ({routesData.length})
          </button>
          <button
            onClick={() => setActiveTab('commodities')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 ${
              activeTab === 'commodities' ? 'bg-purple-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-white bg-slate-900'
            }`}
          >
            <Package className="w-3.5 h-3.5" />
            Commodities Matrix ({commoditiesData.length})
          </button>
        </div>
      </div>

      {/* Data Table */}
      <div className="glass-panel p-6 overflow-x-auto font-mono text-xs">
        {activeTab === 'ports' && (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 pb-2">
                <th className="p-3">ID</th>
                <th className="p-3">PORT NAME</th>
                <th className="p-3">COUNTRY</th>
                <th className="p-3">LAT / LON</th>
                <th className="p-3">THROUGHPUT (M TEU)</th>
                <th className="p-3">MAX DRAFT (M)</th>
              </tr>
            </thead>
            <tbody>
              {filteredPorts.slice(0, 15).map((port, idx) => (
                <tr key={idx} className="border-b border-slate-900 hover:bg-slate-900/60 transition-all">
                  <td className="p-3 text-cyan-400 font-bold">{port.port_id || `P${idx+1}`}</td>
                  <td className="p-3 text-white font-bold">{port.name}</td>
                  <td className="p-3 text-slate-300">{port.country}</td>
                  <td className="p-3 text-slate-400">{port.lat?.toFixed(2)}, {port.lon?.toFixed(2)}</td>
                  <td className="p-3 text-emerald-400 font-bold">{port.container_throughput_mteu || port.annual_capacity_teu || '12.5'}</td>
                  <td className="p-3 text-amber-400 font-bold">{port.max_draft_m || '15.0'}m</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'routes' && (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 pb-2">
                <th className="p-3">ROUTE ID</th>
                <th className="p-3">ROUTE NAME</th>
                <th className="p-3">ORIGIN - DESTINATION</th>
                <th className="p-3">DISTANCE (NM)</th>
                <th className="p-3">AVG TRANSIT DAYS</th>
              </tr>
            </thead>
            <tbody>
              {filteredRoutes.map((route, idx) => (
                <tr key={idx} className="border-b border-slate-900 hover:bg-slate-900/60 transition-all">
                  <td className="p-3 text-indigo-400 font-bold">{route.route_id}</td>
                  <td className="p-3 text-white font-bold">{route.name || route.route_name}</td>
                  <td className="p-3 text-slate-300">{route.origin} → {route.destination}</td>
                  <td className="p-3 text-cyan-400 font-bold">{route.distance_nm?.toLocaleString()} NM</td>
                  <td className="p-3 text-amber-400 font-bold">{route.avg_transit_days} Days</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'commodities' && (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 pb-2">
                <th className="p-3">ID</th>
                <th className="p-3">COMMODITY NAME</th>
                <th className="p-3">PRIORITY TIER</th>
                <th className="p-3">STOCKOUT THRESHOLD</th>
                <th className="p-3">SAFETY BUFFER DAYS</th>
              </tr>
            </thead>
            <tbody>
              {filteredCommodities.map((comm, idx) => (
                <tr key={idx} className="border-b border-slate-900 hover:bg-slate-900/60 transition-all">
                  <td className="p-3 text-purple-400 font-bold">{comm.commodity_id || `C${idx+1}`}</td>
                  <td className="p-3 text-white font-bold">{comm.name || comm.commodity}</td>
                  <td className="p-3">
                    <span className="bg-purple-950 text-purple-400 border border-purple-800 px-2 py-0.5 rounded font-bold">
                      Tier {comm.tier || 1}
                    </span>
                  </td>
                  <td className="p-3 text-rose-400 font-bold">{comm.critical_stockout_days || 5} Days</td>
                  <td className="p-3 text-emerald-400 font-bold">{comm.safety_buffer_days || 10} Days</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}
