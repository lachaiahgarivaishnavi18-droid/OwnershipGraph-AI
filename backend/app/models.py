from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.String(40), default=now, nullable=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != 'password_hash'}

class User(Base):
    __tablename__ = 'users'
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

class Evidence(Base):
    __tablename__ = 'evidence_sources'
    source_name = db.Column(db.String(200), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)
    source_reference = db.Column(db.Text, nullable=False)
    source_date = db.Column(db.String(10), nullable=False)
    reliability = db.Column(db.Float, default=0.8)
    synthetic = db.Column(db.Boolean, default=False, nullable=False)

class Entity(Base):
    __tablename__ = 'entities'
    external_id = db.Column(db.String(120), unique=True, nullable=False)
    entity_name = db.Column(db.String(240), nullable=False, index=True)
    entity_type = db.Column(db.String(30), nullable=False, index=True)
    jurisdiction = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(120), index=True)
    incorporation_date = db.Column(db.String(10))
    status = db.Column(db.String(40), default='Active')
    aliases = db.Column(db.JSON, default=list)
    source_id = db.Column(db.Integer, db.ForeignKey('evidence_sources.id'), nullable=False)
    verification_status = db.Column(db.String(40), default='Unverified')
    synthetic = db.Column(db.Boolean, default=False, nullable=False)
    updated_at = db.Column(db.String(40), default=now, onupdate=now)

class Relationship(Base):
    __tablename__ = 'ownership_relationships'
    owner_entity_id = db.Column(db.Integer, db.ForeignKey('entities.id'), nullable=False, index=True)
    owned_entity_id = db.Column(db.Integer, db.ForeignKey('entities.id'), nullable=False, index=True)
    ownership_percentage = db.Column(db.Float)
    control_type = db.Column(db.String(40), default='OWNS', nullable=False)
    valid_from = db.Column(db.String(10))
    valid_to = db.Column(db.String(10))
    source_id = db.Column(db.Integer, db.ForeignKey('evidence_sources.id'), nullable=False)
    confidence = db.Column(db.Float, default=0.8)
    verification_status = db.Column(db.String(40), default='Unverified')
    __table_args__ = (db.CheckConstraint('ownership_percentage IS NULL OR (ownership_percentage >= 0 AND ownership_percentage <= 100)'), db.CheckConstraint('confidence >= 0 AND confidence <= 1'))

class Investigation(Base):
    __tablename__ = 'investigations'
    title = db.Column(db.String(240), nullable=False)
    target_entity_id = db.Column(db.Integer, db.ForeignKey('entities.id'), nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(40), default='Draft', nullable=False)
    decision = db.Column(db.Text)
    reviewed_at = db.Column(db.String(40))
    updated_at = db.Column(db.String(40), default=now, onupdate=now)

class Assessment(Base):
    __tablename__ = 'risk_assessments'
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigations.id'), nullable=False, index=True)
    risk_score = db.Column(db.Float, nullable=False)
    risk_category = db.Column(db.String(20), nullable=False)
    assessment_version = db.Column(db.String(40), default='rules-1.0')
    model_version = db.Column(db.String(80))
    explanation = db.Column(db.JSON, nullable=False)
    workflow_snapshot = db.Column(db.JSON)

class Indicator(Base):
    __tablename__ = 'risk_indicators'
    assessment_id = db.Column(db.Integer, db.ForeignKey('risk_assessments.id'), nullable=False)
    indicator_name = db.Column(db.String(120), nullable=False)
    indicator_score = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    contribution = db.Column(db.Float, nullable=False)
    evidence_reference = db.Column(db.JSON, default=list)
    confidence = db.Column(db.Float)

class Finding(Base):
    __tablename__ = 'graph_findings'
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigations.id'), nullable=False)
    finding_type = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    evidence_reference = db.Column(db.JSON, default=list)

class AgentLog(Base):
    __tablename__ = 'agent_execution_logs'
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigations.id'), nullable=False, index=True)
    agent_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    input_summary = db.Column(db.JSON)
    output_summary = db.Column(db.JSON)
    error_message = db.Column(db.Text)
    execution_time = db.Column(db.Float)
    model_version = db.Column(db.String(80), default='deterministic-1.0')
    prompt_version = db.Column(db.String(40), default='evidence-template-1.0')

class Note(Base):
    __tablename__ = 'analyst_notes'
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)
    evidence_references = db.Column(db.JSON, default=list)

class Audit(Base):
    __tablename__ = 'audit_logs'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(80), nullable=False)
    resource_type = db.Column(db.String(80), nullable=False)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.JSON, default=dict)

class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.JSON, nullable=False)

class Revoked(db.Model):
    __tablename__ = 'revoked_tokens'
    jti = db.Column(db.String(80), primary_key=True)
    expires_at = db.Column(db.Integer, nullable=False)

class Report(Base):
    __tablename__ = 'reports'
    investigation_id = db.Column(db.Integer, db.ForeignKey('investigations.id'), nullable=False)
    format = db.Column(db.String(8), nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
