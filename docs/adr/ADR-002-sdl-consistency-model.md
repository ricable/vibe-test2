# ADR-002: Shared Data Layer (SDL) Consistency Model

## Status
Accepted

## Date
2026-01-26

## Context

The Near-RT RIC architecture relies on the Shared Data Layer (SDL) as the primary persistence mechanism for xApp state. The SDL enables stateless microservice design by externalizing state, but this introduces significant distributed systems challenges under the CAP theorem.

### Problem Statement

1. **Latency Requirements**: Near-RT RIC control loops operate in 10ms-1s range, requiring sub-millisecond data access
2. **Concurrent xApps**: Multiple xApps may read/write overlapping data (e.g., UE context, cell configuration)
3. **Failure Scenarios**: Network partitions between xApps and SDL, SDL node failures
4. **Consistency vs. Availability**: Trade-off decisions impact control loop correctness

### Key Questions

- What consistency guarantees does the SDL provide under partition?
- How do we handle concurrent updates to shared state?
- What happens when SDL is unavailable during a control decision?

### Drivers

- O-RAN-WG3-Near-RT-RIC-Architecture-v04.00 Section 6.3 (SDL)
- CAP Theorem (Brewer's Conjecture)
- PACELC Theorem extension
- Redis Cluster consistency model (reference implementation)

## Decision

We adopt a **tunable consistency model** for the SDL with the following configurations:

### Primary Consistency Mode: Eventual Consistency with Causal Ordering

**Rationale**: For the majority of xApp interactions, eventual consistency with causal ordering provides the best balance of performance and correctness.

```
┌──────────────────────────────────────────────────────────────────┐
│                     SDL Consistency Levels                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Level 1: EVENTUAL (Default)                                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ • Reads may return stale data                             │    │
│  │ • Writes are asynchronously replicated                    │    │
│  │ • Latency: < 1ms read, < 5ms write                       │    │
│  │ • Use case: Telemetry cache, statistics                   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Level 2: CAUSAL (Recommended for xApps)                         │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ • Causal ordering preserved within session                │    │
│  │ • Read-your-writes guarantee                              │    │
│  │ • Latency: < 2ms read, < 10ms write                      │    │
│  │ • Use case: UE context, xApp coordination                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Level 3: LINEARIZABLE (Critical Operations Only)                │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ • Strong consistency (appears sequential)                 │    │
│  │ • Requires quorum writes                                  │    │
│  │ • Latency: < 5ms read, < 20ms write                      │    │
│  │ • Use case: Conflict resolution, lock acquisition         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### SDL Data Categories and Consistency Mapping

| Data Category | Consistency Level | Rationale |
|--------------|-------------------|-----------|
| UE Context | CAUSAL | Multiple xApps may update; causal ordering prevents lost updates |
| E2 Subscription State | LINEARIZABLE | Critical for subscription lifecycle management |
| Telemetry Cache | EVENTUAL | High volume, staleness acceptable |
| xApp Configuration | LINEARIZABLE | Configuration changes must be atomic |
| Conflict Resolution State | LINEARIZABLE | Required for deterministic conflict resolution |
| KPI Aggregations | EVENTUAL | Statistical data tolerates minor inconsistency |

### Conflict Resolution Strategy

When concurrent updates occur to the same key:

```
┌─────────────────────────────────────────────────────────────────┐
│                 Optimistic Concurrency Control                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Read with Version                                           │
│     ┌─────────────────────────────────────────┐                 │
│     │ GET ue:12345 → {data: {...}, version: 7}│                 │
│     └─────────────────────────────────────────┘                 │
│                                                                  │
│  2. Modify and Write with Version Check                         │
│     ┌─────────────────────────────────────────┐                 │
│     │ SET ue:12345 {...} IF version == 7      │                 │
│     └─────────────────────────────────────────┘                 │
│                                                                  │
│  3. On Conflict (version mismatch)                              │
│     ┌─────────────────────────────────────────┐                 │
│     │ a) Retry with fresh read (default)      │                 │
│     │ b) Apply merge function (if registered) │                 │
│     │ c) Escalate to Conflict Mitigation      │                 │
│     └─────────────────────────────────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Failure Handling

**Scenario 1: SDL Partition (xApp cannot reach SDL)**

```
Decision: FAIL-SAFE
- xApp MUST NOT execute control actions if SDL read fails
- Cached state may be used for READ-ONLY decisions only
- Alarm raised: SDL_PARTITION_DETECTED
```

**Scenario 2: SDL Node Failure (partial cluster)**

```
Decision: CONTINUE WITH DEGRADED CONSISTENCY
- Remaining nodes handle requests
- Consistency may temporarily degrade to EVENTUAL
- Recovery triggers state reconciliation
```

**Scenario 3: Split-Brain**

```
Decision: REJECT WRITES, ALLOW READS
- Write operations fail with SPLIT_BRAIN error
- Read operations continue with stale data warning
- Manual intervention required for resolution
```

### SDL Interface Contract

```typescript
interface SDLService {
  // Basic operations with consistency control
  get<T>(namespace: string, key: string, options?: {
    consistency: 'EVENTUAL' | 'CAUSAL' | 'LINEARIZABLE'
  }): Promise<VersionedValue<T>>;

  set<T>(namespace: string, key: string, value: T, options?: {
    consistency: 'EVENTUAL' | 'CAUSAL' | 'LINEARIZABLE',
    expectedVersion?: number,  // For OCC
    ttl?: number               // Auto-expiry in seconds
  }): Promise<WriteResult>;

  // Atomic operations
  compareAndSet<T>(namespace: string, key: string,
    expected: T, newValue: T): Promise<boolean>;

  // Group operations (same consistency for all keys)
  getGroup<T>(namespace: string, keys: string[], options?: {
    consistency: 'EVENTUAL' | 'CAUSAL' | 'LINEARIZABLE'
  }): Promise<Map<string, VersionedValue<T>>>;

  // Subscription for reactive updates
  subscribe(namespace: string, pattern: string,
    callback: (event: SDLEvent) => void): Subscription;
}

interface VersionedValue<T> {
  value: T;
  version: number;
  timestamp: number;
  consistency: 'EVENTUAL' | 'CAUSAL' | 'LINEARIZABLE';
}
```

## Consequences

### Positive

- **Performance**: Tunable consistency allows optimization per use case
- **Correctness**: Critical operations protected by linearizable consistency
- **Resilience**: Clear failure handling prevents undefined behavior
- **Flexibility**: xApps can choose appropriate consistency level

### Negative

- **Complexity**: Developers must understand consistency trade-offs
- **Latency Variance**: Higher consistency = higher latency
- **Testing**: Need to test under various failure scenarios
- **Monitoring**: Requires observability into consistency level usage

### Implementation Notes

1. **Reference Implementation**: Redis Cluster with custom consistency layer
2. **Metrics to Track**:
   - SDL operation latency by consistency level
   - OCC retry rate
   - Partition detection events
   - Split-brain incidents

### Trade-off Analysis

```
                    Consistency vs. Availability vs. Latency

     LINEARIZABLE ─────┬─────────────────────────────────────────►
                       │                              High Latency
                       │                              Low Availability
                       │
         CAUSAL ───────┼─────────────────────────────────────────►
                       │                              Medium
                       │
       EVENTUAL ───────┼─────────────────────────────────────────►
                       │                              Low Latency
                       ▼                              High Availability
```

## Related ADRs

- ADR-001: O-RAN Bounded Context Architecture
- ADR-004: xApp Conflict Mitigation Strategy

## References

- O-RAN-WG3-Near-RT-RIC-Architecture-v04.00
- Brewer, E. "CAP Twelve Years Later"
- Kleppmann, M. "Designing Data-Intensive Applications"
- Redis Cluster Specification
