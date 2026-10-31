const API_BASE = "http://localhost:8000/api";

export async function sendChatMessage(message, customerId = "CUST-4921", caseId = null) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, customer_id: customerId, case_id: caseId })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to process message with Saarthi engine");
  }
  return res.json();
}

export async function fetchCases(status = null) {
  const url = status ? `${API_BASE}/cases?status=${status}` : `${API_BASE}/cases`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch cases");
  return res.json();
}

export async function fetchCaseDetail(caseId) {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) throw new Error(`Failed to fetch details for case ${caseId}`);
  return res.json();
}

export async function fetchPendingApprovals() {
  const res = await fetch(`${API_BASE}/approvals`);
  if (!res.ok) throw new Error("Failed to fetch pending approvals");
  return res.json();
}

export async function submitApprovalAction(approvalId, decision, notes = "") {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, notes, supervisor_id: "SUPV-OPS-01" })
  });
  if (!res.ok) throw new Error("Failed to submit approval action");
  return res.json();
}

export async function sendAgentReply(caseId, message) {
  const res = await fetch(`${API_BASE}/cases/${caseId}/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  if (!res.ok) throw new Error("Failed to deliver supervisor reply");
  return res.json();
}

export async function fetchChaosState() {
  const res = await fetch(`${API_BASE}/admin/chaos`);
  if (!res.ok) throw new Error("Failed to fetch chaos settings");
  return res.json();
}

export async function updateChaosState(updates) {
  const res = await fetch(`${API_BASE}/admin/chaos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates)
  });
  if (!res.ok) throw new Error("Failed to update chaos settings");
  return res.json();
}

export async function resetPrototype() {
  const res = await fetch(`${API_BASE}/admin/reset`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to reset prototype");
  return res.json();
}

export async function fetchScenarios() {
  const res = await fetch(`${API_BASE}/admin/scenarios`);
  if (!res.ok) throw new Error("Failed to fetch scenario presets");
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error("Failed to fetch real prototype metrics");
  return res.json();
}

