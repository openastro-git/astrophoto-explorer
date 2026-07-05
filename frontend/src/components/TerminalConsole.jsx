import React, { useState, useEffect, useRef } from 'react';
import { createLogsWebSocket } from '../api/astroApi';
import { Terminal, Trash2 } from 'lucide-react';

function TerminalConsole({ visible = false }) {
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef(null);

  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;

    const connect = () => {
      ws = createLogsWebSocket({
        onOpen: () => {
          setIsConnected(true);
        },
        onMessage: (data) => {
          if (data && data.type === 'log') {
            setLogs(prev => {
              // Extract lines if data contains multiple newlines
              const messages = data.message.split('\n');
              const filteredMessages = messages.filter(m => m.trim().length > 0);
              
              const newLogs = [...prev, ...filteredMessages];
              // Keep maximum 500 lines to avoid slow rendering
              return newLogs.slice(-500);
            });
          }
        },
        onError: () => {
          setIsConnected(false);
        },
        onClose: () => {
          setIsConnected(false);
          // Auto-reconnect
          reconnectTimeout = setTimeout(connect, 3000);
        }
      });
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll, visible]);

  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <div className={`fixed bottom-0 left-0 right-0 z-40 bg-slate-900 border-t border-slate-700 transition-all duration-300 ${!visible ? 'h-0 border-none overflow-hidden opacity-0 pointer-events-none' : 'h-64'}`}>
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 h-10 bg-slate-950 border-b border-slate-800 select-none">
        <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
          <Terminal size={14} className="text-blue-400" />
          <span>System Console Logs</span>
          <span 
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-amber-500 animate-pulse'}`} 
            title={isConnected ? 'Connected to API logs' : 'Connecting to API logs...'} 
          />
        </div>
        <div className="flex items-center space-x-3 text-slate-400">
          <button 
            onClick={clearLogs} 
            title="Clear Console"
            className="p-1 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
          >
            <Trash2 size={14} />
          </button>
          <button 
            onClick={() => setAutoScroll(!autoScroll)} 
            title={autoScroll ? "Disable Auto-Scroll" : "Enable Auto-Scroll"}
            className={`p-1 text-[10px] uppercase font-bold rounded transition-colors hover:bg-slate-800 ${autoScroll ? 'text-blue-400' : 'text-slate-500'}`}
          >
            Scroll-Lock
          </button>
        </div>
      </div>

      {/* Logs Area */}
      <div className="p-4 h-52 overflow-y-auto font-mono text-[11px] text-slate-300 bg-slate-950 leading-relaxed whitespace-pre-wrap select-text selection:bg-blue-600 selection:text-white">
        {logs.length === 0 ? (
          <div className="text-slate-500 italic text-center pt-8">No console output received yet...</div>
        ) : (
          logs.map((log, index) => {
            // Colorize log message levels
            let colorClass = 'text-slate-300';
            if (log.includes('[ERROR]') || log.toLowerCase().includes('error:') || log.includes('Traceback')) {
              colorClass = 'text-red-400 font-semibold';
            } else if (log.includes('[WARN]') || log.toLowerCase().includes('warning:') || log.includes('WARNING')) {
              colorClass = 'text-amber-400';
            } else if (log.includes('[INFO]') || log.includes('INFO:')) {
              colorClass = 'text-sky-400/80';
            } else if (log.includes('[OK]') || log.includes('success') || log.includes('Successfully')) {
              colorClass = 'text-emerald-400';
            } else if (log.startsWith('[INIT]') || log.startsWith('[PACK]')) {
              colorClass = 'text-purple-400';
            }
            return (
              <div key={index} className={`${colorClass} py-0.5 border-b border-slate-900/40`}>
                {log}
              </div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}

export default TerminalConsole;
