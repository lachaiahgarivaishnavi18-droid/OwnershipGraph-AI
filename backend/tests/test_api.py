import io
from app.models import db, User, Investigation, Audit
from werkzeug.security import generate_password_hash
from conftest import login

def test_login_logout_and_authorization(client,headers):
    assert client.get('/api/entities').status_code==401
    assert client.get('/api/audit',headers=headers).status_code==403
    assert client.post('/api/auth/login',json={'username':'analyst','password':'wrong'}).status_code==401
    assert client.post('/api/auth/logout',headers=headers).status_code==200
    assert client.get('/api/auth/me',headers=headers).status_code==401

def test_entity_search_create_and_validation(client,headers):
    data={'external_id':'TEST-1','entity_name':'Test Synthetic Company','entity_type':'COMPANY','jurisdiction':'Demo','source_id':1,'synthetic':True}
    r=client.post('/api/entities',json=data,headers=headers); assert r.status_code==201
    result=client.get('/api/entities/search?q=Synthetic',headers=headers).json
    assert any(e['external_id']=='TEST-1' for e in result['items'])
    assert client.post('/api/entities',json=data,headers=headers).status_code==409
    data['entity_type']='Invalid'
    assert client.post('/api/entities',json=data,headers=headers).status_code==422
    assert client.get('/api/entities?page=0',headers=headers).status_code==422

def test_review_workflow_reports_and_audit(client,headers,app):
    r=client.post('/api/agents/run/1',headers=headers)
    assert r.status_code==200,r.json
    assert r.json['report']['human_approval_required']
    logs=client.get('/api/agents/logs/1',headers=headers).json['items']
    assert len(logs)==7 and all(l['output_summary']['agent'] for l in logs)
    assert client.post('/api/investigations/1/notes',json={'note':'Request current shareholder register [SRC-1]'},headers=headers).status_code==201
    for fmt,magic in [('pdf',b'%PDF'),('csv',b'\xef\xbb\xbf')]:
        result=client.post('/api/reports/generate/1',json={'format':fmt},headers=headers)
        assert result.status_code==201
        file=client.get(result.json['download_url'],headers=headers)
        assert file.status_code==200 and file.data.startswith(magic)
    assert client.put('/api/investigations/1',json={'status':'Pending Review'},headers=headers).status_code==200
    assert client.put('/api/investigations/1',json={'status':'Approved','decision':'Approved'},headers=headers).status_code==403
    reviewer=login(client,'reviewer')
    assert client.put('/api/investigations/1',json={'status':'Approved','decision':'Source gaps recorded; academic demo accepted.'},headers=reviewer).status_code==200
    assert client.post('/api/agents/run/1',headers=headers).status_code==422
    admin=login(client,'admin')
    assert client.get('/api/audit',headers=admin).json['total']>=5

def test_case_assignment_isolation(client,headers,app):
    user=User(username='other',email='other@demo.invalid',role='analyst',password_hash=generate_password_hash('Test-Demo-Password-2026'));db.session.add(user);db.session.flush()
    row=Investigation(title='Private case',target_entity_id=11,assigned_user_id=user.id);db.session.add(row);db.session.commit()
    assert client.get(f'/api/investigations/{row.id}',headers=headers).status_code==403
    assert client.get('/api/investigations',headers=headers).json['total']==2

def test_atomic_import_dry_run_and_errors(client,headers):
    csv=b'external_id,entity_name,entity_type,jurisdiction,source_id,synthetic\nTEST-IMPORT,Demo import,COMPANY,Demo,1,true\n'
    r=client.post('/api/import/entities',data={'file':(io.BytesIO(csv),'records.csv'),'dry_run':'true'},headers=headers)
    assert r.status_code==200 and r.json['valid_rows']==1 and r.json['imported']==0
    r=client.post('/api/import/entities',data={'file':(io.BytesIO(csv),'records.csv'),'dry_run':'false'},headers=headers)
    assert r.status_code==200 and r.json['imported']==1
    assert client.get(f"/api/import/status/{r.json['job_id']}",headers=headers).status_code==200
    invalid=csv+b'INVALID,Bad,PERSON,Demo,999,true\n'
    r=client.post('/api/import/entities',data={'file':(io.BytesIO(invalid),'records.csv'),'dry_run':'false'},headers=headers)
    assert r.status_code==422 and r.json['imported']==0

def test_settings_scoring_dashboard_and_assistant(client,headers):
    config=client.get('/api/settings',headers=headers).json
    assert client.put('/api/settings',json=config,headers=headers).status_code==403
    admin=login(client,'admin'); config['weights']['opacity']=99
    assert client.put('/api/settings',json=config,headers=admin).status_code==422
    assert client.get('/api/dashboard/summary',headers=headers).json['total_entities']==12
    answer=client.post('/api/assistant',json={'entity_id':1,'question':'Are sanctions connected?'},headers=headers).json
    assert 'not connected' in answer['answer'] and answer['evidence']
