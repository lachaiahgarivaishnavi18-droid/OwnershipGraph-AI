from app.models import db,Relationship,User
from conftest import login

def test_settings_changes_are_versioned_and_thresholds_apply(client,headers):
    admin=login(client,'admin')
    cfg=client.get('/api/settings',headers=admin).json
    cfg['jurisdiction_thresholds']={'United Kingdom':40};cfg['version']='rules-test-2'
    assert client.put('/api/settings',json=cfg,headers=admin).status_code==200
    assert client.get('/api/ownership/1',headers=headers).json['threshold']==40
    assert client.get('/api/risk/1',headers=headers).json['version']=='rules-test-2'

def test_disabled_users_and_reviewer_writes_are_rejected(client,headers):
    reviewer=login(client,'reviewer')
    assert client.post('/api/agents/run/1',headers=reviewer).status_code==403
    assert client.post('/api/investigations',json={'title':'New case','target_entity_id':1},headers=reviewer).status_code==403
    admin=login(client,'admin')
    assert client.put('/api/users/2',json={'active':False},headers=admin).status_code==200
    assert client.get('/api/entities',headers=headers).status_code==401

def test_report_snapshots_do_not_change_with_new_source_data(client,headers):
    assert client.post('/api/agents/run/1',headers=headers).status_code==200
    rel=db.session.get(Relationship,1);rel.ownership_percentage=10;db.session.commit()
    exported=client.post('/api/reports/generate/1',json={'format':'csv'},headers=headers)
    content=client.get(exported.json['download_url'],headers=headers).data.decode('utf-8-sig')
    assert 'agent_report.ownership.paths' in content
    assert ',36.0' in content # original .6*.6 path remains bound to saved assessment

def test_relationship_validation_non_finite_and_unknown_sources(client,headers):
    data={'owner_entity_id':4,'owned_entity_id':11,'ownership_percentage':101,'source_id':1}
    assert client.post('/api/relationships',json=data,headers=headers).status_code==422
    data['ownership_percentage']=50;data['source_id']=999
    assert client.post('/api/relationships',json=data,headers=headers).status_code==422
    data['source_id']=1;data['valid_from']='2025-01-01';data['valid_to']='2020-01-01'
    assert client.post('/api/relationships',json=data,headers=headers).status_code==422
