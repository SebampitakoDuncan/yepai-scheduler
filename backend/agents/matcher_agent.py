from typing import Dict, Any, List
from .base import BaseAgent, AgentMessage, MessageType
from models.employee import Employee, Station


class MatcherAgent(BaseAgent):
    """Agent responsible for matching employees to stations based on skills."""
    
    def __init__(self):
        super().__init__(name="MatcherAgent")
    
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process skill matching requests."""
        action = message.action
        payload = message.payload
        
        if action == "match_skills":
            employees = payload.get("employees", [])
            station_requirements = payload.get("station_requirements", {})
            result = self.match_employees_to_stations(employees, station_requirements)
            return self.send_message(
                recipient=message.sender,
                action="skill_match_result",
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id,
            )
        
        if action == "validate_station_coverage":
            assignments = payload.get("assignments", [])
            requirements = payload.get("requirements", {})
            result = self.validate_station_coverage(assignments, requirements)
            return self.send_message(
                recipient=message.sender,
                action="coverage_validation_result",
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
    
    def match_employees_to_stations(
        self,
        employees: List[Dict[str, Any]],
        station_requirements: Dict[str, int],
    ) -> Dict[str, Any]:
        """Match employees to stations based on skills and requirements."""
        self.set_status("matching")
        
        # Group employees by their primary station
        station_pools = {
            "Kitchen": [],
            "Counter": [],
            "McCafe": [],
            "Dessert": [],
            "Multi-Station": [],
            "Multi-Station McCafe": [],
        }
        
        for emp in employees:
            primary = emp.get("primary_station", "Counter")
            if primary in station_pools:
                station_pools[primary].append(emp)
        
        # Calculate coverage
        station_coverage = {}
        unassignable = []
        
        for station, required in station_requirements.items():
            qualified = []
            
            # Primary station match
            if station in station_pools:
                qualified.extend(station_pools[station])
            
            # Multi-station employees can fill Kitchen and Counter
            if station in ["Kitchen", "Counter"]:
                qualified.extend(station_pools["Multi-Station"])
                qualified.extend(station_pools["Multi-Station McCafe"])
            
            # McCafe-certified multi-station
            if station == "McCafe":
                qualified.extend(station_pools["Multi-Station McCafe"])
            
            # Remove duplicates
            seen_ids = set()
            unique_qualified = []
            for emp in qualified:
                if emp.get("id") not in seen_ids:
                    seen_ids.add(emp.get("id"))
                    unique_qualified.append(emp)
            
            coverage_ratio = len(unique_qualified) / required if required > 0 else 1.0
            
            station_coverage[station] = {
                "required": required,
                "available": len(unique_qualified),
                "coverage_ratio": round(coverage_ratio, 2),
                "is_sufficient": len(unique_qualified) >= required,
                "qualified_employees": [e.get("id") for e in unique_qualified],
            }
            
            if len(unique_qualified) < required:
                unassignable.append({
                    "station": station,
                    "shortage": required - len(unique_qualified),
                })
        
        self.set_status("complete")
        
        return {
            "station_coverage": station_coverage,
            "shortages": unassignable,
            "has_shortages": len(unassignable) > 0,
            "total_employees": len(employees),
        }
    
    def validate_station_coverage(
        self,
        assignments: List[Dict[str, Any]],
        requirements: Dict[str, int],
    ) -> Dict[str, Any]:
        """Validate that station coverage meets requirements."""
        station_counts = {}
        for assignment in assignments:
            station = assignment.get("station", "Unknown")
            station_counts[station] = station_counts.get(station, 0) + 1
        
        gaps = []
        for station, required in requirements.items():
            actual = station_counts.get(station, 0)
            if actual < required:
                gaps.append({
                    "station": station,
                    "required": required,
                    "actual": actual,
                    "gap": required - actual,
                })
        
        return {
            "is_valid": len(gaps) == 0,
            "station_counts": station_counts,
            "gaps": gaps,
        }
    
    def recommend_cross_training(
        self,
        employees: List[Dict[str, Any]],
        shortages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Recommend employees for cross-training to address shortages."""
        recommendations = []
        
        for shortage in shortages:
            station = shortage.get("station")
            count_needed = shortage.get("shortage", 0)
            
            candidates = []
            for emp in employees:
                primary = emp.get("primary_station", "")
                # Multi-station employees are good candidates
                if "Multi" in primary:
                    continue
                # Look for employees in related stations
                if station == "Kitchen" and primary == "Counter":
                    candidates.append(emp)
                elif station == "Counter" and primary == "Kitchen":
                    candidates.append(emp)
                elif station == "McCafe" and "Multi" in primary:
                    candidates.append(emp)
            
            recommendations.append({
                "station": station,
                "candidates": [c.get("name") for c in candidates[:count_needed]],
                "training_needed": True,
            })
        
        return recommendations
