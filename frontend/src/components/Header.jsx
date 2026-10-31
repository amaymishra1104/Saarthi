import React from 'react';
import { ShieldCheck, MessageSquare, Activity, UserCheck, Sliders, BarChart3, Lock } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, pendingApprovalsCount = 0 }) {
  const tabs = [
    { id: 'chat', label: 'Customer Chat', icon: MessageSquare },
    { id: 'trace', label: 'Agent Trace', icon: Activity },
    { 
      id: 'human', 
      label: 'Human Console', 
      icon: UserCheck,
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : null 
    },
    { id: 'scenarios', label: 'Scenarios & Chaos', icon: Sliders },
    { id: 'metrics', label: 'Honest Metrics', icon: BarChart3 },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Product Tagline */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-700 to-teal-500 flex items-center justify-center text-white shadow-md shadow-teal-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-xl text-slate-900 tracking-tight">SAARTHI</span>
                <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                  Autonomous
                </span>
                <span className="text-xs uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
                  <Lock className="w-3 h-3" /> Gate Protected
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                Don't automate the conversation. <span className="font-semibold text-teal-700">Automate the resolution.</span>
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-1 sm:space-x-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-teal-50 text-teal-800 border border-teal-300 shadow-sm font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
                  <span className="hidden md:inline">{tab.label}</span>
                  {tab.badge && (
                    <span className="ml-1.5 px-1.5 py-0.5 text-xs font-bold rounded-full bg-amber-500 text-white animate-pulse">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}

