import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Phone,
  PhoneCall,
  Activity,
  Clock,
  User,
  Zap,
} from 'lucide-react';

interface CallState {
  call_sid: string;
  caller: string;
  start_time: string;
  duration_sec: number;
  audio_state: string;
  turns: number;
  last_tool: string;
  conversation_history: Array<{ role: string; content: string }>;
}

interface PhoneMessage {
  type: string;
  data?: {
    active_calls?: CallState[];
    call_sid?: string;
    caller?: string;
  };
}

const STATE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  idle: { bg: 'bg-gray-500/20', text: 'text-gray-400', label: 'Idle' },
  listening: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'Listening' },
  thinking: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'Thinking' },
  speaking: { bg: 'bg-purple-500/20', text: 'text-purple-400', label: 'Speaking' },
  executing: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Executing' },
};

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export default function PhoneSection() {
  const [activeCalls, setActiveCalls] = useState<CallState[]>([]);
  const [selectedCall, setSelectedCall] = useState<CallState | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  const connectWs = useCallback(() => {
    try {
      const ws = new WebSocket('ws://localhost:8100/ws/phone');
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        ws.send(JSON.stringify({ type: 'ping' }));
      };

      ws.onmessage = (event) => {
        try {
          const msg: PhoneMessage = JSON.parse(event.data);
          if (msg.type === 'active_calls' && msg.data?.active_calls) {
            setActiveCalls(msg.data.active_calls);
          } else if (msg.type === 'call_state' && msg.data) {
            const callData = msg.data as unknown as CallState;
            setActiveCalls((prev) => {
              const idx = prev.findIndex((c) => c.call_sid === callData.call_sid);
              if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = callData;
                return updated;
              }
              return [...prev, callData];
            });
            setSelectedCall((prev) =>
              prev?.call_sid === callData.call_sid ? callData : prev
            );
          } else if (msg.type === 'pong') {
            // Keepalive
          }
        } catch {
          // skip malformed
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connectWs, 3000);
      };

      ws.onerror = () => setWsConnected(false);
    } catch {
      setWsConnected(false);
    }
  }, []);

  useEffect(() => {
    connectWs();
    return () => {
      wsRef.current?.close();
    };
  }, [connectWs]);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [selectedCall?.conversation_history]);

  const stateInfo = selectedCall
    ? STATE_COLORS[selectedCall.audio_state] || STATE_COLORS.idle
    : STATE_COLORS.idle;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Phone size={24} className="text-jarvis-accentPink" />
          <h1 className="text-xl font-semibold text-jarvis-text">Phone</h1>
          <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs ${wsConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-red-400'}`} />
            {wsConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <div className="text-xs text-jarvis-textMuted">
          {activeCalls.length} active call{activeCalls.length !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="flex-1 flex gap-4 overflow-hidden">
        {/* Left: Call List */}
        <div className="w-64 flex flex-col gap-2 overflow-y-auto">
          {activeCalls.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-jarvis-textMuted">
              <PhoneCall size={48} className="mb-3 opacity-30" />
              <p className="text-sm">No active calls</p>
              <p className="text-xs mt-1 opacity-60">Waiting for incoming calls...</p>
            </div>
          ) : (
            activeCalls.map((call) => {
              const cs = STATE_COLORS[call.audio_state] || STATE_COLORS.idle;
              return (
                <motion.button
                  key={call.call_sid}
                  onClick={() => setSelectedCall(call)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`w-full text-left p-3 rounded-xl border transition-all ${
                    selectedCall?.call_sid === call.call_sid
                      ? 'border-jarvis-accentPink/50 bg-jarvis-accentPink/10'
                      : 'border-white/5 bg-white/5 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-2 h-2 rounded-full ${cs.text.replace('text-', 'bg-')}`} />
                    <span className="text-sm font-medium text-jarvis-text truncate">{call.caller}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-jarvis-textMuted">
                    <span>{formatDuration(call.duration_sec)}</span>
                    <span className={cs.text}>{cs.label}</span>
                  </div>
                </motion.button>
              );
            })
          )}
        </div>

        {/* Right: Call Detail */}
        <div className="flex-1 flex flex-col">
          {selectedCall ? (
            <>
              {/* Call Info Card */}
              <div className="p-4 rounded-xl border border-white/5 bg-white/5 mb-3">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${stateInfo.bg}`}>
                      <User size={20} className={stateInfo.text} />
                    </div>
                    <div>
                      <div className="font-medium text-jarvis-text">{selectedCall.caller}</div>
                      <div className="text-xs text-jarvis-textMuted">{selectedCall.call_sid}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1.5 text-jarvis-text">
                      <Clock size={14} />
                      <span className="font-mono">{formatDuration(selectedCall.duration_sec)}</span>
                    </div>
                  </div>
                </div>

                {/* Status Bar */}
                <div className="flex gap-2">
                  {(['listening', 'thinking', 'speaking', 'executing'] as const).map((state) => {
                    const info = STATE_COLORS[state];
                    const isActive = selectedCall.audio_state === state;
                    return (
                      <div
                        key={state}
                        className={`flex-1 py-1 rounded text-center text-xs transition-all ${
                          isActive ? `${info.bg} ${info.text} font-medium` : 'bg-white/5 text-jarvis-textMuted/50'
                        }`}
                      >
                        {info.label}
                      </div>
                    );
                  })}
                </div>

                {selectedCall.last_tool && (
                  <div className="mt-2 flex items-center gap-2 text-xs text-jarvis-textMuted">
                    <Zap size={12} />
                    Last tool: <span className="text-jarvis-accentPink">{selectedCall.last_tool}</span>
                  </div>
                )}
              </div>

              {/* Live Transcript */}
              <div className="flex-1 flex flex-col overflow-hidden rounded-xl border border-white/5 bg-white/5">
                <div className="px-3 py-2 border-b border-white/5 text-xs font-medium text-jarvis-textMuted flex items-center gap-2">
                  <Activity size={12} />
                  Live Transcript
                  <span className="ml-auto text-jarvis-textMuted/50">{selectedCall.turns} turns</span>
                </div>
                <div ref={transcriptRef} className="flex-1 overflow-y-auto p-3 space-y-3">
                  <AnimatePresence>
                    {selectedCall.conversation_history.map((msg, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'}`}
                      >
                        <div
                          className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
                            msg.role === 'user'
                              ? 'bg-jarvis-accentPink/15 text-jarvis-text rounded-bl-sm'
                              : 'bg-jarvis-accentBlue/15 text-jarvis-text rounded-br-sm'
                          }`}
                        >
                          <div className="text-[10px] text-jarvis-textMuted mb-0.5">
                            {msg.role === 'user' ? '🎤 User' : '🤖 JARVIS'}
                          </div>
                          {msg.content}
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-jarvis-textMuted">
              <Phone size={64} className="mb-4 opacity-20" />
              <p className="text-lg font-medium">Phone Panel</p>
              <p className="text-sm mt-1 opacity-60">Select a call to view details</p>
              <div className="mt-6 p-4 rounded-xl border border-white/5 bg-white/5 max-w-md text-center">
                <p className="text-xs text-jarvis-textMuted">
                  Configure your Twilio credentials in <code className="text-jarvis-accentPink">.env</code> and start the telephony server:
                </p>
                <code className="block mt-2 text-xs text-jarvis-accentPink bg-black/30 px-3 py-2 rounded-lg">
                  python -m interface.telephony.twilio_server
                </code>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
