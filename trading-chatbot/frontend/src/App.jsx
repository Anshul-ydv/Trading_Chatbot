import { useState, useEffect } from 'react'
import useWebSocket from 'react-use-websocket'
import axios from 'axios'
import { LineChart, Activity, MessageSquare, Send, Plus, Trash2 } from 'lucide-react'
import FyersStatus from './components/FyersStatus'
import { ChartComponent } from './components/ChartComponent'

const demoTickers = {
  RELIANCE: {
    symbol: 'RELIANCE',
    ltp: 3200.25,
    volume: 3200000,
    timestamp: new Date().toISOString(),
    change: 12.5,
  },
  TCS: {
    symbol: 'TCS',
    ltp: 4285.1,
    volume: 2100000,
    timestamp: new Date().toISOString(),
    change: -8.4,
  },
  INFY: {
    symbol: 'INFY',
    ltp: 1582.7,
    volume: 4100000,
    timestamp: new Date().toISOString(),
    change: 5.1,
  },
}

function App() {
  const [tickers, setTickers] = useState({})
  const [selectedTicker, setSelectedTicker] = useState(null)
  const [chatInput, setChatInput] = useState('')
  const [newTickerInput, setNewTickerInput] = useState('')
  const [isAddingTicker, setIsAddingTicker] = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [bootstrapError, setBootstrapError] = useState(null)
  const [bootstrapComplete, setBootstrapComplete] = useState(false)
  const [chartData, setChartData] = useState([])

  const { lastMessage } = useWebSocket('ws://127.0.0.1:8000/ws/updates', {
    shouldReconnect: () => true,
  })

  useEffect(() => {
    if (selectedTicker) {
      const fetchHistory = async () => {
        try {
          const res = await axios.get(`/api/history/${selectedTicker}`)
          setChartData(res.data)
        } catch (err) {
          console.error('Failed to fetch history', err)
          setChartData([])
        }
      }
      fetchHistory()
    }
  }, [selectedTicker])

  useEffect(() => {
    if (lastMessage !== null) {
      const data = JSON.parse(lastMessage.data)
      setTickers(prev => ({
        ...prev,
        [data.symbol]: data
      }))
    }
  }, [lastMessage])

  useEffect(() => {
    let cancelled = false

    const bootstrapTickerFeed = async () => {
      try {
        const res = await axios.get('/api/screen', {
          params: { limit: 5, strategy: 'breakout' }
        })
        if (!cancelled && Array.isArray(res.data) && res.data.length) {
          setTickers(prev => {
            if (Object.keys(prev).length) return prev
            const mapped = {}
            for (const row of res.data) {
              mapped[row.ticker] = {
                symbol: row.ticker,
                ltp: row.entry ?? row.target ?? 100,
                volume: Math.round(row.score * 100000) || 500000,
                timestamp: new Date().toISOString(),
                change: (row.score ?? 0).toFixed(2)
              }
            }
            return mapped
          })
        }
      } catch (err) {
        console.warn('Ticker bootstrap failed, using demo data', err)
        setBootstrapError('Backend not reachable. Showing demo data.')
        setTickers(prev => Object.keys(prev).length ? prev : demoTickers)
      } finally {
        if (!cancelled) {
          setBootstrapComplete(true)
        }
      }
    }

    if (!bootstrapComplete && Object.keys(tickers).length === 0) {
      bootstrapTickerFeed()
    }

    return () => {
      cancelled = true
    }
  }, [bootstrapComplete, tickers])

  useEffect(() => {
    if (!selectedTicker) {
      const symbols = Object.keys(tickers)
      if (symbols.length) {
        setSelectedTicker(symbols[0])
      }
    }
  }, [tickers, selectedTicker])

  const handleChat = async (e) => {
    e.preventDefault()
    if (!chatInput.trim() || !selectedTicker) return

    const question = chatInput
    setChatHistory(prev => [...prev, { role: 'user', content: question }])
    setChatInput('')
    setLoading(true)

    try {
      const res = await axios.post('/api/chat', {
        ticker: selectedTicker,
        question: question
      })
      setChatHistory(prev => [...prev, { role: 'assistant', content: res.data.response }])
    } catch (err) {
      console.error(err)
      setChatHistory(prev => [...prev, { role: 'error', content: 'Failed to get response' }])
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveTicker = async (e, tickerToRemove) => {
    e.stopPropagation()
    if (!confirm(`Are you sure you want to remove ${tickerToRemove}?`)) return

    try {
      await axios.delete(`/api/tickers/${tickerToRemove}`)
      setTickers(prev => {
        const next = { ...prev }
        delete next[tickerToRemove]
        return next
      })
      if (selectedTicker === tickerToRemove) {
        setSelectedTicker(null)
      }
    } catch (err) {
      console.error('Failed to remove ticker', err)
      alert('Failed to remove ticker. Please try again.')
    }
  }

  const handleAddTicker = async (e) => {
    e.preventDefault()
    if (!newTickerInput.trim()) return

    setIsAddingTicker(true)
    try {
      const tickerToAdd = newTickerInput.toUpperCase().trim()
      await axios.post('/api/tickers', { ticker: tickerToAdd })
      setNewTickerInput('')
    } catch (err) {
      console.error('Failed to add ticker', err)
      alert('Failed to add ticker. Please try again.')
    } finally {
      setIsAddingTicker(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0e11] text-gray-100 flex font-sans">
      {/* Sidebar / Watchlist */}
      <div className="w-80 border-r border-gray-800 bg-[#151924] flex flex-col h-screen">
        <div className="p-4 border-b border-gray-800 flex-shrink-0">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent mb-4">
            TradeBot Pro
          </h1>
          <FyersStatus />
          {bootstrapError && (
            <div className="mt-3 text-xs text-yellow-400 bg-yellow-900/20 border border-yellow-700/50 rounded px-2 py-1.5">
              {bootstrapError}
            </div>
          )}
        </div>
        
        <div className="p-3 flex-1 overflow-y-auto min-h-0">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2 px-2">
            <Activity size={14} className="text-blue-500" /> Market Watch
          </h2>
          <div className="space-y-1">
            {Object.values(tickers).map((tick) => {
              const isPositive = (tick.change || 0) >= 0;
              return (
                <div 
                  key={tick.symbol}
                  onClick={() => setSelectedTicker(tick.symbol)}
                  className={`p-3 rounded-lg cursor-pointer transition-all duration-200 group ${
                    selectedTicker === tick.symbol 
                      ? 'bg-blue-600/10 border border-blue-500/30' 
                      : 'hover:bg-gray-800 border border-transparent'
                  }`}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className={`font-bold ${selectedTicker === tick.symbol ? 'text-blue-400' : 'text-gray-200'}`}>
                      {tick.symbol}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className={`font-mono font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                        ₹{tick.ltp?.toFixed(2)}
                      </span>
                      <button
                        onClick={(e) => handleRemoveTicker(e, tick.symbol)}
                        className="p-1 hover:bg-red-500/20 rounded text-gray-500 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                        title="Remove ticker"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 group-hover:text-gray-400">
                    <span>Vol: {(tick.volume / 1000).toFixed(1)}k</span>
                    <span className={`${isPositive ? 'text-green-500/70' : 'text-red-500/70'}`}>
                      {isPositive ? '+' : ''}{tick.change}%
                    </span>
                  </div>
                </div>
              );
            })}
            {Object.keys(tickers).length === 0 && (
              <div className="text-gray-600 text-sm text-center py-8 italic">
                Waiting for market data...
              </div>
            )}
          </div>
        </div>

        {/* Add Ticker Section */}
        <div className="p-4 border-t border-gray-800 flex-shrink-0">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Plus size={14} className="text-green-500" /> Add Ticker
          </h2>
          <form onSubmit={handleAddTicker} className="flex gap-2">
            <input
              type="text"
              value={newTickerInput}
              onChange={(e) => setNewTickerInput(e.target.value)}
              placeholder="Enter ticker symbol"
              className="flex-1 bg-gray-900 border border-gray-700 text-gray-200 rounded-lg pl-4 pr-2 py-2.5 text-sm focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-all placeholder-gray-600"
            />
            <button 
              type="submit" 
              disabled={isAddingTicker || !newTickerInput.trim()}
              className="px-3 py-2 bg-green-600 hover:bg-green-500 rounded-md text-white disabled:opacity-50 disabled:hover:bg-green-600 transition-colors text-sm flex items-center gap-1"
            >
              {isAddingTicker ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  Adding...
                </>
              ) : (
                <>
                  <Plus size={16} />
                  Add Ticker
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col bg-[#0b0e11] h-screen overflow-hidden">
        {selectedTicker ? (
          <>
            {/* Header */}
            <div className="h-16 border-b border-gray-800 flex items-center justify-between px-6 bg-[#151924] flex-shrink-0">
              <div className="flex items-center gap-4">
                <h1 className="text-2xl font-bold text-white">{selectedTicker}</h1>
                <div className="flex items-center gap-2 text-sm">
                  <span className={`px-2 py-0.5 rounded ${
                    (tickers[selectedTicker]?.change || 0) >= 0 
                      ? 'bg-green-500/10 text-green-400' 
                      : 'bg-red-500/10 text-red-400'
                  }`}>
                    {(tickers[selectedTicker]?.change || 0) >= 0 ? '+' : ''}
                    {tickers[selectedTicker]?.change}%
                  </span>
                  <span className="text-gray-400">NSE</span>
                </div>
              </div>
              <div className="flex gap-4 text-sm text-gray-400">
                <div className="flex flex-col items-end">
                  <span className="text-xs text-gray-500">LTP</span>
                  <span className="font-mono text-white">₹{tickers[selectedTicker]?.ltp?.toFixed(2)}</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-xs text-gray-500">Volume</span>
                  <span className="font-mono text-white">{tickers[selectedTicker]?.volume?.toLocaleString()}</span>
                </div>
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 p-4 flex gap-4 overflow-hidden">
              {/* Chart Placeholder */}
              <div className="flex-1 bg-[#151924] rounded-xl border border-gray-800 p-1 flex flex-col relative overflow-hidden group">
                {chartData.length > 0 ? (
                  <ChartComponent data={chartData} />
                ) : (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center space-y-4">
                      <div className="relative">
                        <div className="absolute inset-0 bg-blue-500 blur-3xl opacity-10"></div>
                        <LineChart size={64} className="relative z-10 mx-auto text-gray-600 animate-pulse" />
                      </div>
                      <div>
                        <p className="text-gray-400 font-medium">Loading Chart Data...</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Chat Pane */}
              <div className="w-96 bg-[#151924] rounded-xl border border-gray-800 flex flex-col shadow-xl h-full">
                <div className="p-4 border-b border-gray-800 flex items-center gap-2 bg-[#1a1f2e] rounded-t-xl flex-shrink-0">
                  <div className="p-1.5 bg-blue-500/10 rounded-lg">
                    <MessageSquare size={16} className="text-blue-400" />
                  </div>
                  <span className="font-semibold text-sm">AI Market Assistant</span>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent min-h-0">
                  {chatHistory.length === 0 && (
                    <div className="text-center text-gray-600 text-sm mt-10 px-6">
                      <p>Ask me about support levels, trends, or news for {selectedTicker}.</p>
                    </div>
                  )}
                  {chatHistory.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed ${
                        msg.role === 'user' 
                          ? 'bg-blue-600 text-white rounded-br-none' 
                          : 'bg-gray-800 text-gray-200 rounded-bl-none border border-gray-700'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex justify-start">
                      <div className="bg-gray-800 rounded-2xl rounded-bl-none p-3 border border-gray-700 flex gap-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                      </div>
                    </div>
                  )}
                </div>

                <form onSubmit={handleChat} className="p-3 border-t border-gray-800 bg-[#1a1f2e] rounded-b-xl">
                  <div className="relative flex items-center">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Ask a question..."
                      className="w-full bg-gray-900 border border-gray-700 text-gray-200 rounded-lg pl-4 pr-10 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder-gray-600"
                    />
                    <button 
                      type="submit" 
                      disabled={loading || !chatInput.trim()}
                      className="absolute right-1.5 p-1.5 bg-blue-600 hover:bg-blue-500 rounded-md text-white disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
                    >
                      <Send size={14} />
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500 space-y-4">
            <Activity size={64} className="text-gray-700" />
            <p className="text-lg font-medium">Select a ticker to start analyzing</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
