import csv
import io
import json
import time
from datetime import date
from functools import wraps
from flask import Blueprint, request, jsonify, abort, g, current_app, send_file
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, Entity, Evidence, Relationship, Investigation, Assessment, Indicator, Finding, AgentLog, Note, Audit, Setting, Revoked, Report, now
from .schemas import EntityInput, RelationshipInput, RegisterInput, SignupInput, InvestigationInput, SettingsInput
from .engine import ownership, network, assess, settings

api=Blueprint('api',__name__)

def auth(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args,**kwargs):
            user=db.session.get(User,int(get_jwt_identity()))
            if not user or not user.active: abort(401,description='Account is unavailable')
            if roles and user.role not in roles: abort(403,description='Role is not authorized')
            g.user=user
            return fn(*args,**kwargs)
        return wrapped
    return decorator

def payload():
    data=request.get_json()
    if not isinstance(data,dict): abort(400,description='Expected a JSON object')
    return data

def audit(action,kind,resource_id=None,details=None):
    db.session.add(Audit(user_id=g.user.id if hasattr(g,'user') else None,action=action,resource_type=kind,resource_id=resource_id,details=details or {}))

def entity_or_404(entity_id): return db.get_or_404(Entity,entity_id)

def case_or_404(case_id):
    row=db.get_or_404(Investigation,case_id)
    if g.user.role!='administrator' and row.assigned_user_id!=g.user.id and row.reviewer_id!=g.user.id: abort(403,description='Investigation is not assigned to you')
    return row

def cases_query():
    q=db.session.query(Investigation)
    if g.user.role!='administrator': q=q.filter(db.or_(Investigation.assigned_user_id==g.user.id,Investigation.reviewer_id==g.user.id))
    return q

def page(q):
    p=request.args.get('page',1,type=int); size=request.args.get('per_page',25,type=int)
    if p<1 or not 1<=size<=100: abort(422,description='Invalid pagination')
    total=q.count()
    return jsonify(items=[r.to_dict() for r in q.offset((p-1)*size).limit(size).all()],total=total,page=p,pages=(total+size-1)//size)

def validate_refs(data):
    if not db.session.get(Evidence,data['source_id']): raise ValueError('Unknown evidence source_id')
    for key in ['owner_entity_id','owned_entity_id']:
        if key in data and not db.session.get(Entity,data[key]): raise ValueError(f'Unknown {key}')

@api.get('/health')
def health(): return jsonify(status='ok',demo=current_app.config['DEMO_MODE'],screening='disconnected',llm='evidence-template')

@api.post('/auth/login')
def login():
    data=payload(); username=data.get('username',''); password=data.get('password','')
    if not isinstance(username,str) or not isinstance(password,str) or len(password)>128: abort(400)
    user=db.session.query(User).filter(db.func.lower(User.username)==username.strip().lower()).first()
    if not user or not check_password_hash(user.password_hash,password) or not user.active: abort(401,description='Invalid username or password')
    g.user=user; audit('login','user',user.id); db.session.commit()
    return jsonify(access_token=create_access_token(identity=str(user.id)),user=user.to_dict())

@api.get('/auth/config')
def auth_config():
    return jsonify(registration_enabled=current_app.config['ALLOW_SELF_REGISTRATION'],demo_mode=current_app.config['DEMO_MODE'])

@api.post('/auth/signup')
def signup():
    if not current_app.config['ALLOW_SELF_REGISTRATION']: abort(403,description='Self-registration is disabled. Contact your administrator.')
    data=SignupInput.model_validate(payload()).model_dump()
    username=data['username'].lower();email=data['email'].lower()
    duplicate=db.session.query(User).filter(db.or_(db.func.lower(User.username)==username,db.func.lower(User.email)==email)).first()
    if duplicate: abort(409,description='Username or email is already registered. Please sign in or use different details.')
    user=User(username=username,email=email,role='analyst',password_hash=generate_password_hash(data['password']))
    db.session.add(user);db.session.flush();g.user=user
    audit('self_register','user',user.id,{'role':'analyst'});db.session.commit()
    return jsonify(access_token=create_access_token(identity=str(user.id)),user=user.to_dict()),201

@api.get('/auth/me')
@auth()
def me(): return jsonify(g.user.to_dict())

@api.post('/auth/register')
@auth('administrator')
def register():
    data=RegisterInput.model_validate(payload()).model_dump(); password=data.pop('password')
    user=User(**data,password_hash=generate_password_hash(password)); db.session.add(user); db.session.flush()
    audit('create','user',user.id); db.session.commit(); return jsonify(user.to_dict()),201

@api.post('/auth/logout')
@auth()
def logout():
    token=get_jwt(); db.session.add(Revoked(jti=token['jti'],expires_at=token['exp'])); audit('logout','user',g.user.id); db.session.commit(); return jsonify(status='logged out')

@api.get('/entities')
@api.get('/entities/search')
@auth()
def entities():
    q=db.session.query(Entity); term=request.args.get('q','').strip()
    if term:
        if request.args.get('exact')=='true': q=q.filter(db.or_(db.func.lower(Entity.entity_name)==term.lower(),Entity.registration_number==term,Entity.external_id==term))
        else:
            escaped=term.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            q=q.filter(db.or_(Entity.entity_name.ilike(f'%{escaped}%',escape='\\'),Entity.registration_number.ilike(f'%{escaped}%',escape='\\'),Entity.external_id.ilike(f'%{escaped}%',escape='\\')))
    for field in ['jurisdiction','entity_type']:
        if request.args.get(field): q=q.filter(getattr(Entity,field)==request.args[field])
    return page(q.order_by(Entity.entity_name))

@api.post('/entities')
@auth('administrator','analyst')
def create_entity():
    data=EntityInput.model_validate(payload()).model_dump(mode='json'); validate_refs(data)
    source=db.session.get(Evidence,data['source_id'])
    if source.synthetic!=data['synthetic']: raise ValueError('Synthetic classification must match evidence source')
    row=Entity(**data); db.session.add(row); db.session.flush(); audit('create','entity',row.id); db.session.commit(); return jsonify(row.to_dict()),201

@api.route('/entities/<int:entity_id>',methods=['GET','PUT','DELETE'])
@auth()
def entity_detail(entity_id):
    row=entity_or_404(entity_id)
    if request.method=='GET': return jsonify(**row.to_dict(),source=db.session.get(Evidence,row.source_id).to_dict())
    if g.user.role not in {'administrator','analyst'}: abort(403)
    if request.method=='DELETE':
        if g.user.role!='administrator': abort(403)
        db.session.delete(row)
    else:
        data=EntityInput.model_validate(payload()).model_dump(mode='json'); validate_refs(data)
        if db.session.get(Evidence,data['source_id']).synthetic!=data['synthetic']: raise ValueError('Synthetic classification must match evidence')
        for key,value in data.items(): setattr(row,key,value)
    audit(request.method.lower(),'entity',entity_id); db.session.commit(); return jsonify(status='saved')

@api.route('/relationships',methods=['GET','POST'])
@auth()
def relationships():
    if request.method=='GET': return page(db.session.query(Relationship).order_by(Relationship.id))
    if g.user.role not in {'administrator','analyst'}: abort(403)
    data=RelationshipInput.model_validate(payload()).model_dump(mode='json'); validate_refs(data)
    row=Relationship(**data); db.session.add(row); db.session.flush(); audit('create','relationship',row.id); db.session.commit(); return jsonify(row.to_dict()),201

@api.route('/evidence',methods=['GET','POST'])
@auth()
def evidence():
    if request.method=='GET': return page(db.session.query(Evidence))
    if g.user.role not in {'administrator','analyst'}: abort(403)
    data=payload()
    allowed={'source_name','source_type','source_reference','source_date','reliability','synthetic'}
    if set(data)-allowed or not all(data.get(k) for k in ['source_name','source_type','source_reference','source_date']): raise ValueError('Evidence requires name, type, reference and ISO source_date')
    date.fromisoformat(data['source_date'])
    if not isinstance(data.get('synthetic',False),bool) or not 0<=data.get('reliability',0.8)<=1: raise ValueError('Invalid evidence classification or reliability')
    row=Evidence(**data); db.session.add(row); db.session.flush(); audit('create','evidence',row.id); db.session.commit(); return jsonify(row.to_dict()),201

@api.get('/ownership/<int:entity_id>')
@api.get('/ownership/<int:entity_id>/<view>')
@auth()
def ownership_api(entity_id,view=None):
    entity_or_404(entity_id)
    depth=request.args.get('depth',settings()['max_depth'],type=int); threshold=request.args.get('threshold',type=float); as_of=request.args.get('as_of')
    if not 1<=depth<=12 or (threshold is not None and not 0<=threshold<=100): raise ValueError('Depth must be 1–12 and threshold 0–100')
    if as_of: date.fromisoformat(as_of)
    data=ownership(entity_id,depth,threshold,as_of)
    if view=='direct': return jsonify(items=[r.to_dict() for r in db.session.query(Relationship).filter_by(owned_entity_id=entity_id).all() if r.control_type in {'OWNS','SHAREHOLDER_OF'} and (not r.valid_from or r.valid_from<=data['as_of']) and (not r.valid_to or r.valid_to>=data['as_of'])])
    if view=='indirect': return jsonify(items=[p for p in data['paths'] if p['depth']>1])
    if view=='paths': return jsonify(items=data['paths'],gaps=data['gaps'])
    if view not in {None,'ubo'}: abort(404)
    return jsonify(data)

@api.get('/graph/<int:entity_id>')
@api.get('/graph/<int:entity_id>/<view>')
@auth()
def graph_api(entity_id,view=None):
    entity_or_404(entity_id); data=network(entity_id)
    if view=='cycles': return jsonify(cycles=data['cycles'],limits=data['cycle_search_limit'])
    if view=='connections': return jsonify(items=data['shared_connections'])
    if view not in {None,'analytics'}: abort(404)
    return jsonify(data)

@api.post('/graph/sync')
@auth('administrator')
def graph_sync():
    from .neo import sync
    try: result=sync()
    except Exception: abort(503,description='Neo4j synchronization failed; check service configuration')
    audit('sync','graph'); db.session.commit(); return jsonify(result)

def save_assessment(case,result,graph=None,ml=None,report=None):
    row=Assessment(investigation_id=case.id,risk_score=result['score'],risk_category=result['category'],assessment_version=result['version'],model_version=(ml or {}).get('model_version'),explanation=result,workflow_snapshot=report)
    db.session.add(row); db.session.flush()
    for i in result['indicators']: db.session.add(Indicator(assessment_id=row.id,indicator_name=i['name'],indicator_score=i['score'] or 0,weight=i['weight'],contribution=i['contribution'],evidence_reference=i['evidence'],confidence=result['confidence']))
    for f in (graph or {}).get('findings',[]): db.session.add(Finding(investigation_id=case.id,finding_type=f['indicator_name'],description=f['description'],severity=f['severity'],evidence_reference=f['evidence']))
    return row

@api.post('/risk/assess/<int:entity_id>')
@auth('administrator','analyst')
def risk_assess(entity_id):
    entity_or_404(entity_id); data=payload(); case=case_or_404(data.get('investigation_id',0))
    if case.target_entity_id!=entity_id: raise ValueError('Investigation target does not match')
    if case.status in {'Approved','Closed','Pending Review'}: raise ValueError('Reopen investigation before changing its assessment')
    result=assess(entity_id); save_assessment(case,result); audit('assess','investigation',case.id); db.session.commit(); return jsonify(result)

@api.get('/risk/<int:entity_id>')
@api.get('/risk/<int:entity_id>/explanation')
@auth()
def risk_get(entity_id): entity_or_404(entity_id); return jsonify(assess(entity_id))

@api.route('/investigations',methods=['GET','POST'])
@auth()
def investigations():
    if request.method=='GET': return page(cases_query().order_by(Investigation.updated_at.desc()))
    if g.user.role not in {'analyst','administrator'}: abort(403)
    data=InvestigationInput.model_validate(payload()).model_dump(); entity_or_404(data['target_entity_id'])
    row=Investigation(**data,assigned_user_id=g.user.id); db.session.add(row); db.session.flush(); audit('create','investigation',row.id); db.session.commit(); return jsonify(row.to_dict()),201

@api.route('/investigations/<int:case_id>',methods=['GET','PUT','DELETE'])
@auth()
def case_detail(case_id):
    row=case_or_404(case_id)
    if request.method=='GET': return jsonify(**row.to_dict(),target=entity_or_404(row.target_entity_id).to_dict(),notes=[n.to_dict() for n in db.session.query(Note).filter_by(investigation_id=case_id)],assessments=[a.to_dict() for a in db.session.query(Assessment).filter_by(investigation_id=case_id).order_by(Assessment.id.desc())],logs=[l.to_dict() for l in db.session.query(AgentLog).filter_by(investigation_id=case_id)])
    if request.method=='DELETE':
        # Preserve auditability: deletion is a soft close.
        if g.user.role!='administrator': abort(403)
        row.status='Closed'
    else:
        data=payload()
        if set(data)-{'status','reviewer_id','decision'}: raise ValueError('Unknown investigation update field')
        if 'reviewer_id' in data:
            if g.user.role not in {'administrator','analyst'} or row.status in {'Approved','Closed','Pending Review'}: abort(403)
            reviewer=db.get_or_404(User,data['reviewer_id'])
            if reviewer.role!='reviewer' or not reviewer.active or reviewer.id==row.assigned_user_id: raise ValueError('Select an active independent reviewer')
            row.reviewer_id=reviewer.id
        new=data.get('status',row.status)
        transitions={'Draft':{'In Progress'},'In Progress':{'Pending Review'},'Pending Review':{'Approved','Rejected','In Progress'},'Rejected':{'In Progress'},'Approved':{'Closed'},'Closed':set()}
        if new!=row.status:
            if new not in transitions[row.status]: raise ValueError('Invalid investigation status transition')
            if row.status=='Pending Review':
                if g.user.role!='administrator' and (g.user.role!='reviewer' or row.reviewer_id!=g.user.id): abort(403)
                if g.user.id==row.assigned_user_id: abort(403,description='Independent human reviewer required')
                if not isinstance(data.get('decision'),str) or len(data['decision'].strip())<3: raise ValueError('A review decision reason is required')
                row.decision=data['decision'][:10000]; row.reviewed_at=now()
            elif g.user.role not in {'administrator','analyst'}: abort(403)
            if new=='Pending Review':
                if not row.reviewer_id: raise ValueError('Assign a reviewer before submission')
                if not db.session.query(Assessment).filter_by(investigation_id=row.id).first(): raise ValueError('Run the assessment before submission')
            row.status=new
    row.updated_at=now(); audit('update','investigation',case_id,{'status':row.status}); db.session.commit(); return jsonify(row.to_dict())

@api.post('/investigations/<int:case_id>/notes')
@auth()
def add_note(case_id):
    row=case_or_404(case_id); data=payload(); text=data.get('note',''); refs=data.get('evidence_references',[])
    if not isinstance(text,str) or not 1<=len(text.strip())<=10000 or not isinstance(refs,list) or any(not isinstance(r,str) for r in refs): raise ValueError('Note must contain 1–10000 characters and string evidence references')
    note=Note(investigation_id=row.id,user_id=g.user.id,note=text,evidence_references=refs); db.session.add(note); audit('note','investigation',row.id); db.session.commit(); return jsonify(note.to_dict()),201

@api.post('/agents/run/<int:case_id>')
@auth('administrator','analyst')
def agents_run(case_id):
    row=case_or_404(case_id)
    if row.status not in {'Draft','In Progress','Rejected'}: raise ValueError('Investigation must be editable to run agents')
    from .agents import run_workflow
    try: result=run_workflow(row)
    except Exception:
        audit('workflow_failed','investigation',row.id); db.session.commit()
        abort(503,description='Workflow failed. Inspect execution logs; no assessment was saved.')
    if 'risk' not in result: raise ValueError('Insufficient entity evidence; manual review required')
    save_assessment(row,result['risk'],result['graph'],result['ml'],result.get('report')); row.status='In Progress'; row.updated_at=now()
    audit('run_agents','investigation',row.id); db.session.commit(); return jsonify(result)

@api.get('/agents/status/<int:case_id>')
@api.get('/agents/logs/<int:case_id>')
@auth()
def agent_logs(case_id):
    case_or_404(case_id); return jsonify(items=[l.to_dict() for l in db.session.query(AgentLog).filter_by(investigation_id=case_id).order_by(AgentLog.id)])

@api.post('/assistant')
@auth()
def assistant():
    data=payload(); target=data.get('entity_id'); question=data.get('question','')
    if not isinstance(question,str) or not 1<=len(question)<=2000: raise ValueError('Question must contain 1–2000 characters')
    entity=entity_or_404(target); own=ownership(target); net=network(target); risk=assess(target,own,net); q=question.lower()
    if any(x in q for x in ['sanction','pep','media']): answer='Sanctions, PEP and adverse-media sources are not connected. No screening determination is available.'
    elif any(x in q for x in ['ubo','beneficial','owner','path']): answer=f"Upstream persons for {entity.entity_name}: "+'; '.join(f"{o['name']}: {o['path_estimate_percentage']}% simple-path estimate" for o in own['owners'])+('. Combined ownership is withheld because records need reconciliation.' if own['aggregation_withheld'] else f". Illustrative candidate threshold: {own['threshold']}%.")
    elif 'director' in q: answer=json.dumps(net['shared_connections'])
    elif any(x in q for x in ['circular','cycle']): answer=f"{len(net['cycles'])} ownership cycles observed in the connected component: {net['cycles']}. These require investigation and are not proof of wrongdoing."
    elif any(x in q for x in ['missing','document','request','next']): answer=' '.join(risk['missing_information']+risk['recommended_next_steps'])
    elif any(x in q for x in ['risk','score','why']): answer=f"Observed-indicator score {risk['score']}/100 ({risk['category']}); "+'; '.join(f"{i['name']}: {i['contribution']} points" for i in risk['indicators'] if i['available'])+'. '+risk['score_interpretation']
    else: answer=f"{entity.entity_name} has {len(own['paths'])} upstream person paths and {len(own['gaps'])} unresolved evidence issues. Ask about ownership, paths, risk, directors, cycles or missing documents. Information outside these records is unavailable."
    from .llm import summarize,facts_for
    narrative=summarize(facts_for(own,risk),question)
    if narrative['status']=='completed': answer+='\nEvidence highlights: '+' '.join(s['text'] for s in narrative['statements'])
    audit('assistant_query','entity',target,{'mode':narrative['mode'],'model_version':narrative['model_version']});db.session.commit()
    return jsonify(answer=answer,evidence=own['evidence'],mode=narrative['mode'],narrative=narrative,synthetic=entity.synthetic)

@api.get('/dashboard/summary')
@api.get('/dashboard/risk-distribution')
@api.get('/dashboard/trends')
@auth()
def dashboard():
    cases=cases_query().all(); ids=[c.id for c in cases]; assessments=db.session.query(Assessment).filter(Assessment.investigation_id.in_(ids)).order_by(Assessment.id).all()
    latest={a.investigation_id:a for a in assessments}; distribution={k:0 for k in ['Low','Medium','High','Critical']}
    for a in latest.values(): distribution[a.risk_category]+=1
    entities=db.session.query(Entity).all(); targets={c.target_entity_id for c in cases}
    ubo=sum(sum(o['potential_ubo'] for o in ownership(t)['owners']) for t in targets)
    def count(field,rows):
        out={}
        for row in rows: key=getattr(row,field); out[key]=out.get(key,0)+1
        return out
    trends={}
    for c in cases: day=c.created_at[:10]; trends[day]=trends.get(day,0)+1
    return jsonify(total_entities=len(entities),total_investigations=len(cases),entities_analyzed=len(latest),potential_ubos=ubo,structures_analyzed=len({a.investigation_id for a in assessments}),graph_anomalies=db.session.query(Finding).filter(Finding.investigation_id.in_(ids)).count(),pending_review=sum(c.status=='Pending Review' for c in cases),risk_distribution=distribution,entity_types=count('entity_type',entities),jurisdictions=count('jurisdiction',entities),investigation_status=count('status',cases),trends=[{'date':k,'count':v} for k,v in sorted(trends.items())],recent_investigations=[{**c.to_dict(),'target_name':db.session.get(Entity,c.target_entity_id).entity_name,'risk_score':latest[c.id].risk_score if c.id in latest else None,'risk_category':latest[c.id].risk_category if c.id in latest else 'Unassessed'} for c in sorted(cases,key=lambda c:c.updated_at,reverse=True)[:10]],data_quality_alerts=sum(len(ownership(t)['gaps']) for t in targets),recent_findings=[f.to_dict() for f in db.session.query(Finding).filter(Finding.investigation_id.in_(ids)).order_by(Finding.id.desc()).limit(5)],synthetic_entities=sum(e.synthetic for e in entities))

@api.route('/settings',methods=['GET','PUT'])
@auth()
def settings_api():
    if request.method=='GET': return jsonify(settings())
    if g.user.role!='administrator': abort(403)
    data=SettingsInput.model_validate(payload()).model_dump(mode='json'); row=db.session.get(Setting,'risk')
    if row: row.value=data
    else: db.session.add(Setting(key='risk',value=data))
    audit('configure','settings',details=data); db.session.commit(); return jsonify(data)

@api.get('/users')
@auth()
def users():
    if g.user.role!='administrator': return jsonify(items=[{'id':u.id,'username':u.username,'role':u.role} for u in db.session.query(User).filter_by(role='reviewer',active=True)])
    return page(db.session.query(User).order_by(User.id))

@api.put('/users/<int:user_id>')
@auth('administrator')
def user_update(user_id):
    row=db.get_or_404(User,user_id); data=payload()
    if set(data)-{'role','active'} or ('role' in data and data['role'] not in {'administrator','analyst','reviewer'}) or ('active' in data and not isinstance(data['active'],bool)): raise ValueError('Invalid user update')
    if row.id==g.user.id: raise ValueError('Cannot modify your own access')
    for k,v in data.items(): setattr(row,k,v)
    audit('update','user',user_id,data); db.session.commit(); return jsonify(row.to_dict())

@api.get('/audit')
@auth('administrator')
def audit_list(): return page(db.session.query(Audit).order_by(Audit.id.desc()))

@api.post('/import/<kind>')
@auth('administrator','analyst')
def import_data(kind):
    if kind not in {'entities','ownership'}: abort(404)
    file=request.files.get('file')
    if not file or not file.filename: raise ValueError('Upload a CSV or XLSX file')
    suffix=file.filename.rsplit('.',1)[-1].lower()
    if suffix=='csv':
        try: rows=list(csv.DictReader(io.StringIO(file.read().decode('utf-8-sig'))))
        except UnicodeDecodeError: raise ValueError('CSV must be UTF-8')
    elif suffix=='xlsx':
        import zipfile
        raw=file.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(x.file_size for x in archive.infolist())>25*1024*1024: raise ValueError('Expanded XLSX exceeds 25 MB')
        from openpyxl import load_workbook
        workbook=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
        try:
            sheet=workbook.active
            values=sheet.iter_rows(values_only=True)
            headers=next(values,())
            if not headers or any(not isinstance(h,str) or not h.strip() for h in headers) or len(set(headers))!=len(headers):
                raise ValueError('XLSX requires unique nonempty text column headers')
            rows=[]
            for cells in values:
                if not any(v is not None for v in cells): continue
                rows.append(dict(zip(headers,cells)))
                if len(rows)>5000: raise ValueError('Import requires 1–5000 rows')
        finally: workbook.close()
    else: raise ValueError('Only CSV and XLSX are accepted')
    if not rows or len(rows)>5000: raise ValueError('Import requires 1–5000 rows')
    schema=EntityInput if kind=='entities' else RelationshipInput; model=Entity if kind=='entities' else Relationship
    valid=[]; errors=[]; seen=set()
    for index,row in enumerate(rows,2):
        try:
            cleaned={k:v for k,v in row.items() if v!='' and v is not None}
            if 'aliases' in cleaned and isinstance(cleaned['aliases'],str): cleaned['aliases']=json.loads(cleaned['aliases'])
            data=schema.model_validate(cleaned).model_dump(mode='json'); validate_refs(data)
            if kind=='entities':
                if db.session.get(Evidence,data['source_id']).synthetic!=data['synthetic']: raise ValueError('Synthetic classification must match source')
                key=data['external_id']
                if key in seen or db.session.query(Entity).filter_by(external_id=key).first(): raise ValueError('Duplicate external_id')
            else:
                key=(data['owner_entity_id'],data['owned_entity_id'],data['control_type'],data['valid_from'],data['valid_to'])
                if key in seen or db.session.query(Relationship).filter_by(**{k:data[k] for k in ['owner_entity_id','owned_entity_id','control_type','valid_from','valid_to']}).first(): raise ValueError('Duplicate or conflicting active relationship; reconcile before ingestion')
            seen.add(key); valid.append(data)
        except Exception as exc: errors.append({'row':index,'error':str(exc)[:600]})
    dry=request.form.get('dry_run','true').lower()!='false'
    result={'kind':kind,'dry_run':dry,'valid_rows':len(valid),'errors':errors,'imported':0}
    if not errors and not dry:
        db.session.add_all(model(**r) for r in valid); result['imported']=len(valid)
    audit('import_validation' if dry else 'import','import',details=result); db.session.flush(); log=db.session.query(Audit).filter_by(user_id=g.user.id,resource_type='import').order_by(Audit.id.desc()).first(); result['job_id']=log.id; db.session.commit()
    return jsonify(result),422 if errors else 200

@api.get('/import/status/<int:job_id>')
@auth()
def import_status(job_id):
    row=db.get_or_404(Audit,job_id)
    if row.resource_type!='import' or (row.user_id!=g.user.id and g.user.role!='administrator'): abort(403)
    return jsonify(row.details)

@api.post('/reports/generate/<int:case_id>')
@auth()
def report_generate(case_id):
    case=case_or_404(case_id); fmt=payload().get('format','pdf')
    if fmt not in {'pdf','csv'}: raise ValueError('Report format must be pdf or csv')
    assessment=db.session.query(Assessment).filter_by(investigation_id=case_id).order_by(Assessment.id.desc()).first()
    if not assessment: raise ValueError('Run an investigation assessment before exporting')
    snapshot={'investigation':case.to_dict(),'target':entity_or_404(case.target_entity_id).to_dict(),'assessment':{k:v for k,v in assessment.to_dict().items() if k!='workflow_snapshot'},'agent_report':assessment.workflow_snapshot,'notes':[n.to_dict() for n in db.session.query(Note).filter_by(investigation_id=case_id)],'generated_at':now()}
    row=Report(investigation_id=case_id,format=fmt,snapshot=snapshot); db.session.add(row); db.session.flush(); audit('export','report',row.id); db.session.commit(); return jsonify(id=row.id,download_url=f'/api/reports/{row.id}/download'),201

@api.get('/reports/<int:report_id>/download')
@auth()
def report_download(report_id):
    row=db.get_or_404(Report,report_id); case_or_404(row.investigation_id)
    from .reports import render
    data,mime=render(row.snapshot,row.format)
    return send_file(io.BytesIO(data),mimetype=mime,as_attachment=True,download_name=f'ownershipgraph-investigation-{row.investigation_id}.{row.format}')
