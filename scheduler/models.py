# plain dataclasses or Pydantic models to hold input data cleanly.
from datetime import time
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any


class OrmBaseModel(BaseModel):
    # model_config = {
    #     "from_attributes": True
    # }
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    def __hash__(self) -> int:
        return self.id.__hash__()


class Department(OrmBaseModel):
    id: int
    name: str


class Shift(OrmBaseModel):
    id: int
    name: str


class Section(OrmBaseModel):
    id: int
    name: str
    department: Department
    shift: Shift
    semester: int


class TimeSlot(OrmBaseModel):
    id: int
    day: str
    slot_number: int
    start_time: time
    end_time: time

    shift: Shift

    score: Optional[float] = 0.0


class Room(OrmBaseModel):
    id: int
    name: str
    department: Department
    is_lab: bool


class Course(OrmBaseModel):
    id: int
    code: str
    name: str
    department: Department
    semester: int
    credit: float
    sessions_per_week: int
    duration_per_session: int
    preferred_teachers: List[int]
    is_lab: bool

    shifts: List[Shift]

    # Tracking
    score: Optional[float] = 0.0



class Teacher(OrmBaseModel):
    id: int
    name: str
    initial: str
    department: Department
    max_classes_per_week: int
    preferred_time_slots: List[TimeSlot]  # Format: "Day-slot_number"
    preferred_courses: List[int]
    minimum_classes_per_day: int

    # Tracker
    score: Optional[float] = 0.0
    load: Optional[int] = 0


class Assignment(OrmBaseModel):
    course: Course
    teacher: Teacher
    slot_group: List[TimeSlot]
    room: Room

    section: Optional[Section] = None
    shift: Optional[Shift] = None

    score: Optional[float] = 0.0


class Constrains(OrmBaseModel):
    id: int
    type: str
    condition: str
    severity: str
    score_weight: float
    key: str


