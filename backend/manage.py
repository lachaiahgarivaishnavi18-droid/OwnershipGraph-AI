"""Operator commands. Run from repository root with PYTHONPATH=backend."""
import argparse
import json
import os
import getpass
from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, User, Entity, Relationship, Evidence
from app.seed import seed

parser=argparse.ArgumentParser()
parser.add_argument('command',choices=['init','seed','bootstrap-admin','export-demo','sync-graph'])
args=parser.parse_args()
app=create_app()
with app.app_context():
    if args.command=='init': db.create_all(); print('Schema initialized. Use Alembic migrations for managed deployment.')
    elif args.command=='seed':
        if not app.config['DEMO_MODE']: raise RuntimeError('Demo seeding is disabled')
        seed(); print('Synthetic demo records seeded.')
    elif args.command=='bootstrap-admin':
        if db.session.query(User).filter_by(role='administrator').first(): raise RuntimeError('An administrator already exists')
        username=input('Administrator username: '); email=input('Email: '); password=getpass.getpass('Password (12+ characters): ')
        from app.schemas import RegisterInput
        data=RegisterInput(username=username,email=email,password=password,role='administrator').model_dump(); data.pop('password')
        db.session.add(User(**data,password_hash=generate_password_hash(password))); db.session.commit(); print('Administrator created.')
    elif args.command=='export-demo':
        out=Path(__file__).resolve().parents[1]/'data'/'sample'/'demo.json'
        out.write_text(json.dumps({'synthetic':True,'entities':[e.to_dict() for e in db.session.query(Entity)],'relationships':[r.to_dict() for r in db.session.query(Relationship)],'sources':[s.to_dict() for s in db.session.query(Evidence)]},indent=2),encoding='utf-8'); print(out)
    else:
        from app.neo import sync
        print(sync())
