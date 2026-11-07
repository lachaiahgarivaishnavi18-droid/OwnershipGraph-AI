"""Generate an isolated, evidence-linked synthetic report for visual QA."""
import sys
import os
import secrets
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app import create_app
from app.models import db
from app.seed import seed

password=secrets.token_urlsafe(24)
os.environ['DEMO_PASSWORD']=password
os.environ['LLM_ENABLED']='false'
os.environ['NEO4J_URI']=''
app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://','RATELIMIT_ENABLED':False})
with app.app_context():
    db.create_all();seed();client=app.test_client()
    token=client.post('/api/auth/login',json={'username':'analyst','password':password}).json['access_token']
    headers={'Authorization':'Bearer '+token}
    run=client.post('/api/agents/run/1',headers=headers)
    assert run.status_code==200,run.json
    report=client.post('/api/reports/generate/1',json={'format':'pdf'},headers=headers)
    response=client.get(report.json['download_url'],headers=headers)
    assert response.status_code==200 and response.data.startswith(b'%PDF')
    out=Path(__file__).resolve().parents[1]/'output'/'pdf';out.mkdir(parents=True,exist_ok=True)
    (out/'demo-investigation.pdf').write_bytes(response.data)
    print(f'Workflow completed; PDF generated at {out / "demo-investigation.pdf"}')
