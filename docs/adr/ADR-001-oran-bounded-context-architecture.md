# ADR-001: O-RAN Bounded Context Architecture

## Status
Accepted

## Date
2026-01-26

## Context

The O-RAN Alliance specification defines a disaggregated RAN architecture comprising multiple functional components (SMO, Non-RT RIC, Near-RT RIC, O-CU, O-DU, O-RU) connected through standardized interfaces (O1, O2, A1, E2, Open FH). Translating this architectural vision into a maintainable software system requires careful application of Domain-Driven Design principles.

### Problem Statement

The O-RAN ecosystem presents several architectural challenges:

1. **Distributed Complexity**: Multiple autonomous components with different latency requirements (sub-10ms for Near-RT RIC, >1s for Non-RT RIC)
2. **Domain Entanglement**: Risk of creating a "Big Ball of Mud" where policy management, real-time control, inventory, and telemetry concerns become entangled
3. **Model Integrity**: Each O-RAN component has its own data model (E2SM for E2, A1 Policy Types for A1, 3GPP NRM for O1)
4. **Team Autonomy**: Different teams may own different RIC components, requiring clear boundaries

### Drivers

- O-RAN-WG1-Architecture-Description-v07.00
- O-RAN-WG2-Non-RT-RIC-Architecture-v05.00
- O-RAN-WG3-Near-RT-RIC-Architecture-v04.00
- 3GPP TS 28.541 (NRM Model)
- Domain-Driven Design principles (Eric Evans, Vaughn Vernon)

## Decision

We will decompose the O-RAN solution into **four primary Bounded Contexts**, each with explicit boundaries, ubiquitous language, and ownership:

### 1. Real-Time Control Context (Near-RT RIC)

**Responsibility**: Optimization of radio resources with 10ms-1s control loops

**Key Aggregates**:
- `UEContext` - Root aggregate for User Equipment state
- `E2Subscription` - Manages telemetry stream lifecycle
- `ControlAction` - Represents actions sent to E2 Nodes

**Domain Events**:
- `UEContextEstablished`
- `HandoverTriggered`
- `ControlActionExecuted`
- `ConflictDetected`

**Invariants**:
- A Control Action MUST NOT violate active A1 Policy constraints
- E2 Subscriptions MUST be associated with valid xApp instances
- UE Context state transitions MUST follow 3GPP state machine

### 2. Policy and Intent Context (Non-RT RIC)

**Responsibility**: Translation of business intent to technical constraints (>1s loops)

**Key Aggregates**:
- `Intent` - High-level business goal (e.g., "Maximize Energy Efficiency")
- `A1Policy` - Technical policy derived from intent
- `rAppInstance` - Lifecycle of rApp deployments

**Domain Events**:
- `IntentCreated`
- `PolicyDerived`
- `PolicyEnforced`
- `ComplianceViolation`

**Invariants**:
- An A1 Policy MUST be derived from a valid Intent
- Policy Types MUST be registered before policy instances are created
- rApps MUST have valid R1 interface bindings

### 3. Network Inventory Context (TE&IV/SMO)

**Responsibility**: Source of truth for network topology and configuration

**Key Aggregates**:
- `ManagedElement` - Network function representation (gNB, O-CU, O-DU)
- `TopologyGraph` - Relationships between network elements
- `ConfigurationItem` - Configuration state of network elements

**Domain Events**:
- `NodeDiscovered`
- `TopologySynchronized`
- `ConfigurationDriftDetected`
- `RelationshipUpdated`

**Invariants**:
- ManagedElement identifiers MUST be globally unique (DN format)
- Topology changes MUST be versioned for audit
- Configuration MUST conform to 3GPP NRM schema

### 4. Telemetry and Observability Context

**Responsibility**: Ingestion and processing of network telemetry data

**Key Aggregates**:
- `MeasurementJob` - PM collection configuration
- `Alarm` - Fault management entity
- `KPIDefinition` - KPI calculation rules

**Domain Events**:
- `VESEventReceived`
- `PMFileCollected`
- `AlarmRaised`
- `AlarmCleared`
- `KPIThresholdBreached`

**Invariants**:
- Alarms MUST follow X.733 alarm model
- PM data MUST be timestamped with collection interval
- VES events MUST conform to VES schema version

## Context Mapping

### Relationships Between Contexts

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SMO Framework                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │ Network Inventory│    │    Policy &     │    │   Telemetry &   │     │
│  │    Context      │    │  Intent Context │    │  Observability  │     │
│  │   (TE&IV)       │    │  (Non-RT RIC)   │    │    Context      │     │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘     │
│           │                      │                      │               │
│           │ Conformist           │ Customer-Supplier    │ Published    │
│           │                      │                      │ Language     │
└───────────┼──────────────────────┼──────────────────────┼───────────────┘
            │                      │ A1 Interface         │
            │ O1 Interface         │                      │ VES/PM
            │                      ▼                      │
┌───────────┴──────────────────────────────────────────────┴───────────────┐
│                        Near-RT RIC Platform                              │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │              Real-Time Control Context                               │ │
│  │                                                                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐│ │
│  │  │ xApp 1   │  │ xApp 2   │  │ xApp N   │  │        SDL           ││ │
│  │  │(Traffic) │  │(Handover)│  │ (QoS)    │  │ (Shared Data Layer)  ││ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────────────┘│ │
│  │       │             │             │                                 │ │
│  │       └─────────────┴─────────────┘                                 │ │
│  │                     │                                               │ │
│  └─────────────────────┼───────────────────────────────────────────────┘ │
└─────────────────────────┼────────────────────────────────────────────────┘
                          │ E2 Interface
                          ▼
              ┌───────────────────────┐
              │       E2 Nodes        │
              │   (O-CU, O-DU, O-RU)  │
              └───────────────────────┘
```

### Integration Patterns

| Source Context | Target Context | Pattern | Interface |
|---------------|----------------|---------|-----------|
| Policy & Intent | Real-Time Control | Customer-Supplier | A1 |
| Real-Time Control | Telemetry | Published Language | Internal |
| Network Inventory | All | Conformist | O1/NETCONF |
| Telemetry | Policy & Intent | Event-Driven | VES |

## Consequences

### Positive

- **Clear Boundaries**: Each context has explicit transactional boundaries
- **Team Autonomy**: Teams can own and evolve their contexts independently
- **Model Integrity**: Each context maintains its own ubiquitous language
- **Scalability**: Contexts can be scaled independently based on load
- **Technology Freedom**: Each context can choose appropriate persistence and messaging technologies

### Negative

- **Integration Complexity**: Anti-corruption layers needed at context boundaries
- **Data Duplication**: Some data may be replicated across contexts
- **Eventual Consistency**: Cross-context operations require saga patterns
- **Learning Curve**: Teams must understand DDD patterns and O-RAN domain

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Context creep | Regular domain model reviews |
| Tight coupling | Enforce interface contracts via CI/CD |
| Stale models | Automated schema validation |

## Related ADRs

- ADR-002: Shared Data Layer Consistency Model
- ADR-003: A1 Interface Policy Schema Validation
- ADR-004: xApp Conflict Mitigation Strategy

## References

- O-RAN Alliance WG1/WG2/WG3 Specifications
- Eric Evans, "Domain-Driven Design: Tackling Complexity in the Heart of Software"
- Vaughn Vernon, "Implementing Domain-Driven Design"
- 3GPP TS 28.541 (Network Resource Model)
