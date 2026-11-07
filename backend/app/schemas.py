from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)

class EntityInput(Strict):
    external_id: str = Field(min_length=1, max_length=120)
    entity_name: str = Field(min_length=1, max_length=240)
    entity_type: Literal['PERSON','COMPANY','TRUST','PARTNERSHIP','FOUNDATION','OTHER','ADDRESS','DIRECTOR','JURISDICTION']
    jurisdiction: str = Field(min_length=1,max_length=100)
    registration_number: str | None = Field(default=None,max_length=120)
    incorporation_date: date | None = None
    status: str = Field(default='Active',max_length=40)
    aliases: list[str] = Field(default_factory=list,max_length=30)
    source_id: int = Field(gt=0)
    verification_status: Literal['Verified','Unverified','Disputed'] = 'Unverified'
    synthetic: bool = False

class RelationshipInput(Strict):
    owner_entity_id: int = Field(gt=0)
    owned_entity_id: int = Field(gt=0)
    ownership_percentage: float | None = Field(default=None,ge=0,le=100)
    control_type: Literal['OWNS','SHAREHOLDER_OF','CONTROLS','DIRECTOR_OF','BENEFICIARY_OF','TRUSTEE_OF','REGISTERED_AT','RELATED_TO'] = 'OWNS'
    valid_from: date | None = None
    valid_to: date | None = None
    source_id: int = Field(gt=0)
    confidence: float = Field(default=0.8,ge=0,le=1)
    verification_status: Literal['Verified','Unverified','Disputed'] = 'Unverified'

    @model_validator(mode='after')
    def dates(self):
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError('valid_to must be on or after valid_from')
        return self

class RegisterInput(Strict):
    username: str = Field(min_length=3,max_length=80)
    email: str = Field(min_length=3,max_length=254,pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(min_length=12,max_length=128)
    role: Literal['administrator','analyst','reviewer'] = 'analyst'

class SignupInput(Strict):
    username: str = Field(min_length=3,max_length=80,pattern=r'^[A-Za-z0-9_.-]+$')
    email: str = Field(min_length=3,max_length=254,pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    password: str = Field(min_length=8,max_length=128)

class InvestigationInput(Strict):
    title: str = Field(min_length=3,max_length=240)
    target_entity_id: int = Field(gt=0)

class AgentOutput(Strict):
    agent: str
    status: Literal['completed','unavailable','manual_review']
    data: dict
    evidence: list[str]

class StageData(BaseModel):
    model_config=ConfigDict(extra='allow',allow_inf_nan=False)

class EntityStage(StageData):
    id:int
    entity_name:str
    source_id:int=Field(gt=0)
    normalized_name:str
    possible_duplicate_ids:list[int]

class OwnershipPath(StageData):
    owner_id:int
    entity_ids:list[int]
    relationship_ids:list[int]
    depth:int=Field(ge=1,le=12)
    attributable_percentage:float|None=Field(ge=0,le=100)
    confidence:float=Field(ge=0,le=1)
    evidence:list[str]

class OwnershipStage(StageData):
    target_id:int
    paths:list[OwnershipPath]
    owners:list[dict]
    gaps:list[dict]
    aggregation_withheld:bool

class GraphStage(StageData):
    nodes:list[dict]
    edges:list[dict]
    cycles:list[list[int]]
    metrics:list[dict]
    findings:list[dict]

class ModelStage(StageData):
    status:Literal['experimental','unavailable']
    model_version:str|None

class RiskIndicator(StageData):
    name:str
    score:float|None=Field(ge=0,le=100)
    weight:float=Field(ge=0,le=100)
    contribution:float=Field(ge=0,le=100)
    available:bool
    evidence:list[str]

class RiskStage(StageData):
    score:float=Field(ge=0,le=100)
    category:Literal['Low','Medium','High','Critical']
    indicators:list[RiskIndicator]
    confidence:float=Field(ge=0,le=1)
    data_completeness:float=Field(ge=0,le=100)
    missing_information:list[str]
    recommended_next_steps:list[str]

class RecommendationStage(StageData):
    actions:list[str]
    missing_information:list[str]
    human_approval_required:Literal[True]

class ReportStage(StageData):
    title:str
    summary:str
    observed_facts:dict
    ownership:OwnershipStage
    risk:RiskStage
    human_approval_required:Literal[True]

STAGE_SCHEMAS={'entity':EntityStage,'ownership':OwnershipStage,'graph':GraphStage,'ml':ModelStage,'risk':RiskStage,'recommendations':RecommendationStage,'report':ReportStage}

DEFAULT_SETTINGS = {
    'ubo_threshold': 25, 'jurisdiction_thresholds': {}, 'max_depth': 8,
    'weights': {'opacity':20,'complexity':15,'jurisdiction':15,'screening':20,'network':15,'inconsistency':10,'changes':5},
    'categories': [30,60,80], 'retention_days':365,
    'version':'rules-1.0',
}

class SettingsInput(Strict):
    ubo_threshold: float = Field(ge=0,le=100)
    jurisdiction_thresholds: dict[str,float] = Field(default_factory=dict)
    max_depth: int = Field(ge=1,le=12)
    weights: dict[str,float]
    categories: list[float] = Field(min_length=3,max_length=3)
    retention_days: int = Field(ge=30,le=3650)
    version: str = Field(min_length=1,max_length=40)

    @model_validator(mode='after')
    def valid(self):
        if set(self.weights) != set(DEFAULT_SETTINGS['weights']) or any(v<0 or v>100 for v in self.weights.values()) or abs(sum(self.weights.values())-100)>0.001:
            raise ValueError('weights must use all seven indicators and sum to 100')
        if not 0 < self.categories[0] < self.categories[1] < self.categories[2] <= 100:
            raise ValueError('categories must be three increasing boundaries')
        if any(not 0<=v<=100 for v in self.jurisdiction_thresholds.values()):
            raise ValueError('jurisdiction thresholds must be between 0 and 100')
        return self
