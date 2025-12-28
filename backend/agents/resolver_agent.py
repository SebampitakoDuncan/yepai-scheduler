from typing import Dict, Any, List
from .base import BaseAgent, AgentMessage, MessageType
from models.constraints import ConflictType


class ResolverAgent(BaseAgent):
    """Agent responsible for resolving scheduling conflicts."""
    
    def __init__(self):
        super().__init__(name="ResolverAgent")
    
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process conflict resolution requests."""
        action = message.action
        payload = message.payload
        
        if action == "resolve_conflicts":
            conflicts = payload.get("conflicts", [])
            roster = payload.get("roster", [])
            employees = payload.get("employees", [])
            result = self.resolve_all_conflicts(conflicts, roster, employees)
            return self.send_message(
                recipient=message.sender,
                action="resolution_result",
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id,
            )
        
        if action == "suggest_resolutions":
            conflict = payload.get("conflict", {})
            roster = payload.get("roster", [])
            employees = payload.get("employees", [])
            result = self.suggest_resolutions(conflict, roster, employees)
            return self.send_message(
                recipient=message.sender,
                action="suggestions_result",
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
    
    def resolve_all_conflicts(
        self,
        conflicts: List[Dict[str, Any]],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Attempt to resolve all conflicts in priority order."""
        self.set_status("resolving")
        
        # Sort conflicts by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_conflicts = sorted(
            conflicts,
            key=lambda c: severity_order.get(c.get("severity", "low"), 4)
        )
        
        resolutions_applied = []
        unresolved = []
        modified_roster = [dict(r) for r in roster]  # Deep copy
        
        for conflict in sorted_conflicts:
            suggestions = self.suggest_resolutions(conflict, modified_roster, employees)
            
            if suggestions.get("options"):
                # Apply the best (first) resolution
                best_option = suggestions["options"][0]
                
                # Apply changes to roster
                success = self._apply_resolution(modified_roster, best_option)
                
                if success:
                    resolutions_applied.append({
                        "conflict": conflict,
                        "resolution": best_option,
                        "applied": True,
                    })
                else:
                    unresolved.append(conflict)
            else:
                unresolved.append(conflict)
        
        self.set_status("complete")
        
        return {
            "resolutions_applied": len(resolutions_applied),
            "unresolved_count": len(unresolved),
            "resolutions": resolutions_applied,
            "unresolved_conflicts": unresolved,
            "modified_roster": modified_roster,
        }
    
    def suggest_resolutions(
        self,
        conflict: Dict[str, Any],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate ranked resolution options for a conflict."""
        conflict_type = conflict.get("type", "")
        options = []
        
        if conflict_type == ConflictType.REST_PERIOD_VIOLATION.value:
            options = self._resolve_rest_period_violation(conflict, roster, employees)
        
        elif conflict_type == ConflictType.MAX_HOURS_EXCEEDED.value:
            options = self._resolve_max_hours_exceeded(conflict, roster, employees)
        
        elif conflict_type == ConflictType.MIN_HOURS_NOT_MET.value:
            options = self._resolve_min_hours_not_met(conflict, roster, employees)
        
        elif conflict_type == ConflictType.UNDERSTAFFED.value:
            options = self._resolve_understaffed(conflict, roster, employees)
        
        elif conflict_type == ConflictType.NO_MANAGER.value:
            options = self._resolve_no_manager(conflict, roster, employees)
        
        elif conflict_type == ConflictType.SKILL_MISMATCH.value:
            options = self._resolve_skill_mismatch(conflict, roster, employees)
        
        else:
            options = [{
                "description": f"Manual review required for {conflict_type}",
                "impact_score": 10.0,
                "changes": [],
            }]
        
        # Sort by impact score
        options.sort(key=lambda o: o.get("impact_score", 10))
        
        return {
            "conflict": conflict,
            "options": options[:5],  # Top 5 options
        }
    
    def _resolve_rest_period_violation(
        self,
        conflict: Dict[str, Any],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate options to resolve rest period violations."""
        options = []
        emp_id = conflict.get("employee_id")
        days = conflict.get("days", [])
        
        if len(days) >= 2:
            # Option 1: Change first day to non-closing shift
            options.append({
                "description": f"Change shift on {days[0]} to First Half (ends earlier)",
                "impact_score": 2.0,
                "changes": [{
                    "employee_id": emp_id,
                    "day": days[0],
                    "field": "shift_code",
                    "new_value": "1F",
                }],
            })
            
            # Option 2: Change second day to later start
            options.append({
                "description": f"Change shift on {days[1]} to Second Half (starts later)",
                "impact_score": 2.0,
                "changes": [{
                    "employee_id": emp_id,
                    "day": days[1],
                    "field": "shift_code",
                    "new_value": "2F",
                }],
            })
            
            # Option 3: Day off on second day
            options.append({
                "description": f"Give day off on {days[1]}",
                "impact_score": 4.0,
                "changes": [{
                    "employee_id": emp_id,
                    "day": days[1],
                    "field": "shift_code",
                    "new_value": "/",
                }],
            })
        
        return options
    
    def _resolve_max_hours_exceeded(
        self,
        conflict: Dict[str, Any],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate options to reduce hours."""
        options = []
        emp_id = conflict.get("employee_id")
        
        # Find employee's schedule
        emp_schedule = next((r for r in roster if r.get("employee_id") == emp_id), None)
        if not emp_schedule:
            return options
        
        shifts = emp_schedule.get("shifts", {})
        
        # Find shifts to potentially remove (prefer longer shifts)
        shift_hours = []
        for day, shift_info in shifts.items():
            hours = shift_info.get("hours", 0)
            if hours > 0:
                shift_hours.append((day, hours, shift_info.get("shift_code")))
        
        shift_hours.sort(key=lambda x: x[1], reverse=True)
        
        for day, hours, shift_code in shift_hours[:3]:
            options.append({
                "description": f"Remove shift on {day} ({hours}h)",
                "impact_score": hours / 2,  # Impact based on hours lost
                "changes": [{
                    "employee_id": emp_id,
                    "day": day,
                    "field": "shift_code",
                    "new_value": "/",
                }],
            })
            
            # Option to reduce to shorter shift
            if shift_code in ["3F"]:  # Full day
                options.append({
                    "description": f"Reduce {day} to half shift (1F)",
                    "impact_score": hours / 4,
                    "changes": [{
                        "employee_id": emp_id,
                        "day": day,
                        "field": "shift_code",
                        "new_value": "1F",
                    }],
                })
        
        return options
    
    def _resolve_min_hours_not_met(
        self,
        conflict: Dict[str, Any],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate options to add hours."""
        options = []
        emp_id = conflict.get("employee_id")
        
        emp_schedule = next((r for r in roster if r.get("employee_id") == emp_id), None)
        if not emp_schedule:
            return options
        
        shifts = emp_schedule.get("shifts", {})
        
        # Find days off to potentially fill
        for day, shift_info in shifts.items():
            if shift_info.get("shift_code") == "/":
                options.append({
                    "description": f"Add Day Shift on {day} (+8.5h)",
                    "impact_score": 1.0,
                    "changes": [{
                        "employee_id": emp_id,
                        "day": day,
                        "field": "shift_code",
                        "new_value": "S",
                    }],
                })
        
        return options
    
    def _resolve_understaffed(
        self,
        conflict: Dict[str, Any],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate options to add staff."""
        options = []
        days = conflict.get("days", [])
        
        # Find employees with days off on the affected day
        for day in days:
            for emp in employees:
                emp_id = emp.get("id")
                emp_name = emp.get("name")
                
                # Check if employee has day off
                emp_schedule = next((r for r in roster if r.get("employee_id") == emp_id), None)
                if emp_schedule:
                    if emp_schedule.get("shifts", {}).get(day, {}).get("shift_code") == "/":
                        # Check if employee is available
                        availability = emp.get("availability", {})
                        if day in availability or not availability:
                            options.append({
                                "description": f"Add {emp_name} to work on {day}",
                                "impact_score": 1.5,
                                "changes": [{
                                    "employee_id": emp_id,
                                    "day": day,
                                    "field": "shift_code",
                                    "new_value": "S",
                                }],
                            })
        
        return options
    
    def _resolve_no_manager(
        self,
        conflict: Dict[str, Any],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate options to add manager coverage."""
        options = []
        days = conflict.get("days", [])
        
        # Find managers
        managers = [e for e in employees if e.get("is_manager")]
        
        for day in days:
            for mgr in managers:
                mgr_id = mgr.get("id")
                mgr_name = mgr.get("name")
                
                mgr_schedule = next((r for r in roster if r.get("employee_id") == mgr_id), None)
                if mgr_schedule:
                    if mgr_schedule.get("shifts", {}).get(day, {}).get("shift_code") == "/":
                        options.append({
                            "description": f"Add Manager {mgr_name} to work on {day}",
                            "impact_score": 1.0,
                            "changes": [{
                                "employee_id": mgr_id,
                                "day": day,
                                "field": "shift_code",
                                "new_value": "S",
                            }],
                        })
        
        return options
    
    def _resolve_skill_mismatch(
        self,
        conflict: Dict[str, Any],
        roster: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate options to resolve skill mismatches."""
        options = []
        
        station = conflict.get("station")
        day = conflict.get("day")
        
        # Find employees qualified for the station
        for emp in employees:
            primary = emp.get("primary_station", "")
            if primary == station or station in emp.get("certified_stations", []):
                emp_id = emp.get("id")
                emp_name = emp.get("name")
                
                emp_schedule = next((r for r in roster if r.get("employee_id") == emp_id), None)
                if emp_schedule:
                    current_shift = emp_schedule.get("shifts", {}).get(day, {})
                    if current_shift.get("station") != station:
                        options.append({
                            "description": f"Reassign {emp_name} to {station} on {day}",
                            "impact_score": 2.0,
                            "changes": [{
                                "employee_id": emp_id,
                                "day": day,
                                "field": "station",
                                "new_value": station,
                            }],
                        })
        
        return options
    
    def _apply_resolution(
        self,
        roster: List[Dict[str, Any]],
        resolution: Dict[str, Any],
    ) -> bool:
        """Apply a resolution to the roster."""
        changes = resolution.get("changes", [])
        
        for change in changes:
            emp_id = change.get("employee_id")
            day = change.get("day")
            field = change.get("field")
            new_value = change.get("new_value")
            
            for emp_schedule in roster:
                if emp_schedule.get("employee_id") == emp_id:
                    if "shifts" in emp_schedule and day in emp_schedule["shifts"]:
                        emp_schedule["shifts"][day][field] = new_value
                        return True
        
        return False
