from enum import Enum
from typing import Optional
from pydantic import BaseModel
from datetime import time


class ShiftType(str, Enum):
    DAY_SHIFT = "S"           # 06:30 - 15:00 (8.5 hours)
    FIRST_HALF = "1F"         # 06:30 - 15:30 (9 hours)
    SECOND_HALF = "2F"        # 14:00 - 23:00 (9 hours)
    FULL_DAY = "3F"           # 08:00 - 20:00 (12 hours)
    SHIFT_CHANGE = "SC"       # 11:00 - 20:00 (9 hours)
    MEETING = "M"             # Varies (8 hours)
    DAY_OFF = "/"             # Rest day (0 hours)


SHIFT_DEFINITIONS = {
    ShiftType.DAY_SHIFT: {
        "name": "Day Shift",
        "start": time(6, 30),
        "end": time(15, 0),
        "hours": 8.5,
        "is_opening": True,
        "is_closing": False,
        "covers_lunch_peak": True,      # 11:00-14:00 ✓
        "covers_dinner_peak": False,    # 17:00-21:00 ✗
    },
    ShiftType.FIRST_HALF: {
        "name": "First Half",
        "start": time(6, 30),
        "end": time(15, 30),
        "hours": 9.0,
        "is_opening": True,
        "is_closing": False,
        "covers_lunch_peak": True,      # 11:00-14:00 ✓
        "covers_dinner_peak": False,    # 17:00-21:00 ✗
    },
    ShiftType.SECOND_HALF: {
        "name": "Second Half",
        "start": time(14, 0),
        "end": time(23, 0),
        "hours": 9.0,
        "is_opening": False,
        "is_closing": True,
        "covers_lunch_peak": False,     # Starts at 14:00, misses most
        "covers_dinner_peak": True,     # 17:00-21:00 ✓
    },
    ShiftType.FULL_DAY: {
        "name": "Full Day",
        "start": time(8, 0),
        "end": time(20, 0),
        "hours": 12.0,
        "is_opening": False,
        "is_closing": False,
        "covers_lunch_peak": True,      # 11:00-14:00 ✓
        "covers_dinner_peak": True,     # Covers 17:00-20:00 (most of peak)
    },
    ShiftType.SHIFT_CHANGE: {
        "name": "Shift Change",
        "start": time(11, 0),
        "end": time(20, 0),
        "hours": 9.0,
        "is_opening": False,
        "is_closing": False,
        "covers_lunch_peak": True,      # 11:00-14:00 ✓
        "covers_dinner_peak": True,     # Covers 17:00-20:00 (most of peak)
    },
    ShiftType.MEETING: {
        "name": "Meeting",
        "start": time(9, 0),
        "end": time(17, 0),
        "hours": 8.0,
        "is_opening": False,
        "is_closing": False,
        "covers_lunch_peak": True,      # 11:00-14:00 ✓
        "covers_dinner_peak": False,    # 17:00-21:00 ✗
    },
    ShiftType.DAY_OFF: {
        "name": "Day Off",
        "start": None,
        "end": None,
        "hours": 0.0,
        "is_opening": False,
        "is_closing": False,
        "covers_lunch_peak": False,
        "covers_dinner_peak": False,
    },
}


class Shift(BaseModel):
    shift_type: ShiftType
    
    @property
    def name(self) -> str:
        return SHIFT_DEFINITIONS[self.shift_type]["name"]
    
    @property
    def start_time(self) -> Optional[time]:
        return SHIFT_DEFINITIONS[self.shift_type]["start"]
    
    @property
    def end_time(self) -> Optional[time]:
        return SHIFT_DEFINITIONS[self.shift_type]["end"]
    
    @property
    def hours(self) -> float:
        return SHIFT_DEFINITIONS[self.shift_type]["hours"]
    
    @property
    def is_opening(self) -> bool:
        return SHIFT_DEFINITIONS[self.shift_type]["is_opening"]
    
    @property
    def is_closing(self) -> bool:
        return SHIFT_DEFINITIONS[self.shift_type]["is_closing"]
    
    def covers_period(self, start: time, end: time) -> bool:
        """Check if this shift covers a specific time period."""
        if self.start_time is None or self.end_time is None:
            return False
        return self.start_time <= start and self.end_time >= end
    
    def covers_lunch_peak(self) -> bool:
        """Check if shift covers lunch peak (11:00-14:00)."""
        return self.covers_period(time(11, 0), time(14, 0))
    
    def covers_dinner_peak(self) -> bool:
        """Check if shift covers dinner peak (17:00-21:00)."""
        return self.covers_period(time(17, 0), time(21, 0))
    
    @staticmethod
    def get_hours_for_code(code: str) -> float:
        """Get hours for a shift code."""
        try:
            shift_type = ShiftType(code)
            return SHIFT_DEFINITIONS[shift_type]["hours"]
        except ValueError:
            return 0.0


class ShiftAssignment(BaseModel):
    employee_id: str
    day: str  # e.g., "2024-12-09"
    shift_type: ShiftType
    station: str
    
    class Config:
        use_enum_values = True
