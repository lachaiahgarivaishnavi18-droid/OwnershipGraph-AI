"""Operator retention control. Preview by default; --apply purges closed-case content.

Case metadata, audit history and source records remain. Legal holds always exclude
cases: pass their IDs with --hold. No scheduler or deletion runs automatically.
"""
import argparse
from datetime import datetime,timezone,timedelta
from app import create_app
from app.engine import settings
from app.models import db,Investigation,Assessment,Indicator,Report,Note,AgentLog,Finding,Audit,Revoked

def candidates(hold=()):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=settings()['retention_days'])).isoformat()
    return db.session.query(Investigation).filter(Investigation.status=='Closed',Investigation.updated_at<cutoff,Investigation.id.notin_(list(hold))).all()

def purge(cases):
    for case in cases:
        assessments=db.session.query(Assessment.id).filter_by(investigation_id=case.id)
        db.session.query(Indicator).filter(Indicator.assessment_id.in_(assessments)).delete(synchronize_session=False)
        for model in [Report,Note,AgentLog,Finding,Assessment]: db.session.query(model).filter_by(investigation_id=case.id).delete(synchronize_session=False)
        case.decision='Case content purged under configured retention policy.'
        db.session.add(Audit(action='retention_purge',resource_type='investigation',resource_id=case.id,details={'policy_days':settings()['retention_days']}))
    db.session.query(Revoked).filter(Revoked.expires_at<int(datetime.now(timezone.utc).timestamp())).delete()
    db.session.commit()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--hold',type=int,nargs='*',default=[]);args=parser.parse_args()
    app=create_app()
    with app.app_context():
        cases=candidates(args.hold);print({'eligible_closed_case_ids':[c.id for c in cases],'apply':args.apply,'excluded_legal_hold_ids':args.hold})
        if args.apply: purge(cases)
