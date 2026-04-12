import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { 
  Shield, Activity, AlertTriangle, TrendingUp, TrendingDown, 
  Pause, Play, Settings, FileText, Users, Clock, Zap,
  DollarSign, Percent, BarChart3, RefreshCw, Lock
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API = `${BACKEND_URL}/api`;

// ============== Utility Functions ==============
const formatCurrency = (value) => {
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
};

const formatPercent = (value) => {
  return `${(value * 100).toFixed(2)}%`;
};

const getRegimeColor = (regime) => {
  const colors = {
    risk_on: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    neutral: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    risk_off: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    emergency: "bg-red-500/20 text-red-400 border-red-500/30",
    unknown: "bg-slate-500/20 text-slate-400 border-slate-500/30"
  };
  return colors[regime] || colors.unknown;
};

const getActionColor = (action) => {
  const colors = {
    hold: "bg-slate-500/20 text-slate-300",
    buy: "bg-emerald-500/20 text-emerald-400",
    sell: "bg-red-500/20 text-red-400",
    reduce_exposure: "bg-amber-500/20 text-amber-400",
    emergency_exit: "bg-red-600/20 text-red-500"
  };
  return colors[action] || colors.hold;
};

// ============== Components ==============

const StatusIndicator = ({ status, label }) => (
  <div className="flex items-center gap-2">
    <div className={`w-2 h-2 rounded-full ${status ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
    <span className="text-xs text-slate-400">{label}</span>
  </div>
);

const MetricCard = ({ title, value, subtitle, icon: Icon, trend, color = "text-cyan-400" }) => (
  <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur">
    <CardContent className="p-4">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider">{title}</p>
          <p className={`text-2xl font-mono font-bold mt-1 ${color}`}>{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className="p-2 bg-slate-800/50 rounded-lg">
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
      </div>
      {trend !== undefined && (
        <div className="flex items-center mt-2 gap-1">
          {trend >= 0 ? (
            <TrendingUp className="w-3 h-3 text-emerald-400" />
          ) : (
            <TrendingDown className="w-3 h-3 text-red-400" />
          )}
          <span className={`text-xs ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {trend >= 0 ? '+' : ''}{trend.toFixed(2)}%
          </span>
        </div>
      )}
    </CardContent>
  </Card>
);

const RiskGauge = ({ value, max, label, color }) => {
  const percentage = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className={color}>{value.toFixed(2)}% / {max}%</span>
      </div>
      <Progress value={percentage} className="h-1.5 bg-slate-800" />
    </div>
  );
};

const ArtifactItem = ({ artifact }) => (
  <div className="p-3 bg-slate-800/30 rounded-lg border border-slate-700/30 hover:border-cyan-500/30 transition-colors">
    <div className="flex justify-between items-start">
      <div className="flex items-center gap-2">
        <Badge className={getRegimeColor(artifact.regime)}>
          {artifact.regime}
        </Badge>
        <Badge className={getActionColor(artifact.action_taken)}>
          {artifact.action_taken}
        </Badge>
      </div>
      <span className="text-xs text-slate-500 font-mono">
        #{artifact.cycle_number}
      </span>
    </div>
    <div className="mt-2 flex items-center gap-4 text-xs text-slate-400">
      <span className="font-mono">{artifact.artifact_hash?.slice(0, 12)}...</span>
      <span>{new Date(artifact.timestamp).toLocaleTimeString()}</span>
    </div>
  </div>
);

const ProposalItem = ({ proposal }) => (
  <div className="p-3 bg-slate-800/30 rounded-lg border border-slate-700/30">
    <div className="flex justify-between items-start">
      <div>
        <h4 className="font-medium text-slate-200">{proposal.title}</h4>
        <p className="text-xs text-slate-400 mt-1">{proposal.description}</p>
      </div>
      <Badge variant={proposal.status === 'active' ? 'default' : 'secondary'}>
        {proposal.status}
      </Badge>
    </div>
    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
      <div className="text-emerald-400">For: {proposal.votes_for}</div>
      <div className="text-red-400">Against: {proposal.votes_against}</div>
      <div className="text-slate-400">Abstain: {proposal.votes_abstain}</div>
    </div>
  </div>
);

// ============== Main Dashboard ==============

const Dashboard = () => {
  const [agentStatus, setAgentStatus] = useState(null);
  const [marketData, setMarketData] = useState({});
  const [artifacts, setArtifacts] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [emergencyStatus, setEmergencyStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cycleLoading, setCycleLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, ethRes, btcRes, artifactsRes, proposalsRes, emergencyRes] = await Promise.all([
        axios.get(`${API}/agent/status`),
        axios.get(`${API}/market/price/ETH`).catch(() => ({ data: { price: 0 } })),
        axios.get(`${API}/market/price/BTC`).catch(() => ({ data: { price: 0 } })),
        axios.get(`${API}/artifacts/recent?count=20`),
        axios.get(`${API}/governance/proposals`),
        axios.get(`${API}/emergency/status`)
      ]);

      setAgentStatus(statusRes.data);
      setMarketData({
        ETH: ethRes.data,
        BTC: btcRes.data
      });
      setArtifacts(Array.isArray(artifactsRes.data) ? artifactsRes.data : []);
      setProposals(Array.isArray(proposalsRes.data) ? proposalsRes.data : []);
      setEmergencyStatus(emergencyRes.data);
      setError(null);
    } catch (e) {
      console.error("Error fetching data:", e);
      setError("Failed to fetch data. Backend may be starting up...");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const runCycle = async (asset = "ETH") => {
    setCycleLoading(true);
    try {
      await axios.post(`${API}/agent/cycle?asset=${asset}`);
      await fetchData();
    } catch (e) {
      console.error("Cycle error:", e);
    } finally {
      setCycleLoading(false);
    }
  };

  const togglePause = async () => {
    try {
      if (emergencyStatus?.is_trading_paused) {
        await axios.post(`${API}/emergency/resume`);
      } else {
        await axios.post(`${API}/emergency/pause`);
      }
      await fetchData();
    } catch (e) {
      console.error("Pause toggle error:", e);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-cyan-500 mx-auto animate-pulse" />
          <p className="mt-4 text-slate-400">Initializing Sentinel-01...</p>
        </div>
      </div>
    );
  }

  const portfolio = agentStatus?.portfolio || {};
  const metrics = agentStatus?.metrics || {};

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-cyan-500/10 rounded-lg">
                <Shield className="w-6 h-6 text-cyan-500" />
              </div>
              <div>
                <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                  SENTINEL-01
                </h1>
                <p className="text-xs text-slate-500">AETHEL Foundation</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <StatusIndicator 
                status={!emergencyStatus?.is_trading_paused} 
                label={emergencyStatus?.is_trading_paused ? "PAUSED" : "ACTIVE"} 
              />
              <Badge className={getRegimeColor(agentStatus?.current_regime)}>
                {agentStatus?.current_regime?.toUpperCase()}
              </Badge>
              <span className="text-xs font-mono text-slate-500">
                v{agentStatus?.version}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Emergency Alert */}
      {emergencyStatus?.is_emergency_active && (
        <Alert className="m-4 bg-red-500/10 border-red-500/30">
          <AlertTriangle className="h-4 w-4 text-red-500" />
          <AlertTitle className="text-red-400">Emergency Active</AlertTitle>
          <AlertDescription className="text-red-300">
            Level: {emergencyStatus.current_level} - Trading is suspended
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert className="m-4 bg-amber-500/10 border-amber-500/30">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <AlertDescription className="text-amber-300">{error}</AlertDescription>
        </Alert>
      )}

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="bg-slate-900 border border-slate-800" data-testid="dashboard-tabs">
            <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
            <TabsTrigger value="market" data-testid="tab-market">Market</TabsTrigger>
            <TabsTrigger value="artifacts" data-testid="tab-artifacts">Artifacts</TabsTrigger>
            <TabsTrigger value="governance" data-testid="tab-governance">Governance</TabsTrigger>
            <TabsTrigger value="risk" data-testid="tab-risk">Risk</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6" data-testid="overview-content">
            {/* Quick Actions */}
            <div className="flex gap-3 flex-wrap">
              <Button 
                onClick={() => runCycle("ETH")} 
                disabled={cycleLoading || emergencyStatus?.is_trading_paused}
                className="bg-cyan-600 hover:bg-cyan-500"
                data-testid="run-cycle-btn"
              >
                {cycleLoading ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Zap className="w-4 h-4 mr-2" />
                )}
                Run Cycle (ETH)
              </Button>
              <Button 
                onClick={() => runCycle("BTC")} 
                disabled={cycleLoading || emergencyStatus?.is_trading_paused}
                variant="outline"
                className="border-slate-700"
                data-testid="run-cycle-btc-btn"
              >
                Run Cycle (BTC)
              </Button>
              <Button 
                onClick={togglePause}
                variant={emergencyStatus?.is_trading_paused ? "default" : "destructive"}
                data-testid="pause-toggle-btn"
              >
                {emergencyStatus?.is_trading_paused ? (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Resume
                  </>
                ) : (
                  <>
                    <Pause className="w-4 h-4 mr-2" />
                    Pause
                  </>
                )}
              </Button>
              <Button 
                onClick={fetchData} 
                variant="ghost" 
                size="icon"
                data-testid="refresh-btn"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard 
                title="Portfolio Value" 
                value={formatCurrency(portfolio.total_value || 0)}
                subtitle={`Cash: ${formatCurrency(portfolio.cash_balance || 0)}`}
                icon={DollarSign}
                trend={((portfolio.total_value - 100000) / 100000) * 100}
                color="text-cyan-400"
              />
              <MetricCard 
                title="Drawdown" 
                value={formatPercent(portfolio.current_drawdown || 0)}
                subtitle="Max: 5.00%"
                icon={TrendingDown}
                color={portfolio.current_drawdown > 0.03 ? "text-red-400" : "text-emerald-400"}
              />
              <MetricCard 
                title="Total Cycles" 
                value={metrics.total_cycles || 0}
                subtitle={`${metrics.successful_trades || 0} trades`}
                icon={Activity}
                color="text-blue-400"
              />
              <MetricCard 
                title="Success Rate" 
                value={`${metrics.success_rate || 100}%`}
                subtitle={`${metrics.risk_blocks || 0} blocked`}
                icon={Shield}
                color="text-emerald-400"
              />
            </div>

            {/* Two Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Portfolio Positions */}
              <Card className="bg-slate-900/50 border-slate-700/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-300">Positions</CardTitle>
                </CardHeader>
                <CardContent>
                  {Object.keys(portfolio.positions || {}).length === 0 ? (
                    <p className="text-slate-500 text-sm">No open positions</p>
                  ) : (
                    <div className="space-y-2">
                      {Object.entries(portfolio.positions || {}).map(([asset, value]) => (
                        <div key={asset} className="flex justify-between items-center p-2 bg-slate-800/30 rounded">
                          <span className="font-mono text-cyan-400">{asset}</span>
                          <span className="font-mono">{formatCurrency(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Recent Artifacts */}
              <Card className="bg-slate-900/50 border-slate-700/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-300">Recent Artifacts</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[200px]">
                    <div className="space-y-2">
                      {(Array.isArray(artifacts) ? artifacts : []).slice(0, 5).map((artifact, i) => (
                        <ArtifactItem key={artifact.artifact_id || i} artifact={artifact} />
                      ))}
                      {artifacts.length === 0 && (
                        <p className="text-slate-500 text-sm">No artifacts yet. Run a cycle to generate.</p>
                      )}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>

            {/* Policy Hash */}
            <Card className="bg-slate-900/50 border-slate-700/50">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Lock className="w-5 h-5 text-cyan-500" />
                  <div>
                    <p className="text-xs text-slate-500">POLICY HASH</p>
                    <p className="font-mono text-sm text-cyan-400" data-testid="policy-hash">
                      {agentStatus?.policy_hash}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Market Tab */}
          <TabsContent value="market" className="space-y-6" data-testid="market-content">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {['ETH', 'BTC'].map(asset => {
                const data = marketData[asset] || {};
                return (
                  <Card key={asset} className="bg-slate-900/50 border-slate-700/50">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <span className="text-2xl font-bold">{asset}</span>
                        {data.price_change_24h >= 0 ? (
                          <TrendingUp className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <TrendingDown className="w-5 h-5 text-red-400" />
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <p className="text-3xl font-mono font-bold text-cyan-400">
                          {formatCurrency(data.price || 0)}
                        </p>
                        <p className={`text-sm ${data.price_change_24h >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {data.price_change_24h >= 0 ? '+' : ''}{(data.price_change_24h || 0).toFixed(2)}% (24h)
                        </p>
                      </div>
                      <Separator className="bg-slate-800" />
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-slate-500">Volume 24h</p>
                          <p className="font-mono">{formatCurrency(data.volume_24h || 0)}</p>
                        </div>
                        <div>
                          <p className="text-slate-500">Market Cap</p>
                          <p className="font-mono">{formatCurrency(data.market_cap || 0)}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* Artifacts Tab */}
          <TabsContent value="artifacts" className="space-y-6" data-testid="artifacts-content">
            <Card className="bg-slate-900/50 border-slate-700/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-cyan-500" />
                  Validation Artifacts
                </CardTitle>
                <CardDescription>
                  Every decision cycle generates a verifiable artifact
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px]">
                  <div className="space-y-3">
                    {(Array.isArray(artifacts) ? artifacts : []).map((artifact, i) => (
                      <ArtifactItem key={artifact.artifact_id || i} artifact={artifact} />
                    ))}
                    {artifacts.length === 0 && (
                      <p className="text-slate-500 text-center py-8">
                        No artifacts yet. Run cycles to generate validation artifacts.
                      </p>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Governance Tab */}
          <TabsContent value="governance" className="space-y-6" data-testid="governance-content">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="bg-slate-900/50 border-slate-700/50 lg:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="w-5 h-5 text-cyan-500" />
                    Proposals
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-3">
                      {(Array.isArray(proposals) ? proposals : []).map((proposal, i) => (
                        <ProposalItem key={proposal.proposal_id || i} proposal={proposal} />
                      ))}
                      {proposals.length === 0 && (
                        <p className="text-slate-500 text-center py-8">
                          No active proposals
                        </p>
                      )}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-slate-700/50">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-slate-300">Governance Stats</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-xs text-slate-500">Quorum Required</p>
                    <p className="text-lg font-mono text-cyan-400">51%</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Proposal Duration</p>
                    <p className="text-lg font-mono">24 hours</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Execution Delay</p>
                    <p className="text-lg font-mono">6 hours</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Emergency Quorum</p>
                    <p className="text-lg font-mono text-amber-400">66%</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Risk Tab */}
          <TabsContent value="risk" className="space-y-6" data-testid="risk-content">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-900/50 border-slate-700/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-cyan-500" />
                    Risk Limits
                  </CardTitle>
                  <CardDescription>Constitutional limits - NEVER violated</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <RiskGauge 
                    value={(portfolio.current_drawdown || 0) * 100} 
                    max={5} 
                    label="Drawdown"
                    color={(portfolio.current_drawdown || 0) > 0.04 ? "text-red-400" : "text-emerald-400"}
                  />
                  <RiskGauge 
                    value={2} 
                    max={2} 
                    label="Max Single Trade"
                    color="text-slate-400"
                  />
                  <RiskGauge 
                    value={3} 
                    max={3} 
                    label="Max Daily Loss"
                    color="text-slate-400"
                  />
                  <RiskGauge 
                    value={20} 
                    max={20} 
                    label="Max Position"
                    color="text-slate-400"
                  />
                  <RiskGauge 
                    value={30} 
                    max={30} 
                    label="Min Liquidity"
                    color="text-emerald-400"
                  />
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-slate-700/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-cyan-500" />
                    Reputation Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-slate-800/30 rounded-lg">
                      <p className="text-xs text-slate-500">Total Cycles</p>
                      <p className="text-2xl font-mono font-bold text-cyan-400">{metrics.total_cycles || 0}</p>
                    </div>
                    <div className="p-3 bg-slate-800/30 rounded-lg">
                      <p className="text-xs text-slate-500">Success Rate</p>
                      <p className="text-2xl font-mono font-bold text-emerald-400">{metrics.success_rate || 100}%</p>
                    </div>
                    <div className="p-3 bg-slate-800/30 rounded-lg">
                      <p className="text-xs text-slate-500">Risk Blocks</p>
                      <p className="text-2xl font-mono font-bold text-amber-400">{metrics.risk_blocks || 0}</p>
                    </div>
                    <div className="p-3 bg-slate-800/30 rounded-lg">
                      <p className="text-xs text-slate-500">Policy Violations</p>
                      <p className="text-2xl font-mono font-bold text-emerald-400">{metrics.policy_violations || 0}</p>
                    </div>
                  </div>
                  <Separator className="bg-slate-800" />
                  <div>
                    <p className="text-xs text-slate-500">Governance Compliance</p>
                    <p className="text-lg font-mono text-emerald-400">{metrics.governance_compliance || 100}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Max Drawdown Experienced</p>
                    <p className="text-lg font-mono">
                      {((metrics.max_drawdown_experienced || 0) * 100).toFixed(2)}%
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-8 py-4">
        <div className="container mx-auto px-4 text-center text-xs text-slate-600">
          <p>AETHEL Foundation | Sentinel-01 ERC-8004 Agent</p>
          <p className="mt-1">Capital Preservation First | Profit Secondary</p>
        </div>
      </footer>
    </div>
  );
};

function App() {
  return (
    <div className="App dark">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
