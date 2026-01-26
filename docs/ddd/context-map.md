# O-RAN Domain-Driven Design Context Map

## Overview

This document describes the relationships between Bounded Contexts in the O-RAN architecture, following Strategic Domain-Driven Design principles. The context map identifies integration patterns, data ownership, and team collaboration models.

## Context Map Visualization

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    O-RAN Platform Context Map                                    │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│                                    ┌─────────────────────────────────────┐                      │
│                                    │         Shared Kernel               │                      │
│                                    │  • Timestamp, Duration, TimeRange   │                      │
│                                    │  • PLMNId, SNSSAI                   │                      │
│                                    │  • Domain Events Base               │                      │
│                                    │  • Result Types                     │                      │
│                                    └──────────────┬──────────────────────┘                      │
│                                                   │                                              │
│                    ┌──────────────────────────────┼──────────────────────────────┐              │
│                    │                              │                              │              │
│                    ▼                              ▼                              ▼              │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────────┐ │
│  │                             │  │                             │  │                         │ │
│  │   Network Inventory         │  │   Policy & Intent           │  │   Telemetry &          │ │
│  │   Context (TE&IV)           │  │   Context (Non-RT RIC)      │  │   Observability        │ │
│  │                             │  │                             │  │   Context              │ │
│  │  Generic Subdomain          │  │  Supporting Domain          │  │  Supporting Domain     │ │
│  │                             │  │                             │  │                         │ │
│  │  Owner: Platform Team       │  │  Owner: AI/ML Team          │  │  Owner: Observability  │ │
│  │                             │  │                             │  │          Team          │ │
│  └──────────┬──────────────────┘  └──────────┬──────────────────┘  └───────────┬─────────────┘ │
│             │                                │                                 │               │
│             │ Conformist                     │ Customer-Supplier               │ Published    │
│             │ (3GPP NRM)                     │ (A1 Interface)                  │ Language     │
│             │                                │                                 │ (VES/PM)     │
│             │                                │                                 │               │
│             ▼                                ▼                                 ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                                           │ │
│  │                           Real-Time Control Context                                      │ │
│  │                              (Near-RT RIC)                                               │ │
│  │                                                                                           │ │
│  │                            ★ CORE DOMAIN ★                                               │ │
│  │                                                                                           │ │
│  │                         Owner: RIC Platform Team                                         │ │
│  │                                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                        Internal Subcontexts                                          │ │ │
│  │  │                                                                                      │ │ │
│  │  │   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                        │ │ │
│  │  │   │   xApp       │     │   Conflict   │     │     SDL      │                        │ │ │
│  │  │   │   Runtime    │◄───►│  Mitigation  │◄───►│   Service    │                        │ │ │
│  │  │   └──────────────┘     └──────────────┘     └──────────────┘                        │ │ │
│  │  │          │                                                                           │ │ │
│  │  │          │ E2 Interface                                                              │ │ │
│  │  │          ▼                                                                           │ │ │
│  │  │   ┌──────────────┐                                                                   │ │ │
│  │  │   │  E2 Nodes    │                                                                   │ │ │
│  │  │   │ (O-CU/O-DU)  │                                                                   │ │ │
│  │  │   └──────────────┘                                                                   │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                                           │ │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Bounded Context Relationships

### 1. Network Inventory → All Contexts (CONFORMIST)

**Upstream**: Network Inventory Context (TE&IV)
**Downstream**: Real-Time Control, Policy & Intent, Telemetry

**Pattern**: Conformist

The Network Inventory Context exposes the 3GPP Network Resource Model (NRM) which all other contexts must conform to. There is no Anti-Corruption Layer; downstream contexts adopt the upstream model directly.

```typescript
// Network Inventory exposes the standard 3GPP DN format
interface NetworkInventoryContract {
  // All contexts use the same DN format
  getManagedElement(dn: DistinguishedName): Promise<ManagedElement>;
  getTopology(subNetworkDn: DistinguishedName): Promise<TopologyGraph>;
  getNeighborRelations(cellDn: DistinguishedName): Promise<NeighborRelation[]>;
}

// Downstream contexts adopt without transformation
class RealTimeControlTopologyAdapter implements TopologyProvider {
  constructor(private inventory: NetworkInventoryContract) {}

  async getCellNeighbors(cellDn: DistinguishedName): Promise<CellId[]> {
    // Direct usage of upstream model
    const relations = await this.inventory.getNeighborRelations(cellDn);
    return relations.map(r => r.targetCellNCI);
  }
}
```

**Integration Points**:
- O1 Interface (NETCONF/YANG)
- R1 Topology Query Service

### 2. Policy & Intent → Real-Time Control (CUSTOMER-SUPPLIER)

**Upstream (Supplier)**: Policy & Intent Context (Non-RT RIC)
**Downstream (Customer)**: Real-Time Control Context (Near-RT RIC)

**Pattern**: Customer-Supplier

The Policy & Intent Context defines PolicyType schemas that the Real-Time Control Context must implement. The customer (Near-RT RIC) can request features but must accept the supplier's priorities.

```typescript
// Supplier (Non-RT RIC) defines the contract
interface A1PolicyContract {
  // Policy Types defined by supplier
  getPolicyTypes(): Promise<PolicyType[]>;
  getPolicyType(id: PolicyTypeId): Promise<PolicyType>;

  // Policy instances
  getPolicies(typeId: PolicyTypeId): Promise<A1Policy[]>;
  getPolicy(id: PolicyId): Promise<A1Policy>;

  // Status reporting from customer
  reportPolicyStatus(id: PolicyId, status: PolicyStatus): Promise<void>;
}

// Customer (Near-RT RIC) implements enforcement
class PolicyEnforcementService {
  async enforcePolicy(policy: A1Policy): Promise<EnforcementResult> {
    // Validate against PolicyType schema
    const schema = await this.a1Client.getPolicyType(policy.policyTypeId);
    if (!this.validateSchema(policy.policyData, schema)) {
      return { success: false, reason: 'SCHEMA_VIOLATION' };
    }

    // Apply policy constraints to xApps
    await this.applyPolicyConstraints(policy);

    // Report status back to supplier
    await this.a1Client.reportPolicyStatus(policy.policyId, {
      enforced: true,
      timestamp: Timestamp.now()
    });

    return { success: true };
  }
}
```

**Integration Points**:
- A1 Interface (REST/JSON)
- Policy Type Registry

### 3. Real-Time Control → Telemetry (PUBLISHED LANGUAGE)

**Upstream (Publisher)**: Real-Time Control Context
**Downstream (Subscriber)**: Telemetry & Observability Context

**Pattern**: Published Language

The Real-Time Control Context publishes telemetry using standardized VES events and PM counter formats. The Telemetry Context subscribes without requiring tight coupling.

```typescript
// Published Language: VES Event Format
interface VESFaultEvent {
  commonEventHeader: {
    domain: 'fault';
    eventId: string;
    eventName: string;
    sourceName: string;
    reportingEntityName: string;
    startEpochMicrosec: number;
    lastEpochMicrosec: number;
  };
  faultFields: {
    alarmCondition: string;
    eventSeverity: string;
    specificProblem: string;
    vfStatus: string;
  };
}

// Publisher (Real-Time Control)
class E2TelemetryPublisher {
  async publishFault(alarm: E2Alarm): Promise<void> {
    const vesEvent: VESFaultEvent = this.transformToVES(alarm);
    await this.vesCollector.send(vesEvent);
  }

  private transformToVES(alarm: E2Alarm): VESFaultEvent {
    // Transform internal model to published language
    return {
      commonEventHeader: {
        domain: 'fault',
        eventId: alarm.id,
        eventName: `Fault_${alarm.type}`,
        sourceName: alarm.e2NodeId,
        reportingEntityName: this.ricId,
        startEpochMicrosec: alarm.timestamp.toEpochMs() * 1000,
        lastEpochMicrosec: Timestamp.now().toEpochMs() * 1000
      },
      faultFields: {
        alarmCondition: alarm.condition,
        eventSeverity: this.mapSeverity(alarm.severity),
        specificProblem: alarm.description,
        vfStatus: alarm.active ? 'Active' : 'Idle'
      }
    };
  }
}

// Subscriber (Telemetry Context)
class VESEventProcessor {
  async processVESBatch(events: VESEvent[]): Promise<void> {
    for (const event of events) {
      // Process according to published language schema
      switch (event.commonEventHeader.domain) {
        case 'fault':
          await this.processFault(event as VESFaultEvent);
          break;
        case 'measurement':
          await this.processMeasurement(event as VESMeasurementEvent);
          break;
        // ...
      }
    }
  }
}
```

**Integration Points**:
- VES Collector API
- PM File Transfer (SFTP/FTPS)

### 4. Telemetry → Policy & Intent (EVENT-DRIVEN)

**Upstream**: Telemetry & Observability Context
**Downstream**: Policy & Intent Context

**Pattern**: Event-Driven (via Published Language)

The Telemetry Context publishes KPI threshold breaches and alarm correlations that the Policy & Intent Context consumes for compliance monitoring and policy adjustment.

```typescript
// Event Types
interface KPIThresholdBreachEvent extends DomainEvent {
  eventType: 'KPIThresholdBreached';
  kpiId: string;
  scope: string;
  currentValue: number;
  threshold: number;
  thresholdLevel: 'WARNING' | 'MINOR' | 'MAJOR' | 'CRITICAL';
}

interface AlarmCorrelationEvent extends DomainEvent {
  eventType: 'AlarmCorrelated';
  correlationId: string;
  rootCauseAlarmId: string;
  affectedElements: string[];
  correlationScore: number;
}

// Consumer (Policy & Intent Context)
class ComplianceEventHandler {
  @EventHandler('KPIThresholdBreached')
  async onKPIThresholdBreach(event: KPIThresholdBreachEvent): Promise<void> {
    // Find policies that may be affected
    const affectedPolicies = await this.policyRepository
      .findByScope(event.scope);

    for (const policy of affectedPolicies) {
      // Update compliance status
      await this.complianceService.recordViolation(policy.policyId, {
        kpiId: event.kpiId,
        observedValue: event.currentValue,
        targetValue: event.threshold,
        timestamp: event.timestamp
      });
    }
  }
}
```

## Anti-Corruption Layers

### A1 Interface ACL (Near-RT RIC side)

```typescript
/**
 * Translates A1 wire format to internal domain model
 */
class A1InterfaceACL {
  // Inbound: A1 → Domain
  translatePolicyInstance(a1Policy: A1PolicyInstanceDTO): LocalPolicyConstraint {
    return {
      id: a1Policy.policyId,
      type: this.mapPolicyType(a1Policy.policyTypeId),
      scope: this.translateScope(a1Policy.scope),
      constraints: this.extractConstraints(a1Policy.policyData),
      priority: this.derivePriority(a1Policy),
      effectiveFrom: Timestamp.now(),
      effectiveUntil: a1Policy.ttl
        ? Timestamp.now().add(Duration.seconds(a1Policy.ttl))
        : undefined
    };
  }

  // Outbound: Domain → A1
  translatePolicyStatus(enforcement: EnforcementResult): A1PolicyStatusDTO {
    return {
      enforced: enforcement.success,
      reason: enforcement.reason,
      timestamp: enforcement.timestamp.toISO()
    };
  }

  private translateScope(a1Scope: any): ControlScope {
    // Transform A1 scope format to internal format
    if (a1Scope.ueId) {
      return { type: 'UE', identifiers: [a1Scope.ueId] };
    }
    if (a1Scope.cellIds) {
      return { type: 'CELL', identifiers: a1Scope.cellIds };
    }
    if (a1Scope.sliceId) {
      return {
        type: 'SLICE',
        identifiers: [`${a1Scope.sliceId.sst}-${a1Scope.sliceId.sd || ''}`]
      };
    }
    return { type: 'NETWORK', identifiers: [] };
  }
}
```

### E2 Interface ACL

```typescript
/**
 * Translates between E2AP messages and domain model
 */
class E2InterfaceACL {
  // Inbound: E2AP Indication → Domain Event
  translateIndication(indication: E2APIndication): DomainEvent[] {
    const events: DomainEvent[] = [];

    // Decode ASN.1 payload based on RAN function
    const decoded = this.e2smDecoder.decode(
      indication.ranFunctionId,
      indication.ricIndicationMessage
    );

    // Transform to domain events
    switch (indication.indicationType) {
      case E2IndicationType.REPORT:
        events.push(this.translateReport(decoded));
        break;
      case E2IndicationType.INSERT:
        events.push(this.translateInsert(decoded));
        break;
    }

    return events;
  }

  // Outbound: Domain → E2AP Control Request
  translateControlAction(action: ControlAction): E2APControlRequest {
    return {
      ricRequestId: {
        ricRequestorId: this.ricId,
        ricInstanceId: action.correlationId
      },
      ranFunctionId: action.ranFunctionId,
      ricCallProcessId: action.callProcessId,
      ricControlHeader: this.e2smEncoder.encodeHeader(action),
      ricControlMessage: this.e2smEncoder.encodeMessage(action.actionPayload),
      ricControlAckRequest: E2AckRequest.ACK
    };
  }
}
```

### O1 Interface ACL (Network Inventory)

```typescript
/**
 * Translates between NETCONF/YANG and domain model
 */
class O1InterfaceACL {
  // Inbound: NETCONF → Domain
  translateNetconfResponse(response: NetconfGetConfigResponse): ManagedElement {
    const data = this.yangParser.parse(response.data);

    return {
      dn: new DistinguishedName(data['dn']),
      managedElementId: data['id'],
      elementType: this.mapElementType(data['class']),
      vendorName: data['vendorName'],
      swVersion: data['swVersion'],
      administrativeState: this.mapAdminState(data['administrativeState']),
      operationalState: this.mapOpState(data['operationalState']),
      usageState: this.mapUsageState(data['usageState']),
      attributes: this.flattenAttributes(data),
      lastConfigSync: Timestamp.now()
    };
  }

  // Outbound: Domain → NETCONF
  translateToEditConfig(
    element: ManagedElement,
    changes: ConfigurationChange[]
  ): NetconfEditConfigRequest {
    const yangData = this.buildYangPayload(element.dn, changes);

    return {
      target: 'running',
      defaultOperation: 'merge',
      testOption: 'test-then-set',
      config: yangData
    };
  }
}
```

## Integration Patterns Summary

| Source Context | Target Context | Pattern | Protocol | Data Format |
|---------------|----------------|---------|----------|-------------|
| Network Inventory | Real-Time Control | Conformist | O1/NETCONF | YANG/XML |
| Network Inventory | Policy & Intent | Conformist | R1/REST | JSON |
| Network Inventory | Telemetry | Conformist | O1/NETCONF | YANG/XML |
| Policy & Intent | Real-Time Control | Customer-Supplier | A1/REST | JSON |
| Real-Time Control | Telemetry | Published Language | VES/HTTP | JSON |
| Telemetry | Policy & Intent | Event-Driven | Kafka | Avro/JSON |
| Real-Time Control | E2 Nodes | ACL | E2AP/SCTP | ASN.1 |

## Team Collaboration Model

### Team Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Team Organization                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    RIC Platform Team                                       │  │
│  │                                                                             │  │
│  │  Responsibilities:                                                          │  │
│  │  • Real-Time Control Context (Core Domain)                                  │  │
│  │  • SDL Service                                                              │  │
│  │  • E2 Interface implementation                                              │  │
│  │  • xApp Framework and SDK                                                   │  │
│  │  • Conflict Mitigation Handler                                              │  │
│  │                                                                             │  │
│  │  Collaborates with: AI/ML Team (A1 interface), Platform Team (O1)          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    AI/ML Team                                              │  │
│  │                                                                             │  │
│  │  Responsibilities:                                                          │  │
│  │  • Policy & Intent Context                                                  │  │
│  │  • Intent Translation (including GenAI integration)                         │  │
│  │  • rApp Framework                                                           │  │
│  │  • ML Model Catalog                                                         │  │
│  │  • GNN Training Pipelines                                                   │  │
│  │                                                                             │  │
│  │  Collaborates with: RIC Platform Team (A1), Observability Team (KPI)       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    Platform Team                                           │  │
│  │                                                                             │  │
│  │  Responsibilities:                                                          │  │
│  │  • Network Inventory Context (TE&IV)                                        │  │
│  │  • O1 Interface (NETCONF Gateway)                                           │  │
│  │  • Configuration Management                                                  │  │
│  │  • Topology Database (RuVector)                                             │  │
│  │                                                                             │  │
│  │  Collaborates with: All teams (provides topology data)                      │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    Observability Team                                      │  │
│  │                                                                             │  │
│  │  Responsibilities:                                                          │  │
│  │  • Telemetry & Observability Context                                        │  │
│  │  • VES Collector                                                            │  │
│  │  • PM File Collection                                                       │  │
│  │  • Alarm Management                                                         │  │
│  │  • KPI Calculation Engine                                                   │  │
│  │                                                                             │  │
│  │  Collaborates with: AI/ML Team (KPI threshold events)                      │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Communication Channels

| Teams | Mechanism | Frequency | Topics |
|-------|-----------|-----------|--------|
| RIC Platform ↔ AI/ML | API Contract Review | Bi-weekly | A1 schema changes, policy types |
| RIC Platform ↔ Platform | Sync Meeting | Weekly | O1 model updates, topology changes |
| AI/ML ↔ Observability | Event Schema Review | Monthly | KPI definitions, threshold events |
| All Teams | Architecture Forum | Monthly | Cross-cutting concerns, ADR reviews |

## Evolution Guidelines

### Adding New Bounded Contexts

1. Identify the subdomain type (Core, Supporting, Generic)
2. Define the Ubiquitous Language
3. Map relationships to existing contexts
4. Choose appropriate integration patterns
5. Design Anti-Corruption Layers where needed
6. Document in this context map

### Changing Integration Patterns

1. Assess impact on downstream contexts
2. Version the interface (semantic versioning)
3. Communicate changes through Architecture Forum
4. Implement changes behind feature flags
5. Provide migration period for downstream teams
6. Update ADRs and this context map

### Shared Kernel Changes

1. Require consensus from all consuming teams
2. Document breaking changes
3. Version independently from contexts
4. Provide backward compatibility for 2 versions
5. Schedule deprecation of old versions
