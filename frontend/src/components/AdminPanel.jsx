import React, { useState, useEffect } from 'react';
import { Sliders, Flame, RotateCcw, Play, CheckCircle2, AlertOctagon, HelpCircle, Shield, ArrowRight } from 'lucide-react';
import { fetchScenarios, fetchChaosState, updateChaosState, resetPrototype } from '../api';

export default function AdminPanel({ onSelectScenario }) {
  const [scenarios, setScenarios] = useState([]);
  const [chaos, setChaos] = useState({
    lookup_fail: false,
    api_timeout: false,
    ambiguous_status: false,
    duplicate_attempt: false,
    verification_mismatch: false
  });
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [scList, chState] = await Promise.all([
        fetchScenarios(),
        fetchChaosState()
      ]);
      setScenarios(scList);
      setChaos(chState);
    } catch (e) {
      console.error(e);
    }
  };

  const toggleChaos = async (key) => {
    const updated = !chaos[key];
    const newState = { ...chaos, [key]: updated };
    setChaos(newState);
    try {
      await updateChaosState({ [key]: updated });
      setActionMessage({ type: "info", text: `Chaos switch '${key}' set to ${updated ? 'ENABLED' : 'DISABLED'}` });
    } catch (e) {
      console.error(e);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Reset all test cases, audit logs, and transaction states to pristine seed data?")) return;
    setLoading(true);
    try {
      await resetPrototype();
      await loadData();
      setActionMessage({ type: "success", text: "Successfully reset database and mock payments core to pristine seed data." });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-4 space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-teal-600" />
            Admin & Demo Scenario Control Center
          </h2>
          <p className="text-xs text-slate-500">
            Trigger benchmark scenarios A through I or inject upstream banking chaos to verify safety guardrails.
          </p>
        </div>

        <button
          onClick={handleReset}
          disabled={loading}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 border border-slate-300 shadow-sm disabled:opacity-50"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset All Prototype Data</span>
        </button>
      </div>

      {actionMessage && (
        <div className={`p-3 rounded-lg text-xs font-semibold flex items-center justify-between ${
          actionMessage.type === 'success' ? 'bg-teal-50 border border-teal-300 text-teal-900' : 'bg-slate-100 border border-slate-300 text-slate-800'
        }`}>
          <span>{actionMessage.text}</span>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>
      )}

      {/* Upstream Chaos Simulation Switchboard */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className="w-5 h-5 text-amber-500" />
            <h3 className="font-bold text-sm text-slate-900">
              Payments Switch Chaos Engineering Controls
            </h3>
          </div>
          <span className="text-[11px] font-mono font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
            Failure Matrix Verification
          </span>
        </div>
        <p className="text-xs text-slate-500">
          Toggle upstream banking anomalies to verify that Saarthi strictly adheres to the non-negotiable failure matrix rules (never infer status, bounded retry, post-action verify).
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-2">
          {[
            { id: "lookup_fail", label: "Lookup 500 Failure", desc: "Core switch lookup returns 500/404" },
            { id: "api_timeout", label: "Gateway 504 Timeout", desc: "Upstream switch times out after retry limit" },
            { id: "ambiguous_status", label: "Ambiguous / Pending", desc: "Forces status to UNCONFIRMED" },
            { id: "duplicate_attempt", label: "Duplicate Debits", desc: "Forces duplicate debit conditions" },
            { id: "verification_mismatch", label: "Verification Mismatch", desc: "Reversal API succeeds but state remains unchanged" },
          ].map((item) => {
            const isEnabled = !!chaos[item.id];
            return (
              <div
                key={item.id}
                onClick={() => toggleChaos(item.id)}
                className={`p-3 rounded-xl border cursor-pointer transition-all ${
                  isEnabled
                    ? 'bg-amber-50 border-amber-400 ring-2 ring-amber-400/20'
                    : 'bg-slate-50 border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs text-slate-900">{item.label}</span>
                  <span className={`w-3 h-3 rounded-full ${isEnabled ? 'bg-amber-500 animate-ping' : 'bg-slate-300'}`} />
                </div>
                <p className="text-[11px] text-slate-500 leading-snug">{item.desc}</p>
                <div className="mt-2 text-[10px] font-mono font-bold uppercase tracking-wider">
                  Status: <span className={isEnabled ? 'text-amber-800' : 'text-slate-400'}>{isEnabled ? 'ACTIVE' : 'OFF'}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Seeded Scenarios Benchmark Matrix */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-sm text-slate-900">
            Pitch Deck Benchmark Scenarios (A through I)
          </h3>
          <p className="text-xs text-slate-500">
            Click "Run Scenario" to load the complaint and launch the autonomous loop in Customer Chat.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((sc) => (
            <div
              key={sc.scenario_id}
              className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-teal-400 hover:shadow-md transition-all flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-bold text-xs text-slate-900">{sc.title}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800">
                    {sc.category}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mb-2 leading-relaxed">
                  {sc.description}
                </p>
                <div className="text-[11px] font-mono text-slate-500 space-y-0.5 bg-white p-2 rounded border border-slate-200/80">
                  <div>Customer: <span className="font-semibold text-slate-800">{sc.customer_id}</span></div>
                  <div>Txn: <span className="font-semibold text-slate-800">{sc.txn_id || 'N/A'}</span> (₹{sc.amount})</div>
                  <div>Expected: <span className="font-semibold text-teal-700">{sc.expected_outcome}</span></div>
                </div>
              </div>

              <button
                onClick={() => onSelectScenario(sc)}
                className="w-full py-2 bg-white hover:bg-teal-600 hover:text-white text-teal-700 border border-teal-300 rounded-lg text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-1.5"
              >
                <span>Run Scenario</span>
                <Play className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

