# ADR-003: A1 Interface Policy Schema Validation

## Status
Accepted

## Date
2026-01-26

## Context

The A1 interface connects the Non-RT RIC to the Near-RT RIC, carrying policy directives that guide real-time control decisions. The interface must support diverse policy types (traffic steering, QoS management, energy efficiency) while maintaining strict schema validation to prevent runtime errors in the control plane.

### Problem Statement

1. **Policy Type Diversity**: O-RAN defines multiple policy types (A1-P, A1-EI), each with different schemas
2. **Schema Evolution**: Policy schemas must evolve without breaking existing deployments
3. **Validation Performance**: Schema validation must not add significant latency to policy delivery
4. **Error Handling**: Invalid policies must be rejected with actionable error messages
5. **Custom Policies**: Operators may define custom policy types beyond standard O-RAN types

### Current State

The A1 interface specification (O-RAN-WG2-A1-v05.00) defines:
- Policy Type registration endpoint
- Policy instance CRUD operations
- JSON Schema as the validation mechanism
- A1-P (Policy) and A1-EI (Enrichment Information) message types

### Drivers

- O-RAN-WG2-A1-v05.00 (A1 Interface Specification)
- O-RAN-WG2-A1-TD-R003-v05.00 (A1 Test and Design)
- JSON Schema Draft-07/2019-09
- OpenAPI Specification 3.0+

## Decision

We adopt a **layered schema validation strategy** with compile-time and runtime components:

### Schema Registry Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Non-RT RIC (Policy Source)                    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Policy Management Service                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │   Intent    │  │   Policy    │  │   Schema Registry   │   │  │
│  │  │  Translator │→ │  Generator  │→ │   (Source of Truth) │   │  │
│  │  └─────────────┘  └─────────────┘  └──────────┬──────────┘   │  │
│  └───────────────────────────────────────────────┼───────────────┘  │
└──────────────────────────────────────────────────┼──────────────────┘
                                                   │ Schema Sync (A1)
                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Near-RT RIC (Policy Consumer)                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    A1 Policy Handler                           │  │
│  │  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │ Schema Cache    │  │  Validator  │  │ Policy Enforcer │   │  │
│  │  │ (Local Replica) │→ │  (AJV/Fast) │→ │    (xApps)      │   │  │
│  │  └─────────────────┘  └─────────────┘  └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Policy Type Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    O-RAN Policy Type Taxonomy                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  A1-P (Policy Management)                                           │
│  ├── ORAN_TrafficSteeringPreference_2.0.0                          │
│  │   └── Scope: UE-level, Cell-level traffic steering              │
│  │                                                                  │
│  ├── ORAN_QoSTarget_1.0.0                                          │
│  │   └── Scope: QoS class optimization targets                     │
│  │                                                                  │
│  ├── ORAN_LoadBalancing_2.0.0                                      │
│  │   └── Scope: Inter-cell load distribution                       │
│  │                                                                  │
│  └── Custom_<Operator>_<Name>_<Version>                            │
│      └── Scope: Operator-specific policies                         │
│                                                                      │
│  A1-EI (Enrichment Information)                                     │
│  ├── EI_<TypeId>                                                   │
│  │   └── External enrichment data for xApp decisions               │
│  │                                                                  │
│  └── GeoLocation_1.0.0, TrafficPrediction_1.0.0, etc.             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Schema Validation Rules

#### 1. Policy Type Registration Validation

```json
{
  "$schema": "https://json-schema.org/draft/2019-09/schema",
  "$id": "urn:o-ran:a1:policy-type:meta-schema",
  "type": "object",
  "required": ["policyTypeId", "name", "description", "policyTypeSchema"],
  "properties": {
    "policyTypeId": {
      "type": "integer",
      "minimum": 1,
      "description": "Unique identifier for policy type"
    },
    "name": {
      "type": "string",
      "pattern": "^[A-Za-z][A-Za-z0-9_]*$"
    },
    "description": {
      "type": "string",
      "maxLength": 1024
    },
    "policyTypeSchema": {
      "$ref": "https://json-schema.org/draft/2019-09/schema"
    },
    "statusSchema": {
      "$ref": "https://json-schema.org/draft/2019-09/schema"
    }
  }
}
```

#### 2. Policy Instance Validation Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Policy Validation Pipeline                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Step 1: Structural Validation (Fast Path)                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • JSON syntax validation                                        │  │
│  │ • Required fields: policyId, policyTypeId, scope, policyData   │  │
│  │ • Type checking on envelope fields                              │  │
│  │ • Latency target: < 100μs                                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                              │                                        │
│                              ▼                                        │
│  Step 2: Schema Validation (Cached Schemas)                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Lookup PolicyType schema from cache                           │  │
│  │ • AJV compiled validator execution                              │  │
│  │ • Collect all validation errors (allErrors: true)               │  │
│  │ • Latency target: < 500μs                                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                              │                                        │
│                              ▼                                        │
│  Step 3: Semantic Validation (Business Rules)                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Scope validation (UE exists, Cell is managed)                 │  │
│  │ • Constraint feasibility (target values achievable)             │  │
│  │ • Conflict pre-check with existing policies                     │  │
│  │ • Latency target: < 5ms                                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                              │                                        │
│                              ▼                                        │
│  Step 4: Acceptance or Rejection                                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ • Store policy in SDL                                           │  │
│  │ • Notify subscribed xApps                                       │  │
│  │ • Return A1PolicyStatus: ENFORCED | NOT_ENFORCED | DELETED     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Schema Versioning Strategy

```
Version Format: <Major>.<Minor>.<Patch>

Major: Breaking changes (field removal, type change)
       → Requires new PolicyTypeId registration
       → Old and new versions can coexist

Minor: Backward-compatible additions (new optional fields)
       → Same PolicyTypeId, new schema version
       → Old policies remain valid

Patch: Bug fixes, description updates
       → No schema changes
       → Documentation only
```

### Error Response Format

```json
{
  "error": {
    "code": "POLICY_VALIDATION_FAILED",
    "message": "Policy instance failed schema validation",
    "details": [
      {
        "path": "/policyData/qosTarget/latencyMs",
        "keyword": "maximum",
        "message": "must be <= 100",
        "actual": 150,
        "expected": 100
      },
      {
        "path": "/scope/ueId",
        "keyword": "pattern",
        "message": "must match pattern '^[0-9]{15}$'",
        "actual": "invalid-ue",
        "expected": "IMSI format"
      }
    ],
    "policyTypeId": 20000,
    "policyId": "policy-123"
  }
}
```

### Example: Traffic Steering Policy Schema

```json
{
  "$schema": "https://json-schema.org/draft/2019-09/schema",
  "$id": "urn:o-ran:a1:policy-type:ORAN_TrafficSteeringPreference_2.0.0",
  "type": "object",
  "required": ["scope", "tspResources"],
  "properties": {
    "scope": {
      "type": "object",
      "oneOf": [
        {
          "required": ["ueId"],
          "properties": {
            "ueId": { "type": "string", "pattern": "^[0-9]{15}$" }
          }
        },
        {
          "required": ["sliceId"],
          "properties": {
            "sliceId": {
              "type": "object",
              "properties": {
                "sst": { "type": "integer", "minimum": 0, "maximum": 255 },
                "sd": { "type": "string", "pattern": "^[0-9A-Fa-f]{6}$" }
              }
            }
          }
        }
      ]
    },
    "tspResources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["cellIdList", "preference"],
        "properties": {
          "cellIdList": {
            "type": "array",
            "items": { "$ref": "#/$defs/cellId" },
            "minItems": 1
          },
          "preference": {
            "type": "string",
            "enum": ["SHALL", "PREFER", "AVOID", "FORBID"]
          }
        }
      }
    }
  },
  "$defs": {
    "cellId": {
      "type": "object",
      "required": ["plmnId", "cId"],
      "properties": {
        "plmnId": { "$ref": "#/$defs/plmnId" },
        "cId": { "type": "string", "pattern": "^[0-9A-Fa-f]{7,9}$" }
      }
    },
    "plmnId": {
      "type": "object",
      "required": ["mcc", "mnc"],
      "properties": {
        "mcc": { "type": "string", "pattern": "^[0-9]{3}$" },
        "mnc": { "type": "string", "pattern": "^[0-9]{2,3}$" }
      }
    }
  }
}
```

## Consequences

### Positive

- **Type Safety**: Policies validated before reaching xApps
- **Fast Validation**: Compiled schemas enable sub-millisecond validation
- **Clear Errors**: Structured error responses aid debugging
- **Extensibility**: Custom policy types supported via registry
- **Evolution**: Schema versioning enables backward compatibility

### Negative

- **Schema Maintenance**: Schemas must be kept in sync across RICs
- **Complexity**: Multiple validation layers add implementation complexity
- **Performance Overhead**: Semantic validation may add latency
- **Schema Drift**: Risk of cache invalidation issues

### Implementation Recommendations

1. **Use AJV (Another JSON Validator)** for JavaScript/TypeScript implementations
2. **Pre-compile schemas** at startup and cache compiled validators
3. **Implement schema caching** with TTL and invalidation on update
4. **Log validation failures** with full context for debugging
5. **Monitor validation latency** percentiles (p50, p95, p99)

## Related ADRs

- ADR-001: O-RAN Bounded Context Architecture
- ADR-004: xApp Conflict Mitigation Strategy

## References

- O-RAN-WG2-A1-v05.00 (A1 Interface Specification)
- JSON Schema Draft 2019-09
- AJV Documentation (https://ajv.js.org/)
- O-RAN Policy Type Catalog (O-RAN-WG2-A1-Catalog)
