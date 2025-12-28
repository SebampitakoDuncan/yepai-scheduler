from enum import Enum
from typing import Dict, List
from pydantic import BaseModel


class StoreType(str, Enum):
    CBD_CORE = "CBD Core Area"
    SUBURBAN = "Suburban Residential"
    HIGHWAY = "Highway"


class PeriodType(str, Enum):
    NORMAL = "Normal"
    PEAK = "Peak"


class StaffingRequirement(BaseModel):
    kitchen_staff: int
    counter_staff: int
    mccafe_staff: int = 0
    dessert_station_staff: int = 0
    offline_dessert_station_staff: int = 0
    
    @property
    def total_staff(self) -> int:
        return (
            self.kitchen_staff + 
            self.counter_staff + 
            self.mccafe_staff + 
            self.dessert_station_staff + 
            self.offline_dessert_station_staff
        )


class Store(BaseModel):
    store_id: str
    location_type: StoreType
    
    # Staffing requirements by period
    normal_requirements: StaffingRequirement
    peak_requirements: StaffingRequirement
    
    # Operating hours
    opening_time: str = "06:30"
    closing_time: str = "23:00"
    
    # Peak periods (hours)
    lunch_peak_start: int = 11
    lunch_peak_end: int = 14
    dinner_peak_start: int = 17
    dinner_peak_end: int = 21
    
    # Manager requirements
    min_managers_on_duty: int = 1
    peak_managers_on_duty: int = 2
    
    class Config:
        use_enum_values = True
    
    def get_requirements(self, is_peak: bool = False) -> StaffingRequirement:
        """Get staffing requirements for normal or peak periods."""
        return self.peak_requirements if is_peak else self.normal_requirements
    
    def is_peak_hour(self, hour: int) -> bool:
        """Check if a given hour is during peak period."""
        return (
            (self.lunch_peak_start <= hour < self.lunch_peak_end) or
            (self.dinner_peak_start <= hour < self.dinner_peak_end)
        )
    
    def has_mccafe(self) -> bool:
        """Check if store has McCafe station."""
        return self.normal_requirements.mccafe_staff > 0
    
    def has_dessert_station(self) -> bool:
        """Check if store has dessert station."""
        return self.normal_requirements.dessert_station_staff > 0
