// All names and relationships are synthetic academic demonstration data.
MERGE (p:Entity:PERSON {id:4}) SET p.name='Elena Vale',p.type='PERSON',p.synthetic=true;
MERGE (h:Entity:COMPANY {id:2}) SET h.name='Northstar Holdings',h.type='COMPANY',h.synthetic=true;
MERGE (t:Entity:COMPANY {id:1}) SET t.name='Aster Maritime Group',t.type='COMPANY',t.synthetic=true;
MATCH (p:Entity {id:4}),(h:Entity {id:2}),(t:Entity {id:1})
MERGE (p)-[a:OWNS {id:4}]->(h) SET a.ownership_percentage=60,a.source_id=1,a.synthetic=true
MERGE (h)-[b:OWNS {id:1}]->(t) SET b.ownership_percentage=60,b.source_id=1,b.synthetic=true;
