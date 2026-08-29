import React, { useState } from 'react';
import { Copy, Check, Search, ChevronDown, ChevronRight, Eye, Code } from 'lucide-react';

export default function JsonViewer({ data, title = "PAYLOAD JSON" }) {
  const [copied, setCopied] = useState(false);
  const [search, setSearch] = useState('');
  const [rawView, setRawView] = useState(false);
  const [collapsedKeys, setCollapsedKeys] = useState({});

  const jsonString = JSON.stringify(data, null, 2) || '{}';
  const lines = jsonString.split('\n');

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleKey = (key) => {
    setCollapsedKeys(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Basic syntax highlighter helper
  const renderHighlightedLine = (line) => {
    const keyMatch = line.match(/^(\s*)(".*?"):(.*)/);
    if (keyMatch) {
      const [, indent, key, value] = keyMatch;
      let valSpan = <span className="text-slate-300">{value}</span>;
      if (value.trim().startsWith('"')) valSpan = <span className="json-string">{value}</span>;
      else if (/^\s*(true|false)/.test(value)) valSpan = <span className="json-boolean">{value}</span>;
      else if (/^\s*\d+/.test(value)) valSpan = <span className="json-number">{value}</span>;
      else if (/^\s*null/.test(value)) valSpan = <span className="json-null">{value}</span>;

      return (
        <>
          <span>{indent}</span>
          <span className="json-key">{key}</span>:
          {valSpan}
        </>
      );
    }
    return <span className="text-slate-300">{line}</span>;
  };

  return (
    <div className="panel-dark overflow-hidden font-mono text-xs">
      
      {/* Header Bar */}
      <div className="bg-[#10161D] px-4 py-2 border-b border-white/5 flex items-center justify-between gap-2">
        <span className="text-slate-400 font-bold flex items-center gap-1.5">
          <Code className="w-3.5 h-3.5 text-cyan-400" />
          {title}
        </span>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="w-3 h-3 text-slate-500 absolute left-2 top-2" />
            <input
              type="text"
              placeholder="Search JSON..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-[#080B10] border border-white/10 rounded pl-7 pr-2 py-0.5 text-[11px] text-white focus:outline-none focus:border-cyan-500 w-28 sm:w-36"
            />
          </div>

          {/* Toggle Raw */}
          <button
            onClick={() => setRawView(!rawView)}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-white/5"
            title={rawView ? "Formatted View" : "Raw JSON View"}
          >
            <Eye className="w-3.5 h-3.5" />
          </button>

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="px-2.5 py-1 bg-white/5 hover:bg-white/10 text-slate-300 rounded border border-white/10 flex items-center gap-1 text-[11px] transition-all"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied ✓' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Code Container */}
      <div className="p-3 bg-[#080B10] overflow-x-auto max-h-72 leading-relaxed">
        {lines.map((line, idx) => {
          if (search && !line.toLowerCase().includes(search.toLowerCase())) return null;
          return (
            <div key={idx} className="flex gap-3 hover:bg-white/5 px-1 rounded">
              <span className="text-slate-600 select-none w-8 text-right shrink-0">{idx + 1}</span>
              <pre className="whitespace-pre">
                {rawView ? line : renderHighlightedLine(line)}
              </pre>
            </div>
          );
        })}
      </div>

    </div>
  );
}
