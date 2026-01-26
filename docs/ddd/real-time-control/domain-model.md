# Real-Time Control Context - Domain Model

## Context Overview

The Real-Time Control Context is the **Core Domain** of the Near-RT RIC platform. It is responsible for optimizing radio resources through control loops executing in the 10ms to 1s latency range. This context hosts xApps that consume E2 telemetry and issue control actions to E2 Nodes.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **xApp** | A microservice application running on the Near-RT RIC that implements specific RAN optimization logic |
| **E2 Node** | A RAN function (O-CU, O-DU) that exposes the E2 interface for telemetry and control |
| **E2 Subscription** | An agreement between an xApp and E2 Node to receive periodic or event-triggered telemetry |
| **Control Action** | A command issued by an xApp to modify E2 Node behavior (handover, PRB allocation, parameter change) |
| **UE Context** | The aggregated state of a User Equipment including connection state, QoS flows, and measurement configuration |
| **Conflict** | A situation where multiple xApps issue contradictory control actions for overlapping scopes |
| **SDL** | Shared Data Layer - the distributed key-value store for xApp state |

## Aggregates

### 1. UEContext (Aggregate Root)

The `UEContext` aggregate represents the complete state of a User Equipment as observed and managed by the Near-RT RIC.

```typescript
// Aggregate Root
interface UEContext {
  // Identity
  ueId: RNTI;                    // Value Object
  imsi?: IMSI;                   // Value Object (optional, privacy)

  // Connection State
  connectionState: UEConnectionState;  // Entity
  servingCell: CellId;           // Value Object
  handoverCandidates: CellId[];  // Value Objects

  // QoS Configuration
  bearers: Bearer[];             // Entities
  qosFlows: QoSFlow[];           // Entities

  // Measurement Configuration
  measurementConfig: MeasurementConfig;  // Entity

  // Metadata
  version: number;               // For optimistic concurrency
  lastUpdated: Timestamp;
}

// Invariants:
// 1. A UE MUST have exactly one serving cell when in RRC_CONNECTED state
// 2. handoverCandidates MUST NOT include the serving cell
// 3. Bearer IDs MUST be unique within the UE context
// 4. QoS flow 5QI values MUST be valid (1-255)
```

#### Entities within UEContext

```typescript
interface Bearer {
  bearerId: number;
  type: 'DRB' | 'SRB';
  qosFlowIds: number[];
  pdcpConfig: PDCPConfig;
}

interface QoSFlow {
  qosFlowId: number;
  fiveQI: number;
  arpPriority: number;
  gbrParams?: GBRParameters;
}

interface MeasurementConfig {
  configId: string;
  reportType: 'PERIODIC' | 'EVENT_TRIGGERED';
  triggerQuantity: 'RSRP' | 'RSRQ' | 'SINR';
  reportInterval?: number;      // ms, for periodic
  eventConfig?: MeasurementEvent;
}
```

#### Value Objects

```typescript
// RNTI - Radio Network Temporary Identifier
class RNTI {
  private readonly value: number;

  constructor(value: number) {
    if (value < 0 || value > 65535) {
      throw new InvalidRNTIError(value);
    }
    this.value = value;
  }

  equals(other: RNTI): boolean {
    return this.value === other.value;
  }
}

// CellId - Global Cell Identity
class CellId {
  readonly plmnId: PLMNId;
  readonly nrCellId: string;  // 36-bit as hex

  constructor(plmnId: PLMNId, nrCellId: string) {
    if (!this.isValidNRCellId(nrCellId)) {
      throw new InvalidCellIdError(nrCellId);
    }
    this.plmnId = plmnId;
    this.nrCellId = nrCellId;
  }

  private isValidNRCellId(id: string): boolean {
    return /^[0-9A-Fa-f]{9}$/.test(id);
  }

  toString(): string {
    return `${this.plmnId.toString()}-${this.nrCellId}`;
  }
}

// PLMNId - Public Land Mobile Network Identity
class PLMNId {
  readonly mcc: string;  // 3 digits
  readonly mnc: string;  // 2-3 digits

  constructor(mcc: string, mnc: string) {
    if (!/^\d{3}$/.test(mcc)) throw new InvalidMCCError(mcc);
    if (!/^\d{2,3}$/.test(mnc)) throw new InvalidMNCError(mnc);
    this.mcc = mcc;
    this.mnc = mnc;
  }
}
```

### 2. E2Subscription (Aggregate Root)

Manages the lifecycle of telemetry subscriptions between xApps and E2 Nodes.

```typescript
interface E2Subscription {
  // Identity
  subscriptionId: SubscriptionId;
  requestId: E2RequestId;        // Unique per xApp-E2Node pair

  // Ownership
  xAppId: XAppId;
  e2NodeId: E2NodeId;

  // Subscription Details
  ranFunctionId: number;
  actionType: 'REPORT' | 'INSERT' | 'POLICY';
  eventTriggerDefinition: Buffer;  // ASN.1 encoded
  actionDefinitions: ActionDefinition[];

  // State
  state: SubscriptionState;
  subsequentActionRequired: boolean;

  // Lifecycle timestamps
  createdAt: Timestamp;
  confirmedAt?: Timestamp;
  deletedAt?: Timestamp;
}

enum SubscriptionState {
  PENDING = 'PENDING',
  ACTIVE = 'ACTIVE',
  FAILED = 'FAILED',
  DELETING = 'DELETING',
  DELETED = 'DELETED'
}

// Invariants:
// 1. A subscription MUST transition through states in order: PENDING -> ACTIVE or FAILED
// 2. Only ACTIVE subscriptions can transition to DELETING
// 3. ranFunctionId MUST be supported by the target E2 Node
// 4. One xApp MUST NOT have duplicate subscriptions for same (e2NodeId, ranFunctionId, eventTrigger)
```

### 3. ControlAction (Aggregate Root)

Represents a control command issued by an xApp to an E2 Node.

```typescript
interface ControlAction {
  // Identity
  actionId: ControlActionId;
  correlationId: string;         // For tracing across xApps

  // Source
  xAppId: XAppId;
  priority: number;              // 1-100, from A1 policy

  // Target
  e2NodeId: E2NodeId;
  ranFunctionId: number;
  scope: ControlScope;

  // Action Details
  actionType: ControlActionType;
  actionPayload: Buffer;         // E2SM-encoded

  // State Machine
  state: ControlActionState;
  conflictResolution?: ConflictResolution;

  // Timing
  requestedAt: Timestamp;
  executedAt?: Timestamp;
  timeToLive: number;            // ms
}

interface ControlScope {
  type: 'UE' | 'CELL' | 'SLICE' | 'BEARER';
  identifiers: string[];
}

enum ControlActionType {
  HANDOVER = 'HANDOVER',
  PRB_ALLOCATION = 'PRB_ALLOCATION',
  POWER_CONTROL = 'POWER_CONTROL',
  PARAMETER_UPDATE = 'PARAMETER_UPDATE',
  BEARER_MODIFICATION = 'BEARER_MODIFICATION'
}

enum ControlActionState {
  PENDING = 'PENDING',           // Created, not yet sent
  CONFLICTING = 'CONFLICTING',   // In conflict resolution
  APPROVED = 'APPROVED',         // Cleared by CMH
  SENT = 'SENT',                 // Sent to E2 Node
  ACKNOWLEDGED = 'ACKNOWLEDGED', // ACK received
  FAILED = 'FAILED',             // NACK or timeout
  REJECTED = 'REJECTED'          // Rejected by CMH
}

// Invariants:
// 1. An action MUST have a valid scope matching its actionType
// 2. Priority MUST be derived from the governing A1 Policy
// 3. TTL MUST be within Near-RT bounds (10ms - 1s)
// 4. State transitions MUST follow the defined state machine
```

## Domain Events

```typescript
// UE Context Events
interface UEContextEstablished {
  eventType: 'UEContextEstablished';
  ueId: RNTI;
  servingCell: CellId;
  timestamp: Timestamp;
}

interface UEContextReleased {
  eventType: 'UEContextReleased';
  ueId: RNTI;
  cause: ReleaseCase;
  timestamp: Timestamp;
}

interface HandoverTriggered {
  eventType: 'HandoverTriggered';
  ueId: RNTI;
  sourceCell: CellId;
  targetCell: CellId;
  triggerReason: string;
  xAppId: XAppId;
  timestamp: Timestamp;
}

// E2 Subscription Events
interface SubscriptionCreated {
  eventType: 'SubscriptionCreated';
  subscriptionId: SubscriptionId;
  xAppId: XAppId;
  e2NodeId: E2NodeId;
  timestamp: Timestamp;
}

interface SubscriptionConfirmed {
  eventType: 'SubscriptionConfirmed';
  subscriptionId: SubscriptionId;
  timestamp: Timestamp;
}

interface SubscriptionFailed {
  eventType: 'SubscriptionFailed';
  subscriptionId: SubscriptionId;
  cause: string;
  timestamp: Timestamp;
}

// Control Action Events
interface ControlActionRequested {
  eventType: 'ControlActionRequested';
  actionId: ControlActionId;
  xAppId: XAppId;
  actionType: ControlActionType;
  scope: ControlScope;
  timestamp: Timestamp;
}

interface ControlActionExecuted {
  eventType: 'ControlActionExecuted';
  actionId: ControlActionId;
  executionLatency: number;      // ms
  timestamp: Timestamp;
}

interface ConflictDetected {
  eventType: 'ConflictDetected';
  conflictId: string;
  actions: ControlActionId[];
  conflictType: string;
  timestamp: Timestamp;
}

interface ConflictResolved {
  eventType: 'ConflictResolved';
  conflictId: string;
  resolution: 'ACCEPTED' | 'REJECTED' | 'MERGED';
  winnerId?: ControlActionId;
  timestamp: Timestamp;
}
```

## Domain Services

### E2SubscriptionService

```typescript
interface E2SubscriptionService {
  /**
   * Create a new E2 subscription for an xApp
   * @throws DuplicateSubscriptionError if equivalent subscription exists
   * @throws UnsupportedRANFunctionError if E2 Node doesn't support function
   */
  createSubscription(
    xAppId: XAppId,
    e2NodeId: E2NodeId,
    ranFunctionId: number,
    eventTrigger: EventTriggerDefinition,
    actions: ActionDefinition[]
  ): Promise<E2Subscription>;

  /**
   * Delete an existing subscription
   * @throws SubscriptionNotFoundError
   * @throws InvalidStateTransitionError if subscription not ACTIVE
   */
  deleteSubscription(subscriptionId: SubscriptionId): Promise<void>;

  /**
   * Process subscription confirmation from E2 Node
   */
  confirmSubscription(subscriptionId: SubscriptionId): Promise<void>;

  /**
   * Get all subscriptions for an xApp
   */
  getXAppSubscriptions(xAppId: XAppId): Promise<E2Subscription[]>;
}
```

### ControlActionService

```typescript
interface ControlActionService {
  /**
   * Submit a control action for execution
   * Action goes through conflict mitigation before reaching E2 Node
   */
  submitAction(
    xAppId: XAppId,
    actionType: ControlActionType,
    scope: ControlScope,
    payload: ControlPayload
  ): Promise<ControlAction>;

  /**
   * Query action status
   */
  getActionStatus(actionId: ControlActionId): Promise<ControlActionState>;

  /**
   * Cancel a pending action (if not yet sent)
   */
  cancelAction(actionId: ControlActionId): Promise<boolean>;
}
```

### UEContextService

```typescript
interface UEContextService {
  /**
   * Get current UE context (from SDL)
   */
  getUEContext(ueId: RNTI): Promise<UEContext | null>;

  /**
   * Update UE context with optimistic concurrency control
   * @throws ConcurrencyConflictError if version mismatch
   */
  updateUEContext(
    ueId: RNTI,
    expectedVersion: number,
    updates: Partial<UEContext>
  ): Promise<UEContext>;

  /**
   * Get UEs in a specific cell
   */
  getUEsInCell(cellId: CellId): Promise<UEContext[]>;

  /**
   * Get handover candidates for a UE
   */
  getHandoverCandidates(ueId: RNTI): Promise<CellId[]>;
}
```

## Repository Interfaces

```typescript
interface UEContextRepository {
  findById(ueId: RNTI): Promise<UEContext | null>;
  findByCell(cellId: CellId): Promise<UEContext[]>;
  save(context: UEContext): Promise<void>;
  delete(ueId: RNTI): Promise<void>;
}

interface E2SubscriptionRepository {
  findById(id: SubscriptionId): Promise<E2Subscription | null>;
  findByXApp(xAppId: XAppId): Promise<E2Subscription[]>;
  findByE2Node(e2NodeId: E2NodeId): Promise<E2Subscription[]>;
  save(subscription: E2Subscription): Promise<void>;
  delete(id: SubscriptionId): Promise<void>;
}

interface ControlActionRepository {
  findById(id: ControlActionId): Promise<ControlAction | null>;
  findPendingByScope(scope: ControlScope): Promise<ControlAction[]>;
  save(action: ControlAction): Promise<void>;
  updateState(id: ControlActionId, state: ControlActionState): Promise<void>;
}
```

## Anti-Corruption Layer

The Real-Time Control Context interfaces with external systems through an Anti-Corruption Layer (ACL):

### A1 Policy ACL

```typescript
interface A1PolicyACL {
  /**
   * Translate A1 Policy into local policy constraints
   */
  translatePolicy(a1Policy: A1PolicyDTO): LocalPolicyConstraint;

  /**
   * Check if a control action complies with active policies
   */
  checkCompliance(action: ControlAction): ComplianceResult;
}
```

### E2 Interface ACL

```typescript
interface E2InterfaceACL {
  /**
   * Translate domain ControlAction to E2AP Control Request
   */
  toE2ControlRequest(action: ControlAction): E2APControlRequest;

  /**
   * Translate E2AP Indication to domain event
   */
  fromE2Indication(indication: E2APIndication): DomainEvent;
}
```

## Module Structure

```
real-time-control/
├── domain/
│   ├── aggregates/
│   │   ├── UEContext.ts
│   │   ├── E2Subscription.ts
│   │   └── ControlAction.ts
│   ├── entities/
│   │   ├── Bearer.ts
│   │   ├── QoSFlow.ts
│   │   └── MeasurementConfig.ts
│   ├── value-objects/
│   │   ├── RNTI.ts
│   │   ├── CellId.ts
│   │   ├── PLMNId.ts
│   │   └── ControlScope.ts
│   ├── events/
│   │   └── index.ts
│   └── services/
│       ├── E2SubscriptionService.ts
│       ├── ControlActionService.ts
│       └── UEContextService.ts
├── application/
│   ├── commands/
│   │   ├── CreateSubscriptionCommand.ts
│   │   ├── SubmitControlActionCommand.ts
│   │   └── TriggerHandoverCommand.ts
│   ├── queries/
│   │   ├── GetUEContextQuery.ts
│   │   └── GetActiveSubscriptionsQuery.ts
│   └── handlers/
│       └── index.ts
├── infrastructure/
│   ├── repositories/
│   │   ├── SDLUEContextRepository.ts
│   │   ├── SDLE2SubscriptionRepository.ts
│   │   └── SDLControlActionRepository.ts
│   ├── acl/
│   │   ├── A1PolicyACL.ts
│   │   └── E2InterfaceACL.ts
│   └── messaging/
│       └── E2APMessageBus.ts
└── api/
    └── xAppAPI.ts
```
