import { EmployeeSchedule } from '../types';

interface RosterGridProps {
  roster: EmployeeSchedule[];
  days: string[];
}

const shiftStyles: Record<string, string> = {
  'S': 'bg-[#FFCC00]/20 text-[#996600]',
  '1F': 'bg-[#FFCC00]/20 text-[#996600]',
  '2F': 'bg-[#DA291C]/10 text-[#DA291C]',
  '3F': 'bg-green-100 text-green-700',
  'SC': 'bg-blue-100 text-blue-700',
  'M': 'bg-purple-100 text-purple-700',
  '/': 'bg-gray-100 text-gray-400',
};

function formatDay(dateStr: string): { day: string; date: string; isWeekend: boolean } {
  const date = new Date(dateStr);
  const dayNames = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  const dayOfWeek = date.getDay();
  return {
    day: dayNames[dayOfWeek],
    date: date.getDate().toString(),
    isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
  };
}

export function RosterGrid({ roster, days }: RosterGridProps) {
  // Sort: managers first, then by name
  const sortedRoster = [...roster].sort((a, b) => {
    if (a.is_manager !== b.is_manager) return a.is_manager ? -1 : 1;
    return a.employee_name.localeCompare(b.employee_name);
  });

  return (
    <div className="overflow-y-auto max-h-[600px]">
      <table className="w-full border-collapse text-[11px]">
        <thead className="sticky top-0 z-10">
          <tr className="bg-[#F7F7F7]">
            <th className="text-left py-2 px-2 font-semibold text-[#6E6E6E] border-b border-[#E0E0E0] w-[140px]">
              Employee
            </th>
            <th className="text-center py-2 px-1 font-semibold text-[#6E6E6E] border-b border-[#E0E0E0] w-8">
              T
            </th>
            {days.map(day => {
              const { day: dayName, date, isWeekend } = formatDay(day);
              return (
                <th
                  key={day}
                  className={`text-center py-2 px-0.5 font-semibold border-b border-[#E0E0E0] w-9 ${
                    isWeekend ? 'bg-[#FFCC00]/10 text-[#996600]' : 'text-[#6E6E6E]'
                  }`}
                >
                  <div className="leading-tight">
                    <div className="text-[9px] opacity-70">{dayName}</div>
                    <div className="text-[10px] font-bold">{date}</div>
                  </div>
                </th>
              );
            })}
            <th className="text-right py-2 px-2 font-semibold text-[#6E6E6E] border-b border-[#E0E0E0] w-12">
              Hrs
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedRoster.map((employee, idx) => (
            <tr 
              key={employee.employee_id} 
              className={`${idx % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'} hover:bg-[#F5F5F5]`}
            >
              <td className="py-1.5 px-2 border-b border-[#F0F0F0]">
                <div className="flex items-center gap-1.5">
                  <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[9px] font-bold ${
                    employee.is_manager 
                      ? 'bg-[#FFCC00] text-[#292929]' 
                      : 'bg-[#E0E0E0] text-[#6E6E6E]'
                  }`}>
                    {employee.employee_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                  </span>
                  <div className="truncate max-w-[100px]">
                    <span className="font-medium text-[#292929]">
                      {employee.employee_name.split(' ')[0]}
                    </span>
                    <span className="text-[#999] ml-0.5">
                      {employee.employee_name.split(' ').slice(1).map(n => n[0]).join('')}
                    </span>
                  </div>
                </div>
              </td>
              <td className="py-1.5 px-1 text-center border-b border-[#F0F0F0]">
                <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                  employee.employee_type === 'Full-Time' || employee.employee_type === 'Full-time'
                    ? 'bg-green-100 text-green-700' 
                    : employee.employee_type === 'Part-Time' || employee.employee_type === 'Part-time'
                    ? 'bg-gray-100 text-gray-600'
                    : 'bg-[#FFCC00]/20 text-[#996600]'
                }`}>
                  {(employee.employee_type === 'Full-Time' || employee.employee_type === 'Full-time') ? 'F' : 
                   (employee.employee_type === 'Part-Time' || employee.employee_type === 'Part-time') ? 'P' : 'C'}
                </span>
              </td>
              {days.map(day => {
                const shift = employee.shifts[day];
                const code = shift?.shift_code || '/';
                const { isWeekend } = formatDay(day);
                return (
                  <td 
                    key={day} 
                    className={`py-1.5 px-0.5 text-center border-b border-[#F0F0F0] ${
                      isWeekend ? 'bg-[#FFCC00]/5' : ''
                    }`}
                  >
                    <span className={`inline-block w-7 py-0.5 rounded text-[9px] font-bold ${
                      shiftStyles[code] || 'bg-gray-100 text-gray-400'
                    }`}>
                      {code === '/' ? '-' : code}
                    </span>
                  </td>
                );
              })}
              <td className="py-1.5 px-2 text-right border-b border-[#F0F0F0]">
                <span className={`font-bold ${
                  employee.total_hours > 76 ? 'text-[#E74C3C]' : 
                  employee.total_hours < 40 ? 'text-[#F39C12]' : 
                  'text-[#292929]'
                }`}>
                  {employee.total_hours.toFixed(0)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
