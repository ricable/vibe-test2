# Shared Kernel - Common Types and Patterns

## Overview

The Shared Kernel contains types, value objects, and patterns that are shared across multiple Bounded Contexts. Changes to this kernel require coordination between all consuming contexts.

## Shared Value Objects

### Timestamp

```typescript
/**
 * Immutable timestamp with timezone awareness
 * Used across all contexts for temporal data
 */
class Timestamp {
  private readonly epochMs: number;
  private readonly timezone: string;

  private constructor(epochMs: number, timezone: string = 'UTC') {
    this.epochMs = epochMs;
    this.timezone = timezone;
  }

  static now(): Timestamp {
    return new Timestamp(Date.now());
  }

  static fromEpochMs(ms: number): Timestamp {
    return new Timestamp(ms);
  }

  static fromISO(iso: string): Timestamp {
    return new Timestamp(Date.parse(iso));
  }

  toEpochMs(): number {
    return this.epochMs;
  }

  toISO(): string {
    return new Date(this.epochMs).toISOString();
  }

  toDate(): Date {
    return new Date(this.epochMs);
  }

  isBefore(other: Timestamp): boolean {
    return this.epochMs < other.epochMs;
  }

  isAfter(other: Timestamp): boolean {
    return this.epochMs > other.epochMs;
  }

  add(duration: Duration): Timestamp {
    return new Timestamp(this.epochMs + duration.toMs());
  }

  subtract(duration: Duration): Timestamp {
    return new Timestamp(this.epochMs - duration.toMs());
  }

  equals(other: Timestamp): boolean {
    return this.epochMs === other.epochMs;
  }
}
```

### Duration

```typescript
/**
 * Represents a time duration
 */
class Duration {
  private readonly ms: number;

  private constructor(ms: number) {
    if (ms < 0) throw new InvalidDurationError(ms);
    this.ms = ms;
  }

  static zero(): Duration {
    return new Duration(0);
  }

  static milliseconds(ms: number): Duration {
    return new Duration(ms);
  }

  static seconds(s: number): Duration {
    return new Duration(s * 1000);
  }

  static minutes(m: number): Duration {
    return new Duration(m * 60 * 1000);
  }

  static hours(h: number): Duration {
    return new Duration(h * 60 * 60 * 1000);
  }

  static days(d: number): Duration {
    return new Duration(d * 24 * 60 * 60 * 1000);
  }

  toMs(): number {
    return this.ms;
  }

  toSeconds(): number {
    return this.ms / 1000;
  }

  toMinutes(): number {
    return this.ms / (60 * 1000);
  }

  toHours(): number {
    return this.ms / (60 * 60 * 1000);
  }

  plus(other: Duration): Duration {
    return new Duration(this.ms + other.ms);
  }

  minus(other: Duration): Duration {
    return new Duration(Math.max(0, this.ms - other.ms));
  }

  isLongerThan(other: Duration): boolean {
    return this.ms > other.ms;
  }
}
```

### TimeRange

```typescript
/**
 * Represents a time interval with start and end
 */
class TimeRange {
  readonly start: Timestamp;
  readonly end: Timestamp;

  constructor(start: Timestamp, end: Timestamp) {
    if (end.isBefore(start)) {
      throw new InvalidTimeRangeError(start, end);
    }
    this.start = start;
    this.end = end;
  }

  static lastMinutes(minutes: number): TimeRange {
    const now = Timestamp.now();
    return new TimeRange(
      now.subtract(Duration.minutes(minutes)),
      now
    );
  }

  static lastHours(hours: number): TimeRange {
    const now = Timestamp.now();
    return new TimeRange(
      now.subtract(Duration.hours(hours)),
      now
    );
  }

  static lastDays(days: number): TimeRange {
    const now = Timestamp.now();
    return new TimeRange(
      now.subtract(Duration.days(days)),
      now
    );
  }

  duration(): Duration {
    return Duration.milliseconds(
      this.end.toEpochMs() - this.start.toEpochMs()
    );
  }

  contains(timestamp: Timestamp): boolean {
    return !timestamp.isBefore(this.start) && !timestamp.isAfter(this.end);
  }

  overlaps(other: TimeRange): boolean {
    return !this.end.isBefore(other.start) && !this.start.isAfter(other.end);
  }
}
```

### PLMNId (Public Land Mobile Network Identity)

```typescript
/**
 * Identifies a mobile network (MCC + MNC)
 */
class PLMNId {
  readonly mcc: string;  // Mobile Country Code (3 digits)
  readonly mnc: string;  // Mobile Network Code (2-3 digits)

  constructor(mcc: string, mnc: string) {
    if (!/^\d{3}$/.test(mcc)) {
      throw new InvalidMCCError(mcc);
    }
    if (!/^\d{2,3}$/.test(mnc)) {
      throw new InvalidMNCError(mnc);
    }
    this.mcc = mcc;
    this.mnc = mnc;
  }

  static fromString(plmn: string): PLMNId {
    // Format: "310-410" or "310410"
    const match = plmn.match(/^(\d{3})-?(\d{2,3})$/);
    if (!match) throw new InvalidPLMNFormatError(plmn);
    return new PLMNId(match[1], match[2]);
  }

  toString(): string {
    return `${this.mcc}-${this.mnc}`;
  }

  toNumeric(): string {
    return `${this.mcc}${this.mnc}`;
  }

  equals(other: PLMNId): boolean {
    return this.mcc === other.mcc && this.mnc === other.mnc;
  }
}
```

### S-NSSAI (Single Network Slice Selection Assistance Information)

```typescript
/**
 * Identifies a network slice
 */
class SNSSAI {
  readonly sst: number;   // Slice/Service Type (0-255)
  readonly sd?: string;   // Slice Differentiator (optional, 6 hex chars)

  constructor(sst: number, sd?: string) {
    if (sst < 0 || sst > 255) {
      throw new InvalidSSTError(sst);
    }
    if (sd && !/^[0-9A-Fa-f]{6}$/.test(sd)) {
      throw new InvalidSDError(sd);
    }
    this.sst = sst;
    this.sd = sd?.toUpperCase();
  }

  static standardSlice(type: 'eMBB' | 'URLLC' | 'MIoT'): SNSSAI {
    const sstMap = { eMBB: 1, URLLC: 2, MIoT: 3 };
    return new SNSSAI(sstMap[type]);
  }

  toString(): string {
    return this.sd ? `${this.sst}-${this.sd}` : `${this.sst}`;
  }

  equals(other: SNSSAI): boolean {
    return this.sst === other.sst && this.sd === other.sd;
  }
}
```

## Shared Interfaces

### Identity Types

```typescript
/**
 * Base interface for all aggregate identifiers
 */
interface AggregateId {
  readonly value: string;
  toString(): string;
  equals(other: AggregateId): boolean;
}

/**
 * UUID-based identifier
 */
class UUID implements AggregateId {
  readonly value: string;

  private constructor(value: string) {
    this.value = value;
  }

  static generate(): UUID {
    return new UUID(crypto.randomUUID());
  }

  static fromString(value: string): UUID {
    if (!this.isValid(value)) {
      throw new InvalidUUIDError(value);
    }
    return new UUID(value);
  }

  private static isValid(value: string): boolean {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
  }

  toString(): string {
    return this.value;
  }

  equals(other: AggregateId): boolean {
    return this.value === other.value;
  }
}
```

### Domain Event Base

```typescript
/**
 * Base interface for all domain events
 */
interface DomainEvent {
  readonly eventId: string;
  readonly eventType: string;
  readonly aggregateId: string;
  readonly aggregateType: string;
  readonly timestamp: Timestamp;
  readonly metadata?: EventMetadata;
}

interface EventMetadata {
  correlationId?: string;
  causationId?: string;
  userId?: string;
  source?: string;
}

/**
 * Abstract base class for domain events
 */
abstract class BaseDomainEvent implements DomainEvent {
  readonly eventId: string;
  readonly timestamp: Timestamp;
  abstract readonly eventType: string;
  abstract readonly aggregateId: string;
  abstract readonly aggregateType: string;

  constructor() {
    this.eventId = UUID.generate().toString();
    this.timestamp = Timestamp.now();
  }
}
```

### Result Types

```typescript
/**
 * Represents the result of an operation that may fail
 */
type Result<T, E = Error> = Success<T> | Failure<E>;

class Success<T> {
  readonly isSuccess = true;
  readonly isFailure = false;
  readonly value: T;

  constructor(value: T) {
    this.value = value;
  }
}

class Failure<E> {
  readonly isSuccess = false;
  readonly isFailure = true;
  readonly error: E;

  constructor(error: E) {
    this.error = error;
  }
}

function success<T>(value: T): Result<T, never> {
  return new Success(value);
}

function failure<E>(error: E): Result<never, E> {
  return new Failure(error);
}

/**
 * Validation result with multiple errors
 */
interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

interface ValidationError {
  field: string;
  message: string;
  code: string;
}
```

### Pagination

```typescript
/**
 * Pagination request parameters
 */
interface PaginationRequest {
  page: number;      // 0-indexed
  pageSize: number;
  sortBy?: string;
  sortDirection?: 'ASC' | 'DESC';
}

/**
 * Paginated response wrapper
 */
interface PaginatedResponse<T> {
  items: T[];
  pagination: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

function paginate<T>(
  items: T[],
  totalItems: number,
  request: PaginationRequest
): PaginatedResponse<T> {
  const totalPages = Math.ceil(totalItems / request.pageSize);
  return {
    items,
    pagination: {
      page: request.page,
      pageSize: request.pageSize,
      totalItems,
      totalPages,
      hasNext: request.page < totalPages - 1,
      hasPrevious: request.page > 0
    }
  };
}
```

## Shared Domain Services

### EventPublisher

```typescript
/**
 * Interface for publishing domain events
 */
interface EventPublisher {
  publish(event: DomainEvent): Promise<void>;
  publishAll(events: DomainEvent[]): Promise<void>;
}

/**
 * Interface for subscribing to domain events
 */
interface EventSubscriber {
  subscribe<T extends DomainEvent>(
    eventType: string,
    handler: (event: T) => Promise<void>
  ): Subscription;
}

interface Subscription {
  unsubscribe(): void;
}
```

### AuditLogger

```typescript
/**
 * Interface for audit logging across contexts
 */
interface AuditLogger {
  log(entry: AuditEntry): Promise<void>;
}

interface AuditEntry {
  action: string;
  actor: string;
  resource: string;
  resourceId: string;
  timestamp: Timestamp;
  outcome: 'SUCCESS' | 'FAILURE';
  details?: Record<string, any>;
  correlationId?: string;
}
```

## Shared Exceptions

```typescript
/**
 * Base class for domain exceptions
 */
abstract class DomainException extends Error {
  abstract readonly code: string;
  readonly timestamp: Timestamp;

  constructor(message: string) {
    super(message);
    this.timestamp = Timestamp.now();
    this.name = this.constructor.name;
  }
}

/**
 * Entity not found
 */
class EntityNotFoundException extends DomainException {
  readonly code = 'ENTITY_NOT_FOUND';
  readonly entityType: string;
  readonly entityId: string;

  constructor(entityType: string, entityId: string) {
    super(`${entityType} with id ${entityId} not found`);
    this.entityType = entityType;
    this.entityId = entityId;
  }
}

/**
 * Validation failed
 */
class ValidationException extends DomainException {
  readonly code = 'VALIDATION_FAILED';
  readonly errors: ValidationError[];

  constructor(errors: ValidationError[]) {
    super(`Validation failed: ${errors.map(e => e.message).join(', ')}`);
    this.errors = errors;
  }
}

/**
 * Concurrency conflict
 */
class ConcurrencyException extends DomainException {
  readonly code = 'CONCURRENCY_CONFLICT';
  readonly entityType: string;
  readonly entityId: string;
  readonly expectedVersion: number;
  readonly actualVersion: number;

  constructor(
    entityType: string,
    entityId: string,
    expectedVersion: number,
    actualVersion: number
  ) {
    super(
      `Concurrency conflict for ${entityType} ${entityId}: ` +
      `expected version ${expectedVersion}, actual ${actualVersion}`
    );
    this.entityType = entityType;
    this.entityId = entityId;
    this.expectedVersion = expectedVersion;
    this.actualVersion = actualVersion;
  }
}

/**
 * Operation not permitted
 */
class OperationNotPermittedException extends DomainException {
  readonly code = 'OPERATION_NOT_PERMITTED';
  readonly operation: string;
  readonly reason: string;

  constructor(operation: string, reason: string) {
    super(`Operation ${operation} not permitted: ${reason}`);
    this.operation = operation;
    this.reason = reason;
  }
}

/**
 * Invalid state transition
 */
class InvalidStateTransitionException extends DomainException {
  readonly code = 'INVALID_STATE_TRANSITION';
  readonly currentState: string;
  readonly targetState: string;

  constructor(currentState: string, targetState: string) {
    super(`Cannot transition from ${currentState} to ${targetState}`);
    this.currentState = currentState;
    this.targetState = targetState;
  }
}
```

## Module Structure

```
shared-kernel/
├── value-objects/
│   ├── Timestamp.ts
│   ├── Duration.ts
│   ├── TimeRange.ts
│   ├── PLMNId.ts
│   ├── SNSSAI.ts
│   └── index.ts
├── identity/
│   ├── AggregateId.ts
│   ├── UUID.ts
│   └── index.ts
├── events/
│   ├── DomainEvent.ts
│   ├── EventPublisher.ts
│   ├── EventSubscriber.ts
│   └── index.ts
├── results/
│   ├── Result.ts
│   ├── ValidationResult.ts
│   └── index.ts
├── pagination/
│   ├── PaginationRequest.ts
│   ├── PaginatedResponse.ts
│   └── index.ts
├── exceptions/
│   ├── DomainException.ts
│   ├── EntityNotFoundException.ts
│   ├── ValidationException.ts
│   ├── ConcurrencyException.ts
│   └── index.ts
├── services/
│   ├── AuditLogger.ts
│   └── index.ts
└── index.ts
```
