import time
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from .models import db, Entity, AgentLog
from .schemas import AgentOutput,STAGE_SCHEMAS
from .engine import ownership, network, assess
from .ml import predict

class State(TypedDict,total=False):
    investigation_id:int
    target_id:int
    entity:dict
    ownership:dict
    graph:dict
    ml:dict
    risk:dict
    recommendations:dict
    report:dict
    insufficient:bool

def run_workflow(investigation):
    stages=[('Entity Intelligence','entity'),('Ownership Discovery','ownership'),('Graph Analytics','graph'),('Machine Learning','ml'),('Financial Crime Risk','risk'),('Investigation Recommendations','recommendations'),('Final Reporting','report')]
    workflow=StateGraph(State)
    def node(name,key):
        def execute(state):
            started=time.monotonic()
            try:
                target=state['target_id']; status='completed'; evidence=[]
                if key=='entity':
                    entity=db.session.get(Entity,target)
                    if not entity: raise ValueError('Target entity no longer exists')
                    duplicates=db.session.query(Entity).filter(db.func.lower(Entity.entity_name)==entity.entity_name.lower(),Entity.id!=target).all()
                    data={**entity.to_dict(),'normalized_name':entity.entity_name.casefold(),'possible_duplicate_ids':[e.id for e in duplicates]}; evidence=[f'SRC-{entity.source_id}']
                elif key=='ownership':
                    data=ownership(target); evidence=data['evidence']; status='manual_review' if data['gaps'] else 'completed'
                    from .neo import ownership_paths
                    projection=ownership_paths(target,data['max_depth'],data['as_of'])
                    if projection['status']=='queried':
                        sql_paths={tuple(p['relationship_ids']) for p in data['paths']}
                        neo_paths={tuple(p['relationship_ids']) for p in projection['paths']}
                        projection['matches_sql']=sql_paths==neo_paths
                        if not projection['matches_sql']: status='manual_review'
                    data['graph_projection']=projection
                elif key=='graph': data=network(target); evidence=[r for f in data['findings'] for r in f['evidence']]
                elif key=='ml': data=predict(target); status='unavailable' if data['status']=='unavailable' else 'manual_review'
                elif key=='risk': data=assess(target,state['ownership'],state['graph']); evidence=state['ownership']['evidence']
                elif key=='recommendations': data={'actions':state['risk']['recommended_next_steps'],'missing_information':state['risk']['missing_information'],'human_approval_required':True}; status='manual_review'
                else:
                    data={'title':investigation.title,'summary':f"{state['entity']['entity_name']}: {len(state['ownership']['owners'])} upstream persons discovered; observed-indicator score {state['risk']['score']}/100 ({state['risk']['category']}).",'observed_facts':state['entity'],'ownership':state['ownership'],'algorithmic_indicators':state['graph']['findings'],'model_prediction':state['ml'],'risk':state['risk'],'recommendations':state['recommendations'],'analyst_judgments':[],'unverified_allegations':[],'human_approval_required':True,'llm_mode':'Evidence template; no external LLM invoked','version':'report-1.0'}
                    from .llm import summarize,facts_for
                    narrative=summarize(facts_for(state['ownership'],state['risk']))
                    data['narrative']=narrative;data['llm_mode']=narrative['mode']
                    if narrative['status']=='completed': data['summary']+=' '+' '.join(s['text'] for s in narrative['statements'])
                    evidence=state['ownership']['evidence']
                validated=STAGE_SCHEMAS[key].model_validate(data).model_dump(mode='json')
                output=AgentOutput(agent=name,status=status,data=validated,evidence=evidence)
                db.session.add(AgentLog(investigation_id=investigation.id,agent_name=name,status=status,input_summary={'target_id':target},output_summary=output.model_dump(mode='json'),execution_time=time.monotonic()-started,model_version=data.get('narrative',{}).get('model_version') or data.get('model_version') or 'deterministic-1.0',prompt_version='extractive-evidence-1.0' if key=='report' else 'evidence-template-1.0'))
                db.session.flush()
                return {key:output.data,'insufficient':key=='entity' and not data.get('source_id')}
            except Exception as exc:
                db.session.add(AgentLog(investigation_id=investigation.id,agent_name=name,status='failed',error_message=type(exc).__name__,execution_time=time.monotonic()-started))
                db.session.flush()
                raise
        return execute
    for name,key in stages: workflow.add_node('agent_'+key,node(name,key),retry=RetryPolicy(max_attempts=2))
    workflow.add_edge(START,'agent_entity')
    workflow.add_conditional_edges('agent_entity',lambda s:END if s.get('insufficient') else 'agent_ownership',[END,'agent_ownership'])
    for (_,a),(_,b) in zip(stages[1:],stages[2:]): workflow.add_edge('agent_'+a,'agent_'+b)
    workflow.add_edge('agent_report',END)
    # Bounded recursion; deterministic local stages. Network calls live outside the workflow.
    return workflow.compile().invoke({'investigation_id':investigation.id,'target_id':investigation.target_entity_id},config={'recursion_limit':20})
