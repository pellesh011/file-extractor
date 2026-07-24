from pydantic import BaseModel, Field


class StartDownloadRequest(BaseModel):
    candidate_id: str | None = Field(None, description="Optional candidate identifier")


class StatisticsRequest(BaseModel):
    pass
