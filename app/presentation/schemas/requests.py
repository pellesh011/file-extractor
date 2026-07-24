from pydantic import BaseModel, Field


class StartDownloadRequest(BaseModel):
    candidate_id: str | None = Field(None, description="Optional candidate identifier")


class StatisticsRequest(BaseModel):
    pass


class CalculateStatsRequest(BaseModel):
    file_ids: list[str] = Field(..., description="List of file IDs to calculate statistics for")
