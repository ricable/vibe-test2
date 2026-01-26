# ADR-005: GenAI Integration via R1 Interface

## Status
Accepted

## Date
2026-01-26

## Context

The O-RAN Alliance has introduced the R1 interface to enable rApps in the Non-RT RIC to consume SMO services and provide advanced optimization capabilities. With the emergence of Generative AI (GenAI) technologies, there is significant opportunity to enhance rApp capabilities with LLM-based agents for intent translation, anomaly explanation, and predictive recommendations.

### Problem Statement

1. **Intent Complexity**: Business intents expressed in natural language need translation to A1 policies
2. **Explanation Gap**: Network operators need understandable explanations for AI-driven decisions
3. **Knowledge Integration**: GenAI agents require access to network context without direct database access
4. **Latency Constraints**: R1 operations must complete within reasonable timeframes (seconds, not milliseconds)
5. **Hallucination Risk**: GenAI outputs must be validated before affecting network operations

### Opportunity Areas for GenAI

```
┌─────────────────────────────────────────────────────────────────────┐
│                   GenAI Use Cases in O-RAN                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Intent Translation                                              │
│     "Optimize video streaming for the stadium area this weekend"    │
│     → Structured A1 Policy with QoS targets, geofence, time window  │
│                                                                      │
│  2. Anomaly Explanation                                             │
│     Input: Alarm cluster + PM data + topology                       │
│     Output: "Root cause appears to be fiber cut on backhaul link    │
│              to site X, affecting 12 cells"                         │
│                                                                      │
│  3. Configuration Recommendation                                    │
│     "What parameter changes would improve 5G coverage in downtown?" │
│     → Ranked list of actionable recommendations with trade-offs     │
│                                                                      │
│  4. Documentation Query                                             │
│     "What are the O-RAN requirements for xApp onboarding?"         │
│     → Synthesized answer from O-RAN specifications                  │
│                                                                      │
│  5. Predictive Guidance                                             │
│     "Forecast traffic for cell X during next major event"          │
│     → Time-series prediction with confidence intervals              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Drivers

- O-RAN-WG2-Non-RT-RIC-Architecture-v05.00 Section 8 (R1 Interface)
- O-RAN-WG2-R1-Interface-v02.00
- Anthropic Claude / OpenAI GPT-4 / Google Gemini capabilities
- Industry trends in AI-augmented network operations (AI/ML for Network 5.0)

## Decision

We adopt a **Tool-Augmented GenAI Agent Architecture** integrated via the R1 interface, with strict guardrails to ensure safety and reliability.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SMO / Non-RT RIC Platform                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                          R1 Interface Layer                            │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    R1 Service Catalog                            │  │  │
│  │  │  • Topology Query Service                                        │  │  │
│  │  │  • PM Data Access Service                                        │  │  │
│  │  │  • Alarm Management Service                                      │  │  │
│  │  │  • Policy Management Service                                     │  │  │
│  │  │  • AI/ML Model Catalog Service                                   │  │  │
│  │  │  • GenAI Agent Service (NEW)                                     │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                       GenAI Agent Framework                            │  │
│  │                                                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Intent    │  │   Anomaly   │  │   Config    │  │    Doc      │  │  │
│  │  │ Translator  │  │  Explainer  │  │ Recommender │  │   Query     │  │  │
│  │  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │  │
│  │         │                │                │                │         │  │
│  │         └────────────────┴────────────────┴────────────────┘         │  │
│  │                                   │                                   │  │
│  │                                   ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    Tool Orchestration Layer                      │ │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │ │  │
│  │  │  │ Topology │ │   PM     │ │  Alarm   │ │ Schema   │           │ │  │
│  │  │  │   Tool   │ │  Tool    │ │  Tool    │ │Validator │           │ │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                   │                                   │  │
│  │                                   ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │                      Guardrail Layer                             │ │  │
│  │  │  • Output validation (schema check, safety filter)              │ │  │
│  │  │  • Hallucination detection (grounding check)                    │ │  │
│  │  │  • Rate limiting (per-agent, per-user)                          │ │  │
│  │  │  • Audit logging (all inputs/outputs)                           │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### GenAI Agent Specifications

#### 1. Intent Translator Agent

**Purpose**: Convert natural language intents to structured A1 policies

```typescript
interface IntentTranslatorAgent {
  // Input: Natural language intent
  input: {
    naturalLanguageIntent: string;
    context?: {
      targetRegion?: GeoFence;
      timeWindow?: TimeRange;
      priorityHint?: 'LOW' | 'MEDIUM' | 'HIGH';
    };
  };

  // Output: Structured policy candidates
  output: {
    policies: Array<{
      policyTypeId: number;
      policyData: object;
      confidence: number;  // 0.0 - 1.0
      explanation: string;
    }>;
    clarificationQuestions?: string[];  // If intent is ambiguous
    warnings?: string[];  // Potential issues with the request
  };
}
```

**Example Flow**:

```
User Input: "Make sure our premium customers get the best 5G experience
             in the downtown area during business hours"

Agent Processing:
1. [Tool: TopologyQuery] Get cells in downtown area
2. [Tool: PMData] Analyze current QoS metrics for the area
3. [Tool: SchemaLookup] Retrieve QoS policy type schema
4. [LLM Reasoning] Map "premium customers" → QCI 1-4, high priority
5. [LLM Reasoning] Map "best experience" → latency < 10ms, throughput > 100Mbps
6. [LLM Generation] Generate A1 policy structure
7. [Tool: SchemaValidator] Validate generated policy

Output:
{
  "policies": [{
    "policyTypeId": 20001,
    "policyData": {
      "scope": {
        "qosClass": [1, 2, 3, 4],
        "geofence": { "type": "Polygon", "coordinates": [...] },
        "timeWindow": { "start": "08:00", "end": "18:00", "days": [1,2,3,4,5] }
      },
      "targets": {
        "latencyMs": { "max": 10 },
        "throughputMbps": { "min": 100 }
      }
    },
    "confidence": 0.87,
    "explanation": "Created QoS policy targeting premium QoS classes (QCI 1-4)
                    with strict latency and throughput targets for the
                    specified downtown area during weekday business hours."
  }],
  "warnings": [
    "Meeting 100 Mbps throughput target may require load balancing adjustments",
    "3 cells in the area currently show capacity constraints"
  ]
}
```

#### 2. Anomaly Explainer Agent

**Purpose**: Provide human-readable root cause analysis for network anomalies

```typescript
interface AnomalyExplainerAgent {
  input: {
    alarmIds: string[];
    timeRange: TimeRange;
    includeTopology: boolean;
    includePMData: boolean;
  };

  output: {
    summary: string;  // Executive summary
    rootCauses: Array<{
      cause: string;
      confidence: number;
      affectedElements: string[];
      evidence: string[];
    }>;
    recommendations: string[];
    relatedIncidents?: string[];  // From historical data
  };
}
```

#### 3. Configuration Recommender Agent

**Purpose**: Suggest parameter optimizations based on goals

```typescript
interface ConfigRecommenderAgent {
  input: {
    goal: string;  // Natural language goal
    scope: {
      cells?: string[];
      region?: GeoFence;
    };
    constraints?: {
      maxChanges?: number;
      excludeParameters?: string[];
    };
  };

  output: {
    recommendations: Array<{
      parameter: string;
      currentValue: any;
      recommendedValue: any;
      impact: string;
      confidence: number;
      reversible: boolean;
    }>;
    tradeoffs: string[];
    simulationResults?: object;  // If simulation available
  };
}
```

### Tool Definitions for Agents

```typescript
const genAITools = [
  {
    name: "topology_query",
    description: "Query network topology from TE&IV",
    parameters: {
      type: "object",
      properties: {
        entityType: { type: "string", enum: ["gNB", "Cell", "Sector"] },
        filters: { type: "object" },
        includeRelationships: { type: "boolean" }
      }
    }
  },
  {
    name: "pm_data_fetch",
    description: "Fetch performance measurement data",
    parameters: {
      type: "object",
      properties: {
        metrics: { type: "array", items: { type: "string" } },
        scope: { type: "object" },
        timeRange: { type: "object" },
        aggregation: { type: "string", enum: ["AVG", "MAX", "MIN", "SUM"] }
      }
    }
  },
  {
    name: "alarm_query",
    description: "Query active or historical alarms",
    parameters: {
      type: "object",
      properties: {
        severity: { type: "array", items: { type: "string" } },
        timeRange: { type: "object" },
        correlationId: { type: "string" }
      }
    }
  },
  {
    name: "policy_schema_lookup",
    description: "Get A1 policy type schema for policy generation",
    parameters: {
      type: "object",
      properties: {
        policyTypeId: { type: "integer" },
        includeExamples: { type: "boolean" }
      }
    }
  },
  {
    name: "validate_policy",
    description: "Validate a generated policy against its schema",
    parameters: {
      type: "object",
      properties: {
        policyTypeId: { type: "integer" },
        policyData: { type: "object" }
      }
    }
  },
  {
    name: "spec_search",
    description: "Search O-RAN and 3GPP specifications",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string" },
        documents: { type: "array", items: { type: "string" } }
      }
    }
  }
];
```

### Guardrail Implementation

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Guardrail Pipeline                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Stage 1: Input Sanitization                                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ • Prompt injection detection                                    │ │
│  │ • PII/sensitive data filtering                                  │ │
│  │ • Input length limits (prevent context overflow)                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                         │                                            │
│                         ▼                                            │
│  Stage 2: Tool Call Validation                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ • Tool whitelist enforcement                                    │ │
│  │ • Parameter bounds checking                                     │ │
│  │ • Rate limiting per tool (prevent DoS)                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                         │                                            │
│                         ▼                                            │
│  Stage 3: Output Validation                                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ • Schema validation for structured outputs                      │ │
│  │ • Grounding check (output must reference tool results)          │ │
│  │ • Safety filter (no harmful recommendations)                    │ │
│  │ • Confidence threshold enforcement                              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                         │                                            │
│                         ▼                                            │
│  Stage 4: Human Review (Optional)                                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ • If confidence < threshold → route to human                   │ │
│  │ • If output affects > N elements → require approval            │ │
│  │ • If flagged by safety filter → block + escalate               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### R1 API Extension for GenAI

```yaml
openapi: 3.0.3
info:
  title: R1 GenAI Agent Service
  version: 1.0.0

paths:
  /r1/genai/intent-translator:
    post:
      summary: Translate natural language intent to A1 policy
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IntentTranslatorRequest'
      responses:
        '200':
          description: Policy candidates generated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IntentTranslatorResponse'

  /r1/genai/anomaly-explainer:
    post:
      summary: Explain network anomalies
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AnomalyExplainerRequest'
      responses:
        '200':
          description: Anomaly explanation generated

  /r1/genai/config-recommender:
    post:
      summary: Get configuration recommendations
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ConfigRecommenderRequest'
      responses:
        '200':
          description: Recommendations generated
```

### Configuration

```yaml
genaiAgents:
  enabled: true

  provider:
    type: "anthropic"  # anthropic | openai | azure | local
    model: "claude-sonnet-4-20250514"
    apiKeySecret: "genai-api-key"

  rateLimit:
    requestsPerMinute: 60
    tokensPerMinute: 100000

  guardrails:
    inputMaxLength: 4000
    confidenceThreshold: 0.7
    humanReviewThreshold: 0.5
    maxAffectedElements: 100
    blockedPatterns:
      - "delete all"
      - "shutdown network"
      - "disable security"

  agents:
    intentTranslator:
      enabled: true
      maxPolicyCandidates: 3
    anomalyExplainer:
      enabled: true
      maxAlarms: 50
    configRecommender:
      enabled: true
      requireApproval: true

  audit:
    enabled: true
    logAllRequests: true
    retentionDays: 90
```

## Consequences

### Positive

- **Accessibility**: Natural language interface lowers barrier for network optimization
- **Explainability**: AI decisions become understandable to operators
- **Productivity**: Reduces time to translate business goals to technical policies
- **Knowledge Capture**: Documents decisions and reasoning for audit

### Negative

- **Latency**: GenAI calls add seconds to R1 operations
- **Cost**: API calls to external providers have associated costs
- **Reliability**: Depends on external API availability
- **Trust Calibration**: Users may over-trust or under-trust AI outputs

### Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Hallucination | Mandatory grounding check + tool-based verification |
| Prompt injection | Input sanitization + tool whitelist |
| Unsafe recommendations | Safety filter + human review for high-impact changes |
| API outage | Graceful degradation + fallback to manual policy creation |
| Data leakage | On-premise deployment option + PII filtering |

## Related ADRs

- ADR-001: O-RAN Bounded Context Architecture
- ADR-003: A1 Interface Policy Schema Validation
- ADR-006: GNN Integration for Topology Analysis

## References

- O-RAN-WG2-Non-RT-RIC-Architecture-v05.00
- O-RAN-WG2-R1-Interface-v02.00
- Anthropic Claude Documentation
- "LLMs for Network Operations" (IEEE ComMag 2024)
- NIST AI Risk Management Framework
