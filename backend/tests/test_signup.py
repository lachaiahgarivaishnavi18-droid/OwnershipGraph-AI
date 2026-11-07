from app.models import db,User,Audit
from app.demo_accounts import update_demo_password

DETAILS={'username':'new_analyst','email':'new@example.invalid','password':'demo@2026'}

def test_signup_creates_hashed_analyst_and_signs_in(client,app):
    response=client.post('/api/auth/signup',json=DETAILS)
    assert response.status_code==201,response.json
    assert response.json['user']['role']=='analyst'
    assert 'password_hash' not in response.json['user']
    token=response.json['access_token'];headers={'Authorization':'Bearer '+token}
    assert client.get('/api/auth/me',headers=headers).status_code==200
    assert client.get('/api/audit',headers=headers).status_code==403
    assert client.post('/api/investigations',headers=headers,json={'title':'My first investigation','target_entity_id':1}).status_code==201
    user=db.session.query(User).filter_by(username='new_analyst').one()
    assert user.password_hash!=DETAILS['password']
    assert db.session.query(Audit).filter_by(action='self_register',user_id=user.id).count()==1
    assert client.post('/api/auth/login',json={'username':'NEW_ANALYST','password':'demo@2026'}).status_code==200

def test_signup_rejects_duplicate_case_insensitive_and_privileged_roles(client):
    assert client.post('/api/auth/signup',json=DETAILS).status_code==201
    assert client.post('/api/auth/signup',json={**DETAILS,'username':'NEW_ANALYST','email':'other@example.invalid'}).status_code==409
    assert client.post('/api/auth/signup',json={**DETAILS,'username':'another','email':'NEW@EXAMPLE.INVALID'}).status_code==409
    assert client.post('/api/auth/signup',json={**DETAILS,'username':'escalation','role':'administrator'}).status_code==422

def test_signup_can_be_disabled_and_validates_password(client,app):
    assert client.post('/api/auth/signup',json={**DETAILS,'password':'short'}).status_code==422
    app.config['ALLOW_SELF_REGISTRATION']=False
    assert client.get('/api/auth/config').json['registration_enabled'] is False
    assert client.post('/api/auth/signup',json=DETAILS).status_code==403

def test_demo_password_update_changes_only_demo_accounts(client,app,monkeypatch):
    assert client.post('/api/auth/signup',json={**DETAILS,'password':'personal-password'}).status_code==201
    monkeypatch.setenv('DEMO_PASSWORD','demo@2026')
    assert update_demo_password()==3
    for username in ['analyst','reviewer','admin']:
        assert client.post('/api/auth/login',json={'username':username,'password':'demo@2026'}).status_code==200
    assert client.post('/api/auth/login',json={'username':'new_analyst','password':'personal-password'}).status_code==200
    assert db.session.query(Audit).filter_by(action='demo_password_updated').count()==3
