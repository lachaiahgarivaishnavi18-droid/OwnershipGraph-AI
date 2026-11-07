import os
from datetime import date
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from .models import db, User, Entity, Evidence, Relationship, Investigation, Setting
from .schemas import DEFAULT_SETTINGS

def seed():
    if db.session.query(User).first():
        return
    password = os.environ.get('DEMO_PASSWORD')
    if not password or len(password)<8:
        raise ValueError('Set DEMO_PASSWORD (at least 8 characters) before seeding')
    for name,role in [('admin','administrator'),('analyst','analyst'),('reviewer','reviewer')]:
        db.session.add(User(username=name,email=f'{name}@demo.invalid',role=role,password_hash=generate_password_hash(password)))
    source=Evidence(source_name='Synthetic academic demonstration',source_type='synthetic',source_reference='data/sample/demo.json',source_date=date.today().isoformat(),synthetic=True,reliability=0.85)
    db.session.add(source); db.session.flush()
    records=[('Aster Maritime Group','COMPANY','United Kingdom'),('Northstar Holdings','COMPANY','Netherlands'),('Cedar Capital Partners','COMPANY','Singapore'),('Elena Vale','PERSON','United Kingdom'),('Marcus Chen','PERSON','Singapore'),('Harbor Trustees','TRUST','Jersey'),('Orion Logistics','COMPANY','United Kingdom'),('Lumen Advisory','COMPANY','Ireland'),('Tessa Rowan','PERSON','Ireland'),('Shared registered office','ADDRESS','United Kingdom'),('Atlas Research','COMPANY','Germany'),('Unresolved Ventures','COMPANY','Netherlands')]
    for i,(name,kind,jurisdiction) in enumerate(records,1):
        db.session.add(Entity(id=i,external_id=f'DEMO-{i:03}',entity_name=name,entity_type=kind,jurisdiction=jurisdiction,registration_number=f'SYN-{10000+i}' if kind=='COMPANY' else None,incorporation_date='2014-06-12' if kind=='COMPANY' else None,source_id=source.id,synthetic=True,verification_status='Unverified'))
    db.session.flush()
    edges=[(2,1,60,'OWNS'),(3,1,30,'OWNS'),(6,1,None,'OWNS'),(4,2,60,'OWNS'),(5,2,40,'OWNS'),(4,3,20,'OWNS'),(5,3,80,'OWNS'),(1,7,70,'OWNS'),(7,8,40,'OWNS'),(8,7,10,'OWNS'),(9,1,None,'DIRECTOR_OF'),(9,7,None,'DIRECTOR_OF'),(9,8,None,'DIRECTOR_OF'),(1,10,None,'REGISTERED_AT'),(7,10,None,'REGISTERED_AT'),(12,8,40,'OWNS')]
    for owner,target,pct,kind in edges:
        db.session.add(Relationship(owner_entity_id=owner,owned_entity_id=target,ownership_percentage=pct,control_type=kind,source_id=source.id,valid_from='2020-01-01',confidence=0.85))
    db.session.add(Setting(key='risk',value=DEFAULT_SETTINGS))
    db.session.add(Investigation(title='Aster Maritime · ownership review',target_entity_id=1,assigned_user_id=2,reviewer_id=3,status='In Progress'))
    db.session.add(Investigation(title='Orion Logistics · structural review',target_entity_id=7,assigned_user_id=2,reviewer_id=3,status='Draft'))
    if db.engine.dialect.name=='postgresql':
        # Explicit stable demo entity IDs must advance PostgreSQL's serial sequence.
        db.session.execute(text("SELECT setval(pg_get_serial_sequence('entities','id'), (SELECT MAX(id) FROM entities), true)"))
    db.session.commit()
