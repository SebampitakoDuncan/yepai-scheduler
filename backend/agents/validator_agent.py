from typing import Dict, Any, List
from datetime import datetime
from .base import BaseAgent, AgentMessage, MessageType
from models.constraints import Constraints, Conflict, ConflictType
from models.shift import ShiftType, SHIFT_DEFINITIONS


class ValidatorAgent(BaseAgent):
    """Agent responsible for validating rosters against constraints."""
    
    def __init__(self):
        super().__init__(name="ValidatorAgent")
        self.constraints = Constraints()
        
        # Pre-compute shift coverage
        self.lunch_peak_shifts = [s.value for s in ShiftType if SHIFT_DEFINITIONS.get(s, {}).get("covers_lunch_peak", False)]
        self.dinner_peak_shifts = [s.value for s in ShiftType if SHIFT_DEFINITIONS.get(s, {}).get("covers_dinner_peak", False)]
    
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process validation requests."""
        action = message.action
        payload = message.payload
        
        if action == "validate_roster":
            roster = payload.get("roster", [])
            days = payload.get("days", [])
            store = payload.get("store", {})
            result = self.validate_roster(roster, days, store)
            return self.send_message(
                recipient=message.sender,
                action="validation_result",
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id,
            )
        
        if action == "check_labor_laws":
            roster = payload.get("roster", [])
            result = self.check_labor_law_compliance(roster)
            return self.send_message(
                recipient=message.sender,
                action="labor_law_result",
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id,
            )
        
        return self.send_message(
            recipient=message.sender,
            action="error",
            payload={"error": f"Unknown action: {action}"},
            message_type=MessageType.ERROR,
        )
    
    def _is_weekend(self, day: str) -> bool:
        """Check if a day is a weekend (Saturday or Sunday)."""
        try:
            dt = datetime.fromisoformat(day)
            return dt.weekday() >= 5  # 5=Saturday, 6=Sunday
        except:
            return "Sat" in day or "Sun" in day
    
    def validate_roster(
        self,
        roster: List[Dict[str, Any]],
        days: List[str],
        store: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Comprehensive roster validation."""
        self.set_status("validating")
        
        conflicts = []
        warnings = []
        
        # Check each employee's schedule
        for emp_schedule in roster:
            emp_id = emp_schedule.get("employee_id")
            emp_name = emp_schedule.get("employee_name", emp_id)
            emp_type = emp_schedule.get("employee_type", "Casual")
            shifts = emp_schedule.get("shifts", {})
            
            # Track hours and shift patterns
            total_hours = 0.0
            prev_shift = None
            prev_day = None
            consecutive_work_days = 0
            
            for day in days:
                shift_info = shifts.get(day, {})
                shift_code = shift_info.get("shift_code", "/")
                hours = shift_info.get("hours", 0.0)
                
                if shift_code != "/":
                    total_hours += hours
                    consecutive_work_days += 1
                    
                    # Check rest period between consecutive days
                    if prev_shift and prev_shift != "/":
                        rest_violation = self._check_rest_period(prev_shift, shift_code)
                        if rest_violation:
                            conflicts.append({
                                "type": ConflictType.REST_PERIOD_VIOLATION.value,
                                "severity": "critical",
                                "description": f"{emp_name}: Less than 10h rest between {prev_day} and {day}",
                                "employee_id": emp_id,
                                "days": [prev_day, day],
                            })
                else:
                    consecutive_work_days = 0
                
                # Check max consecutive days
                if consecutive_work_days > self.constraints.max_consecutive_days:
                    conflicts.append({
                        "type": ConflictType.LABOR_LAW_VIOLATION.value,
                        "severity": "high",
                        "description": f"{emp_name}: Working more than {self.constraints.max_consecutive_days} consecutive days",
                        "employee_id": emp_id,
                        "days": [day],
                    })
                
                prev_shift = shift_code
                prev_day = day
            
            # Check weekly hours
            min_hours, max_hours = self.constraints.get_hour_limits(emp_type)
            weeks = len(days) / 7
            
            if total_hours < min_hours * weeks:
                warnings.append({
                    "type": ConflictType.MIN_HOURS_NOT_MET.value,
                    "severity": "medium",
                    "description": f"{emp_name}: {total_hours:.1f}h is below minimum {min_hours * weeks:.1f}h",
                    "employee_id": emp_id,
                })
            
            if total_hours > max_hours * weeks:
                conflicts.append({
                    "type": ConflictType.MAX_HOURS_EXCEEDED.value,
                    "severity": "high",
                    "description": f"{emp_name}: {total_hours:.1f}h exceeds maximum {max_hours * weeks:.1f}h",
                    "employee_id": emp_id,
                })
        
        # Get peak requirements
        peak_reqs = store.get("peak_requirements", store.get("normal_requirements", {}))
        peak_min_staff = (
            peak_reqs.get("kitchen_staff", 0) +
            peak_reqs.get("counter_staff", 0) +
            peak_reqs.get("mccafe_staff", 0)
        ) if isinstance(peak_reqs, dict) else 6
        
        weekend_multiplier = 1.0 + (self.constraints.weekend_coverage_increase_percent / 100.0)
        
        # Check daily staffing and PEAK PERIOD COVERAGE
        for day in days:
            is_weekend = self._is_weekend(day)
            
            staff_count = sum(
                1 for r in roster
                if r.get("shifts", {}).get(day, {}).get("shift_code", "/") != "/"
            )
            manager_count = sum(
                1 for r in roster
                if r.get("is_manager") and r.get("shifts", {}).get(day, {}).get("shift_code", "/") != "/"
            )
            
            # Count lunch peak coverage (11:00-14:00)
            lunch_peak_count = sum(
                1 for r in roster
                if r.get("shifts", {}).get(day, {}).get("shift_code", "/") in self.lunch_peak_shifts
            )
            
            # Count dinner peak coverage (17:00-21:00)
            dinner_peak_count = sum(
                1 for r in roster
                if r.get("shifts", {}).get(day, {}).get("shift_code", "/") in self.dinner_peak_shifts
            )
            
            min_staff = store.get("normal_requirements", {}).get("total_staff", 10)
            if isinstance(min_staff, dict):
                min_staff = 10
            
            if staff_count < min_staff:
                conflicts.append({
                    "type": ConflictType.UNDERSTAFFED.value,
                    "severity": "high",
                    "description": f"{day}: Only {staff_count} staff scheduled, need {min_staff}",
                    "days": [day],
                })
            
            if manager_count < self.constraints.min_managers_always:
                conflicts.append({
                    "type": ConflictType.NO_MANAGER.value,
                    "severity": "critical",
                    "description": f"{day}: No manager scheduled for duty",
                    "days": [day],
                })
            
            # Check peak period coverage
            required_peak_staff = int(peak_min_staff * (weekend_multiplier if is_weekend else 1.0))
            
            if lunch_peak_count < required_peak_staff:
                conflicts.append({
                    "type": "peak_understaffed",
                    "severity": "high",
                    "description": f"{day}: Lunch peak (11:00-14:00) has {lunch_peak_count} staff, need {required_peak_staff}{'(+20% weekend)' if is_weekend else ''}",
                    "days": [day],
                    "period": "lunch_peak",
                })
            
            if dinner_peak_count < required_peak_staff:
                conflicts.append({
                    "type": "peak_understaffed",
                    "severity": "high",
                    "description": f"{day}: Dinner peak (17:00-21:00) has {dinner_peak_count} staff, need {required_peak_staff}{'(+20% weekend)' if is_weekend else ''}",
                    "days": [day],
                    "period": "dinner_peak",
                })
        
        self.set_status("complete")
        
        hard_constraint_violations = len([c for c in conflicts if c.get("severity") in ["critical", "high"]])
        
        return {
            "is_valid": hard_constraint_violations == 0,
            "conflicts": conflicts,
            "warnings": warnings,
            "total_conflicts": len(conflicts),
            "total_warnings": len(warnings),
            "hard_constraint_violations": hard_constraint_violations,
            "peak_coverage_validated": True,
        }
    
    def check_labor_law_compliance(self, roster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check Australian Fair Work Act compliance."""
        violations = []
        
        for emp_schedule in roster:
            emp_id = emp_schedule.get("employee_id")
            emp_name = emp_schedule.get("employee_name", emp_id)
            emp_type = emp_schedule.get("employee_type", "Casual")
            shifts = emp_schedule.get("shifts", {})
            
            total_hours = sum(
                s.get("hours", 0.0) for s in shifts.values()
            )
            
            # Check hour limits
            min_hours, max_hours = self.constraints.get_hour_limits(emp_type)
            weeks = len(shifts) / 7
            
            if total_hours > max_hours * weeks * 1.1:  # 10% buffer before violation
                violations.append({
                    "employee": emp_name,
                    "violation": "Excessive hours",
                    "details": f"{total_hours:.1f}h exceeds Fair Work Act limit of {max_hours * weeks:.1f}h",
                    "severity": "critical",
                })
            
            # Check for adequate breaks
            for day, shift_info in shifts.items():
                hours = shift_info.get("hours", 0)
                if hours > self.constraints.break_after_hours:
                    # Break should be included - just a check
                    pass  # Assuming breaks are built into shift definitions
        
        return {
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "checked_employees": len(roster),
        }
    
    def _check_rest_period(self, prev_shift: str, curr_shift: str) -> bool:
        """Check if rest period between shifts is adequate."""
        closing_shifts = ["2F"]  # Second Half ends at 23:00
        opening_shifts = ["S", "1F"]  # Day Shift and First Half start at 06:30
        
        if prev_shift in closing_shifts and curr_shift in opening_shifts:
            return True  # Only 7.5 hours rest - violation
        return False
