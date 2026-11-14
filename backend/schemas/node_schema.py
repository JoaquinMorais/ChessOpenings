from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictInt,
    ValidationInfo,
    field_validator,
    model_serializer,
    model_validator,
)


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cp: Optional[StrictInt] = None
    mate: Optional[StrictInt] = None
    source: Literal["manual", "engine", "llm"] = "manual"

    @model_validator(mode="before")
    @classmethod
    def validate_keys(cls, data: object) -> object:
        if isinstance(data, Evaluation):
            return data
        if not isinstance(data, dict):
            raise ValueError(
                "La evaluacion debe ser un objeto con las claves cp o mate."
            )
        unknown = set(data) - {"cp", "mate", "source"}
        if unknown:
            raise ValueError(
                "La evaluacion solo admite las claves cp, mate y source."
            )
        return data

    @field_validator("cp", "mate", mode="before")
    @classmethod
    def validate_integer(cls, value: object, info: ValidationInfo) -> object:
        if value is None:
            return value
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"El campo {info.field_name} debe ser un entero.")
        return value

    @model_validator(mode="after")
    def validate_single_value(self):
        fields = self.model_fields_set.intersection({"cp", "mate"})
        if fields == {"cp"}:
            if self.cp is None or not -9999 <= self.cp <= 9999:
                raise ValueError(
                    "El campo cp debe ser un entero entre -9999 y 9999."
                )
        elif fields == {"mate"}:
            if self.mate is None or self.mate == 0 or abs(self.mate) > 99:
                raise ValueError(
                    "El campo mate debe ser un entero distinto de 0 "
                    "con valor absoluto menor o igual a 99."
                )
        else:
            raise ValueError(
                "La evaluacion debe tener exactamente una de las claves: cp o mate."
            )
        return self

    @model_serializer
    def serialize_evaluation(self) -> Optional[dict[str, int | str]]:
        if self.cp is not None:
            return {"cp": self.cp, "source": self.source}
        if self.mate is not None:
            return {"mate": self.mate, "source": self.source}
        return None


class MoveCreate(BaseModel):
    parent_id: int
    move: str


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None
    evaluation: Optional[Evaluation] = None


class TranspositionInfo(BaseModel):
    node_id: int
    path_san: str


class NodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    opening_id: int
    parent_id: Optional[int] = None
    move_san: Optional[str] = None
    move_uci: Optional[str] = None
    fen: str
    ply: int
    order_index: int
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None
    evaluation: Optional[Evaluation] = None
    transposition_of: Optional[TranspositionInfo] = None


class NodeTree(BaseModel):
    id: int
    san: Optional[str] = None
    uci: Optional[str] = None
    fen: str
    ply: int
    order_index: int
    name: Optional[str] = None
    comment: Optional[str] = None
    classification: Optional[str] = None
    evaluation: Optional[Evaluation] = None
    children: list["NodeTree"] = []


NodeTree.model_rebuild()