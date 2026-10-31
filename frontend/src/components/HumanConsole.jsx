import React, { useState, useEffect } from 'react';
import { UserCheck, ShieldAlert, CheckCircle, XCircle, Send, FileText, AlertTriangle, ArrowRight, RefreshCw, MessageSquare } from 'lucide-react';
import { fetchPendingApprovals, submitApprovalAction, fetchCases, fetchCaseDetail, sendAgentReply } from '../api';

export default function HumanConsole({ onCaseUpdated }) {
  const [approvals, setApprovals] = useState([]);
  const [escalatedCases, setEscalatedCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [activeTab, setActiveTab] = useState("approvals"); // "approvals" | "queue"
  const [loading, setLoading] = useState(false);
  const [actionNotes, setActionNotes] = useState("");
  const [replyMessage, setReplyMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusNotification, setStatusNotification] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [apprs, cases] = await Promise.all([
        fetchPendingApprovals(),
        fetchCases()
      ]);
      setApprovals(apprs);
      const escalated = cases.filter(c => c.status === "ESCALATED" || c.status === "AWAITING_STATUS_CHANGE" || c.status === "PENDING_APPROVAL");
      setEscalatedCases(escalated);

      if (apprs.length > 0) {
        loadDetail(apprs[0].case_id);
      } else if (escalated.length > 0) {
        loadDetail(escalated[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (cid) => {
    try {
      const detail = await fetchCaseDetail(cid);
      setSelectedCase(detail);
    } catch (e) {
      console.error(e);
    }
  };

  const handleApproval = async (approvalId, decision) => {
    setIsSubmitting(true);
    setStatusNotification(null);
    try {
      const res = await submitApprovalAction(approvalId, decision, actionNotes);
      setStatusNotification({
        type: decision === "APPROVE" ? "success" : "warning",
        message: res.message
      });
      setActionNotes("");
      await loadData();
      if (onCaseUpdated) onCaseUpdated();
    } catch (err) {
      setStatusNotification({ type: "error", message: err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendReply = async () => {
    if (!replyMessage.trim() || !selectedCase) return;
    setIsSubmitting(true);
    try {
      await sendAgentReply(selectedCase.case.id, replyMessage);
      setStatusNotification({ type: "success", message: "Reply successfully delivered to customer." });
      setReplyMessage("");
      await loadDetail(selectedCase.case.id);
    } catch (err) {
      setStatusNotification({ type: "error", message: err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-4 space-y-4">
      {/* Console Top Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-amber-600" />
            Human Agent & Supervisor Operations Console
          </h2>
          <p className="text-xs text-slate-500">
            Saarthi escalates when approval is required, risk is flagged, status is unconfirmed, or verification fails.
            Human operators start where Saarthi stopped.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => { setActiveTab("approvals"); }}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === "approvals"
                ? "bg-amber-100 text-amber-900 border border-amber-300 shadow-sm"
                : "bg-slate-50 text-slate-600 hover:bg-slate-100"
            }`}
          >
            <span>Approvals Queue</span>
            {approvals.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-500 text-white">
                {approvals.length}
              </span>
            )}
          </button>
          <button
            onClick={() => { setActiveTab("queue"); }}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === "queue"
                ? "bg-teal-100 text-teal-900 border border-teal-300 shadow-sm"
                : "bg-slate-50 text-slate-600 hover:bg-slate-100"
            }`}
          >
            <span>Escalation Ledger</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">
              {escalatedCases.length}
            </span>
          </button>
          <button
            onClick={loadData}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {statusNotification && (
        <div className={`p-3 rounded-xl text-xs font-semibold flex items-center justify-between ${
          statusNotification.type === 'success'
            ? 'bg-teal-50 border border-teal-300 text-teal-900'
            : statusNotification.type === 'warning'
            ? 'bg-amber-50 border border-amber-300 text-amber-900'
            : 'bg-red-50 border border-red-300 text-red-900'
        }`}>
          <span>{statusNotification.message}</span>
          <button onClick={() => setStatusNotification(null)} className="text-slate-400 hover:text-slate-700">✕</button>
        </div>
      )}

      {/* Main Grid: Queue on Left, Case Brief & Action on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Col: Queue */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
            {activeTab === "approvals" ? "High-Value Authorization Queue" : "Active Escalations"}
          </h3>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {activeTab === "approvals" ? (
              approvals.length === 0 ? (
                <div className="text-center py-10 text-xs text-slate-400">
                  <CheckCircle className="w-8 h-8 text-teal-500 mx-auto mb-2 opacity-60" />
                  No pending supervisor authorizations. All auto-limits satisfied!
                </div>
              ) : (
                approvals.map((appr) => {
                  const isSelected = selectedCase?.case?.id === appr.case_id;
                  return (
                    <div
                      key={appr.id}
                      onClick={() => loadDetail(appr.case_id)}
                      className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                        isSelected
                          ? "bg-amber-50 border-amber-300 ring-1 ring-amber-400"
                          : "bg-slate-50 border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between font-bold text-slate-900 mb-1">
                        <span>{appr.case_id}</span>
                        <span className="text-amber-800 font-mono">₹{appr.amount.toLocaleString()}</span>
                      </div>
                      <div className="text-slate-500 text-[11px] mb-1">
                        Txn: <span className="font-mono text-slate-700">{appr.txn_id}</span>
                      </div>
                      <p className="text-slate-600 line-clamp-2 text-[11px]">
                        {appr.gate_reason}
                      </p>
                    </div>
                  );
                })
              )
            ) : (
              escalatedCases.length === 0 ? (
                <div className="text-center py-10 text-xs text-slate-400">
                  No escalated cases in current queue.
                </div>
              ) : (
                escalatedCases.map((ec) => {
                  const isSelected = selectedCase?.case?.id === ec.id;
                  return (
                    <div
                      key={ec.id}
                      onClick={() => loadDetail(ec.id)}
                      className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                        isSelected
                          ? "bg-teal-50 border-teal-300 ring-1 ring-teal-400"
                          : "bg-slate-50 border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between font-bold text-slate-900 mb-1">
                        <span>{ec.id}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-200 text-slate-800">
                          {ec.status}
                        </span>
                      </div>
                      <div className="text-slate-500 text-[11px] mb-1">
                        Txn: <span className="font-mono text-slate-700">{ec.txn_id || "Unassigned"}</span>
                      </div>
                      <p className="text-slate-600 line-clamp-2 text-[11px]">
                        {ec.complaint_text}
                      </p>
                    </div>
                  );
                })
              )
            )}
          </div>
        </div>

        {/* Right 2 Cols: Structured Case Brief & Supervisor Action */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedCase ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-xs text-slate-500">
              Select a case from the queue to review the Structured Case Brief.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Supervisor Action Box if Pending Approval */}
              {selectedCase.case.status === "PENDING_APPROVAL" && (
                <div className="bg-amber-50/80 border border-amber-300 rounded-xl p-4 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-extrabold text-sm text-amber-900 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      Supervisor Authorization Required (Tier 2 Threshold)
                    </span>
                    <span className="text-xs font-mono font-bold text-amber-900 bg-amber-200/80 px-2 py-0.5 rounded">
                      Action: initiate_reversal
                    </span>
                  </div>

                  <p className="text-xs text-amber-950 font-medium leading-relaxed">
                    Saarthi's deterministic permission gate halted automated execution because this amount exceeds the ₹5,000 threshold.
                    Review the Case Brief below. If approved, Saarthi will autonomously trigger the reversal and perform post-action verification.
                  </p>

                  <div className="flex flex-col sm:flex-row items-center gap-2 pt-2 border-t border-amber-200/80">
                    <input
                      type="text"
                      placeholder="Optional supervisor notes or verification reference..."
                      value={actionNotes}
                      onChange={(e) => setActionNotes(e.target.value)}
                      className="flex-1 bg-white border border-amber-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/30"
                    />
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <button
                        onClick={() => {
                          const appr = approvals.find(a => a.case_id === selectedCase.case.id);
                          if (appr) handleApproval(appr.id, "APPROVE");
                        }}
                        disabled={isSubmitting}
                        className="flex-1 sm:flex-initial px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-1.5 disabled:opacity-50"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Approve Reversal</span>
                      </button>
                      <button
                        onClick={() => {
                          const appr = approvals.find(a => a.case_id === selectedCase.case.id);
                          if (appr) handleApproval(appr.id, "REJECT");
                        }}
                        disabled={isSubmitting}
                        className="flex-1 sm:flex-initial px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-1.5 disabled:opacity-50"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Case Brief Viewer */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-teal-600" />
                    <h3 className="font-bold text-sm text-slate-900">
                      Structured Case Brief: {selectedCase.case.id}
                    </h3>
                  </div>
                  <span className="text-xs text-slate-500">
                    Status: <span className="font-bold text-slate-800">{selectedCase.case.status}</span>
                  </span>
                </div>

                {selectedCase.case.case_brief ? (
                  <div className="prose prose-sm max-w-none text-xs text-slate-700 space-y-3 whitespace-pre-wrap bg-slate-50/70 p-4 rounded-xl border border-slate-200 font-mono">
                    {selectedCase.case.case_brief}
                  </div>
                ) : (
                  <div className="p-6 text-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                    No structured brief was required for this case (fully automated resolution).
                  </div>
                )}

                {/* Direct Reply to Customer Form */}
                <div className="pt-3 border-t border-slate-100 space-y-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
                    Human Agent Reply to Customer
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Send a direct update to the customer (Output Guard protected)..."
                      value={replyMessage}
                      onChange={(e) => setReplyMessage(e.target.value)}
                      className="flex-1 bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500/30 placeholder:text-slate-400"
                    />
                    <button
                      onClick={handleSendReply}
                      disabled={!replyMessage.trim() || isSubmitting}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all flex items-center gap-1 disabled:opacity-50"
                    >
                      <span>Send</span>
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

