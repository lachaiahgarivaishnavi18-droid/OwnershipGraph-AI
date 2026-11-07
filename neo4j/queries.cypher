// Parameters: $target (SQL id), $as_of (ISO date). Economic interest only.
MATCH p=(owner:Entity)-[:OWNS|SHAREHOLDER_OF*1..8]->(target:Entity {id:$target})
WHERE owner.type = 'PERSON'
AND all(r IN relationships(p) WHERE
 (r.valid_from IS NULL OR r.valid_from <= $as_of) AND
 (r.valid_to IS NULL OR r.valid_to >= $as_of))
AND all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m.id=n.id))
RETURN owner.id, [n IN nodes(p) | n.id] AS entity_path,
 [r IN relationships(p) | r.id] AS relationship_ids,
 CASE WHEN all(r IN relationships(p) WHERE r.ownership_percentage IS NOT NULL)
 THEN reduce(interest=100.0,r IN relationships(p) | interest*r.ownership_percentage/100.0)
 ELSE null END AS path_estimate;

// Cycles bounded at twelve edges, no implication of wrongdoing.
MATCH p=(e:Entity)-[:OWNS|SHAREHOLDER_OF*1..12]->(e)
RETURN [n IN nodes(p) | n.id] AS cycle LIMIT 100;

MATCH (d:Entity)-[r:DIRECTOR_OF]->(company:Entity)
WITH d,collect(company.id) AS companies, collect(r.id) AS evidence
WHERE size(companies)>1 RETURN d.id,companies,evidence;
