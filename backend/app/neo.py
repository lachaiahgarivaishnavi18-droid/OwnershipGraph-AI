import os
from neo4j import GraphDatabase
from .engine import graph_data

ALLOWED={'OWNS','SHAREHOLDER_OF','CONTROLS','DIRECTOR_OF','BENEFICIARY_OF','TRUSTEE_OF','REGISTERED_AT','RELATED_TO'}

def ownership_paths(target,depth,as_of):
    uri=os.getenv('NEO4J_URI')
    if not uri: return {'status':'unavailable','backend':'SQL/NetworkX','reason':'Neo4j is not configured'}
    depth=int(depth)
    if not 1<=depth<=12: raise ValueError('Invalid graph traversal depth')
    query=f'''MATCH p=(owner:Entity)-[:OWNS|SHAREHOLDER_OF*1..{depth}]->(target:Entity {{id:$target}})
    WHERE owner.type='PERSON'
    AND all(r IN relationships(p) WHERE (r.valid_from IS NULL OR r.valid_from <= $as_of)
    AND (r.valid_to IS NULL OR r.valid_to >= $as_of))
    AND all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m.id=n.id))
    RETURN owner.id AS owner_id, [n IN nodes(p) | n.id] AS entity_ids,
    [r IN relationships(p) | r.id] AS relationship_ids LIMIT 10001'''
    try:
        with GraphDatabase.driver(uri,auth=(os.getenv('NEO4J_USER','neo4j'),os.getenv('NEO4J_PASSWORD')),connection_timeout=3) as driver:
            with driver.session() as session:
                from neo4j import Query
                paths=[dict(r) for r in session.run(Query(query,timeout=5),target=target,as_of=as_of)]
        return {'status':'queried','backend':'Neo4j','paths':paths[:10000],'truncated':len(paths)>10000}
    except Exception:
        return {'status':'unavailable','backend':'SQL/NetworkX','reason':'Neo4j query failed; SQL remains authoritative'}

def sync():
    uri=os.getenv('NEO4J_URI')
    if not uri: return {'status':'unavailable','reason':'NEO4J_URI is not configured; SQL/NetworkX demo is active'}
    entities,edges=graph_data()
    with GraphDatabase.driver(uri,auth=(os.getenv('NEO4J_USER','neo4j'),os.getenv('NEO4J_PASSWORD')),connection_timeout=5) as driver:
        def write(tx):
            tx.run('CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE').consume()
            for e in entities.values():
                label=e['entity_type']
                if label not in {'PERSON','COMPANY','TRUST','PARTNERSHIP','FOUNDATION','ADDRESS','DIRECTOR','JURISDICTION','OTHER'}: raise ValueError('Invalid graph label')
                tx.run(f'MERGE (e:Entity {{id:$id}}) SET e:{label}, e.name=$name, e.type=$type, e.jurisdiction=$jurisdiction',id=e['id'],name=e['entity_name'],type=label,jurisdiction=e['jurisdiction']).consume()
            # Projection exclusively owned by this application; replace edges atomically.
            tx.run('MATCH (:Entity)-[r]->(:Entity) WHERE r.managed_by = $owner DELETE r',owner='ownershipgraph').consume()
            for e in edges:
                kind=e['control_type']
                if kind not in ALLOWED: raise ValueError('Invalid relationship type')
                tx.run(f'MATCH (a:Entity {{id:$owner}}),(b:Entity {{id:$target}}) MERGE (a)-[r:{kind} {{id:$id}}]->(b) SET r += $props',owner=e['owner_entity_id'],target=e['owned_entity_id'],id=e['id'],props={**{k:v for k,v in e.items() if v is not None},'managed_by':'ownershipgraph'}).consume()
            return len(edges)
        with driver.session() as session: count=session.execute_write(write)
    return {'status':'synchronized','nodes':len(entities),'edges':count}
