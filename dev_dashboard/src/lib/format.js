// Display helpers shared by pages. Missing values are shown as "—", never filled in.
export const API_BASE = 'http://localhost:5001';
export const NA = '—';
export const fmtUsd = (v) => (v === null || v === undefined || Number.isNaN(v)) ? NA : `$${Math.round(v).toLocaleString()}`;
export const fmtNum = (v, digits = 2) => (v === null || v === undefined || Number.isNaN(v)) ? NA : (+v).toFixed(digits);
export const hasPlan = (r) => r?.status === 'completed';
