import React, { useState } from 'react';
import { Building2, MessageSquare, LayoutDashboard } from 'lucide-react';
import CitizenChat from './components/CitizenChat';
import AdminDashboard from './components/AdminDashboard';

export default function App() {
  const [view, setView] = useState<'citizen' | 'admin'>('citizen');

  return (
    <div className="min-h-screen flex flex-col bg-slate-100">
      <header className="bg-slate-900 text-white px-6 py-3.5 shadow-md">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="bg-blue-600 p-2 rounded-xl">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight">
                Smart City Citizen Service Chatbot
              </h1>
              <p className="text-[11px] text-slate-400">
                Citation-Backed RAG • Multimodal 311 Triage • PostGIS 50m Deduplication
              </p>
            </div>
          </div>

          <nav className="flex items-center bg-slate-800 p-1 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setView('citizen')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition ${
                view === 'citizen' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Citizen Portal</span>
            </button>
            <button
              onClick={() => setView('admin')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition ${
                view === 'admin' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span>Officer Dashboard</span>
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1 p-4 md:p-6">
        {view === 'citizen' ? <CitizenChat /> : <AdminDashboard />}
      </main>
    </div>
  );
}
