import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Get backend URL from environment variable or use default
const API = process.env.REACT_APP_BACKEND_URL || '';

const TradingDashboard = () => {
  const [opportunities, setOpportunities] = useState([]);
  const [analyses, setAnalyses] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [performance, setPerformance] = useState({});
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [isTrading, setIsTrading] = useState(false);
  const [activePositions, setActivePositions] = useState([]);
  const [executionMode, setExecutionMode] = useState('SIMULATION');
  const [backtestResults, setBacktestResults] = useState(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestStatus, setBacktestStatus] = useState(null);

  const fetchData = async () => {
    try {
      const [opportunitiesRes, analysesRes, decisionsRes, perfRes, positionsRes, modeRes, backtestStatusRes] = await Promise.all([
        axios.get(`${API}/api/opportunities`),
        axios.get(`${API}/api/analyses`),
        axios.get(`${API}/api/decisions`),
        axios.get(`${API}/api/performance`),
        axios.get(`${API}/api/active-positions`),
        axios.get(`${API}/api/trading/execution-mode`),
        axios.get(`${API}/api/backtest/status`)
      ]);

      setOpportunities(opportunitiesRes.data.opportunities || []);
      setAnalyses(analysesRes.data.analyses || []);
      setDecisions(decisionsRes.data.decisions || []);
      setPerformance(perfRes.data.performance || {});
      setActivePositions(positionsRes.data.data?.active_positions || []);
      setExecutionMode(modeRes.data.execution_mode || 'SIMULATION');
      setBacktestStatus(backtestStatusRes.data.data || null);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 90) return 'text-green-600';
    if (confidence >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSignalColor = (signal) => {
    if (signal === 'LONG') return 'text-green-600 bg-green-50';
    if (signal === 'SHORT') return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  // Navigation tabs
  const tabs = [
    { id: 'dashboard', name: 'Dashboard' },
    { id: 'opportunities', name: 'Opportunities' },
    { id: 'ia1-analysis', name: 'IA1 Analysis' },
    { id: 'ia2-decisions', name: 'IA2 Decisions' },
    { id: 'active-positions', name: 'Active Positions' },
    { id: 'bingx-trading', name: 'BingX Trading' },
    { id: 'backtesting', name: 'Backtesting' },
    { id: 'performance', name: 'Performance' }
  ];

  // Get recent activities (mix of analyses and decisions)
  const getRecentActivities = () => {
    const activities = [];
    
    // Add recent analyses
    analyses.slice(0, 3).forEach(analysis => {
      activities.push({
        symbol: analysis.symbol,
        action: analysis.signal || 'HOLD',
        confidence: (analysis.confidence * 100).toFixed(1),
        entry: analysis.current_price?.toFixed(6) || 'N/A',
        timestamp: analysis.timestamp,
        type: 'analysis'
      });
    });

    // Add recent decisions
    decisions.slice(0, 3).forEach(decision => {
      activities.push({
        symbol: decision.symbol,
        action: decision.signal || 'HOLD',
        confidence: (decision.confidence * 100).toFixed(1),
        entry: decision.entry_price?.toFixed(6) || 'N/A',
        timestamp: decision.timestamp,
        type: 'decision'
      });
    });

    // Sort by timestamp and take top 5
    return activities
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, 5);
  };

  const DashboardTab = () => (
    <div className="space-y-6">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-gray-900">{opportunities.length}</div>
          <div className="text-sm text-gray-600 mt-1">Active market opportunities</div>
          <div className="text-lg font-semibold text-blue-600 mt-2">Opportunities</div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-gray-900">{analyses.length}</div>
          <div className="text-sm text-gray-600 mt-1">Technical analysis completed</div>
          <div className="text-lg font-semibold text-blue-600 mt-2">IA1 Analyses</div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-gray-900">{decisions.length}</div>
          <div className="text-sm text-gray-600 mt-1">Strategic decisions made</div>
          <div className="text-lg font-semibold text-blue-600 mt-2">IA2 Decisions</div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-3xl font-bold text-gray-900">{activePositions.length}</div>
          <div className="text-sm text-gray-600 mt-1">Open trading positions</div>
          <div className="text-lg font-semibold text-blue-600 mt-2">Active Positions</div>
        </div>
      </div>

      {/* Latest Activity */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Latest Activity</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {getRecentActivities().map((activity, index) => (
            <div key={index} className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="font-bold text-gray-900">{activity.symbol}</div>
                <div className={`px-2 py-1 rounded-full text-sm font-medium ${getSignalColor(activity.action)}`}>
                  {activity.action} - {activity.confidence}% confidence
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600">{formatTime(activity.timestamp)}</div>
                <div className="text-sm text-gray-500">Entry: ${activity.entry}</div>
              </div>
            </div>
          ))}
          {getRecentActivities().length === 0 && (
            <div className="px-6 py-8 text-center text-gray-500">
              No recent activity
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const OpportunitiesTab = () => (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Market Opportunities</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Change 24h</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Volume</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Market Cap</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {opportunities.map((opportunity, index) => (
              <tr key={index}>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{opportunity.symbol}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">${opportunity.current_price?.toFixed(6) || 'N/A'}</td>
                <td className={`px-6 py-4 whitespace-nowrap ${opportunity.price_change_24h >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {opportunity.price_change_24h?.toFixed(2) || 0}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">${opportunity.volume_24h?.toLocaleString() || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">${opportunity.market_cap?.toLocaleString() || 'N/A'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {opportunities.length === 0 && (
          <div className="px-6 py-8 text-center text-gray-500">
            No opportunities available
          </div>
        )}
      </div>
    </div>
  );

  const AnalysesTab = () => (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">IA1 Technical Analysis</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">R/R Ratio</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {analyses.map((analysis, index) => (
              <tr key={index}>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{analysis.symbol}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded-full text-sm font-medium ${getSignalColor(analysis.signal)}`}>
                    {analysis.signal}
                  </span>
                </td>
                <td className={`px-6 py-4 whitespace-nowrap ${getConfidenceColor(analysis.confidence * 100)}`}>
                  {(analysis.confidence * 100).toFixed(1)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">{analysis.risk_reward_ratio?.toFixed(2) || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">{formatTime(analysis.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {analyses.length === 0 && (
          <div className="px-6 py-8 text-center text-gray-500">
            No analyses available
          </div>
        )}
      </div>
    </div>
  );

  const DecisionsTab = () => (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">IA2 Strategic Decisions</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Decision</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entry Price</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {decisions.map((decision, index) => (
              <tr key={index}>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{decision.symbol}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded-full text-sm font-medium ${getSignalColor(decision.signal)}`}>
                    {decision.signal}
                  </span>
                </td>
                <td className={`px-6 py-4 whitespace-nowrap ${getConfidenceColor(decision.confidence * 100)}`}>
                  {(decision.confidence * 100).toFixed(1)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-900">${decision.entry_price?.toFixed(6) || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">{formatTime(decision.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {decisions.length === 0 && (
          <div className="px-6 py-8 text-center text-gray-500">
            No decisions available
          </div>
        )}
      </div>
    </div>
  );

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardTab />;
      case 'opportunities':
        return <OpportunitiesTab />;
      case 'ia1-analysis':
        return <AnalysesTab />;
      case 'ia2-decisions':
        return <DecisionsTab />;
      case 'active-positions':
        return (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Active Positions</h3>
            {activePositions.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No active positions</div>
            ) : (
              <div className="space-y-4">
                {activePositions.map((position, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <div className="font-medium">{position.symbol}</div>
                      <div className={`px-2 py-1 rounded ${getSignalColor(position.side)}`}>
                        {position.side}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      default:
        return (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">{tabs.find(t => t.id === activeTab)?.name}</h3>
            <div className="text-center text-gray-500 py-8">Coming soon...</div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <div className="text-2xl">🤖</div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Ultra Professional Trading Bot</h1>
                <p className="text-sm text-gray-600">AI-Enhanced Dual Analysis System</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${isTrading ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">{isTrading ? 'Active' : 'Inactive'}</span>
              </div>
              <div className="text-sm text-gray-600">
                Mode: <span className="font-medium">{executionMode}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.name}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          renderActiveTab()
        )}
      </div>
    </div>
  );
};

export default TradingDashboard;