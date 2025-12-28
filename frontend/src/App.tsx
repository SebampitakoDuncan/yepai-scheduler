import { useState } from 'react';
import {
  Calendar,
  Clock,
  Download,
  Play,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Users,
  Timer,
  AlertTriangle,
  TrendingUp,
} from 'lucide-react';
import { RosterResponse } from './types';
import { RosterGrid } from './components/RosterGrid';
import { ConflictsList } from './components/ConflictsList';
import { PeakCoveragePanel } from './components/PeakCoveragePanel';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export default function App() {
  const [roster, setRoster] = useState<RosterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState('2024-12-09');
  const [weeks, setWeeks] = useState(2);

  const generateRoster = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: startDate,
          weeks,
          time_limit_seconds: 120,
        }),
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate roster');
      }
      
      const data: RosterResponse = await res.json();
      setRoster(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const exportRoster = async () => {
    try {
      const res = await fetch(`${API_BASE}/export?start_date=${startDate}&weeks=${weeks}`);
      if (!res.ok) throw new Error('Export failed');
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `roster_${startDate}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
    }
  };

  const totalHours = roster?.roster.reduce((sum, emp) => sum + emp.total_hours, 0) || 0;
  const managers = roster?.roster.filter(e => e.is_manager).length || 0;
  const criticalCount = roster?.conflicts.filter(c => c.severity === 'critical').length || 0;

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="header-mcd sticky top-0 z-50">
        <div className="max-w-[1800px] mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-4">
            <div className="logo-box">
              <span className="text-white font-bold text-xl">M</span>
            </div>
            <div>
              <h1 className="text-base font-semibold text-[#292929]">Workforce Scheduler</h1>
              <p className="text-xs text-[#6E6E6E]">Intelligent Rostering System</p>
            </div>
          </div>
          
          {/* Controls */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 input-mcd pr-2">
              <Calendar className="w-4 h-4 text-[#6E6E6E]" />
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-transparent text-sm text-[#292929] outline-none w-32"
              />
            </div>
            
            <select
              value={weeks}
              onChange={(e) => setWeeks(Number(e.target.value))}
              className="input-mcd text-sm"
            >
              <option value={1}>1 Week</option>
              <option value={2}>2 Weeks</option>
              <option value={4}>4 Weeks</option>
            </select>
            
            <button
              onClick={generateRoster}
              disabled={loading}
              className="btn-mcd-primary"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>{loading ? 'Generating...' : 'Generate'}</span>
            </button>
            
            {roster && (
              <button onClick={exportRoster} className="btn-mcd-secondary">
                <Download className="w-4 h-4 text-[#6E6E6E]" />
                <span>Export</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-[1800px] mx-auto px-6 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Empty State */}
        {!roster && !loading && (
          <div className="flex items-center justify-center min-h-[70vh]">
            <div className="text-center max-w-md">
              <div className="empty-state-icon">
                <Users className="w-12 h-12 text-[#292929]" />
              </div>
              
              <h2 className="text-mcd-title mb-4">
                Intelligent Scheduling
              </h2>
              <p className="text-mcd-subtitle leading-relaxed mb-8">
                Generate optimized workforce rosters using multi-agent AI. 
                The system analyzes demand patterns, matches employee skills, 
                and resolves conflicts automatically.
              </p>
              
              <button onClick={generateRoster} className="btn-mcd-primary text-base px-8 py-4">
                <Play className="w-5 h-5" />
                <span>Generate Roster</span>
                <ChevronRight className="w-5 h-5 opacity-60" />
              </button>
              
              {/* Feature tags */}
              <div className="flex items-center justify-center gap-3 mt-8">
                {['Multi-Agent AI', 'Constraint Optimization', 'Fair Work Compliant'].map(feature => (
                  <span key={feature} className="badge-mcd badge-mcd-neutral">
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center min-h-[70vh]">
            <div className="text-center">
              <div className="w-20 h-20 rounded-2xl bg-[#FFCC00] flex items-center justify-center mx-auto mb-6 animate-pulse-yellow">
                <Loader2 className="w-10 h-10 text-[#292929] animate-spin" />
              </div>
              <p className="text-lg font-semibold text-[#292929]">Generating Roster</p>
              <p className="text-sm text-[#6E6E6E] mt-1">Multi-agent system optimizing coverage...</p>
            </div>
          </div>
        )}

        {/* Results */}
        {roster && !loading && (
          <div className="space-y-6">
            {/* Stats Row */}
            <div className="grid grid-cols-6 gap-4">
              <StatCard 
                icon={<Users className="w-5 h-5" />}
                iconClass="icon-box-yellow"
                label="Employees" 
                value={roster.total_employees.toString()} 
                sub={`${managers} managers`}
              />
              <StatCard 
                icon={<Calendar className="w-5 h-5" />}
                iconClass="icon-box-neutral"
                label="Duration" 
                value={`${roster.days.length} days`} 
                sub={`${weeks} week roster`}
              />
              <StatCard 
                icon={<Clock className="w-5 h-5" />}
                iconClass="icon-box-neutral"
                label="Total Hours" 
                value={totalHours.toFixed(0)} 
                sub={`${(totalHours / roster.total_employees).toFixed(1)}h average`}
              />
              <StatCard 
                icon={<Timer className="w-5 h-5" />}
                iconClass="icon-box-success"
                label="Gen Time" 
                value={`${roster.generation_time_seconds}s`} 
                sub="Target: < 180s"
                variant="success"
              />
              <StatCard 
                icon={<AlertTriangle className="w-5 h-5" />}
                iconClass={criticalCount > 0 ? "icon-box-warning" : "icon-box-neutral"}
                label="Conflicts" 
                value={roster.conflicts.length.toString()} 
                sub={criticalCount > 0 ? `${criticalCount} critical` : 'None critical'}
                variant={criticalCount > 0 ? "warning" : undefined}
              />
              <StatCard 
                icon={roster.status === 'success' ? 
                  <CheckCircle2 className="w-5 h-5" /> : 
                  <TrendingUp className="w-5 h-5" />
                }
                iconClass={roster.status === 'success' ? "icon-box-success" : "icon-box-yellow"}
                label="Status" 
                value={roster.status === 'success' ? 'Optimal' : 'Partial'} 
                sub={roster.status === 'success' ? 'All constraints met' : 'Review recommended'}
                variant={roster.status === 'success' ? "success" : "highlight"}
              />
            </div>

            {/* Schedule Overview - Full Width */}
            <div className="card-mcd">
              <div className="card-mcd-header flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-[#292929]">Schedule Overview</h2>
                  <p className="text-xs text-[#6E6E6E] mt-0.5">
                    {roster.roster.filter(e => e.total_hours > 0).length} employees across {roster.days.length} days
                  </p>
                </div>
                <div className="badge-mcd badge-mcd-success">
                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                  <span>Generated in {roster.generation_time_seconds}s</span>
                </div>
              </div>
              <RosterGrid roster={roster.roster} days={roster.days} />
            </div>

            {/* Sidebar - Below Schedule */}
            {roster.peak_coverage && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <PeakCoveragePanel coverage={roster.peak_coverage} days={roster.days} />
              </div>
            )}

            {/* Conflicts - Bottom */}
            {roster.conflicts.length > 0 && (
              <ConflictsList conflicts={roster.conflicts} />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({ 
  icon,
  iconClass,
  label, 
  value, 
  sub, 
  variant,
}: { 
  icon: React.ReactNode;
  iconClass: string;
  label: string; 
  value: string; 
  sub: string;
  variant?: 'success' | 'warning' | 'danger' | 'highlight';
}) {
  const borderClass = variant === 'success' ? 'stat-card-mcd-success' :
                      variant === 'warning' ? 'stat-card-mcd-warning' :
                      variant === 'danger' ? 'stat-card-mcd-danger' :
                      variant === 'highlight' ? 'stat-card-mcd-highlight' : '';

  return (
    <div className={`stat-card-mcd ${borderClass}`}>
      <div className={`icon-box ${iconClass} mb-3`}>
        {icon}
      </div>
      <p className="text-mcd-label mb-1">{label}</p>
      <p className="text-2xl font-bold text-[#292929] tracking-tight">
        {value}
      </p>
      <p className="text-xs text-[#6E6E6E] mt-1">{sub}</p>
    </div>
  );
}
