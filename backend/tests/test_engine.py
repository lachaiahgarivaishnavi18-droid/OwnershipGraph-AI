import pytest
from app.models import db, Relationship, Entity
from app.engine import ownership, network, assess

def test_simple_and_multiple_independent_paths(app):
    # Complete the target register without introducing an unresolvable trust.
    rel=db.session.get(Relationship,3); db.session.delete(rel)
    db.session.add(Relationship(owner_entity_id=4,owned_entity_id=1,ownership_percentage=10,source_id=1))
    db.session.commit()
    result=ownership(1)
    elena=next(o for o in result['owners'] if o['entity_id']==4)
    assert elena['direct_percentage']==10
    assert elena['indirect_percentage']==42 # .6*.6 + .2*.3
    assert elena['combined_percentage']==52
    assert elena['potential_ubo'] is True
    assert len(elena['paths'])==3

def test_missing_percentages_withhold_aggregation(app):
    result=ownership(1)
    assert result['aggregation_withheld']
    assert any(g['kind']=='missing_percentage' for g in result['gaps'])
    assert all(o['combined_percentage'] is None for o in result['owners'])

def test_cycle_bounded_and_flagged(app):
    result=ownership(7,depth=4)
    assert any(g['kind']=='cycle' for g in result['gaps'])
    assert result['aggregation_withheld']
    assert network(7)['cycles']

def test_conflicts_and_overallocation(app):
    db.session.add(Relationship(owner_entity_id=2,owned_entity_id=1,ownership_percentage=60,source_id=1)); db.session.commit()
    result=ownership(1)
    assert {'conflicting_records','overallocated'} <= {g['kind'] for g in result['gaps']}

def test_temporal_control_and_depth(app):
    db.session.add(Relationship(owner_entity_id=9,owned_entity_id=2,ownership_percentage=100,control_type='CONTROLS',source_id=1))
    db.session.add(Relationship(owner_entity_id=9,owned_entity_id=1,ownership_percentage=90,valid_to='2010-01-01',source_id=1)); db.session.commit()
    result=ownership(1,depth=1)
    assert not result['paths']
    assert any(g['kind']=='depth_limit' for g in result['gaps'])
    assert any(c['control_type']=='CONTROLS' for c in result['control_indicators'])
    assert not any(p['owner_id']==9 for p in ownership(1)['paths'])

def test_graph_metrics_disconnected_and_shared(app):
    result=network(1)
    assert result['connected_components']>1
    assert result['shared_connections']
    assert sum(m['pagerank'] for m in result['metrics'])==pytest.approx(1)
    assert network(11)['max_depth']==0

def test_risk_arithmetic_unavailable_data(app):
    risk=assess(1)
    assert risk['score']==pytest.approx(sum(i['contribution'] for i in risk['indicators']))
    assert 0<=risk['score']<=100
    assert next(i for i in risk['indicators'] if i['name']=='screening')['score'] is None
    assert risk['data_completeness']<100

def test_ml_missing_model(app,monkeypatch):
    from app.ml import predict
    monkeypatch.setenv('MODEL_PATH','nonexistent.joblib')
    assert predict(1)['status']=='unavailable'
