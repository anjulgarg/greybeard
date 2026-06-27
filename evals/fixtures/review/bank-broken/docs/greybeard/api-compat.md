# API Compatibility (broken fixture)

Each entry below is missing a required part so the Tier 0 linter must flag it.

### B1. Pin the serializer settings on the public client
Default serializer settings drift between framework versions and silently change
wire output, so we pin them explicitly on the public client.

- evidence-type: code-checkable
- confidence: very-high
- evidence:
  - PR 6001 - "pin the JSON settings, the upgrade reordered keys"

### B2. The search index is rebuilt nightly by the Data team
The product search index is owned and rebuilt by the Data team on a nightly job, so
schema changes must be coordinated with them.

**Future benefit:** A future engineer changing the indexed document shape will know
to coordinate with the Data team's nightly rebuild instead of assuming it is local.

**Application check:** Before changing the indexed document schema, confirm the Data
team's nightly job is updated to match.

- evidence-type: human-attested
- confidence: low
- evidence:
  - attested by data-lead - "Data team owns the nightly search rebuild"

### B3. Always paginate list endpoints
Unbounded list endpoints fall over once a tenant grows large, so every list endpoint
must paginate from day one.

**Future benefit:** A future engineer adding a list endpoint will paginate up front
instead of retrofitting it after a large tenant degrades the service.

**Application check:** Every new list endpoint must accept page/limit parameters and
cap the maximum page size.

- evidence-type: code-checkable
- confidence: high
