import { CheckCircle2, AlertCircle, Sun, Moon, DoorOpen, DoorClosed, TrendingUp } from 'lucide-react';
import { PeakCoverageMetrics } from '../types';

interface PeakCoveragePanelProps {
  coverage: PeakCoverageMetrics;
  days: string[];
}

export function PeakCoveragePanel({ coverage, days }: PeakCoveragePanelProps) {
  if (!coverage || !coverage.daily_coverage) {
    return null;
  }

  const metrics = [
    { 
      label: 'Lunch Peak', 
      met: coverage.lunch_peak_met_all_days, 
      icon: <Sun className="w-4 h-4" />,
      time: '11:00-14:00'
    },
    { 
      label: 'Dinner Peak', 
      met: coverage.dinner_peak_met_all_days, 
      icon: <Moon className="w-4 h-4" />,
      time: '17:00-21:00'
    },
    { 
      label: 'Opening', 
      met: coverage.opening_covered_all_days, 
      icon: <DoorOpen className="w-4 h-4" />,
      time: '06:30'
    },
    { 
      label: 'Closing', 
      met: coverage.closing_covered_all_days, 
      icon: <DoorClosed className="w-4 h-4" />,
      time: '23:00'
    },
  ];

  const allMet = metrics.every(m => m.met);

  return (
    <div className="panel-mcd">
      <div className="panel-mcd-header flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#292929]">Peak Coverage</h3>
          <p className="text-xs text-[#6E6E6E] mt-0.5">Staffing level compliance</p>
        </div>
        <div className={`icon-box ${allMet ? 'icon-box-success' : 'icon-box-warning'}`}>
          {allMet ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
        </div>
      </div>

      <div className="panel-mcd-body space-y-3">
        {metrics.map((metric) => (
          <div key={metric.label} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`icon-box w-8 h-8 rounded-lg ${
                metric.met ? 'icon-box-success' : 'icon-box-warning'
              }`}>
                {metric.icon}
              </div>
              <div>
                <p className="text-sm font-medium text-[#292929]">{metric.label}</p>
                <p className="text-xs text-[#6E6E6E]">{metric.time}</p>
              </div>
            </div>
            <span className={`badge-mcd ${metric.met ? 'badge-mcd-success' : 'badge-mcd-danger'}`}>
              {metric.met ? 'Met' : 'Short'}
            </span>
          </div>
        ))}

        {/* Weekend Coverage */}
        <div className="pt-3 mt-3 border-t border-[#E0E0E0]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`icon-box w-8 h-8 rounded-lg ${
                coverage.meets_weekend_target ? 'icon-box-success' : 'icon-box-yellow'
              }`}>
                <TrendingUp className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-[#292929]">Weekend Increase</p>
                <p className="text-xs text-[#6E6E6E]">Target: +{coverage.weekend_target}%</p>
              </div>
            </div>
            <span className={`badge-mcd ${coverage.meets_weekend_target ? 'badge-mcd-success' : 'badge-mcd-warning'}`}>
              +{coverage.weekend_vs_weekday_increase.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Daily breakdown */}
      <div className="px-4 pb-4">
        <p className="text-mcd-label mb-3">Daily Status</p>
        <div className="grid grid-cols-7 gap-1.5">
          {days.slice(0, 14).map(day => {
            const metrics = coverage.daily_coverage[day];
            if (!metrics) return null;
            
            const date = new Date(day);
            const dayNum = date.getDate();
            const isWeekend = metrics.is_weekend;
            const allGood = metrics.lunch_peak_met && metrics.dinner_peak_met && 
                           metrics.opening_covered && metrics.closing_covered;
            
            return (
              <div
                key={day}
                className={`aspect-square rounded-md flex items-center justify-center text-xs font-semibold border ${
                  allGood 
                    ? isWeekend 
                      ? 'bg-[#FFCC00]/15 border-[#FFCC00]/30 text-[#996600]' 
                      : 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-red-50 border-red-200 text-red-600'
                }`}
                title={`${day}: L:${metrics.lunch_actual}/${metrics.lunch_required} D:${metrics.dinner_actual}/${metrics.dinner_required}`}
              >
                {dayNum}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
