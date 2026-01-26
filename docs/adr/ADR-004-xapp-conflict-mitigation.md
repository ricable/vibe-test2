# ADR-004: xApp Conflict Mitigation Strategy

## Status
Accepted

## Date
2026-01-26

## Context

The Near-RT RIC hosts multiple xApps that may independently decide on control actions for overlapping scopes (same UE, same cell, same slice). Without explicit coordination, these xApps may issue conflicting control requests, leading to oscillation, suboptimal performance, or network instability.

### Problem Statement

1. **Concurrent Decisions**: Multiple xApps may evaluate the same UE/cell state simultaneously
2. **Contradictory Actions**: Traffic Steering xApp wants to handover UE to Cell A, Load Balancing xApp wants to keep UE in Cell B
3. **Priority Ambiguity**: No inherent ordering between xApps for conflict resolution
4. **Latency Sensitivity**: Conflict resolution must not exceed Near-RT loop budget (10ms-1s)
5. **Fairness**: Resolution should not systematically favor one xApp over another

### Types of Conflicts

```
┌─────────────────────────────────────────────────────────────────────┐
│                     xApp Conflict Taxonomy                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Type 1: Direct Action Conflict                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ xApp A: HANDOVER UE-123 → Cell-X                               │ │
│  │ xApp B: HANDOVER UE-123 → Cell-Y                               │ │
│  │ Nature: Mutually exclusive actions on same target              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Type 2: Resource Contention Conflict                               │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ xApp A: Allocate 50 PRBs to Slice-1                            │ │
│  │ xApp B: Allocate 60 PRBs to Slice-2                            │ │
│  │ Total PRBs available: 100                                       │ │
│  │ Nature: Combined demand exceeds capacity                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Type 3: Parameter Conflict                                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ xApp A: Set CIO of Cell-X = +3dB                               │ │
│  │ xApp B: Set CIO of Cell-X = -2dB                               │ │
│  │ Nature: Different values for same parameter                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Type 4: Goal Conflict                                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ xApp A: Minimize Energy (reduce cell power)                    │ │
│  │ xApp B: Maximize Throughput (increase cell power)              │ │
│  │ Nature: Opposing optimization objectives                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Drivers

- O-RAN-WG3-Near-RT-RIC-Architecture-v04.00 Section 7 (Conflict Mitigation)
- O-RAN-WG3-CM-v01.00 (Conflict Mitigation Specification)
- Research: "Machine Learning for Conflict Resolution in O-RAN" (IEEE)
- Multi-Agent Systems Theory

## Decision

We implement a **hierarchical conflict mitigation framework** with three resolution layers:

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Conflict Mitigation Architecture                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      xApp Layer                                   │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │   │
│  │  │ xApp A  │  │ xApp B  │  │ xApp C  │  │ xApp N  │             │   │
│  │  │ (TS)    │  │ (LB)    │  │ (QoS)   │  │  (...)  │             │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘             │   │
│  │       │            │            │            │                    │   │
│  │       └────────────┴────────────┴────────────┘                    │   │
│  │                          │                                        │   │
│  │                          ▼                                        │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │              Conflict Mitigation Handler (CMH)            │    │   │
│  │  │  ┌────────────────────────────────────────────────────┐  │    │   │
│  │  │  │ Layer 1: Pre-Emptive Avoidance                     │  │    │   │
│  │  │  │ • Scope locking (advisory)                         │  │    │   │
│  │  │  │ • Intent declaration                               │  │    │   │
│  │  │  └────────────────────────────────────────────────────┘  │    │   │
│  │  │  ┌────────────────────────────────────────────────────┐  │    │   │
│  │  │  │ Layer 2: Reactive Detection                        │  │    │   │
│  │  │  │ • Action queue inspection                          │  │    │   │
│  │  │  │ • Semantic conflict analysis                       │  │    │   │
│  │  │  └────────────────────────────────────────────────────┘  │    │   │
│  │  │  ┌────────────────────────────────────────────────────┐  │    │   │
│  │  │  │ Layer 3: Resolution & Arbitration                  │  │    │   │
│  │  │  │ • Priority-based selection                         │  │    │   │
│  │  │  │ • ML-based optimization                            │  │    │   │
│  │  │  │ • Human escalation (if configured)                 │  │    │   │
│  │  │  └────────────────────────────────────────────────────┘  │    │   │
│  │  └──────────────────────────────────────────────────────────┘    │   │
│  │                          │                                        │   │
│  │                          ▼                                        │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │                    E2 Termination                         │    │   │
│  │  │         (Resolved actions sent to E2 Nodes)               │    │   │
│  │  └──────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Pre-Emptive Avoidance

**Mechanism**: xApps declare intent before executing actions

```typescript
interface IntentDeclaration {
  xAppId: string;
  timestamp: number;
  targetScope: {
    type: 'UE' | 'CELL' | 'SLICE';
    identifiers: string[];
  };
  intendedAction: {
    type: string;  // e.g., 'HANDOVER', 'PRB_ALLOCATION'
    parameters: Record<string, any>;
  };
  priority: number;  // 1-100, derived from A1 Policy or xApp config
  ttl: number;       // milliseconds until intent expires
}

// CMH Response
interface IntentResponse {
  status: 'GRANTED' | 'QUEUED' | 'DENIED';
  conflictingIntents?: IntentDeclaration[];
  suggestedDelay?: number;  // milliseconds
}
```

**Algorithm**:
1. xApp submits IntentDeclaration to CMH
2. CMH checks SDL for overlapping active intents
3. If no conflict: GRANT and record intent in SDL
4. If conflict with lower priority: GRANT, notify other xApp
5. If conflict with equal/higher priority: QUEUE or DENY

### Layer 2: Reactive Detection

**Mechanism**: Inspect action queue before E2 transmission

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Conflict Detection Algorithm                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Input: ActionQueue = [A1, A2, ..., An] (ordered by submission)     │
│                                                                      │
│  For each pair (Ai, Aj) where i < j:                                │
│    1. Scope Overlap Check                                           │
│       IF Ai.scope ∩ Aj.scope ≠ ∅ THEN continue ELSE skip           │
│                                                                      │
│    2. Action Compatibility Check                                     │
│       MATCH (Ai.type, Aj.type):                                     │
│         (HANDOVER, HANDOVER) → CONFLICT if different targets        │
│         (PRB_ALLOC, PRB_ALLOC) → CONFLICT if sum > capacity         │
│         (PARAM_SET, PARAM_SET) → CONFLICT if different values       │
│         _ → NO_CONFLICT (orthogonal actions)                        │
│                                                                      │
│    3. If CONFLICT detected:                                         │
│       - Record conflict pair in ConflictRegistry                    │
│       - Trigger Layer 3 resolution                                   │
│                                                                      │
│  Output: ConflictSet = {(Ai, Aj, conflict_type), ...}              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 3: Resolution & Arbitration

**Resolution Strategies** (configurable per deployment):

#### Strategy 1: Priority-Based (Default)

```
Resolution Rule:
  IF priority(Ai) > priority(Aj):
    ACCEPT Ai, REJECT Aj
  ELIF priority(Ai) == priority(Aj):
    ACCEPT older action (FIFO)
  ELSE:
    ACCEPT Aj, REJECT Ai

Priority Sources:
  1. A1 Policy priority (highest precedence)
  2. xApp static priority (configured at onboarding)
  3. Action urgency score (computed from telemetry)
```

#### Strategy 2: ML-Based Optimization

```python
# Simplified ML conflict resolution model
class ConflictResolver:
    def resolve(self, actions: List[Action], state: NetworkState) -> Action:
        """
        Use trained model to select optimal action considering:
        - Current network state
        - Historical outcomes of similar conflicts
        - A1 policy objectives (reward shaping)
        """
        features = self.extract_features(actions, state)
        q_values = self.model.predict(features)
        return actions[np.argmax(q_values)]
```

#### Strategy 3: Merge/Negotiate

```
For Parameter Conflicts:
  Merged Value = weighted_average(
    value_A * priority_A,
    value_B * priority_B
  ) / (priority_A + priority_B)

For Resource Contention:
  Proportional Allocation:
    alloc_A = demand_A * (capacity / total_demand)
    alloc_B = demand_B * (capacity / total_demand)
```

### Conflict Resolution State Machine

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ ACCEPTED │   │ REJECTED │   │  MERGED  │
    └────┬─────┘   └────┬─────┘   └────┬─────┘
         │              │              │
         │              │              │
         ▼              ▼              ▼
    ┌──────────────────────────────────────┐
    │              EXECUTED                 │
    │  (Action sent to E2 / Feedback sent  │
    │   to rejected xApp)                   │
    └──────────────────────────────────────┘
```

### Configuration Schema

```yaml
conflictMitigation:
  enabled: true

  preEmptive:
    enabled: true
    intentTTL: 5000  # ms
    maxQueuedIntents: 100

  detection:
    queueInspectionInterval: 10  # ms
    scopeOverlapThreshold: 0.8  # percentage

  resolution:
    strategy: "PRIORITY"  # PRIORITY | ML_BASED | MERGE
    defaultPriority: 50
    tieBreaker: "FIFO"  # FIFO | RANDOM | ML

  ml:
    enabled: false
    modelPath: "/models/conflict_resolver.onnx"
    retrainInterval: 86400  # seconds

  escalation:
    enabled: true
    maxRetries: 3
    escalateToNonRT: true
    humanInLoopThreshold: 5  # consecutive unresolved conflicts
```

### API for xApps

```typescript
interface ConflictMitigationAPI {
  // Pre-emptive layer
  declareIntent(intent: IntentDeclaration): Promise<IntentResponse>;
  withdrawIntent(intentId: string): Promise<void>;

  // Query conflicts
  getActiveConflicts(xAppId: string): Promise<Conflict[]>;
  getConflictHistory(scope: Scope, since: number): Promise<ConflictRecord[]>;

  // Callbacks
  onConflictResolved(callback: (resolution: Resolution) => void): void;
  onActionRejected(callback: (rejection: Rejection) => void): void;
}
```

## Consequences

### Positive

- **Deterministic Resolution**: Clear rules prevent oscillation
- **Fairness**: Priority system balances xApp objectives
- **Extensibility**: ML strategy allows learning from outcomes
- **Observability**: Conflict history enables analysis and optimization
- **A1 Alignment**: Policy priorities propagate to conflict resolution

### Negative

- **Latency Overhead**: Conflict detection adds ~1-5ms per action
- **Complexity**: Three-layer architecture increases implementation effort
- **Configuration Burden**: Priority assignment requires domain expertise
- **ML Risk**: ML-based resolution may make unexpected decisions

### Metrics to Monitor

1. **Conflict Rate**: conflicts/second by type and scope
2. **Resolution Latency**: p50, p95, p99 of resolution time
3. **Rejection Rate**: percentage of actions rejected per xApp
4. **Oscillation Detection**: repeated conflict-resolution cycles on same scope
5. **A1 Compliance**: percentage of resolutions aligned with A1 policy priorities

## Related ADRs

- ADR-001: O-RAN Bounded Context Architecture
- ADR-002: Shared Data Layer Consistency Model
- ADR-005: GenAI Integration via R1 Interface

## References

- O-RAN-WG3-Near-RT-RIC-Architecture-v04.00
- O-RAN-WG3-CM-v01.00 (Conflict Mitigation)
- "Multi-Agent Reinforcement Learning for RAN Control" (IEEE TNSM 2024)
- "Game-Theoretic Approaches to xApp Coordination" (ACM MobiCom 2023)
