import time as time_module
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
from models.employee import Employee, EmployeeType, Station
from models.store import Store, StaffingRequirement
from models.shift import ShiftType, Shift, SHIFT_DEFINITIONS
from models.constraints import Constraints, Conflict, ConflictType, Resolution


class SchedulerService:
    """Core scheduling engine using OR-Tools CP-SAT solver."""
    
    def __init__(
        self,
        employees: List[Employee],
        store: Store,
        constraints: Constraints,
        days: List[str],
    ):
        self.employees = employees
        self.store = store
        self.constraints = constraints
        self.days = days
        self.shift_types = [st for st in ShiftType if st != ShiftType.DAY_OFF]
        self.stations = list(Station)
        
        # Build lookup maps
        self.employee_map = {e.id: e for e in employees}
        self.managers = [e for e in employees if e.is_manager]
        self.crew = [e for e in employees if not e.is_manager]
        
        # Pre-compute shift coverage for peak periods
        self.lunch_peak_shifts = [s for s in self.shift_types if SHIFT_DEFINITIONS[s].get("covers_lunch_peak", False)]
        self.dinner_peak_shifts = [s for s in self.shift_types if SHIFT_DEFINITIONS[s].get("covers_dinner_peak", False)]
        self.opening_shifts = [s for s in self.shift_types if SHIFT_DEFINITIONS[s].get("is_opening", False)]
        self.closing_shifts = [s for s in self.shift_types if SHIFT_DEFINITIONS[s].get("is_closing", False)]
    
    def _is_weekend(self, day: str) -> bool:
        """Check if a day is a weekend (Saturday or Sunday)."""
        try:
            dt = datetime.fromisoformat(day)
            return dt.weekday() >= 5  # 5=Saturday, 6=Sunday
        except:
            return "Sat" in day or "Sun" in day
    
    def generate_roster(self, time_limit_seconds: int = 180) -> Dict[str, Any]:
        """Generate an optimized roster using constraint programming."""
        start_time = time_module.time()
        
        model = cp_model.CpModel()
        
        # Decision variables: employee e works shift s on day d
        shifts = {}
        for e in self.employees:
            for d in self.days:
                for s in self.shift_types:
                    shifts[(e.id, d, s.value)] = model.NewBoolVar(f'shift_e{e.id}_d{d}_s{s.value}')
        
        # Constraint 1: Each employee works at most one shift per day
        for e in self.employees:
            for d in self.days:
                model.AddAtMostOne(
                    shifts[(e.id, d, s.value)] for s in self.shift_types
                )
        
        # Constraint 2: Respect employee availability - only assign if available
        for e in self.employees:
            for d in self.days:
                available_codes = e.availability.get(d, [])
                if not available_codes:
                    # Employee not available this day - force day off
                    for s in self.shift_types:
                        model.Add(shifts[(e.id, d, s.value)] == 0)
                else:
                    # Only allow shifts they're available for
                    for s in self.shift_types:
                        if s.value not in available_codes:
                            model.Add(shifts[(e.id, d, s.value)] == 0)
        
        # Constraint 3: Weekly hours within limits (soft constraint - allow some flexibility)
        for e in self.employees:
            min_hours, max_hours = e.get_hour_limits()
            weekly_hours = []
            for d in self.days:
                for s in self.shift_types:
                    hours = SHIFT_DEFINITIONS[s]["hours"]
                    hour_var = model.NewIntVar(0, int(hours * 10), f'hours_e{e.id}_d{d}_s{s.value}')
                    weekly_hours.append(hour_var)
                    model.Add(hour_var == int(hours * 10)).OnlyEnforceIf(shifts[(e.id, d, s.value)])
                    model.Add(hour_var == 0).OnlyEnforceIf(shifts[(e.id, d, s.value)].Not())
            
            total_hours = sum(weekly_hours)
            week_multiplier = max(1, len(self.days) // 7)
            # Max hours is a hard constraint
            model.Add(total_hours <= int(max_hours * 10 * week_multiplier * 1.1))  # 10% buffer
        
        # Constraint 4: Minimum 10-hour rest between shifts (closing -> opening)
        for e in self.employees:
            for d_idx in range(len(self.days) - 1):
                d1, d2 = self.days[d_idx], self.days[d_idx + 1]
                for s1 in self.shift_types:
                    if SHIFT_DEFINITIONS[s1]["is_closing"]:
                        for s2 in self.shift_types:
                            if SHIFT_DEFINITIONS[s2]["is_opening"]:
                                model.AddBoolOr([
                                    shifts[(e.id, d1, s1.value)].Not(),
                                    shifts[(e.id, d2, s2.value)].Not()
                                ])
        
        # ============================================================
        # PEAK PERIOD COVERAGE CONSTRAINTS (Criteria 2)
        # ============================================================
        
        # Get minimum staff requirements
        normal_min_staff = self.store.normal_requirements.total_staff
        peak_min_staff = self.store.peak_requirements.total_staff
        
        # Calculate 20% weekend increase
        weekend_multiplier = 1.0 + (self.constraints.weekend_coverage_increase_percent / 100.0)
        
        for d in self.days:
            is_weekend = self._is_weekend(d)
            
            # Constraint 5: LUNCH PEAK COVERAGE (11:00-14:00)
            # Count employees working shifts that cover lunch peak
            lunch_peak_workers = []
            for e in self.employees:
                for s in self.lunch_peak_shifts:
                    lunch_peak_workers.append(shifts[(e.id, d, s.value)])
            
            # Apply weekend multiplier for 20% more coverage
            lunch_min_staff = int(peak_min_staff * (weekend_multiplier if is_weekend else 1.0))
            model.Add(sum(lunch_peak_workers) >= lunch_min_staff)
            
            # Constraint 6: DINNER PEAK COVERAGE (17:00-21:00)
            # Count employees working shifts that cover dinner peak
            dinner_peak_workers = []
            for e in self.employees:
                for s in self.dinner_peak_shifts:
                    dinner_peak_workers.append(shifts[(e.id, d, s.value)])
            
            # Apply weekend multiplier for 20% more coverage
            dinner_min_staff = int(peak_min_staff * (weekend_multiplier if is_weekend else 1.0))
            model.Add(sum(dinner_peak_workers) >= dinner_min_staff)
            
            # Constraint 7: OPENING COVERAGE (06:30)
            # Ensure minimum staff for opening
            opening_workers = []
            for e in self.employees:
                for s in self.opening_shifts:
                    opening_workers.append(shifts[(e.id, d, s.value)])
            
            opening_min_staff = max(2, int(normal_min_staff * 0.3))  # At least 2 or 30% of normal
            model.Add(sum(opening_workers) >= opening_min_staff)
            
            # Constraint 8: CLOSING COVERAGE (23:00)
            # Ensure minimum staff for closing
            closing_workers = []
            for e in self.employees:
                for s in self.closing_shifts:
                    closing_workers.append(shifts[(e.id, d, s.value)])
            
            closing_min_staff = max(2, int(normal_min_staff * 0.3))  # At least 2 or 30% of normal
            model.Add(sum(closing_workers) >= closing_min_staff)
            
            # Constraint 9: MANAGER COVERAGE
            # At least 1 manager always on duty
            manager_workers = []
            for e in self.managers:
                for s in self.shift_types:
                    manager_workers.append(shifts[(e.id, d, s.value)])
            
            if self.managers:  # Only add constraint if we have managers
                model.Add(sum(manager_workers) >= self.constraints.min_managers_always)
        
        # ============================================================
        # OBJECTIVE FUNCTION
        # ============================================================
        
        # Objective: Maximize coverage while balancing preferences
        objective_terms = []
        
        for e in self.employees:
            for d in self.days:
                is_weekend = self._is_weekend(d)
                for s in self.shift_types:
                    hours = int(SHIFT_DEFINITIONS[s]["hours"] * 10)
                    
                    # Bonus for covering peak periods
                    peak_bonus = 0
                    if SHIFT_DEFINITIONS[s].get("covers_lunch_peak", False):
                        peak_bonus += 5
                    if SHIFT_DEFINITIONS[s].get("covers_dinner_peak", False):
                        peak_bonus += 5
                    
                    # Extra bonus for weekend coverage
                    if is_weekend:
                        peak_bonus += 3
                    
                    objective_terms.append(shifts[(e.id, d, s.value)] * (hours + peak_bonus))
        
        model.Maximize(sum(objective_terms))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_search_workers = 4
        
        status = solver.Solve(model)
        
        solve_time = time_module.time() - start_time
        
        # Extract solution
        roster = []
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for e in self.employees:
                employee_schedule = {
                    "employee_id": e.id,
                    "employee_name": e.name,
                    "employee_type": e.employee_type.value if hasattr(e.employee_type, 'value') else e.employee_type,
                    "is_manager": e.is_manager,
                    "primary_station": e.primary_station.value if hasattr(e.primary_station, 'value') else e.primary_station,
                    "shifts": {},
                    "total_hours": 0.0,
                }
                
                total_hours = 0.0
                for d in self.days:
                    assigned = False
                    for s in self.shift_types:
                        if solver.Value(shifts[(e.id, d, s.value)]) == 1:
                            employee_schedule["shifts"][d] = {
                                "shift_code": s.value,
                                "shift_name": SHIFT_DEFINITIONS[s]["name"],
                                "hours": SHIFT_DEFINITIONS[s]["hours"],
                                "station": e.primary_station.value if hasattr(e.primary_station, 'value') else e.primary_station,
                            }
                            total_hours += SHIFT_DEFINITIONS[s]["hours"]
                            assigned = True
                            break
                    
                    if not assigned:
                        employee_schedule["shifts"][d] = {
                            "shift_code": "/",
                            "shift_name": "Day Off",
                            "hours": 0.0,
                            "station": None,
                        }
                
                employee_schedule["total_hours"] = total_hours
                roster.append(employee_schedule)
        else:
            # Infeasible - generate a basic roster based on availability
            for e in self.employees:
                employee_schedule = {
                    "employee_id": e.id,
                    "employee_name": e.name,
                    "employee_type": e.employee_type.value if hasattr(e.employee_type, 'value') else e.employee_type,
                    "is_manager": e.is_manager,
                    "primary_station": e.primary_station.value if hasattr(e.primary_station, 'value') else e.primary_station,
                    "shifts": {},
                    "total_hours": 0.0,
                }
                
                total_hours = 0.0
                for d in self.days:
                    available = e.availability.get(d, [])
                    if available:
                        shift_code = available[0]
                        shift_type = None
                        for st in self.shift_types:
                            if st.value == shift_code:
                                shift_type = st
                                break
                        
                        if shift_type:
                            employee_schedule["shifts"][d] = {
                                "shift_code": shift_code,
                                "shift_name": SHIFT_DEFINITIONS[shift_type]["name"],
                                "hours": SHIFT_DEFINITIONS[shift_type]["hours"],
                                "station": e.primary_station.value if hasattr(e.primary_station, 'value') else e.primary_station,
                            }
                            total_hours += SHIFT_DEFINITIONS[shift_type]["hours"]
                        else:
                            employee_schedule["shifts"][d] = {
                                "shift_code": "/",
                                "shift_name": "Day Off",
                                "hours": 0.0,
                                "station": None,
                            }
                    else:
                        employee_schedule["shifts"][d] = {
                            "shift_code": "/",
                            "shift_name": "Day Off",
                            "hours": 0.0,
                            "station": None,
                        }
                
                employee_schedule["total_hours"] = total_hours
                roster.append(employee_schedule)
        
        # Calculate peak coverage metrics
        peak_coverage = self._calculate_peak_coverage(roster)
        
        return {
            "status": "optimal" if status == cp_model.OPTIMAL else "feasible" if status == cp_model.FEASIBLE else "heuristic",
            "solve_time_seconds": round(solve_time, 2),
            "roster": roster,
            "days": self.days,
            "store_id": self.store.store_id,
            "total_employees": len(self.employees),
            "managers_count": len(self.managers),
            "crew_count": len(self.crew),
            "peak_coverage": peak_coverage,
        }
    
    def _calculate_peak_coverage(self, roster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate detailed peak coverage metrics for the roster."""
        lunch_peak_coverage = {}
        dinner_peak_coverage = {}
        opening_coverage = {}
        closing_coverage = {}
        weekend_vs_weekday = {"weekend": 0, "weekday": 0}
        
        peak_min_staff = self.store.peak_requirements.total_staff
        weekend_multiplier = 1.0 + (self.constraints.weekend_coverage_increase_percent / 100.0)
        
        for d in self.days:
            is_weekend = self._is_weekend(d)
            
            lunch_count = 0
            dinner_count = 0
            opening_count = 0
            closing_count = 0
            
            for emp_schedule in roster:
                shift_info = emp_schedule.get("shifts", {}).get(d, {})
                shift_code = shift_info.get("shift_code", "/")
                
                if shift_code == "/":
                    continue
                
                try:
                    shift_type = ShiftType(shift_code)
                    if SHIFT_DEFINITIONS[shift_type].get("covers_lunch_peak", False):
                        lunch_count += 1
                    if SHIFT_DEFINITIONS[shift_type].get("covers_dinner_peak", False):
                        dinner_count += 1
                    if SHIFT_DEFINITIONS[shift_type].get("is_opening", False):
                        opening_count += 1
                    if SHIFT_DEFINITIONS[shift_type].get("is_closing", False):
                        closing_count += 1
                except ValueError:
                    pass
            
            required = int(peak_min_staff * (weekend_multiplier if is_weekend else 1.0))
            
            lunch_peak_coverage[d] = {
                "count": lunch_count,
                "required": required,
                "met": lunch_count >= required,
                "is_weekend": is_weekend,
            }
            
            dinner_peak_coverage[d] = {
                "count": dinner_count,
                "required": required,
                "met": dinner_count >= required,
                "is_weekend": is_weekend,
            }
            
            opening_coverage[d] = {"count": opening_count, "required": 2}
            closing_coverage[d] = {"count": closing_count, "required": 2}
            
            if is_weekend:
                weekend_vs_weekday["weekend"] += lunch_count + dinner_count
            else:
                weekend_vs_weekday["weekday"] += lunch_count + dinner_count
        
        # Calculate weekend vs weekday ratio
        weekday_count = len([d for d in self.days if not self._is_weekend(d)])
        weekend_count = len([d for d in self.days if self._is_weekend(d)])
        
        avg_weekday = weekend_vs_weekday["weekday"] / weekday_count if weekday_count > 0 else 0
        avg_weekend = weekend_vs_weekday["weekend"] / weekend_count if weekend_count > 0 else 0
        weekend_increase_pct = ((avg_weekend / avg_weekday) - 1) * 100 if avg_weekday > 0 else 0
        
        return {
            "lunch_peak": lunch_peak_coverage,
            "dinner_peak": dinner_peak_coverage,
            "opening": opening_coverage,
            "closing": closing_coverage,
            "weekend_coverage_increase_percent": round(weekend_increase_pct, 1),
            "weekend_target_percent": self.constraints.weekend_coverage_increase_percent,
            "meets_weekend_target": weekend_increase_pct >= self.constraints.weekend_coverage_increase_percent * 0.9,
            "summary": {
                "lunch_peak_met": all(v["met"] for v in lunch_peak_coverage.values()),
                "dinner_peak_met": all(v["met"] for v in dinner_peak_coverage.values()),
                "opening_covered": all(v["count"] >= v["required"] for v in opening_coverage.values()),
                "closing_covered": all(v["count"] >= v["required"] for v in closing_coverage.values()),
            }
        }
    
    def validate_roster(self, roster: List[Dict[str, Any]]) -> List[Conflict]:
        """Validate a roster and return any conflicts found."""
        conflicts = []
        
        for emp_schedule in roster:
            emp_id = emp_schedule["employee_id"]
            emp = self.employee_map.get(emp_id)
            if not emp:
                continue
            
            shifts_data = emp_schedule.get("shifts", {})
            total_hours = 0.0
            prev_shift = None
            prev_day = None
            
            for d in self.days:
                shift_info = shifts_data.get(d, {})
                shift_code = shift_info.get("shift_code", "/")
                hours = shift_info.get("hours", 0.0)
                
                total_hours += hours
                
                # Check rest period violation
                if prev_shift and shift_code != "/":
                    prev_def = SHIFT_DEFINITIONS.get(ShiftType(prev_shift)) if prev_shift != "/" else None
                    curr_def = SHIFT_DEFINITIONS.get(ShiftType(shift_code)) if shift_code != "/" else None
                    
                    if prev_def and curr_def:
                        if prev_def["is_closing"] and curr_def["is_opening"]:
                            conflicts.append(Conflict(
                                conflict_type=ConflictType.REST_PERIOD_VIOLATION,
                                severity="critical",
                                description=f"Employee {emp.name} has less than 10 hours rest between {prev_day} closing and {d} opening",
                                affected_employees=[emp_id],
                                affected_days=[prev_day, d],
                            ))
                
                prev_shift = shift_code
                prev_day = d
            
            # Check weekly hours
            min_hours, max_hours = emp.get_hour_limits()
            week_count = len(self.days) // 7
            
            if total_hours < min_hours * week_count:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.MIN_HOURS_NOT_MET,
                    severity="medium",
                    description=f"Employee {emp.name} has {total_hours:.1f}h but needs minimum {min_hours * week_count:.1f}h",
                    affected_employees=[emp_id],
                ))
            
            if total_hours > max_hours * week_count:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.MAX_HOURS_EXCEEDED,
                    severity="high",
                    description=f"Employee {emp.name} has {total_hours:.1f}h exceeding maximum {max_hours * week_count:.1f}h",
                    affected_employees=[emp_id],
                ))
        
        # Check daily staffing
        for d in self.days:
            staff_count = sum(
                1 for emp_schedule in roster 
                if emp_schedule.get("shifts", {}).get(d, {}).get("shift_code", "/") != "/"
            )
            
            min_staff = self.store.normal_requirements.total_staff
            if staff_count < min_staff:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.UNDERSTAFFED,
                    severity="high",
                    description=f"Day {d} has {staff_count} staff but needs minimum {min_staff}",
                    affected_days=[d],
                ))
        
        return conflicts
    
    def resolve_conflict(self, conflict: Conflict, roster: List[Dict[str, Any]]) -> List[Resolution]:
        """Generate possible resolutions for a conflict."""
        resolutions = []
        
        if conflict.conflict_type == ConflictType.REST_PERIOD_VIOLATION:
            for emp_id in conflict.affected_employees:
                emp = self.employee_map.get(emp_id)
                if not emp:
                    continue
                
                # Option 1: Change day 1 to non-closing shift
                if len(conflict.affected_days) >= 2:
                    resolutions.append(Resolution(
                        conflict_id=f"{conflict.conflict_type}_{emp_id}",
                        description=f"Change {emp.name}'s shift on {conflict.affected_days[0]} to First Half (1F)",
                        impact_score=2.0,
                        changes=[{
                            "employee_id": emp_id,
                            "day": conflict.affected_days[0],
                            "new_shift": "1F",
                        }],
                    ))
                    
                    # Option 2: Change day 2 to non-opening shift
                    resolutions.append(Resolution(
                        conflict_id=f"{conflict.conflict_type}_{emp_id}",
                        description=f"Change {emp.name}'s shift on {conflict.affected_days[1]} to Second Half (2F)",
                        impact_score=2.0,
                        changes=[{
                            "employee_id": emp_id,
                            "day": conflict.affected_days[1],
                            "new_shift": "2F",
                        }],
                    ))
                    
                    # Option 3: Give day off on day 2
                    resolutions.append(Resolution(
                        conflict_id=f"{conflict.conflict_type}_{emp_id}",
                        description=f"Give {emp.name} day off on {conflict.affected_days[1]}",
                        impact_score=5.0,  # Higher impact
                        changes=[{
                            "employee_id": emp_id,
                            "day": conflict.affected_days[1],
                            "new_shift": "/",
                        }],
                    ))
        
        elif conflict.conflict_type == ConflictType.UNDERSTAFFED:
            # Find available employees not scheduled
            for d in conflict.affected_days:
                scheduled_ids = set()
                for emp_schedule in roster:
                    if emp_schedule.get("shifts", {}).get(d, {}).get("shift_code", "/") != "/":
                        scheduled_ids.add(emp_schedule["employee_id"])
                
                for emp in self.employees:
                    if emp.id not in scheduled_ids and emp.is_available(d, "S"):
                        resolutions.append(Resolution(
                            conflict_id=f"{conflict.conflict_type}_{d}",
                            description=f"Add {emp.name} to work Day Shift on {d}",
                            impact_score=1.0,
                            changes=[{
                                "employee_id": emp.id,
                                "day": d,
                                "new_shift": "S",
                            }],
                        ))
        
        # Sort by impact score (lower is better)
        resolutions.sort(key=lambda r: r.impact_score)
        
        return resolutions[:5]  # Return top 5 options
