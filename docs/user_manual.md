# Analyst manual

Use the active-entity selector to switch graph, ownership, analytics, risk and
assistant views. Entity discovery supports partial name/registration/ID search,
type/jurisdiction filters and pagination. Entity details disclose synthetic status,
source date and verification. Use corrected source imports and stable identifiers
to maintain records; full entity updates are available through the API.

Drag graph nodes, zoom, fit, search, filter, select a relationship for evidence,
collapse a node or expand all. Select a person in the inspector to highlight their
upstream economic paths. Orange edges indicate bounded circular links. Dashed
relationships include non-economic links. The graph legend identifies node types.

Beneficial ownership allows a temporal snapshot, depth limit and illustrative
threshold. Unknown percentages and ambiguous registers withhold combined totals.
Economic interest, voting/control and trust roles are not interchangeable.

Create a case and run the workflow to save a versioned assessment. The risk page
alone is a live preview. Notes are analyst judgments, not verified source facts.
An assigned independent reviewer must record an approval/rejection/change reason.
Reports preserve the assessment and reviewer status at generation time.

Import CSV or XLSX by selecting a file, validating, correcting reported rows and
then importing. Any error prevents the entire batch. source_id must already exist;
create source references using the authenticated evidence API. Sample files use
the synthetic demo source 1. API docs describe all fields.

Administrators control account creation and assessment configuration. Disabling
an account immediately blocks existing tokens. Logout revokes the current token.
JWTs expire after one hour. Never use synthetic records for real decisions.
