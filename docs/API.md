# API Reference

## Base URLs

- **Development:** http://localhost:8000  
- **Production:** https://your-domain.com

## Authentication

If enabled, include a bearer token:

```
Authorization: Bearer <AI_SERVICE_TOKEN>
```

## Endpoints

### GET /health

**Purpose:** Health check.

**Response:**
```json
{ "status": "healthy" }
```

---

### POST /run-graph

**Purpose:** Execute a LangGraph agent.

**Request body:**
```json
{
  "graph": "matching",
  "input": { "..." : "..." }
}
```

**Response:**
```json
{
  "success": true,
  "graph": "matching",
  "data": { "..." : "..." },
  "error": null
}
```

**Supported graphs:**
- matching
- safety
- onboarding
- events_communities

#### Example: Matching

```json
{
  "graph": "matching",
  "input": {
    "user_id": "test-user-123",
    "tenant_id": "university-1",
    "preferences": { "radiusMeters": 200000, "minScore": 30 }
  }
}
```

#### Example: Safety

```json
{
  "graph": "safety",
  "input": {
    "user_id": "test-user-123",
    "content": "Hello, let's be friends!",
    "content_type": "message"
  }
}
```

#### Example: Onboarding

```json
{
  "graph": "onboarding",
  "input": {
    "user_id": "test-user-123",
    "tenant_id": "university-1",
    "form_data": { "major": "Computer Science", "interests": ["AI"] }
  }
}
```

#### Example: Events & Communities

```json
{
  "graph": "events_communities",
  "input": {
    "user_id": "test-user-123",
    "tenant_id": "university-1",
    "interests": ["AI", "Startups"],
    "location": { "lat": 37.77, "lng": -122.42 }
  }
}
```

---

### GET /docs

**Purpose:** Interactive Swagger UI.

---

### GET /openapi.json

**Purpose:** OpenAPI schema.

---

## Error Codes

- **400** — Invalid input or graph name
- **401** — Missing or invalid bearer token
- **500** — Internal server error
- **504** — Graph execution timeout

## Rate Limiting

No built-in rate limiting by default. Add at the edge (API gateway, load balancer) if needed.
