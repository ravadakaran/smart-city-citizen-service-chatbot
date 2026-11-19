import React, { useState } from 'react';
import {
  Send,
  Camera,
  MapPin,
  Mic,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  BookOpen,
  X,
} from 'lucide-react';
import { sendChatMessage, submitGrievance } from '../api';
import { ChatMessage } from '../types';

const QUICK_PROMPTS = [
  'What is the senior citizen property tax rebate?',
  'Check utility dues for PROP-2026-001',
  'Track ticket 11111111-1111-1111-1111-111111111101',
  'What documents are required for a retail trade license?',
];

export default function CitizenChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      sender: 'bot',
      text: 'Welcome to the Smart City Citizen Service Portal. Ask me about property tax, trade licenses, water supply, transit passes, utility dues—or click **Report 311 Issue** to submit a geotagged civic photo.',
      citations: ['Smart City Citizen Service Charter 2026'],
      grounded: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [desc, setDesc] = useState('');
  const [lat, setLat] = useState('12.8231');
  const [lon, setLon] = useState('80.0442');
  const [submitting311, setSubmitting311] = useState(false);
  const [triageError, setTriageError] = useState<string | null>(null);

  const handleSend = async (overrideText?: string) => {
    const query = (overrideText ?? input).trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      sender: 'citizen',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    if (!overrideText) setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage('citizen-session-1', query);
      if (res.metadata?.open_grievance_drawer) {
        setShowModal(true);
      }
      const botMsg: ChatMessage = {
        id: crypto.randomUUID(),
        sender: 'bot',
        text: res.reply,
        citations: res.citations,
        grounded: res.grounded,
        intent: res.intent,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'bot',
          text: 'Backend service is unreachable. Please verify FastAPI is running on port 8000.',
          grounded: false,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleUseBrowserGPS = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      setLat(pos.coords.latitude.toFixed(6));
      setLon(pos.coords.longitude.toFixed(6));
    });
  };

  const handleVoiceInput = () => {
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: new () => { lang: string; onresult: (e: { results: { transcript: string }[][] }) => void; start: () => void }; webkitSpeechRecognition?: new () => { lang: string; onresult: (e: { results: { transcript: string }[][] }) => void; start: () => void } }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => { lang: string; onresult: (e: { results: { transcript: string }[][] }) => void; start: () => void } }).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
    };
    recognition.start();
  };

  const handleGrievanceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!photo || !desc.trim()) return;
    setSubmitting311(true);
    setTriageError(null);

    try {
      const fd = new FormData();
      fd.append('citizen_id', 'citizen-101');
      fd.append('description', desc);
      fd.append('lat', lat);
      fd.append('lon', lon);
      fd.append('photo', photo);

      const res = await submitGrievance(fd);
      const { triage, ticket } = res;
      const summary =
        ticket.action === 'MERGED_UPVOTE'
          ? `**Geospatial Deduplication Match (Within 50m / 48h):** Your report was merged into existing **${triage.department_code}** ticket \`${ticket.ticket_id}\` (**${triage.issue_subcategory}**, Severity: **${ticket.severity}**). Community Upvotes increased to **${ticket.upvote_count}**.`
          : `**New 311 Civic Ticket Created:** ID \`${ticket.ticket_id}\` routed to **${triage.department_code}** (**${triage.issue_subcategory}**, Severity: **${ticket.severity}**). ${
              ticket.escalated ? 'CRITICAL safety hazard alert dispatched immediately!' : ''
            }`;

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'bot',
          text: summary,
          citations: [`VLM Confidence: ${(triage.confidence * 100).toFixed(1)}% — ${triage.reasoning}`],
          grounded: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
      setShowModal(false);
      setPhoto(null);
      setDesc('');
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to verify or submit civic grievance.';
      setTriageError(detail);
    } finally {
      setSubmitting311(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[78vh]">
      <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center gap-2 overflow-x-auto">
        <span className="text-xs font-semibold text-slate-500 shrink-0">Quick Queries:</span>
        {QUICK_PROMPTS.map((q) => (
          <button
            key={q}
            onClick={() => handleSend(q)}
            className="text-xs bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 rounded-full px-3 py-1 shrink-0 transition"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.sender === 'citizen' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.sender === 'citizen'
                  ? 'bg-blue-700 text-white rounded-br-none'
                  : 'bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200'
              }`}
            >
              <div className="whitespace-pre-line">{m.text}</div>

              {m.citations && m.citations.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-slate-200/80 space-y-1">
                  <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Verified Sources</span>
                  </div>
                  {m.citations.map((c, idx) => (
                    <div
                      key={idx}
                      className="text-[11px] text-slate-600 bg-white px-2 py-1 rounded border border-slate-200 flex items-center gap-1.5"
                    >
                      <BookOpen className="w-3 h-3 text-blue-600 shrink-0" />
                      <span>{c}</span>
                    </div>
                  ))}
                </div>
              )}

              <div
                className={`text-[10px] mt-1.5 ${
                  m.sender === 'citizen' ? 'text-blue-200 text-right' : 'text-slate-400'
                }`}
              >
                {m.timestamp}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="text-xs text-slate-500 italic">
            Retrieving municipal bylaws & verifying citations...
          </div>
        )}
      </div>

      <div className="p-3 bg-white border-t border-slate-200 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 px-3 py-2 rounded-xl text-xs font-semibold shrink-0 transition"
        >
          <Camera className="w-4 h-4" />
          <span>Report 311 Issue</span>
        </button>

        <button
          type="button"
          onClick={handleVoiceInput}
          title="Voice Input"
          className="p-2 text-slate-500 hover:text-blue-700 hover:bg-slate-100 rounded-xl transition"
        >
          <Mic className="w-4 h-4" />
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask about municipal taxes, licenses, bills, or ticket status..."
          className="flex-1 text-sm border border-slate-300 rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
        />

        <button
          type="button"
          onClick={() => handleSend()}
          disabled={loading}
          className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-1.5 transition"
        >
          <Send className="w-4 h-4" />
          <span>Send</span>
        </button>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-5 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="font-bold text-slate-900 flex items-center gap-2">
                <Camera className="w-5 h-5 text-blue-700" />
                <span>Multimodal 311 Civic Grievance</span>
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleGrievanceSubmit} className="mt-4 space-y-3.5 text-sm">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  1. Upload Issue Photograph (JPEG/PNG)
                </label>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  required
                  onChange={(e) => setPhoto(e.target.files?.[0] || null)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  2. Issue Description
                </label>
                <textarea
                  rows={2}
                  required
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  placeholder="e.g., Deep pothole blocking left lane near bus shelter"
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="font-medium text-slate-700">3. GPS Coordinates (50m Dedup Check)</label>
                  <button
                    type="button"
                    onClick={handleUseBrowserGPS}
                    className="text-xs text-blue-700 hover:underline flex items-center gap-1"
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>Use Current GPS</span>
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    placeholder="Latitude"
                    className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs"
                  />
                  <input
                    type="text"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                    placeholder="Longitude"
                    className="border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs"
                  />
                </div>
              </div>

              {triageError && (
                <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{triageError}</span>
                </div>
              )}

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting311}
                  className="px-4 py-2 text-xs font-semibold bg-blue-700 hover:bg-blue-800 text-white rounded-lg flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{submitting311 ? 'Running Vision & PostGIS Triage...' : 'Verify & Submit Ticket'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
