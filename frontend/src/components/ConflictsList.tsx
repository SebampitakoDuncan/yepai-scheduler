import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { Conflict } from '../types';

interface ConflictsListProps {
  conflicts: Conflict[];
}

const severityConfig: Record<string, { 
  icon: React.ReactNode; 
  bgClass: string;
  borderClass: string;
  textClass: string;
  label: string;
}> = {
  critical: {
    icon: <AlertCircle className="w-4 h-4" />,
    bgClass: 'bg-red-50',
    borderClass: 'border-red-200',
    textClass: 'text-red-700',
    label: 'Critical',
  },
  high: {
    icon: <AlertTriangle className="w-4 h-4" />,
    bgClass: 'bg-orange-50',
    borderClass: 'border-orange-200',
    textClass: 'text-orange-700',
    label: 'High',
  },
  medium: {
    icon: <Info className="w-4 h-4" />,
    bgClass: 'bg-yellow-50',
    borderClass: 'border-yellow-200',
    textClass: 'text-yellow-700',
    label: 'Medium',
  },
  low: {
    icon: <Info className="w-4 h-4" />,
    bgClass: 'bg-gray-50',
    borderClass: 'border-gray-200',
    textClass: 'text-gray-600',
    label: 'Low',
  },
};

export function ConflictsList({ conflicts }: ConflictsListProps) {
  // Sort by severity
  const sorted = [...conflicts].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return (order[a.severity as keyof typeof order] ?? 4) - (order[b.severity as keyof typeof order] ?? 4);
  });

  const critical = sorted.filter(c => c.severity === 'critical').length;

  return (
    <div className="card-mcd">
      <div className="card-mcd-header flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#292929]">Conflicts</h3>
          <p className="text-xs text-[#6E6E6E] mt-0.5">
            {conflicts.length} total{critical > 0 ? `, ${critical} critical` : ''}
          </p>
        </div>
        {critical > 0 && (
          <div className="icon-box w-8 h-8 rounded-lg bg-red-100 text-red-600">
            <AlertCircle className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sorted.slice(0, 12).map((conflict, idx) => {
            const config = severityConfig[conflict.severity] || severityConfig.low;
            
            return (
              <div
                key={idx}
                className={`rounded-lg p-3 border ${config.bgClass} ${config.borderClass}`}
              >
                <div className="flex items-start gap-2.5">
                  <div className={`mt-0.5 flex-shrink-0 ${config.textClass}`}>
                    {config.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-semibold uppercase tracking-wide ${config.textClass}`}>
                        {config.label}
                      </span>
                      <span className="text-xs text-[#6E6E6E]">
                        {conflict.type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className={`text-xs leading-relaxed ${config.textClass}`}>
                      {conflict.description}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        {conflicts.length > 12 && (
          <p className="text-center text-xs text-[#6E6E6E] mt-4 pt-3 border-t border-[#E0E0E0]">
            +{conflicts.length - 12} more conflicts
          </p>
        )}
      </div>
    </div>
  );
}
