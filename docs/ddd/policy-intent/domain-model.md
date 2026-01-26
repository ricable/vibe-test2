# Policy and Intent Context - Domain Model

## Context Overview

The Policy and Intent Context is a **Supporting Domain** residing within the Non-RT RIC. It translates high-level business intents into technical A1 policies that guide the Near-RT RIC's real-time control decisions. This context operates at timescales greater than 1 second and focuses on strategic optimization rather than tactical control.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Intent** | A high-level business goal expressed in natural or structured language (e.g., "Maximize energy efficiency during off-peak hours") |
| **A1 Policy** | A technical policy instance conforming to a registered PolicyType schema, sent to the Near-RT RIC via the A1 interface |
| **Policy Type** | A schema defining the structure and constraints for a category of policies (e.g., Traffic Steering, QoS Target) |
| **rApp** | An application running on the Non-RT RIC that consumes R1 services and generates policies or enrichment information |
| **Policy Scope** | The target entities to which a policy applies (UE, Cell, Slice, Network) |
| **Policy Enforcement** | The state indicating whether a policy is actively being enforced by the Near-RT RIC |
| **Compliance** | The degree to which observed network behavior aligns with policy targets |

## Aggregates

### 1. Intent (Aggregate Root)

The `Intent` aggregate captures business goals before they are translated into technical policies.

```typescript
// Aggregate Root
interface Intent {
  // Identity
  intentId: IntentId;

  // Source
  createdBy: UserId | SystemId;
  source: 'OPERATOR' | 'GENAI' | 'AUTOMATION' | 'SLA';

  // Intent Content
  description: string;           // Natural language or structured
  goalType: IntentGoalType;
  targetKPIs: KPITarget[];
  constraints: IntentConstraint[];

  // Scope
  scope: IntentScope;
  effectiveFrom: Timestamp;
  effectiveUntil?: Timestamp;
  recurrence?: RecurrencePattern;

  // Derived Policies
  derivedPolicies: PolicyId[];

  // State
  state: IntentState;
  validationErrors?: string[];

  // Metadata
  version: number;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

enum IntentGoalType {
  MAXIMIZE_THROUGHPUT = 'MAXIMIZE_THROUGHPUT',
  MINIMIZE_LATENCY = 'MINIMIZE_LATENCY',
  MAXIMIZE_COVERAGE = 'MAXIMIZE_COVERAGE',
  MINIMIZE_ENERGY = 'MINIMIZE_ENERGY',
  BALANCE_LOAD = 'BALANCE_LOAD',
  ENSURE_QOS = 'ENSURE_QOS',
  CUSTOM = 'CUSTOM'
}

enum IntentState {
  DRAFT = 'DRAFT',
  VALIDATING = 'VALIDATING',
  VALIDATED = 'VALIDATED',
  TRANSLATING = 'TRANSLATING',
  ACTIVE = 'ACTIVE',
  SUSPENDED = 'SUSPENDED',
  EXPIRED = 'EXPIRED',
  FAILED = 'FAILED'
}

// Invariants:
// 1. An active Intent MUST have at least one derived policy
// 2. effectiveUntil MUST be after effectiveFrom if specified
// 3. KPI targets MUST be achievable (validated against network capacity)
// 4. Scope MUST reference existing network elements
```

#### Value Objects for Intent

```typescript
interface KPITarget {
  kpiId: string;
  targetType: 'MIN' | 'MAX' | 'RANGE' | 'EXACT';
  value: number;
  upperBound?: number;  // For RANGE
  unit: string;
  priority: number;     // For multi-objective optimization
}

interface IntentConstraint {
  constraintType: 'MUST' | 'SHOULD' | 'MUST_NOT';
  parameter: string;
  operator: 'EQ' | 'LT' | 'GT' | 'IN' | 'NOT_IN';
  value: any;
}

interface IntentScope {
  type: 'NETWORK' | 'REGION' | 'CELL_GROUP' | 'SLICE' | 'UE_GROUP';
  identifiers?: string[];
  geofence?: GeoFence;
  timeWindow?: TimeWindow;
}

class GeoFence {
  readonly type: 'Circle' | 'Polygon';
  readonly coordinates: number[][];
  readonly radiusKm?: number;

  contains(point: [number, number]): boolean {
    // Geo containment logic
  }
}

class TimeWindow {
  readonly startTime: string;  // HH:MM format
  readonly endTime: string;
  readonly daysOfWeek: number[];  // 0=Sunday, 6=Saturday
  readonly timezone: string;

  isActive(now: Date): boolean {
    // Time window check logic
  }
}
```

### 2. A1Policy (Aggregate Root)

The `A1Policy` aggregate represents a technical policy ready for enforcement.

```typescript
interface A1Policy {
  // Identity
  policyId: PolicyId;
  policyTypeId: PolicyTypeId;

  // Derivation
  derivedFromIntent?: IntentId;
  translationConfidence?: number;  // 0.0 - 1.0 if GenAI translated

  // Policy Content
  scope: PolicyScope;
  policyData: object;            // Conforms to PolicyType schema
  notificationUri?: string;      // For status callbacks

  // Targeting
  nearRTRICId: NearRTRICId;
  targetXApps?: XAppId[];        // Optional: specific xApp targeting

  // Priority
  priority: number;              // 1-100, used in conflict resolution

  // State
  state: PolicyState;
  enforcementStatus?: EnforcementStatus;
  lastStatusUpdate?: Timestamp;

  // Lifecycle
  createdAt: Timestamp;
  activatedAt?: Timestamp;
  expiresAt?: Timestamp;
}

interface PolicyScope {
  scopeType: 'UE' | 'CELL' | 'SLICE' | 'NETWORK';
  ueId?: string;
  cellIds?: string[];
  sliceId?: { sst: number; sd?: string };
  qosClasses?: number[];
}

enum PolicyState {
  DRAFT = 'DRAFT',
  PENDING_DELIVERY = 'PENDING_DELIVERY',
  DELIVERED = 'DELIVERED',
  ACTIVE = 'ACTIVE',
  UPDATE_PENDING = 'UPDATE_PENDING',
  DELETE_PENDING = 'DELETE_PENDING',
  DELETED = 'DELETED',
  DELIVERY_FAILED = 'DELIVERY_FAILED'
}

interface EnforcementStatus {
  enforced: boolean;
  reason?: string;
  conflictsWith?: PolicyId[];
  enforcementPercentage?: number;  // 0-100
}

// Invariants:
// 1. policyData MUST conform to the PolicyType schema
// 2. A policy MUST target exactly one Near-RT RIC
// 3. Priority MUST be set based on source intent or default rules
// 4. Expired policies MUST be automatically marked DELETED
```

### 3. PolicyType (Aggregate Root)

Registry of policy type schemas that define valid policy structures.

```typescript
interface PolicyType {
  // Identity
  policyTypeId: PolicyTypeId;
  name: string;
  version: SemanticVersion;

  // Schema
  policyTypeSchema: JSONSchema;
  statusSchema?: JSONSchema;
  stateTransitionRules?: TransitionRule[];

  // Metadata
  description: string;
  owner: string;
  supportedBy: NearRTRICId[];

  // Registration
  registeredAt: Timestamp;
  registeredBy: string;
  deprecated: boolean;
  deprecatedAt?: Timestamp;
  replacedBy?: PolicyTypeId;
}

class SemanticVersion {
  readonly major: number;
  readonly minor: number;
  readonly patch: number;

  constructor(versionString: string) {
    const [major, minor, patch] = versionString.split('.').map(Number);
    this.major = major;
    this.minor = minor;
    this.patch = patch;
  }

  isCompatibleWith(other: SemanticVersion): boolean {
    return this.major === other.major;
  }

  toString(): string {
    return `${this.major}.${this.minor}.${this.patch}`;
  }
}

// Invariants:
// 1. policyTypeSchema MUST be valid JSON Schema (draft-07 or later)
// 2. PolicyTypeId MUST be unique in the registry
// 3. Deprecated types MUST specify a replacement if available
// 4. Version changes MUST follow semantic versioning rules
```

### 4. rAppInstance (Aggregate Root)

Manages the lifecycle of rApp deployments and their policy generation capabilities.

```typescript
interface rAppInstance {
  // Identity
  rAppId: rAppId;
  instanceId: string;

  // Registration
  name: string;
  version: string;
  vendor: string;

  // Capabilities
  supportedPolicyTypes: PolicyTypeId[];
  requiredR1Services: R1ServiceId[];
  providedR1Services: R1ServiceId[];

  // State
  state: rAppState;
  health: HealthStatus;

  // Configuration
  configuration: object;
  resourceRequirements: ResourceSpec;

  // Policies
  createdPolicies: PolicyId[];
  maxConcurrentPolicies: number;

  // Lifecycle
  deployedAt: Timestamp;
  lastHealthCheck: Timestamp;
}

enum rAppState {
  DEPLOYING = 'DEPLOYING',
  RUNNING = 'RUNNING',
  SUSPENDED = 'SUSPENDED',
  FAILED = 'FAILED',
  TERMINATING = 'TERMINATING',
  TERMINATED = 'TERMINATED'
}

interface HealthStatus {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  lastCheck: Timestamp;
  errorMessage?: string;
}

// Invariants:
// 1. rApp MUST declare supported policy types at registration
// 2. RUNNING rApps MUST respond to health checks within timeout
// 3. createdPolicies count MUST NOT exceed maxConcurrentPolicies
// 4. Required R1 services MUST be available before deployment
```

## Domain Events

```typescript
// Intent Events
interface IntentCreated {
  eventType: 'IntentCreated';
  intentId: IntentId;
  goalType: IntentGoalType;
  scope: IntentScope;
  createdBy: string;
  timestamp: Timestamp;
}

interface IntentValidated {
  eventType: 'IntentValidated';
  intentId: IntentId;
  validationResult: 'PASSED' | 'FAILED';
  errors?: string[];
  timestamp: Timestamp;
}

interface IntentTranslated {
  eventType: 'IntentTranslated';
  intentId: IntentId;
  derivedPolicies: PolicyId[];
  translationMethod: 'RULE_BASED' | 'GENAI' | 'HYBRID';
  confidence: number;
  timestamp: Timestamp;
}

interface IntentExpired {
  eventType: 'IntentExpired';
  intentId: IntentId;
  effectiveUntil: Timestamp;
  timestamp: Timestamp;
}

// Policy Events
interface PolicyCreated {
  eventType: 'PolicyCreated';
  policyId: PolicyId;
  policyTypeId: PolicyTypeId;
  sourceIntentId?: IntentId;
  timestamp: Timestamp;
}

interface PolicyDelivered {
  eventType: 'PolicyDelivered';
  policyId: PolicyId;
  nearRTRICId: NearRTRICId;
  deliveryLatency: number;
  timestamp: Timestamp;
}

interface PolicyEnforcementChanged {
  eventType: 'PolicyEnforcementChanged';
  policyId: PolicyId;
  previousStatus: EnforcementStatus;
  newStatus: EnforcementStatus;
  timestamp: Timestamp;
}

interface ComplianceViolation {
  eventType: 'ComplianceViolation';
  policyId: PolicyId;
  violationType: string;
  observedValue: number;
  targetValue: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  timestamp: Timestamp;
}

// rApp Events
interface rAppDeployed {
  eventType: 'rAppDeployed';
  rAppId: rAppId;
  instanceId: string;
  timestamp: Timestamp;
}

interface rAppHealthChanged {
  eventType: 'rAppHealthChanged';
  rAppId: rAppId;
  previousHealth: HealthStatus;
  newHealth: HealthStatus;
  timestamp: Timestamp;
}
```

## Domain Services

### IntentTranslationService

```typescript
interface IntentTranslationService {
  /**
   * Validate an intent against network capabilities and constraints
   */
  validateIntent(intent: Intent): Promise<ValidationResult>;

  /**
   * Translate a validated intent into A1 policies
   * May use rule-based or GenAI translation depending on configuration
   */
  translateIntent(intent: Intent): Promise<TranslationResult>;

  /**
   * Re-translate intent after network conditions change
   */
  retranslateIntent(intentId: IntentId): Promise<TranslationResult>;
}

interface TranslationResult {
  success: boolean;
  policies: A1Policy[];
  method: 'RULE_BASED' | 'GENAI' | 'HYBRID';
  confidence: number;
  warnings?: string[];
  suggestedReview?: boolean;
}
```

### PolicyLifecycleService

```typescript
interface PolicyLifecycleService {
  /**
   * Create and deliver a new policy to Near-RT RIC
   */
  createAndDeliverPolicy(
    policyTypeId: PolicyTypeId,
    scope: PolicyScope,
    policyData: object,
    options?: PolicyOptions
  ): Promise<A1Policy>;

  /**
   * Update an existing policy
   */
  updatePolicy(
    policyId: PolicyId,
    updates: Partial<A1PolicyUpdate>
  ): Promise<A1Policy>;

  /**
   * Delete a policy
   */
  deletePolicy(policyId: PolicyId): Promise<void>;

  /**
   * Check policy enforcement status
   */
  getEnforcementStatus(policyId: PolicyId): Promise<EnforcementStatus>;
}
```

### ComplianceMonitoringService

```typescript
interface ComplianceMonitoringService {
  /**
   * Start monitoring compliance for an active policy
   */
  startMonitoring(policyId: PolicyId): Promise<void>;

  /**
   * Get current compliance status
   */
  getComplianceStatus(policyId: PolicyId): Promise<ComplianceStatus>;

  /**
   * Get compliance history
   */
  getComplianceHistory(
    policyId: PolicyId,
    timeRange: TimeRange
  ): Promise<ComplianceRecord[]>;

  /**
   * Register callback for compliance violations
   */
  onViolation(
    callback: (violation: ComplianceViolation) => void
  ): Subscription;
}

interface ComplianceStatus {
  policyId: PolicyId;
  compliant: boolean;
  compliancePercentage: number;
  kpiStatuses: KPIComplianceStatus[];
  lastEvaluated: Timestamp;
}
```

## Repository Interfaces

```typescript
interface IntentRepository {
  findById(id: IntentId): Promise<Intent | null>;
  findByState(state: IntentState): Promise<Intent[]>;
  findActive(): Promise<Intent[]>;
  findExpiring(within: Duration): Promise<Intent[]>;
  save(intent: Intent): Promise<void>;
  delete(id: IntentId): Promise<void>;
}

interface A1PolicyRepository {
  findById(id: PolicyId): Promise<A1Policy | null>;
  findByIntent(intentId: IntentId): Promise<A1Policy[]>;
  findByType(typeId: PolicyTypeId): Promise<A1Policy[]>;
  findActiveByRIC(ricId: NearRTRICId): Promise<A1Policy[]>;
  save(policy: A1Policy): Promise<void>;
  updateState(id: PolicyId, state: PolicyState): Promise<void>;
  delete(id: PolicyId): Promise<void>;
}

interface PolicyTypeRepository {
  findById(id: PolicyTypeId): Promise<PolicyType | null>;
  findAll(): Promise<PolicyType[]>;
  findSupportedByRIC(ricId: NearRTRICId): Promise<PolicyType[]>;
  save(policyType: PolicyType): Promise<void>;
  deprecate(id: PolicyTypeId, replacedBy?: PolicyTypeId): Promise<void>;
}

interface rAppRepository {
  findById(id: rAppId): Promise<rAppInstance | null>;
  findRunning(): Promise<rAppInstance[]>;
  findByCapability(policyTypeId: PolicyTypeId): Promise<rAppInstance[]>;
  save(rApp: rAppInstance): Promise<void>;
  updateState(id: rAppId, state: rAppState): Promise<void>;
}
```

## Anti-Corruption Layer

### Near-RT RIC ACL (A1 Interface)

```typescript
interface A1InterfaceACL {
  /**
   * Transform domain policy to A1 wire format
   */
  toA1PolicyInstance(policy: A1Policy): A1PolicyInstanceDTO;

  /**
   * Transform A1 status response to domain model
   */
  fromA1PolicyStatus(status: A1PolicyStatusDTO): EnforcementStatus;

  /**
   * Handle A1 notification callbacks
   */
  handleNotification(notification: A1NotificationDTO): DomainEvent;
}
```

### R1 Services ACL

```typescript
interface R1ServicesACL {
  /**
   * Query network inventory for scope validation
   */
  getNetworkElements(scope: IntentScope): Promise<NetworkElement[]>;

  /**
   * Get PM data for compliance monitoring
   */
  getPMData(
    scope: PolicyScope,
    kpis: string[],
    timeRange: TimeRange
  ): Promise<PMDataSet>;

  /**
   * Access GenAI services for intent translation
   */
  translateWithGenAI(intent: Intent): Promise<GenAITranslationResult>;
}
```

## Module Structure

```
policy-intent/
├── domain/
│   ├── aggregates/
│   │   ├── Intent.ts
│   │   ├── A1Policy.ts
│   │   ├── PolicyType.ts
│   │   └── rAppInstance.ts
│   ├── value-objects/
│   │   ├── IntentId.ts
│   │   ├── PolicyId.ts
│   │   ├── KPITarget.ts
│   │   ├── GeoFence.ts
│   │   ├── TimeWindow.ts
│   │   └── SemanticVersion.ts
│   ├── events/
│   │   └── index.ts
│   └── services/
│       ├── IntentTranslationService.ts
│       ├── PolicyLifecycleService.ts
│       └── ComplianceMonitoringService.ts
├── application/
│   ├── commands/
│   │   ├── CreateIntentCommand.ts
│   │   ├── TranslateIntentCommand.ts
│   │   ├── CreatePolicyCommand.ts
│   │   └── DeployRAppCommand.ts
│   ├── queries/
│   │   ├── GetIntentStatusQuery.ts
│   │   ├── GetActivePoliciesQuery.ts
│   │   └── GetComplianceReportQuery.ts
│   └── handlers/
│       └── index.ts
├── infrastructure/
│   ├── repositories/
│   │   ├── PostgresIntentRepository.ts
│   │   ├── PostgresA1PolicyRepository.ts
│   │   └── PostgresPolicyTypeRepository.ts
│   ├── acl/
│   │   ├── A1InterfaceACL.ts
│   │   └── R1ServicesACL.ts
│   └── clients/
│       ├── NearRTRICClient.ts
│       └── GenAIClient.ts
└── api/
    ├── IntentAPI.ts
    ├── PolicyAPI.ts
    └── rAppManagementAPI.ts
```
