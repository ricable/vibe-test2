# Telemetry and Observability Context - Domain Model

## Context Overview

The Telemetry and Observability Context spans both the SMO and RIC platforms, handling the ingestion, processing, and exposure of network telemetry data. This context deals with high-volume data streams including Performance Management (PM) data, alarms, and VES (Virtual Function Event Streaming) events. It is a **Supporting Domain** that enables the Core Domain (Real-Time Control) to make informed decisions.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **VES Event** | A JSON-formatted event conforming to the ONAP VES specification, used for real-time event streaming |
| **PM File** | A 3GPP-formatted file containing Performance Management counters collected over a granularity period |
| **KPI** | Key Performance Indicator - a derived metric calculated from PM counters |
| **Alarm** | A notification of an abnormal condition detected in the network, following ITU-T X.733 model |
| **Measurement Job** | A configured task for collecting specific PM counters from network elements |
| **Granularity Period** | The time interval over which PM counters are aggregated (typically 15 minutes) |
| **Event Correlation** | The process of relating multiple alarms/events to identify root cause |

## Aggregates

### 1. MeasurementJob (Aggregate Root)

Manages the configuration and lifecycle of PM data collection tasks.

```typescript
// Aggregate Root
interface MeasurementJob {
  // Identity
  jobId: MeasurementJobId;
  jobName: string;

  // Configuration
  jobType: JobType;
  granularityPeriod: GranularityPeriod;
  reportingPeriod: Duration;

  // Scope
  networkElements: DistinguishedName[];
  managedObjectClasses: string[];

  // Counters
  measurementTypes: MeasurementType[];

  // Schedule
  scheduleType: 'IMMEDIATE' | 'SCHEDULED' | 'RECURRING';
  startTime?: Timestamp;
  endTime?: Timestamp;
  recurrence?: RecurrencePattern;

  // State
  state: JobState;
  lastExecutionTime?: Timestamp;
  nextExecutionTime?: Timestamp;

  // Output
  reportFormat: 'XML_3GPP' | 'JSON' | 'AVRO';
  deliveryMethod: DeliveryMethod;

  // Metadata
  createdAt: Timestamp;
  createdBy: string;
  priority: number;
}

enum JobType {
  CUMULATIVE_COUNTER = 'CUMULATIVE_COUNTER',
  GAUGE = 'GAUGE',
  DER = 'DER',  // Discrete Event Registration
  STATUS_INSPECTION = 'STATUS_INSPECTION'
}

enum GranularityPeriod {
  GP_1_MIN = 60,
  GP_5_MIN = 300,
  GP_15_MIN = 900,
  GP_30_MIN = 1800,
  GP_1_HOUR = 3600
}

enum JobState {
  CREATED = 'CREATED',
  SCHEDULED = 'SCHEDULED',
  RUNNING = 'RUNNING',
  SUSPENDED = 'SUSPENDED',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED'
}

interface DeliveryMethod {
  type: 'FILE' | 'STREAM' | 'PUSH';
  fileLocation?: string;
  streamEndpoint?: string;
  pushUri?: string;
  credentials?: CredentialReference;
}

// Invariants:
// 1. measurementTypes MUST reference valid 3GPP counter definitions
// 2. granularityPeriod MUST be <= reportingPeriod
// 3. endTime MUST be after startTime if both specified
// 4. RUNNING jobs MUST NOT be modified (suspend first)
```

### 2. MeasurementType (Entity)

Defines a PM counter or KPI definition.

```typescript
interface MeasurementType {
  // Identity
  measurementTypeId: string;  // 3GPP counter family.counter format

  // Definition
  name: string;
  description: string;
  counterType: CounterType;
  aggregationMethod: AggregationMethod;
  unit: string;

  // Data Type
  valueType: 'INTEGER' | 'REAL' | 'BOOLEAN';
  minValue?: number;
  maxValue?: number;

  // Derivation (for KPIs)
  formula?: string;
  baseCounters?: string[];

  // Metadata
  source: '3GPP' | 'O-RAN' | 'VENDOR' | 'CUSTOM';
  specification?: string;
  deprecated: boolean;
}

enum CounterType {
  CUMULATIVE = 'CUMULATIVE',  // Always increasing
  GAUGE = 'GAUGE',            // Point-in-time value
  DELTA = 'DELTA',            // Change since last period
  AVERAGE = 'AVERAGE',        // Average over period
  MINIMUM = 'MINIMUM',
  MAXIMUM = 'MAXIMUM'
}

enum AggregationMethod {
  SUM = 'SUM',
  AVERAGE = 'AVERAGE',
  MIN = 'MIN',
  MAX = 'MAX',
  LAST = 'LAST',
  FIRST = 'FIRST'
}
```

### 3. Alarm (Aggregate Root)

Represents a network alarm following ITU-T X.733 model.

```typescript
interface Alarm {
  // Identity
  alarmId: AlarmId;
  alarmRaisedTime: Timestamp;

  // Source
  managedObjectDn: DistinguishedName;
  managedObjectClass: string;

  // Classification (X.733)
  eventType: EventType;
  probableCause: ProbableCause;
  specificProblem?: string;
  perceivedSeverity: PerceivedSeverity;

  // State
  alarmState: AlarmState;
  alarmClearedTime?: Timestamp;
  alarmChangedTime?: Timestamp;
  ackState: AcknowledgementState;
  ackTime?: Timestamp;
  ackUserId?: string;

  // Additional Information
  additionalText?: string;
  additionalInformation: Record<string, string>;
  proposedRepairActions?: string[];

  // Correlation
  correlatedAlarms: AlarmId[];
  rootCauseIndicator: boolean;

  // Notification
  notificationId: number;
  stateChangeNotifications: StateChangeNotification[];
}

enum EventType {
  COMMUNICATIONS_ALARM = 'COMMUNICATIONS_ALARM',
  QUALITY_OF_SERVICE_ALARM = 'QUALITY_OF_SERVICE_ALARM',
  PROCESSING_ERROR_ALARM = 'PROCESSING_ERROR_ALARM',
  EQUIPMENT_ALARM = 'EQUIPMENT_ALARM',
  ENVIRONMENTAL_ALARM = 'ENVIRONMENTAL_ALARM',
  INTEGRITY_VIOLATION = 'INTEGRITY_VIOLATION',
  OPERATIONAL_VIOLATION = 'OPERATIONAL_VIOLATION',
  PHYSICAL_VIOLATION = 'PHYSICAL_VIOLATION',
  SECURITY_SERVICE_VIOLATION = 'SECURITY_SERVICE_VIOLATION',
  TIME_DOMAIN_VIOLATION = 'TIME_DOMAIN_VIOLATION'
}

enum PerceivedSeverity {
  CRITICAL = 1,
  MAJOR = 2,
  MINOR = 3,
  WARNING = 4,
  INDETERMINATE = 5,
  CLEARED = 6
}

enum AlarmState {
  ACTIVE = 'ACTIVE',
  CLEARED = 'CLEARED'
}

enum AcknowledgementState {
  ACKNOWLEDGED = 'ACKNOWLEDGED',
  UNACKNOWLEDGED = 'UNACKNOWLEDGED'
}

enum ProbableCause {
  // Communications alarm causes
  LOSS_OF_SIGNAL = 'LOSS_OF_SIGNAL',
  LOSS_OF_FRAME = 'LOSS_OF_FRAME',
  FRAMING_ERROR = 'FRAMING_ERROR',
  LOCAL_NODE_TRANSMISSION_ERROR = 'LOCAL_NODE_TRANSMISSION_ERROR',
  REMOTE_NODE_TRANSMISSION_ERROR = 'REMOTE_NODE_TRANSMISSION_ERROR',
  CALL_ESTABLISHMENT_ERROR = 'CALL_ESTABLISHMENT_ERROR',
  DEGRADED_SIGNAL = 'DEGRADED_SIGNAL',
  // Equipment alarm causes
  POWER_PROBLEM = 'POWER_PROBLEM',
  TIMING_PROBLEM = 'TIMING_PROBLEM',
  PROCESSOR_PROBLEM = 'PROCESSOR_PROBLEM',
  MEMORY_MISMATCH = 'MEMORY_MISMATCH',
  SOFTWARE_PROGRAM_ERROR = 'SOFTWARE_PROGRAM_ERROR',
  // QoS alarm causes
  THRESHOLD_CROSSED = 'THRESHOLD_CROSSED',
  PERFORMANCE_DEGRADED = 'PERFORMANCE_DEGRADED',
  CONGESTION = 'CONGESTION',
  // ... additional causes
  OTHER = 'OTHER'
}

interface StateChangeNotification {
  notificationId: number;
  timestamp: Timestamp;
  previousSeverity: PerceivedSeverity;
  newSeverity: PerceivedSeverity;
  changeReason: string;
}

// Invariants:
// 1. CLEARED alarms MUST have alarmClearedTime set
// 2. ACKNOWLEDGED alarms MUST have ackTime and ackUserId set
// 3. stateChangeNotifications MUST be ordered by timestamp
// 4. perceivedSeverity transitions MUST follow valid state machine
```

### 4. VESEvent (Entity)

Represents a VES event received from network functions.

```typescript
interface VESEvent {
  // Event Header (required fields)
  eventHeader: VESEventHeader;

  // Domain-specific payload (one of)
  heartbeatFields?: HeartbeatFields;
  faultFields?: FaultFields;
  measurementFields?: MeasurementFields;
  notificationFields?: NotificationFields;
  pnfRegistrationFields?: PnfRegistrationFields;
  stateChangeFields?: StateChangeFields;
  thresholdCrossingAlertFields?: ThresholdCrossingAlertFields;
}

interface VESEventHeader {
  // Identity
  eventId: string;
  eventName: string;
  eventType?: string;

  // Domain
  domain: VESDomain;

  // Source
  sourceId: string;
  sourceName: string;
  reportingEntityId: string;
  reportingEntityName: string;
  nfNamingCode?: string;
  nfVendorName?: string;

  // Timing
  startEpochMicrosec: number;
  lastEpochMicrosec: number;
  timeZoneOffset?: string;

  // Versioning
  vesEventListenerVersion: string;
  version: string;

  // Sequence
  sequence: number;

  // Priority
  priority: VESPriority;
}

enum VESDomain {
  FAULT = 'fault',
  HEARTBEAT = 'heartbeat',
  MEASUREMENT = 'measurement',
  NOTIFICATION = 'notification',
  PNF_REGISTRATION = 'pnfRegistration',
  STATE_CHANGE = 'stateChange',
  THRESHOLD_CROSSING_ALERT = 'thresholdCrossingAlert'
}

enum VESPriority {
  HIGH = 'High',
  MEDIUM = 'Medium',
  NORMAL = 'Normal',
  LOW = 'Low'
}

interface FaultFields {
  faultFieldsVersion: string;
  alarmCondition: string;
  eventCategory?: string;
  eventSeverity: string;
  eventSourceType: string;
  specificProblem: string;
  vfStatus: 'Active' | 'Idle';
  alarmAdditionalInformation?: Record<string, string>;
  alarmInterfaceA?: string;
  nfcNamingCode?: string;
  nfNamingCode?: string;
}

interface MeasurementFields {
  measurementFieldsVersion: string;
  measurementInterval: number;
  additionalMeasurements?: NamedHashMap[];
  cpuUsageArray?: CpuUsage[];
  diskUsageArray?: DiskUsage[];
  memoryUsageArray?: MemoryUsage[];
  networkInterfaceArray?: NetworkInterface[];
}
```

### 5. KPIDefinition (Aggregate Root)

Defines how KPIs are calculated from PM counters.

```typescript
interface KPIDefinition {
  // Identity
  kpiId: KPIId;
  name: string;
  description: string;

  // Calculation
  formula: KPIFormula;
  inputCounters: string[];
  aggregationLevel: AggregationLevel;

  // Output
  unit: string;
  valueType: 'PERCENTAGE' | 'RATIO' | 'COUNT' | 'RATE' | 'DURATION';
  precision?: number;

  // Thresholds
  thresholds?: KPIThreshold[];

  // Applicability
  applicableMOCs: string[];  // Managed Object Classes
  reportingPeriod: GranularityPeriod;

  // Metadata
  category: KPICategory;
  source: '3GPP' | 'O-RAN' | 'CUSTOM';
  version: string;
}

interface KPIFormula {
  expression: string;  // e.g., "(A + B) / C * 100"
  variables: Record<string, string>;  // variable -> counter mapping
  defaultValues?: Record<string, number>;  // defaults if counter missing
}

interface KPIThreshold {
  level: 'WARNING' | 'MINOR' | 'MAJOR' | 'CRITICAL';
  condition: 'ABOVE' | 'BELOW' | 'EQUAL';
  value: number;
  hysteresis?: number;
  duration?: Duration;  // Must exceed threshold for duration
}

enum AggregationLevel {
  CELL = 'CELL',
  GNB = 'GNB',
  TRACKING_AREA = 'TRACKING_AREA',
  SLICE = 'SLICE',
  NETWORK = 'NETWORK'
}

enum KPICategory {
  ACCESSIBILITY = 'ACCESSIBILITY',
  RETAINABILITY = 'RETAINABILITY',
  INTEGRITY = 'INTEGRITY',
  AVAILABILITY = 'AVAILABILITY',
  MOBILITY = 'MOBILITY',
  UTILIZATION = 'UTILIZATION',
  ENERGY = 'ENERGY'
}

// Invariants:
// 1. All inputCounters MUST exist in MeasurementType registry
// 2. formula expression MUST be syntactically valid
// 3. thresholds MUST be ordered by severity
// 4. precision MUST be >= 0 if specified
```

## Domain Events

```typescript
// Measurement Job Events
interface MeasurementJobCreated {
  eventType: 'MeasurementJobCreated';
  jobId: string;
  jobName: string;
  networkElementCount: number;
  measurementTypeCount: number;
  timestamp: Timestamp;
}

interface MeasurementJobExecuted {
  eventType: 'MeasurementJobExecuted';
  jobId: string;
  executionTime: Timestamp;
  recordsCollected: number;
  duration: number;  // ms
  timestamp: Timestamp;
}

interface MeasurementJobFailed {
  eventType: 'MeasurementJobFailed';
  jobId: string;
  failureReason: string;
  failedElements: string[];
  timestamp: Timestamp;
}

// PM Data Events
interface PMFileReceived {
  eventType: 'PMFileReceived';
  fileId: string;
  fileName: string;
  sourceElement: string;
  granularityPeriod: number;
  recordCount: number;
  timestamp: Timestamp;
}

interface PMDataProcessed {
  eventType: 'PMDataProcessed';
  fileId: string;
  metricsIngested: number;
  processingTime: number;  // ms
  timestamp: Timestamp;
}

// Alarm Events
interface AlarmRaised {
  eventType: 'AlarmRaised';
  alarmId: string;
  managedObjectDn: string;
  perceivedSeverity: PerceivedSeverity;
  probableCause: string;
  timestamp: Timestamp;
}

interface AlarmCleared {
  eventType: 'AlarmCleared';
  alarmId: string;
  clearingReason: string;
  duration: number;  // seconds alarm was active
  timestamp: Timestamp;
}

interface AlarmAcknowledged {
  eventType: 'AlarmAcknowledged';
  alarmId: string;
  acknowledgedBy: string;
  timestamp: Timestamp;
}

interface AlarmCorrelated {
  eventType: 'AlarmCorrelated';
  correlationId: string;
  rootCauseAlarmId: string;
  correlatedAlarmIds: string[];
  correlationMethod: string;
  timestamp: Timestamp;
}

// KPI Events
interface KPIThresholdBreached {
  eventType: 'KPIThresholdBreached';
  kpiId: string;
  scope: string;
  thresholdLevel: string;
  actualValue: number;
  thresholdValue: number;
  timestamp: Timestamp;
}

interface KPIThresholdCleared {
  eventType: 'KPIThresholdCleared';
  kpiId: string;
  scope: string;
  newValue: number;
  previousLevel: string;
  timestamp: Timestamp;
}

// VES Events
interface VESEventReceived {
  eventType: 'VESEventReceived';
  eventId: string;
  domain: VESDomain;
  sourceId: string;
  priority: VESPriority;
  timestamp: Timestamp;
}

interface VESBatchProcessed {
  eventType: 'VESBatchProcessed';
  batchId: string;
  eventCount: number;
  processingTime: number;
  timestamp: Timestamp;
}
```

## Domain Services

### PMCollectionService

```typescript
interface PMCollectionService {
  /**
   * Create a new measurement job
   */
  createMeasurementJob(
    config: MeasurementJobConfig
  ): Promise<MeasurementJob>;

  /**
   * Execute a measurement job immediately
   */
  executeJob(jobId: MeasurementJobId): Promise<JobExecutionResult>;

  /**
   * Query PM data
   */
  queryPMData(
    counters: string[],
    scope: DistinguishedName[],
    timeRange: TimeRange,
    aggregation?: AggregationMethod
  ): Promise<PMDataSet>;

  /**
   * Calculate KPI from PM data
   */
  calculateKPI(
    kpiId: KPIId,
    scope: DistinguishedName[],
    timeRange: TimeRange
  ): Promise<KPIValue[]>;
}

interface PMDataSet {
  timeRange: TimeRange;
  granularity: GranularityPeriod;
  data: PMDataPoint[];
  metadata: {
    totalRecords: number;
    missingPeriods: number;
  };
}

interface PMDataPoint {
  timestamp: Timestamp;
  scope: DistinguishedName;
  counters: Record<string, number>;
}
```

### AlarmManagementService

```typescript
interface AlarmManagementService {
  /**
   * Get active alarms, optionally filtered
   */
  getActiveAlarms(filter?: AlarmFilter): Promise<Alarm[]>;

  /**
   * Get alarm history
   */
  getAlarmHistory(
    filter: AlarmFilter,
    timeRange: TimeRange
  ): Promise<Alarm[]>;

  /**
   * Acknowledge an alarm
   */
  acknowledgeAlarm(
    alarmId: AlarmId,
    userId: string,
    comment?: string
  ): Promise<void>;

  /**
   * Clear an alarm manually
   */
  clearAlarm(
    alarmId: AlarmId,
    reason: string
  ): Promise<void>;

  /**
   * Correlate alarms to find root cause
   */
  correlateAlarms(
    alarmIds: AlarmId[]
  ): Promise<AlarmCorrelationResult>;
}

interface AlarmFilter {
  severities?: PerceivedSeverity[];
  eventTypes?: EventType[];
  managedObjectDn?: DistinguishedName;
  probableCauses?: ProbableCause[];
  ackState?: AcknowledgementState;
}

interface AlarmCorrelationResult {
  correlationId: string;
  rootCauseAlarm?: Alarm;
  correlatedAlarms: Alarm[];
  correlationScore: number;
  reasoning: string;
}
```

### VESCollectorService

```typescript
interface VESCollectorService {
  /**
   * Receive and process VES events
   */
  receiveEvents(events: VESEvent[]): Promise<void>;

  /**
   * Query VES events
   */
  queryEvents(
    filter: VESEventFilter,
    timeRange: TimeRange
  ): Promise<VESEvent[]>;

  /**
   * Subscribe to VES events
   */
  subscribe(
    filter: VESEventFilter,
    callback: (event: VESEvent) => void
  ): Subscription;

  /**
   * Get event statistics
   */
  getEventStats(
    timeRange: TimeRange
  ): Promise<VESEventStats>;
}

interface VESEventFilter {
  domains?: VESDomain[];
  priorities?: VESPriority[];
  sourceIds?: string[];
  eventNamePattern?: string;
}
```

### KPICalculationService

```typescript
interface KPICalculationService {
  /**
   * Register a new KPI definition
   */
  registerKPI(definition: KPIDefinition): Promise<void>;

  /**
   * Calculate KPIs for a scope and time range
   */
  calculateKPIs(
    kpiIds: KPIId[],
    scope: AggregationLevel,
    scopeIds: string[],
    timeRange: TimeRange
  ): Promise<KPIResult[]>;

  /**
   * Check KPI thresholds
   */
  evaluateThresholds(
    kpiId: KPIId,
    values: KPIValue[]
  ): Promise<ThresholdEvaluation[]>;

  /**
   * Get KPI trend analysis
   */
  analyzeTrend(
    kpiId: KPIId,
    scope: string,
    timeRange: TimeRange
  ): Promise<TrendAnalysis>;
}

interface KPIResult {
  kpiId: KPIId;
  scope: string;
  timestamp: Timestamp;
  value: number;
  unit: string;
  quality: 'GOOD' | 'SUSPECT' | 'MISSING';
}

interface TrendAnalysis {
  direction: 'IMPROVING' | 'DEGRADING' | 'STABLE';
  changeRate: number;
  forecast: ForecastPoint[];
  anomalies: AnomalyPoint[];
}
```

## Repository Interfaces

```typescript
interface MeasurementJobRepository {
  findById(id: MeasurementJobId): Promise<MeasurementJob | null>;
  findByState(state: JobState): Promise<MeasurementJob[]>;
  findScheduledBefore(time: Timestamp): Promise<MeasurementJob[]>;
  save(job: MeasurementJob): Promise<void>;
  updateState(id: MeasurementJobId, state: JobState): Promise<void>;
}

interface AlarmRepository {
  findById(id: AlarmId): Promise<Alarm | null>;
  findActive(filter?: AlarmFilter): Promise<Alarm[]>;
  findByTimeRange(timeRange: TimeRange, filter?: AlarmFilter): Promise<Alarm[]>;
  findCorrelated(alarmId: AlarmId): Promise<Alarm[]>;
  save(alarm: Alarm): Promise<void>;
  updateState(id: AlarmId, state: AlarmState): Promise<void>;
}

interface VESEventRepository {
  findById(eventId: string): Promise<VESEvent | null>;
  findByTimeRange(timeRange: TimeRange, filter?: VESEventFilter): Promise<VESEvent[]>;
  findRecent(limit: number, filter?: VESEventFilter): Promise<VESEvent[]>;
  save(event: VESEvent): Promise<void>;
  saveBatch(events: VESEvent[]): Promise<void>;
}

interface KPIDefinitionRepository {
  findById(id: KPIId): Promise<KPIDefinition | null>;
  findAll(): Promise<KPIDefinition[]>;
  findByCategory(category: KPICategory): Promise<KPIDefinition[]>;
  save(definition: KPIDefinition): Promise<void>;
}

interface PMDataRepository {
  queryCounters(
    counters: string[],
    scope: DistinguishedName[],
    timeRange: TimeRange
  ): Promise<PMDataSet>;

  storeCounters(data: PMDataPoint[]): Promise<void>;

  aggregateCounters(
    counters: string[],
    scope: DistinguishedName[],
    timeRange: TimeRange,
    method: AggregationMethod
  ): Promise<PMDataSet>;
}
```

## Module Structure

```
telemetry-observability/
├── domain/
│   ├── aggregates/
│   │   ├── MeasurementJob.ts
│   │   ├── Alarm.ts
│   │   ├── VESEvent.ts
│   │   └── KPIDefinition.ts
│   ├── entities/
│   │   ├── MeasurementType.ts
│   │   ├── StateChangeNotification.ts
│   │   └── KPIThreshold.ts
│   ├── value-objects/
│   │   ├── AlarmId.ts
│   │   ├── GranularityPeriod.ts
│   │   ├── PerceivedSeverity.ts
│   │   └── VESEventHeader.ts
│   ├── events/
│   │   └── index.ts
│   └── services/
│       ├── PMCollectionService.ts
│       ├── AlarmManagementService.ts
│       ├── VESCollectorService.ts
│       └── KPICalculationService.ts
├── application/
│   ├── commands/
│   │   ├── CreateMeasurementJobCommand.ts
│   │   ├── AcknowledgeAlarmCommand.ts
│   │   └── RegisterKPICommand.ts
│   ├── queries/
│   │   ├── GetActiveAlarmsQuery.ts
│   │   ├── QueryPMDataQuery.ts
│   │   └── CalculateKPIQuery.ts
│   └── handlers/
│       └── index.ts
├── infrastructure/
│   ├── repositories/
│   │   ├── TimescaleDBPMDataRepository.ts
│   │   ├── PostgresAlarmRepository.ts
│   │   ├── KafkaVESEventRepository.ts
│   │   └── PostgresKPIRepository.ts
│   ├── collectors/
│   │   ├── VESCollector.ts
│   │   ├── PMFileParser.ts
│   │   └── SNMPTrapReceiver.ts
│   └── streaming/
│       ├── KafkaProducer.ts
│       └── KafkaConsumer.ts
└── api/
    ├── PMDataAPI.ts
    ├── AlarmAPI.ts
    ├── VESCollectorAPI.ts
    └── KPIQueryAPI.ts
```
