from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import date


class EmployeeType(str, Enum):
    FULL_TIME = "Full-Time"
    PART_TIME = "Part-Time"
    CASUAL = "Casual"


class Station(str, Enum):
    KITCHEN = "Kitchen"
    COUNTER = "Counter"
    MCCAFE = "McCafe"
    DESSERT = "Dessert"
    MULTI_STATION = "Multi-Station"
    MULTI_STATION_MCCAFE = "Multi-Station McCafe"


class Employee(BaseModel):
    id: str
    name: str
    employee_type: EmployeeType
    primary_station: Station
    certified_stations: List[Station] = []
    is_manager: bool = False
    
    # Availability: day -> list of available shift codes
    availability: Dict[str, List[str]] = {}
    
    # Working hour limits based on employee type
    min_hours_per_week: float = 0
    max_hours_per_week: float = 38
    
    # Fixed hours (for employees with guaranteed hours)
    fixed_hours: Optional[float] = None
    
    class Config:
        use_enum_values = True
    
    def get_hour_limits(self) -> tuple[float, float]:
        """Get min/max weekly hours based on employee type."""
        if self.employee_type == EmployeeType.FULL_TIME:
            return (35.0, 38.0)
        elif self.employee_type == EmployeeType.PART_TIME:
            return (20.0, 32.0)
        else:  # Casual
            return (8.0, 24.0)
    
    def can_work_station(self, station: Station) -> bool:
        """Check if employee is qualified for a station."""
        if self.primary_station == station:
            return True
        if station in self.certified_stations:
            return True
        # Multi-station employees can work multiple areas
        if self.primary_station in [Station.MULTI_STATION, Station.MULTI_STATION_MCCAFE]:
            if station in [Station.KITCHEN, Station.COUNTER]:
                return True
            if self.primary_station == Station.MULTI_STATION_MCCAFE and station == Station.MCCAFE:
                return True
        return False
    
    def is_available(self, day: str, shift_code: str) -> bool:
        """Check if employee is available for a specific day and shift."""
        if day not in self.availability:
            return False
        available_shifts = self.availability.get(day, [])
        if shift_code == "/":  # Day off
            return False
        return shift_code in available_shifts or len(available_shifts) > 0
