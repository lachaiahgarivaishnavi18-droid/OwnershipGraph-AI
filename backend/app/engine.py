"""Deterministic, evidence-linked graph calculations. No LLM calculations."""
from collections import defaultdict, Counter
from itertools import islice
from datetime import date
import networkx as nx
from .models import db, Entity, Relationship, Setting
from .schemas import DEFAULT_SETTINGS

ECONOMIC = {'OWNS','SHAREHOLDER_OF'}

def settings():
    row=db.session.get(Setting,'risk')
    return row.value if row else DEFAULT_SETTINGS

def graph_data(as_of=None):
    as_of=as_of or date.today().isoformat()
    entities={e.id:e.to_dict() for e in db.session.query(Entity).all()}
    edges=[r.to_dict() for r in db.session.query(Relationship).all() if (not r.valid_from or r.valid_from<=as_of) and (not r.valid_to or r.valid_to>=as_of)]
    return entities,edges

def ownership(target,depth=None,threshold=None,as_of=None):
    cfg=settings(); entities,edges=graph_data(as_of)
    if target not in entities: raise ValueError('Entity not found')
    depth=depth or cfg['max_depth']
    threshold=threshold if threshold is not None else cfg['jurisdiction_thresholds'].get(entities[target]['jurisdiction'],cfg['ubo_threshold'])
    incoming=defaultdict(list)
    for edge in edges:
        if edge['control_type'] in ECONOMIC: incoming[edge['owned_entity_id']].append(edge)
    paths=[]; issues=[]; seen_issues=set(); visited=set(); steps=[0]
    def issue(kind,node,refs,description):
        refs=refs or [f"ENTITY-{node} / SRC-{entities[node]['source_id']}"]
        key=(kind,node,tuple(refs))
        if key not in seen_issues:
            seen_issues.add(key); issues.append({'kind':kind,'entity_id':node,'evidence':refs,'description':description})
    def walk(node,chain,rels,factor,confidence):
        steps[0]+=1
        if steps[0]>10000:
            issue('traversal_budget',node,[],'Traversal exceeded 10,000 steps; results are incomplete and require a narrower graph')
            return
        visited.add(node)
        owners=incoming[node]
        if entities[node]['entity_type'] in {'PERSON','DIRECTOR'} and node!=target:
            paths.append({'owner_id':node,'entity_ids':list(reversed(chain)),'relationship_ids':list(reversed([e['id'] for e in rels])),'depth':len(rels),'attributable_percentage':round(factor*100,6) if factor is not None else None,'confidence':confidence,'evidence':[f"REL-{e['id']} / SRC-{e['source_id']}" for e in rels]})
            return
        if not owners:
            issue('unresolved_terminal',node,[], 'No upstream natural-person ownership record is available')
            return
        if len(rels)>=depth:
            issue('depth_limit',node,[],f'Traversal stopped at configured depth {depth}')
            return
        counts=Counter(e['owner_entity_id'] for e in owners)
        total=sum(e['ownership_percentage'] or 0 for e in owners)
        refs=[f"REL-{e['id']}" for e in owners]
        if total>100.000001: issue('overallocated',node,refs,f'Active economic percentages total {total}%')
        if total<99.999999: issue('ownership_gap',node,refs,f'{round(100-total,4)}% of the share register is unaccounted for or unspecified')
        for e in owners:
            owner=e['owner_entity_id']; pct=e['ownership_percentage']
            if counts[owner]>1: issue('conflicting_records',node,[f"REL-{x['id']}" for x in owners if x['owner_entity_id']==owner], 'Multiple active economic records for the same owner and target; no aggregation')
            if pct is None: issue('missing_percentage',node,[f"REL-{e['id']}"], 'Economic ownership percentage is unknown')
            if e['verification_status']=='Disputed': issue('disputed_record',node,[f"REL-{e['id']}"],'Relationship is disputed')
            if owner in chain:
                issue('cycle',node,[f"REL-{x['id']}" for x in rels+[e]],'Circular ownership; simple-path results do not resolve cross-holdings')
                continue
            walk(owner,chain+[owner],rels+[e],None if factor is None or pct is None else factor*pct/100,min(confidence,e['confidence']))
    walk(target,[target],[],1.0,1.0)
    unsafe=any(i['kind'] in {'cycle','conflicting_records','overallocated','missing_percentage','disputed_record','traversal_budget'} for i in issues)
    grouped=defaultdict(list)
    for p in paths: grouped[p['owner_id']].append(p)
    owners=[]
    for owner,ps in grouped.items():
        direct=sum(p['attributable_percentage'] or 0 for p in ps if p['depth']==1)
        indirect=sum(p['attributable_percentage'] or 0 for p in ps if p['depth']>1)
        combined=None if unsafe else round(direct+indirect,6)
        owners.append({'entity_id':owner,'name':entities[owner]['entity_name'],'direct_percentage':None if unsafe else direct,'indirect_percentage':None if unsafe else indirect,'path_estimate_percentage':round(direct+indirect,6),'combined_percentage':combined,'potential_ubo':combined is not None and combined>=threshold,'confidence':min(p['confidence'] for p in ps),'paths':ps})
    return {'target_id':target,'as_of':as_of or date.today().isoformat(),'threshold':threshold,'threshold_is_illustrative':True,'max_depth':depth,'owners':sorted(owners,key=lambda o:-o['path_estimate_percentage']),'direct_relationships':[e for e in edges if e['owned_entity_id']==target and e['control_type'] in ECONOMIC],'paths':paths,'gaps':issues,'aggregation_withheld':unsafe,'complete':not issues,'control_indicators':[e for e in edges if e['owned_entity_id'] in visited and e['control_type'] not in ECONOMIC],'evidence':[f"REL-{e['id']} / SRC-{e['source_id']}" for e in edges if e['owned_entity_id'] in visited],'disclaimer':'Potential UBO candidates require jurisdiction-specific legal and analyst review. Path estimates are not verified ownership determinations.'}

def network(target):
    entities,edges=graph_data(); g=nx.DiGraph(); g.add_nodes_from(entities)
    for e in edges:
        if e['control_type'] in ECONOMIC: g.add_edge(e['owner_entity_id'],e['owned_entity_id'])
    # Restrict analytics to the connected ownership component, avoiding unrelated findings.
    component=nx.node_connected_component(g.to_undirected(),target)
    sub=g.subgraph(component).copy()
    cycles=list(islice(nx.simple_cycles(sub,length_bound=12),100))
    degree=nx.degree_centrality(sub); between=nx.betweenness_centrality(sub)
    # Pure Python PageRank avoids requiring SciPy in the lightweight demo.
    rank={n:1/len(sub) for n in sub}
    for _ in range(60):
        dangling=sum(rank[n] for n in sub if sub.out_degree(n)==0)/len(sub)
        rank={n:0.15/len(sub)+0.85*(dangling+sum(rank[p]/sub.out_degree(p) for p in sub.predecessors(n))) for n in sub}
    undirected=sub.to_undirected()
    communities=list(nx.community.greedy_modularity_communities(undirected)) if sub.number_of_edges() else [set(sub)]
    related=[e for e in edges if e['owner_entity_id'] in component or e['owned_entity_id'] in component]
    shared=[]
    for kind in ['DIRECTOR_OF','REGISTERED_AT']:
        groups=defaultdict(list)
        for e in related:
            if e['control_type']==kind:
                key=e['owner_entity_id'] if kind=='DIRECTOR_OF' else e['owned_entity_id']
                groups[key].append(e)
        for node,es in groups.items():
            if len(es)>=2: shared.append({'type':kind,'entity_id':node,'count':len(es),'evidence':[f"REL-{e['id']} / SRC-{e['source_id']}" for e in es]})
    own=ownership(target)
    findings=[]
    def finding(kind,description,severity,evidence,ids):
        findings.append({'indicator_name':kind,'description':description,'severity':severity,'confidence':0.8,'evidence':evidence,'relevant_entities':ids,'review_action':'Verify current registers and supporting documents with an authorized source.'})
    for c in cycles:
        es=[e for e in edges if e['control_type'] in ECONOMIC and e['owner_entity_id'] in c and e['owned_entity_id'] in c]
        finding('Circular ownership','A directed ownership cycle is present. Cross-holdings need reconciliation.','High',[f"REL-{e['id']}" for e in es],c)
    for s in shared: finding('Shared director' if s['type']=='DIRECTOR_OF' else 'Common address',f"Shared link across {s['count']} records; this may have a legitimate explanation.",'Medium',s['evidence'],[s['entity_id']])
    for gap in own['gaps']: finding(gap['kind'].replace('_',' ').title(),gap['description'],'Medium',gap['evidence'],[gap['entity_id']])
    max_depth=max([p['depth'] for p in own['paths']]+[0])
    if max_depth>=4: finding('Deep ownership chain',f'At least {max_depth} ownership layers observed.','Medium',own['evidence'],list(component))
    displayed=component | {e[k] for e in related for k in ['owner_entity_id','owned_entity_id']}
    return {'nodes':[entities[n] for n in displayed],'edges':related,'cycles':cycles,'cycle_search_limit':{'length':12,'results':100},'metrics':[{'entity_id':n,'name':entities[n]['entity_name'],'degree_centrality':degree[n],'betweenness':between[n],'pagerank':rank[n]} for n in sub],'communities':[sorted(c) for c in communities],'connected_components':nx.number_weakly_connected_components(g),'max_depth':max_depth,'shared_connections':shared,'findings':findings,'concentration':sum((e['ownership_percentage']/100)**2 for e in edges if e['owned_entity_id']==target and e['control_type'] in ECONOMIC and e['ownership_percentage'] is not None),'cross_jurisdiction_links':sum(entities[e['owner_entity_id']]['jurisdiction']!=entities[e['owned_entity_id']]['jurisdiction'] for e in related if e['control_type'] in ECONOMIC)}

def assess(target,own=None,net=None):
    own=own or ownership(target); net=net or network(target); cfg=settings()
    gaps=own['gaps']
    vals={'opacity':min(100,25*len([g for g in gaps if g['kind'] in {'missing_percentage','ownership_gap','unresolved_terminal'}])), 'complexity':min(100,max(0,net['max_depth']-1)*20), 'jurisdiction':None,'screening':None,'network':min(100,len(net['cycles'])*60+len(net['shared_connections'])*15),'inconsistency':min(100,50*len([g for g in gaps if g['kind'] in {'conflicting_records','overallocated','disputed_record'}])),'changes':None}
    indicators=[{'name':k,'score':v,'weight':cfg['weights'][k],'contribution':round((v or 0)*cfg['weights'][k]/100,4),'available':v is not None,'evidence':own['evidence'] if k in {'opacity','complexity','inconsistency'} else [r for f in net['findings'] for r in f['evidence']],'explanation':{'opacity':'Incomplete share registers and unknown upstream owners.','complexity':'Observed upstream layers beyond the direct shareholder.','jurisdiction':'No maintained dated jurisdiction reference connected.','screening':'Sanctions, PEP and adverse-media sources are not connected.','network':'Cycles and shared director/address links; legitimate explanations may exist.','inconsistency':'Conflicting, disputed or overallocated active ownership records.','changes':'No validated historical comparison baseline available.'}[k]} for k,v in vals.items()]
    score=round(sum(i['contribution'] for i in indicators),2)
    category=['Low','Medium','High','Critical'][sum(score>=x for x in cfg['categories'])]
    coverage=sum(i['weight'] for i in indicators if i['available'])
    return {'score':score,'category':category,'indicators':indicators,'version':cfg['version'],'data_completeness':coverage,'confidence':round(max(0,coverage/100*(0.85-min(0.5,len(gaps)*0.05))),2),'missing_information':[i['explanation'] for i in indicators if not i['available']]+[g['description'] for g in gaps],'screening_status':'Not connected','score_interpretation':'Partial observed-indicator score. Unavailable indicators contribute zero without weight renormalization; a low score does not establish low risk.','recommended_next_steps':['Request current shareholder registers and corroborating source documents.','Reconcile unknown percentages and upstream legal-entity owners.','Obtain analyst review before any adverse or external decision.'],'disclaimer':'Indicators support investigation; they are not evidence of criminal activity or a probability of wrongdoing.'}
