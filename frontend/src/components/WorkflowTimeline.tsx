import { CheckCircle2, Activity, Wrench, ClipboardCheck, Zap } from 'lucide-react';
import { WorkflowStep } from '../types';

interface WorkflowTimelineProps {
  steps: WorkflowStep[];
}

const stepIcons: Record<string, React.ReactNode> = {
  'INIT': <Zap className="w-3.5 h-3.5" />,
  'DEMAND': <Activity className="w-3.5 h-3.5" />,
  'MATCH': <Activity className="w-3.5 h-3.5" />,
  'SCHEDULE': <Activity className="w-3.5 h-3.5" />,
  'VALIDATE': <ClipboardCheck className="w-3.5 h-3.5" />,
  'RESOLVE': <Wrench className="w-3.5 h-3.5" />,
  'FINAL': <ClipboardCheck className="w-3.5 h-3.5" />,
  'COMPLETE': <CheckCircle2 className="w-3.5 h-3.5" />,
};

const stepLabels: Record<string, string> = {
  'INIT': 'Init',
  'DEMAND': 'Demand',
  'MATCH': 'Match',
  'SCHEDULE': 'Schedule',
  'VALIDATE': 'Validate',
  'RESOLVE': 'Resolve',
  'FINAL': 'Final',
  'COMPLETE': 'Complete',
};

export function WorkflowTimeline({ steps }: WorkflowTimelineProps) {
  // Get unique workflow stages (group by step type)
  const uniqueSteps = Array.from(
    new Map(steps.map(step => [step.step, step])).values()
  );

  // Sort by order of appearance
  const stepOrder = ['INIT', 'DEMAND', 'MATCH', 'SCHEDULE', 'VALIDATE', 'RESOLVE', 'FINAL', 'COMPLETE'];
  const sortedSteps = uniqueSteps.sort((a, b) => {
    const aIdx = stepOrder.indexOf(a.step);
    const bIdx = stepOrder.indexOf(b.step);
    if (aIdx === -1 && bIdx === -1) return 0;
    if (aIdx === -1) return 1;
    if (bIdx === -1) return -1;
    return aIdx - bIdx;
  });

  return (
    <div className="card-mcd">
      <div className="card-mcd-header">
        <h3 className="text-sm font-semibold text-[#292929]">Agent Workflow</h3>
      </div>

      <div className="p-4">
        <div className="flex items-center justify-center gap-1 flex-wrap">
          {sortedSteps.map((step, idx) => {
            const isComplete = step.step === 'COMPLETE';
            const isLast = idx === sortedSteps.length - 1;
            
            return (
              <div key={`step-${step.step}`} className="flex items-center">
                {/* Step */}
                <div className="flex flex-col items-center">
                  <div className={`icon-box w-8 h-8 rounded-lg ${
                    isComplete ? 'icon-box-success' : 'icon-box-yellow'
                  }`}>
                    {stepIcons[step.step] || <Activity className="w-3.5 h-3.5" />}
                  </div>
                  <p className={`text-[10px] font-medium mt-1.5 text-center whitespace-nowrap ${
                    isComplete ? 'text-[#1B7A45]' : 'text-[#292929]'
                  }`}>
                    {stepLabels[step.step] || step.step}
                  </p>
                </div>
                
                {/* Connector */}
                {!isLast && (
                  <div className="w-6 h-0.5 bg-[#E0E0E0] mx-1" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
