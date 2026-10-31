import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CustomerChat from './components/CustomerChat';
import AgentTrace from './components/AgentTrace';
import HumanConsole from './components/HumanConsole';
import AdminPanel from './components/AdminPanel';
import MetricsDashboard from './components/MetricsDashboard';
import { fetchPendingApprovals } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);

  const checkPendingApprovals = async () => {
    try {
      const apprs = await fetchPendingApprovals();
      setPendingApprovalsCount(apprs.length);
    } catch (e) {
      // Backend may be starting up
    }
  };

  useEffect(() => {
    checkPendingApprovals();
    const interval = setInterval(checkPendingApprovals, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleCaseCreated = (caseId) => {
    setSelectedCaseId(caseId);
    checkPendingApprovals();
  };

  const handleSelectTraceCase = (caseId) => {
    setSelectedCaseId(caseId);
    setActiveTab('trace');
  };

  const handleSelectScenario = (scenario) => {
    setActiveTab('chat');
    // Set a custom event or let user run from chat quick pill
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingApprovalsCount={pendingApprovalsCount}
      />

      <main className="flex-1">
        {activeTab === 'chat' && (
          <CustomerChat
            onCaseCreated={handleCaseCreated}
            onSelectTraceCase={handleSelectTraceCase}
          />
        )}

        {activeTab === 'trace' && (
          <AgentTrace
            selectedCaseId={selectedCaseId}
            onSelectCase={(id) => setSelectedCaseId(id)}
          />
        )}

        {activeTab === 'human' && (
          <HumanConsole
            onCaseUpdated={checkPendingApprovals}
          />
        )}

        {activeTab === 'scenarios' && (
          <AdminPanel
            onSelectScenario={handleSelectScenario}
          />
        )}

        {activeTab === 'metrics' && (
          <MetricsDashboard />
        )}
      </main>
    </div>
  );
}
