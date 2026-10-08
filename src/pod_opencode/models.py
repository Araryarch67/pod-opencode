from typing import Optional, List
from pydantic import BaseModel


class Predecessor(BaseModel):
    task_unique_id: int
    relation_type: str
    lag: str


class TaskInfo(BaseModel):
    unique_id: int
    id: int
    name: str
    wbs: Optional[str] = None
    outline_level: int
    parent_id: Optional[int] = None
    is_summary: bool
    milestone: bool
    start: Optional[str] = None
    finish: Optional[str] = None
    duration: Optional[str] = None
    percent_complete: Optional[float] = None
    actual_start: Optional[str] = None
    actual_finish: Optional[str] = None
    notes: Optional[str] = None
    predecessors: List[Predecessor] = []
    resource_names: List[str] = []


class TaskListResponse(BaseModel):
    tasks: List[TaskInfo]
    count: int


class ResourceInfo(BaseModel):
    unique_id: int
    id: int
    name: str
    resource_type: str
    email: Optional[str] = None
    max_units: Optional[float] = None
    notes: Optional[str] = None


class ResourceListResponse(BaseModel):
    resources: List[ResourceInfo]
    count: int


class AssignmentInfo(BaseModel):
    unique_id: int
    task_unique_id: Optional[int] = None
    task_name: Optional[str] = None
    resource_unique_id: Optional[int] = None
    resource_name: Optional[str] = None
    units: Optional[float] = None
    work: Optional[str] = None
    actual_work: Optional[str] = None
    start: Optional[str] = None
    finish: Optional[str] = None


class AssignmentListResponse(BaseModel):
    assignments: List[AssignmentInfo]
    count: int


class ProjectInfo(BaseModel):
    name: Optional[str] = None
    project_id: Optional[str] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None
    status_date: Optional[str] = None
    author: Optional[str] = None
    company: Optional[str] = None
    currency_symbol: Optional[str] = None
    task_count: int = 0
    resource_count: int = 0


class WriteSuccess(BaseModel):
    status: str = "ok"
    output: str
    affected_unique_id: Optional[int] = None


class ErrorResponse(BaseModel):
    error: str
    code: str
