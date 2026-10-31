import React, { useState } from 'react';
import { Send, Shield, CheckCircle2, Clock, AlertTriangle, ArrowRight, Sparkles, RefreshCw, Lock } from 'lucide-react';
import { sendChatMessage } from '../api';

const QUICK_PRESETS = [
  { label: "Scenario A: ₹2,000 Failed (Zomato)", prompt: "₹2,000 debited for my Zomato order TXN-1001, but the app says payment failed. Please refund my money.", customerId: "CUST-4921" },
  { label: "Scenario B: ₹2,000 Pending (Swiggy)", prompt: "I paid ₹2,000 on Swiggy TXN-1002, money left my bank account but Swiggy says waiting for bank confirmation.", customerId: "CUST-8832" },
  { label: "Scenario E: ₹12,000 Approval (Croma)", prompt: "Payment of ₹12,000 for my Croma purchase TXN-1005 failed. Money got cut from my account.", customerId: "CUST-5541" },
  { label: "Scenario F: Verification Mismatch (Uber)", prompt: "My Uber ride TXN-1006 for ₹1,800 failed at payment gateway. Please reverse.", customerId: "CUST-6120" },
  { label: "Scenario H: Hinglish Query (Blinkit)", prompt: "Mera 1500 cut gaya Blinkit TXN-1008 par merchant bola payment fail ho gaya. Paise wapas chahiye.", customerId: "CUST-1190" },
  { label: "Scenario I: General FAQ", prompt: "What does a debit mean? Why do payments fail sometimes?", customerId: "CUST-4921" },
];

const WORKFLOW_STAGES = [
  { id: "UNDERSTAND", label: "Understand" },
  { id: "INVESTIGATE", label: "Investigate" },
  { id: "DECIDE", label: "Decide" },
  { id: "GATE", label: "Gate (Policy)" },
  { id: "ACT", label: "Act" },
  { id: "VERIFY", label: "Verify" },
  { id: "INFORM", label: "Inform" },
];

export default function CustomerChat({ onCaseCreated, onSelectTraceCase }) {
  const [messages, setMessages] = useState([
    {
      sender: "saarthi",
      text: "Hello! I am Saarthi, your autonomous payments resolution teammate. If your account was debited for a failed or pending payment, describe what happened. I will investigate directly with the banking switch and verify resolution.",
      timestamp: "Just now",
      statusChip: null,
      steps: []
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [currentCustomerId, setCurrentCustomerId] = useState("CUST-4921");
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [latestSteps, setLatestSteps] = useState([]);

  const handleSend = async (textToSend = null, customCustId = null) => {
    const text = textToSend || inputText;
    if (!text.trim() || isInvestigating) return;

    const custId = customCustId || currentCustomerId;
    setInputText("");
    setIsInvestigating(true);
    setActiveStepIndex(0);
    setLatestSteps([]);

    // Add user message to stream
    const userMsg = {
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMsg]);

    // Animate stage tracker realistically
    const stageTimer1 = setTimeout(() => setActiveStepIndex(1), 300);
    const stageTimer2 = setTimeout(() => setActiveStepIndex(2), 600);
    const stageTimer3 = setTimeout(() => setActiveStepIndex(3), 900);

    try {
      const response = await sendChatMessage(text, custId);

      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);
      setActiveStepIndex(6); // completed

      const saarthiMsg = {
        sender: "saarthi",
        text: response.customer_message,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        statusChip: response.status_chip,
        caseId: response.case_id,
        outcome: response.outcome,
        steps: response.steps || [],
        brief: response.case_brief
      };

      setMessages(prev => [...prev, saarthiMsg]);
      setLatestSteps(response.steps || []);

      if (response.case_id && onCaseCreated) {
        onCaseCreated(response.case_id);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          sender: "saarthi",
          text: `Investigation halted: ${err.message}. An escalation team has been notified.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          statusChip: "ESCALATED"
        }
      ]);
    } finally {
      setIsInvestigating(false);
    }
  };

  const renderStatusBadge = (chip) => {
    if (!chip) return null;
    if (chip === "RESOLVED_VERIFIED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-teal-100 text-teal-800 border border-teal-300 shadow-sm">
          <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
          Resolved (Verified via Banking Switch)
        </span>
      );
    }
    if (chip === "AWAITING_STATUS_CHANGE") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800 border border-indigo-300 shadow-sm">
          <Clock className="w-3.5 h-3.5 text-indigo-600" />
          Awaiting Status Change (Unconfirmed)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 shadow-sm">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
        Escalated to Human Operations
      </span>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4.5rem)] max-w-5xl mx-auto px-4 py-4">
      {/* Quick Scenario Pills */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" /> Demo Scenario Quick Starters:
          </span>
          <span className="text-xs text-slate-400">Customer: {currentCustomerId}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {QUICK_PRESETS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => {
                setCurrentCustomerId(p.customerId);
                handleSend(p.prompt, p.customerId);
              }}
              disabled={isInvestigating}
              className="px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-teal-500 hover:text-teal-700 hover:bg-teal-50/50 shadow-sm transition-all disabled:opacity-50"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Container */}
      <div className="flex-1 bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col overflow-hidden">
        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm ${
                  msg.sender === 'user'
                    ? 'bg-slate-900 text-white rounded-br-none'
                    : 'bg-slate-50 border border-slate-200 text-slate-800 rounded-bl-none'
                }`}
              >
                {msg.sender === 'saarthi' && (
                  <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-slate-200/60 text-xs">
                    <span className="font-bold text-teal-800 flex items-center gap-1.5">
                      <Shield className="w-3.5 h-3.5 text-teal-600" /> SAARTHI Core
                    </span>
                    <span className="text-slate-400 text-[11px]">{msg.timestamp}</span>
                  </div>
                )}

                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>

                {msg.statusChip && (
                  <div className="mt-3 pt-2 border-t border-slate-200/80 flex flex-wrap items-center justify-between gap-2">
                    {renderStatusBadge(msg.statusChip)}
                    {msg.caseId && onSelectTraceCase && (
                      <button
                        onClick={() => onSelectTraceCase(msg.caseId)}
                        className="text-xs font-semibold text-teal-700 hover:text-teal-900 underline flex items-center gap-1"
                      >
                        Inspect Agent Trace <ArrowRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Live Step Progress Indicator */}
          {isInvestigating && (
            <div className="p-4 bg-teal-50/60 border border-teal-200 rounded-xl my-3">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-teal-800 flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-teal-600 animate-spin" />
                  Saarthi Autonomous Loop Running...
                </span>
                <span className="text-xs font-mono text-teal-700">Evaluating Deterministic Policy</span>
              </div>
              <div className="grid grid-cols-7 gap-1 sm:gap-2">
                {WORKFLOW_STAGES.map((stg, idx) => {
                  const isCurrent = idx === activeStepIndex;
                  const isDone = idx < activeStepIndex;
                  const isGate = stg.id === "GATE";
                  return (
                    <div key={stg.id} className="text-center">
                      <div
                        className={`h-2 rounded-full mb-1 transition-all duration-300 ${
                          isDone
                            ? isGate ? 'bg-amber-500' : 'bg-teal-600'
                            : isCurrent
                            ? isGate ? 'bg-amber-400 animate-pulse' : 'bg-teal-400 animate-pulse'
                            : 'bg-slate-200'
                        }`}
                      />
                      <span className={`text-[10px] font-semibold block truncate ${
                        isDone || isCurrent ? (isGate ? 'text-amber-800' : 'text-teal-900') : 'text-slate-400'
                      }`}>
                        {stg.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Input Bar & Strict Security Guarantee */}
        <div className="p-3 sm:p-4 bg-slate-50 border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Describe your payment complaint (e.g., '₹2,000 debited for Zomato TXN-1001, payment failed')..."
              disabled={isInvestigating}
              className="flex-1 bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-600 transition-all placeholder:text-slate-400"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isInvestigating}
              className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-semibold transition-all shadow-sm hover:shadow flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>Resolve</span>
              <Send className="w-4 h-4" />
            </button>
          </form>

          {/* Non-negotiable Rule 4 Output Guard Notice */}
          <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500 px-1">
            <span className="flex items-center gap-1 text-slate-600 font-medium">
              <Lock className="w-3.5 h-3.5 text-teal-600" />
              Guaranteed Safety: Saarthi will never ask for OTP, PIN, CVV, or card number.
            </span>
            <span className="text-slate-400 hidden sm:inline">
              Deterministic Application Gate Enforced
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

