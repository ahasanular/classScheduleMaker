# plain dataclasses or Pydantic models to hold input data cleanly.
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

from university.models import Course, Department, ConstrainType


@dataclass
class TimeSlot:
    id: int
    day: str
    slot_number: int
    start_time: datetime
    end_time: datetime

    score: Optional[float] = 0.0


@dataclass
class Room:
    id: int
    name: str
    department: Department
    is_lab: bool


@dataclass
class Course:
    id: int
    code: str
    name: str
    department: Department
    semester: int
    credit: float
    sessions_per_week: int
    duration_per_session: int
    preferred_teachers: List["Teacher"]
    is_lab: bool

    # Tracking
    score: Optional[float] = 0.0


@dataclass
class Teacher:
    id: int
    name: str
    initial: str
    department: Department
    max_classes_per_week: int
    preferred_courses: List[Course]
    preferred_time_slots: List[TimeSlot]  # Format: "Day-slot_number"
    minimum_classes_per_day: int

    # Tracker
    score: Optional[float] = 0.0
    load: Optional[int] = 0


@dataclass
class Assignment:
    course: Course
    teacher: Teacher
    slot_group: List[TimeSlot]
    room: Room

    score: Optional[float] = 0.0

@dataclass
class Constrains:
    id: int
    type: str
    condition: str
    severity: str
    score_weight: float


