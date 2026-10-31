import React, { useState, useEffect } from 'react';
import { Activity, ShieldAlert, CheckCircle, AlertCircle, FileText, Lock, ChevronDown, ChevronRight, Terminal, RefreshCw } from 'lucide-react';
import { fetchCases, fetchCaseDetail } from '../api';

export default function AgentTrace({ selectedCaseId, onSelectCase }) {
  const [cases, setCases] = useState([]);
  const [activeCaseId, setActiveCaseId] = useState(selectedCaseId);
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState({});

  useEffect(() => {
    loadCases();
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      setActiveCaseId(selectedCaseId);
    }
  }, [selectedCaseId]);

  useEffect(() => {
    if (activeCaseId) {
      loadCaseDetails(activeCaseId);
    }
  }, [activeCaseId]);

  const loadCases = async () => {
    try {
      const list = await fetchCases();
      setCases(list);
      if (list.length > 0 && !activeCaseId) {
        setActiveCaseId(list[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadCaseDetails = async (cid) => {
    setLoading(true);
    try {
      const details = await fetchCaseDetail(cid);
      setCaseData(details);
      // Auto-expand all steps by default
      const exp = {};
      details.steps?.forEach((_, idx) => { exp[idx] = true; });
      setExpandedSteps(exp);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const toggleStep = (idx) => {
    setExpandedSteps(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const getStepBadge = (stepName, status) => {
    if (stepName === "GATE") {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 flex items-center gap-1">
          <Lock className="w-3 h-3" /> PERMISSION GATE (DETERMINISTIC)
        </span>
      );
    }
    if (status === "SUCCESS") {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold bg-teal-100 text-teal-800 border border-teal-300">
          SUCCESS
        </span>
      );
    }
    if (status === "PAUSED") {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
          PAUSED (APPROVAL REQ)
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800 border border-red-300">
        {status}
      </span>
    );
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-4 space-y-4">
      {/* Top Header & Case Selector */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-teal-600" />
            Agent Trace & Execution Inspector
          </h2>
          <p className="text-xs text-slate-500">
            Audit-grade visibility into LLM proposals, Deterministic Permission Gate decisions, Policy RAG citations, and post-action verification.
          </p>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Case ID:</label>
          <select
            value={activeCaseId || ""}
            onChange={(e) => {
              setActiveCaseId(e.target.value);
              if (onSelectCase) onSelectCase(e.target.value);
            }}
            className="bg-slate-50 border border-slate-300 text-slate-800 rounded-lg px-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-teal-500/30 flex-1 sm:flex-initial"
          >
            {cases.map(c => (
              <option key={c.id} value={c.id}>
                {c.id} - {c.txn_id || 'No Txn'} ({c.status})
              </option>
            ))}
          </select>
          <button
            onClick={() => loadCaseDetails(activeCaseId)}
            className="p-1.5 text-slate-600 hover:text-teal-700 hover:bg-slate-100 rounded-lg"
            title="Refresh Trace"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-teal-600" />
          Loading case execution telemetry...
        </div>
      ) : !caseData ? (
        <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
          No cases executed yet. Run a prompt in Customer Chat or trigger a Scenario!
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left 2 Cols: Step-by-Step Execution Timeline */}
          <div className="lg:col-span-2 space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-600 flex items-center justify-between">
              <span>Step-by-Step State Machine Trace</span>
              <span className="text-xs font-normal text-slate-400">{caseData.steps?.length || 0} steps recorded</span>
            </h3>

            {caseData.steps?.map((step, idx) => {
              const isGate = step.step_name === "GATE";
              const isVerify = step.step_name === "VERIFY";
              const isExpanded = !!expandedSteps[idx];
              const state = step.state_data || {};

              return (
                <div
                  key={step.id || idx}
                  className={`bg-white border rounded-xl overflow-hidden shadow-sm transition-all ${
                    isGate
                      ? 'border-amber-300 ring-1 ring-amber-400/30 bg-amber-50/20'
                      : isVerify
                      ? 'border-teal-300 ring-1 ring-teal-400/30'
                      : 'border-slate-200'
                  }`}
                >
                  {/* Step Header */}
                  <div
                    onClick={() => toggleStep(idx)}
                    className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-slate-50/80 transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <button className="text-slate-400 hover:text-slate-600">
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>
                      <span className="w-6 h-6 rounded-full bg-slate-100 text-slate-700 text-xs font-bold flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <span className="font-bold text-sm text-slate-900 tracking-tight">
                        {step.step_name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {getStepBadge(step.step_name, step.status)}
                      <span className="text-[11px] font-mono text-slate-400">
                        {new Date(step.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  {/* Step Body (Expanded) */}
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-1 border-t border-slate-100 text-xs space-y-2.5">
                      {/* Highlighted Amber Box for Deterministic Permission Gate */}
                      {isGate && (
                        <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-950 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-extrabold uppercase tracking-wide flex items-center gap-1.5 text-amber-900">
                              <Lock className="w-3.5 h-3.5 text-amber-700" />
                              Gate Decision: {state.gate_decision}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-200 text-amber-900">
                              {state.reason_code}
                            </span>
                          </div>
                          <p className="text-xs text-amber-900 font-medium">{state.reason_detail}</p>
                          {state.policy_citations?.length > 0 && (
                            <div className="pt-1.5 border-t border-amber-200/60">
                              <span className="font-bold text-[11px] text-amber-800">Citations Enforced:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {state.policy_citations.map((c, ci) => (
                                  <span key={ci} className="px-2 py-0.5 rounded bg-white border border-amber-300 text-amber-900 font-mono text-[10px]">
                                    {c}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Highlighted Teal Box for Post-Action State Re-Check */}
                      {isVerify && (
                        <div className={`p-3 rounded-lg border space-y-1 ${
                          state.verified
                            ? 'bg-teal-50 border-teal-200 text-teal-950'
                            : 'bg-red-50 border-red-200 text-red-950'
                        }`}>
                          <div className="flex items-center justify-between font-bold">
                            <span>Authoritative Post-Action State Re-check</span>
                            <span className="uppercase text-[10px] font-mono">
                              {state.verified ? "VERIFIED RESOLVED" : "VERIFICATION MISMATCH"}
                            </span>
                          </div>
                          <p className="text-xs">
                            Expected: <code className="font-bold">{JSON.stringify(state.expected_status)}</code> | Rechecked Core Status: <code className="font-bold">{state.rechecked_status}</code>
                          </p>
                          {state.reversal_ref && (
                            <p className="text-xs text-teal-800 font-mono font-semibold">
                              Settlement Ref: {state.reversal_ref}
                            </p>
                          )}
                        </div>
                      )}

                      {/* State Data JSON Inspector */}
                      <div>
                        <span className="font-semibold text-slate-500 text-[11px] uppercase tracking-wider block mb-1">
                          Step State Payload (PII Masked):
                        </span>
                        <pre className="bg-slate-900 text-teal-300 p-2.5 rounded-lg text-[11px] font-mono overflow-x-auto max-h-48 leading-relaxed">
                          {JSON.stringify(state, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Right Col: Case Summary & Immutable Audit Log */}
          <div className="space-y-4">
            {/* Case Overview Card */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Case Metadata</h4>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Case ID:</span>
                  <span className="font-mono font-bold text-slate-900">{caseData.case.id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Transaction ID:</span>
                  <span className="font-mono font-bold text-slate-900">{caseData.case.txn_id || 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Customer ID:</span>
                  <span className="font-mono text-slate-700">{caseData.case.customer_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Status:</span>
                  <span className="font-bold text-teal-700">{caseData.case.status}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Outcome:</span>
                  <span className="font-mono font-bold text-slate-800">{caseData.case.outcome || 'IN_PROGRESS'}</span>
                </div>
              </div>

              <div>
                <span className="text-[11px] text-slate-400 block mb-1 font-semibold">Original Complaint:</span>
                <p className="text-xs text-slate-700 bg-slate-50 p-2 rounded border border-slate-200">
                  "{caseData.case.complaint_text}"
                </p>
              </div>
            </div>

            {/* Audit Log Stream */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-teal-600" />
                  Immutable Audit Log ({caseData.audit_logs?.length || 0})
                </h4>
                <span className="text-[10px] text-slate-400">Rule 6 Compliant</span>
              </div>
              <div className="max-h-96 overflow-y-auto space-y-2 pr-1">
                {caseData.audit_logs?.map((log) => (
                  <div key={log.id} className="p-2 rounded bg-slate-50 border border-slate-200 text-[11px] space-y-1">
                    <div className="flex items-center justify-between font-mono">
                      <span className="font-bold text-teal-800">{log.action}</span>
                      <span className="text-[10px] text-slate-400">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="text-slate-500">Actor: <span className="font-semibold text-slate-700">{log.actor}</span></div>
                    {log.decision_reason && (
                      <div className="text-slate-700 italic">"{log.decision_reason}"</div>
                    )}
                    {log.policy_citations?.length > 0 && (
                      <div className="text-[10px] text-amber-700 font-mono">
                        {log.policy_citations.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

