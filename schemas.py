from pydantic import BaseModel, Field, field_validator


class RequestModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def strip_string_fields(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class QuestionRequest(RequestModel):
    question: str = Field(min_length=2, max_length=4_000)


class ExplanationRequest(RequestModel):
    topic: str = Field(min_length=2, max_length=1_000)


class TextRequest(RequestModel):
    text: str = Field(min_length=20, max_length=30_000)


class LearningPathRequest(RequestModel):
    topic: str = Field(min_length=2, max_length=1_000)
    level: str = Field(default="Beginner", min_length=2, max_length=30)
