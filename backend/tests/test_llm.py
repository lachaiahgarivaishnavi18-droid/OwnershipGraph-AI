import json
from app.llm import summarize

FACTS=[{'id':'fact_1','text':'Recorded ownership is unknown.','evidence':['REL-1']}]

def configure(monkeypatch):
    monkeypatch.setenv('LLM_ENABLED','true');monkeypatch.setenv('LLM_API_KEY','test-not-a-real-key');monkeypatch.setenv('LLM_MODEL','test-model')

def test_missing_key_uses_deterministic_mode(monkeypatch):
    monkeypatch.delenv('LLM_API_KEY',raising=False)
    assert summarize(FACTS)['status']=='unavailable'

def test_valid_selection_uses_only_server_facts(monkeypatch):
    configure(monkeypatch)
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'model':'test-version','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'selected_fact_ids':['fact_1']})}]}]}
    monkeypatch.setattr('app.llm.httpx.post',lambda *a,**kw:Response())
    result=summarize(FACTS)
    assert result['statements']==FACTS and result['model_version']=='test-version'

def test_hallucinated_ids_fail_closed(monkeypatch):
    configure(monkeypatch)
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'output':[{'type':'message','content':[{'type':'output_text','text':'{"selected_fact_ids":["invented"]}'}]}]}
    monkeypatch.setattr('app.llm.httpx.post',lambda *a,**kw:Response())
    result=summarize(FACTS)
    assert result['status']=='unavailable' and result['statements']==[]

def test_timeout_falls_back(monkeypatch):
    configure(monkeypatch)
    def fail(*a,**kw): raise TimeoutError('not exposed')
    monkeypatch.setattr('app.llm.httpx.post',fail)
    assert summarize(FACTS)['status']=='unavailable'
