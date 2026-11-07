from app.models import db,Investigation,Note,Audit

def test_retention_preview_holds_and_purge(app):
    from retention import candidates,purge
    case=db.session.get(Investigation,1);case.status='Closed';case.updated_at='2010-01-01T00:00:00+00:00'
    db.session.add(Note(investigation_id=1,user_id=2,note='Disposable synthetic note'));db.session.commit()
    assert [c.id for c in candidates()]==[1]
    assert candidates([1])==[]
    assert db.session.query(Note).count()==1
    purge(candidates())
    assert db.session.query(Note).count()==0
    assert db.session.get(Investigation,1).status=='Closed'
    assert db.session.query(Audit).filter_by(action='retention_purge').count()==1
