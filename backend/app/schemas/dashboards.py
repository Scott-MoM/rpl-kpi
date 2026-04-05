from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: str | int | float
    description: str | None = None


class DashboardSection(BaseModel):
    title: str
    metrics: list[DashboardMetric]


class DashboardFilterOptions(BaseModel):
    regions: list[str]


class DashboardDetailRow(BaseModel):
    id: str
    label: str
    date: str | None = None
    region: str | None = None
    value: str | int | float | None = None
    metadata: dict[str, str | int | float | bool | None] = {}


class DashboardDetailPayload(BaseModel):
    section: str
    region: str
    timeframe: str
    rows: list[DashboardDetailRow]


class DashboardSeriesPoint(BaseModel):
    label: str
    value: float
    series: str | None = None


class MLEventDetailPayload(BaseModel):
    event_id: str
    label: str
    date: str | None = None
    region: str | None = None
    event_type: str | None = None
    participants: int = 0
    metadata: list[DashboardDetailRow]
    personal_rows: list[DashboardDetailRow]
    medical_rows: list[DashboardDetailRow]
    emergency_rows: list[DashboardDetailRow]


class FunderDetailPayload(BaseModel):
    funder: str
    region: str
    timeframe: str
    metrics: list[DashboardMetric]
    income_series: list[DashboardSeriesPoint]
    rows: list[DashboardDetailRow]


class DashboardSummary(BaseModel):
    key: str
    label: str
    description: str


class DashboardPayload(BaseModel):
    title: str
    region: str
    timeframe: str
    source: str
    last_updated: str | None = None
    metrics: list[DashboardMetric]
    sections: list[DashboardSection] = []
    notes: list[str] = []
