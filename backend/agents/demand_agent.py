from typing import Dict, Any, List
from .base import BaseAgent, AgentMessage, MessageType
from models.store import Store


class DemandAgent(BaseAgent):
    """Agent responsible for analyzing staffing demand patterns."""
    
    def __init__(self):
        super().__init__(name="DemandAgent")
    
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process demand analysis requests."""
        action = message.action
        payload = message.payload
        
        if action == "analyze_demand":
            store = payload.get("store")
            days = payload.get("days", [])
            result = self.analyze_demand(store, days)
            return self.send_message(
                recipient=message.sender,
                action="demand_analysis_result",
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
    
    def analyze_demand(self, store: Dict[str, Any], days: List[str]) -> Dict[str, Any]:
        """Analyze staffing demand for each day and period."""
        self.set_status("analyzing")
        
        demand_by_day = {}
        
        for day in days:
            # Determine if it's a weekend
            is_weekend = self._is_weekend(day)
            
            # Calculate base requirements
            normal_staff = store.get("normal_requirements", {})
            peak_staff = store.get("peak_requirements", {})
            
            # Weekend adjustment (+20%)
            weekend_multiplier = 1.2 if is_weekend else 1.0
            
            demand_by_day[day] = {
                "is_weekend": is_weekend,
                "periods": {
                    "opening": {
                        "start": "06:30",
                        "end": "08:00",
                        "min_staff": max(2, int(self._get_total_staff(normal_staff) * 0.4)),
                        "priority": "high",
                    },
                    "morning": {
                        "start": "08:00",
                        "end": "11:00",
                        "min_staff": int(self._get_total_staff(normal_staff) * weekend_multiplier),
                        "priority": "medium",
                    },
                    "lunch_peak": {
                        "start": "11:00",
                        "end": "14:00",
                        "min_staff": int(self._get_total_staff(peak_staff) * weekend_multiplier),
                        "priority": "critical",
                    },
                    "afternoon": {
                        "start": "14:00",
                        "end": "17:00",
                        "min_staff": int(self._get_total_staff(normal_staff) * weekend_multiplier),
                        "priority": "medium",
                    },
                    "dinner_peak": {
                        "start": "17:00",
                        "end": "21:00",
                        "min_staff": int(self._get_total_staff(peak_staff) * weekend_multiplier),
                        "priority": "critical",
                    },
                    "closing": {
                        "start": "21:00",
                        "end": "23:00",
                        "min_staff": max(2, int(self._get_total_staff(normal_staff) * 0.4)),
                        "priority": "high",
                    },
                },
                "station_requirements": {
                    "kitchen": {
                        "normal": normal_staff.get("kitchen_staff", 0),
                        "peak": peak_staff.get("kitchen_staff", 0),
                    },
                    "counter": {
                        "normal": normal_staff.get("counter_staff", 0),
                        "peak": peak_staff.get("counter_staff", 0),
                    },
                    "mccafe": {
                        "normal": normal_staff.get("mccafe_staff", 0),
                        "peak": peak_staff.get("mccafe_staff", 0),
                    },
                },
            }
        
        self.set_status("complete")
        
        return {
            "demand_by_day": demand_by_day,
            "total_days": len(days),
            "weekend_days": sum(1 for d in days if self._is_weekend(d)),
        }
    
    def _is_weekend(self, day: str) -> bool:
        """Check if a day string represents a weekend."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(day)
            return dt.weekday() >= 5
        except:
            # Check if day name contains weekend indicator
            return "Sat" in day or "Sun" in day
    
    def _get_total_staff(self, requirements: Dict[str, Any]) -> int:
        """Calculate total staff from requirements dict."""
        return (
            requirements.get("kitchen_staff", 0) +
            requirements.get("counter_staff", 0) +
            requirements.get("mccafe_staff", 0) +
            requirements.get("dessert_station_staff", 0) +
            requirements.get("offline_dessert_station_staff", 0)
        )
