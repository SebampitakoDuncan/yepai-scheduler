from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ConflictType(str, Enum):
    # Hard constraint violations (must fix)
    LABOR_LAW_VIOLATION = "labor_law_violation"
    REST_PERIOD_VIOLATION = "rest_period_violation"
    MAX_HOURS_EXCEEDED = "max_hours_exceeded"
    MIN_HOURS_NOT_MET = "min_hours_not_met"
    SKILL_MISMATCH = "skill_mismatch"
    UNDERSTAFFED = "understaffed"
    NO_MANAGER = "no_manager"
    AVAILABILITY_CONFLICT = "availability_conflict"
    DOUBLE_BOOKING = "double_booking"
    
    # Soft constraint violations (should optimize)
    PREFERENCE_NOT_MET = "preference_not_met"
    UNEVEN_DISTRIBUTION = "uneven_distribution"
    CONSECUTIVE_DAYS = "consecutive_days"
    OVERSTAFFED = "overstaffed"


class Conflict(BaseModel):
    conflict_type: ConflictType
    severity: str  # "critical", "high", "medium", "low"
    description: str
    affected_employees: List[str] = []
    affected_days: List[str] = []
    affected_stations: List[str] = []
    
    class Config:
        use_enum_values = True


class Resolution(BaseModel):
    conflict_id: str
    description: str
    impact_score: float  # Lower is better
    changes: List[Dict[str, Any]]  # List of changes to apply
    
    class Config:
        use_enum_values = True


class Constraints(BaseModel):
    """Australian Fair Work Act and McDonald's operational constraints."""
    
    # Rest period constraints
    min_rest_between_shifts_hours: float = 10.0
    
    # Weekly hour constraints by employee type
    full_time_min_hours: float = 35.0
    full_time_max_hours: float = 38.0
    part_time_min_hours: float = 20.0
    part_time_max_hours: float = 32.0
    casual_min_hours: float = 8.0
    casual_max_hours: float = 24.0
    
    # Daily constraints
    max_hours_per_day: float = 12.0
    min_hours_per_shift: float = 3.0
    
    # Break requirements
    break_after_hours: float = 5.0
    break_duration_minutes: int = 30
    
    # Manager constraints
    min_managers_always: int = 1
    min_managers_opening: int = 1
    min_managers_closing: int = 1
    min_managers_peak: int = 2
    
    # Weekend constraints
    weekend_coverage_increase_percent: float = 20.0
    
    # Consecutive days constraints
    max_consecutive_days: int = 6
    preferred_consecutive_days_off: int = 2
    
    def get_hour_limits(self, employee_type: str) -> tuple[float, float]:
        """Get min/max weekly hours for an employee type."""
        if employee_type == "Full-Time":
            return (self.full_time_min_hours, self.full_time_max_hours)
        elif employee_type == "Part-Time":
            return (self.part_time_min_hours, self.part_time_max_hours)
        else:  # Casual
            return (self.casual_min_hours, self.casual_max_hours)
