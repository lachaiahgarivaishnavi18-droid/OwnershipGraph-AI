import os
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.seed import seed

@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DEMO_PASSWORD','Test-Demo-Password-2026')
    monkeypatch.setenv('LLM_ENABLED','false')
    monkeypatch.setenv('NEO4J_URI','')
    app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://','JWT_SECRET_KEY':'test-secret-with-at-least-thirty-two-characters','RATELIMIT_ENABLED':False})
    with app.app_context():
        db.create_all(); seed(); yield app; db.session.remove(); db.drop_all()

@pytest.fixture
def client(app): return app.test_client()

@pytest.fixture
def headers(client):
    response=client.post('/api/auth/login',json={'username':'analyst','password':'Test-Demo-Password-2026'})
    return {'Authorization':'Bearer '+response.json['access_token']}

def login(client,name):
    r=client.post('/api/auth/login',json={'username':name,'password':'Test-Demo-Password-2026'})
    return {'Authorization':'Bearer '+r.json['access_token']}
