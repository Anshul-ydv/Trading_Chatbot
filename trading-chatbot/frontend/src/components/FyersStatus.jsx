import React, { useState } from 'react';
import { useFyers } from '../hooks/useFyers';
import { Wifi, WifiOff } from 'lucide-react';

const FyersStatus = () => {
  // In a real app, this token should come from a secure auth context or backend
  const [token, setToken] = useState(localStorage.getItem('fyers_token') || '');
  const { isConnected, marketData, subscribe } = useFyers(token);
  const [symbol, setSymbol] = useState('NSE:SBIN-EQ');

  const handleConnect = () => {
    localStorage.setItem('fyers_token', token);
    // Trigger reconnection by updating state if needed, 
    // but hook depends on token so it should auto-trigger if token changed
    window.location.reload(); // Simple reload to apply new token for now
  };

  const handleSubscribe = () => {
    if (symbol) {
        subscribe([symbol]);
    }
  };

  return (
    <div className="bg-[#1a1f2e] p-3 rounded-lg border border-gray-800 mb-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
          Fyers Connection
          {isConnected ? <Wifi className="text-green-500" size={14} /> : <WifiOff className="text-red-500" size={14} />}
        </h3>
        <span className={`text-[10px] px-1.5 py-0.5 rounded ${isConnected ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
          {isConnected ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>

      {!isConnected && (
        <div className="flex flex-col gap-2">
          <input 
            type="password" 
            placeholder="Access Token" 
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 focus:border-blue-500 focus:outline-none w-full"
          />
          <button 
            onClick={handleConnect}
            className="bg-blue-600 hover:bg-blue-500 py-1.5 rounded text-xs font-medium text-white transition-colors w-full"
          >
            Connect
          </button>
        </div>
      )}

      {isConnected && (
        <div className="space-y-2">
            <div className="flex gap-2">
                <input 
                    type="text" 
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 focus:border-blue-500 focus:outline-none flex-1"
                    placeholder="Symbol (e.g. NSE:SBIN-EQ)"
                />
                <button 
                    onClick={handleSubscribe}
                    className="bg-green-600 hover:bg-green-500 px-3 py-1.5 rounded text-xs font-medium text-white transition-colors"
                >
                    Add
                </button>
            </div>
            
            {marketData && Object.keys(marketData).length > 0 && (
               <div className="text-[10px] text-gray-500 mt-2 font-mono bg-gray-900 p-2 rounded border border-gray-800 overflow-hidden text-ellipsis whitespace-nowrap">
                  Latest: {JSON.stringify(marketData).slice(0, 30)}...
               </div>
            )}
        </div>
      )}
    </div>
  );
};

export default FyersStatus;
