# Network Inventory Context (TE&IV) - Domain Model

## Context Overview

The Network Inventory Context maintains the **source of truth** for network topology and configuration. It aligns with the Topology & Inventory (TE&IV) functions of the SMO framework and conforms to 3GPP NRM (Network Resource Model) standards. This is a **Generic Subdomain** as it implements standardized models defined by 3GPP and O-RAN.

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Managed Element** | A logical entity representing a network function (gNB, O-CU, O-DU, O-RU) that can be managed via O1 interface |
| **Distinguished Name (DN)** | A globally unique identifier for managed elements following 3GPP naming convention |
| **Topology Graph** | The graph structure representing relationships between network elements |
| **Neighbor Relation** | A relationship between cells indicating handover possibility |
| **Configuration Item** | A configurable parameter or attribute of a managed element |
| **Inventory Synchronization** | The process of aligning the inventory model with actual network state |
| **Configuration Drift** | Deviation between desired configuration and actual configuration |

## Aggregates

### 1. ManagedElement (Aggregate Root)

The `ManagedElement` aggregate represents a manageable network function.

```typescript
// Aggregate Root
interface ManagedElement {
  // Identity (3GPP DN format)
  dn: DistinguishedName;
  managedElementId: string;

  // Classification
  elementType: ManagedElementType;
  vendorName: string;
  swVersion: string;
  hwVersion?: string;

  // Location
  geographicLocation?: GeoLocation;
  siteId?: string;

  // State
  administrativeState: AdministrativeState;
  operationalState: OperationalState;
  usageState: UsageState;

  // Relationships
  parentDn?: DistinguishedName;
  containedElements: DistinguishedName[];

  // Configuration
  attributes: Record<string, AttributeValue>;
  lastConfigSync: Timestamp;

  // Lifecycle
  createdAt: Timestamp;
  modifiedAt: Timestamp;
  discoveredAt?: Timestamp;
}

enum ManagedElementType {
  GNB = 'GNB',
  GNB_CU_CP = 'GNB_CU_CP',
  GNB_CU_UP = 'GNB_CU_UP',
  GNB_DU = 'GNB_DU',
  O_RU = 'O_RU',
  SMO = 'SMO',
  NEAR_RT_RIC = 'NEAR_RT_RIC',
  NON_RT_RIC = 'NON_RT_RIC'
}

enum AdministrativeState {
  LOCKED = 'LOCKED',
  UNLOCKED = 'UNLOCKED',
  SHUTTING_DOWN = 'SHUTTING_DOWN'
}

enum OperationalState {
  ENABLED = 'ENABLED',
  DISABLED = 'DISABLED'
}

enum UsageState {
  IDLE = 'IDLE',
  ACTIVE = 'ACTIVE',
  BUSY = 'BUSY'
}

// Invariants:
// 1. DN MUST follow 3GPP naming convention
// 2. Contained elements MUST reference existing managed elements
// 3. Parent DN MUST reference an existing managed element if specified
// 4. operationalState DISABLED requires administrativeState LOCKED
```

#### Value Objects

```typescript
// Distinguished Name - 3GPP format
class DistinguishedName {
  private readonly components: DNComponent[];

  constructor(dnString: string) {
    this.components = this.parse(dnString);
    if (!this.isValid()) {
      throw new InvalidDNError(dnString);
    }
  }

  private parse(dn: string): DNComponent[] {
    // Parse format: "SubNetwork=SN1,ManagedElement=gNB-001,GNBCUCPFunction=1"
    return dn.split(',').map(part => {
      const [type, value] = part.split('=');
      return { type, value };
    });
  }

  private isValid(): boolean {
    // Validate against 3GPP NRM naming rules
    return this.components.length > 0 &&
           this.components.every(c => c.type && c.value);
  }

  getParent(): DistinguishedName | null {
    if (this.components.length <= 1) return null;
    return new DistinguishedName(
      this.components.slice(0, -1)
        .map(c => `${c.type}=${c.value}`)
        .join(',')
    );
  }

  toString(): string {
    return this.components.map(c => `${c.type}=${c.value}`).join(',');
  }
}

interface DNComponent {
  type: string;  // e.g., 'SubNetwork', 'ManagedElement', 'NRCellDU'
  value: string;
}

// Geographic Location
class GeoLocation {
  readonly latitude: number;
  readonly longitude: number;
  readonly altitude?: number;
  readonly accuracy?: number;

  constructor(lat: number, lon: number, alt?: number) {
    if (lat < -90 || lat > 90) throw new InvalidLatitudeError(lat);
    if (lon < -180 || lon > 180) throw new InvalidLongitudeError(lon);
    this.latitude = lat;
    this.longitude = lon;
    this.altitude = alt;
  }

  distanceTo(other: GeoLocation): number {
    // Haversine formula
    const R = 6371; // km
    const dLat = this.toRad(other.latitude - this.latitude);
    const dLon = this.toRad(other.longitude - this.longitude);
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(this.toRad(this.latitude)) *
              Math.cos(this.toRad(other.latitude)) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  private toRad(deg: number): number {
    return deg * Math.PI / 180;
  }
}

// Attribute Value with type safety
interface AttributeValue {
  value: any;
  dataType: AttributeDataType;
  unit?: string;
  constraints?: AttributeConstraints;
}

enum AttributeDataType {
  STRING = 'STRING',
  INTEGER = 'INTEGER',
  DECIMAL = 'DECIMAL',
  BOOLEAN = 'BOOLEAN',
  ENUM = 'ENUM',
  DATETIME = 'DATETIME',
  DN = 'DN'
}
```

### 2. NRCellDU (Entity within ManagedElement context)

Represents an NR Cell at the Distributed Unit level.

```typescript
interface NRCellDU {
  // Identity
  dn: DistinguishedName;
  nrCellDuId: number;
  nCI: NRCellIdentity;
  nRPCI: number;  // Physical Cell ID (0-1007)

  // Parent
  gNBDUFunctionDn: DistinguishedName;

  // Radio Configuration
  nRTAC: number;  // Tracking Area Code
  arfcnDL: number;
  arfcnUL?: number;
  bSChannelBwDL: number;  // MHz
  bSChannelBwUL?: number;

  // Power
  pMax?: number;  // dBm
  configuredMaxTxPower?: number;

  // State
  administrativeState: AdministrativeState;
  operationalState: OperationalState;
  cellState: CellState;

  // Relationships
  neighborRelations: NeighborRelationId[];
}

class NRCellIdentity {
  readonly plmnId: PLMNId;
  readonly nrCellId: string;  // 36-bit as hex (9 chars)

  constructor(plmnId: PLMNId, nrCellId: string) {
    if (!/^[0-9A-Fa-f]{9}$/.test(nrCellId)) {
      throw new InvalidNRCellIdError(nrCellId);
    }
    this.plmnId = plmnId;
    this.nrCellId = nrCellId;
  }

  toGlobalCellId(): string {
    return `${this.plmnId.mcc}${this.plmnId.mnc}-${this.nrCellId}`;
  }
}

enum CellState {
  IDLE = 'IDLE',
  INACTIVE = 'INACTIVE',
  ACTIVE = 'ACTIVE'
}
```

### 3. TopologyGraph (Aggregate Root)

Represents the graph structure of network relationships.

```typescript
interface TopologyGraph {
  // Identity
  graphId: string;
  graphName: string;

  // Content
  nodes: TopologyNode[];
  edges: TopologyEdge[];

  // Metadata
  version: number;
  lastUpdated: Timestamp;
  source: 'DISCOVERY' | 'MANUAL' | 'IMPORT';

  // Statistics
  nodeCount: number;
  edgeCount: number;
}

interface TopologyNode {
  nodeId: string;
  dn: DistinguishedName;
  nodeType: string;
  attributes: Record<string, any>;
  position?: GeoLocation;
}

interface TopologyEdge {
  edgeId: string;
  edgeType: TopologyEdgeType;
  sourceDn: DistinguishedName;
  targetDn: DistinguishedName;
  attributes: Record<string, any>;
  bidirectional: boolean;
}

enum TopologyEdgeType {
  CONTAINS = 'CONTAINS',
  NEIGHBOR_OF = 'NEIGHBOR_OF',
  SERVED_BY = 'SERVED_BY',
  BACKHAUL_TO = 'BACKHAUL_TO',
  INTERFERES_WITH = 'INTERFERES_WITH',
  HANDOVER_TARGET = 'HANDOVER_TARGET'
}

// Invariants:
// 1. All edge endpoints MUST reference existing nodes
// 2. CONTAINS edges MUST form a tree (no cycles)
// 3. NEIGHBOR_OF edges MUST be symmetric if bidirectional=true
// 4. Node attributes MUST conform to 3GPP NRM schema
```

### 4. NeighborRelation (Entity)

Represents the ANR (Automatic Neighbor Relation) relationship between cells.

```typescript
interface NeighborRelation {
  // Identity
  relationId: NeighborRelationId;

  // Endpoints
  sourceCellDn: DistinguishedName;
  targetCellDn: DistinguishedName;

  // Neighbor Cell Info
  targetCellNCI: NRCellIdentity;
  targetPCI: number;
  targetARFCN: number;

  // Relation Type
  relationType: NeighborRelationType;
  isRemoveAllowed: boolean;
  isHOAllowed: boolean;

  // ANR State
  isBlocked: boolean;
  blockReason?: string;

  // Statistics (from ANR)
  handoverAttempts: number;
  handoverSuccesses: number;
  handoverFailures: number;
  lastHandoverTime?: Timestamp;

  // Lifecycle
  createdAt: Timestamp;
  createdBy: 'ANR' | 'MANUAL' | 'IMPORT';
  modifiedAt: Timestamp;
}

enum NeighborRelationType {
  INTRA_FREQUENCY = 'INTRA_FREQUENCY',
  INTER_FREQUENCY = 'INTER_FREQUENCY',
  INTER_RAT = 'INTER_RAT'
}

// Invariants:
// 1. sourceCellDn and targetCellDn MUST reference existing NRCellDU
// 2. targetPCI MUST match the PCI of the target cell
// 3. Handover counts MUST be non-negative
// 4. isHOAllowed=false implies no handover attempts
```

### 5. ConfigurationItem (Entity)

Represents a configurable parameter with drift detection.

```typescript
interface ConfigurationItem {
  // Identity
  itemId: string;
  dn: DistinguishedName;
  attributeName: string;

  // Values
  desiredValue: AttributeValue;
  actualValue?: AttributeValue;
  previousValue?: AttributeValue;

  // Drift Detection
  driftStatus: DriftStatus;
  driftDetectedAt?: Timestamp;
  driftDescription?: string;

  // Audit
  lastDesiredChange: Timestamp;
  lastDesiredChangeBy: string;
  lastSyncAttempt?: Timestamp;
  syncResult?: SyncResult;
}

enum DriftStatus {
  IN_SYNC = 'IN_SYNC',
  DRIFTED = 'DRIFTED',
  PENDING_SYNC = 'PENDING_SYNC',
  SYNC_FAILED = 'SYNC_FAILED',
  UNKNOWN = 'UNKNOWN'
}

interface SyncResult {
  success: boolean;
  timestamp: Timestamp;
  errorMessage?: string;
  retryCount: number;
}
```

## Domain Events

```typescript
// Managed Element Events
interface ManagedElementDiscovered {
  eventType: 'ManagedElementDiscovered';
  dn: string;
  elementType: ManagedElementType;
  discoveryMethod: 'O1' | 'IMPORT' | 'MANUAL';
  timestamp: Timestamp;
}

interface ManagedElementStateChanged {
  eventType: 'ManagedElementStateChanged';
  dn: string;
  previousState: { admin: AdministrativeState; operational: OperationalState };
  newState: { admin: AdministrativeState; operational: OperationalState };
  timestamp: Timestamp;
}

interface ManagedElementDeleted {
  eventType: 'ManagedElementDeleted';
  dn: string;
  reason: string;
  timestamp: Timestamp;
}

// Topology Events
interface TopologyUpdated {
  eventType: 'TopologyUpdated';
  graphId: string;
  changeType: 'NODE_ADDED' | 'NODE_REMOVED' | 'EDGE_ADDED' | 'EDGE_REMOVED' | 'ATTRIBUTE_CHANGED';
  affectedDns: string[];
  timestamp: Timestamp;
}

interface NeighborRelationCreated {
  eventType: 'NeighborRelationCreated';
  relationId: string;
  sourceCellDn: string;
  targetCellDn: string;
  createdBy: string;
  timestamp: Timestamp;
}

interface NeighborRelationModified {
  eventType: 'NeighborRelationModified';
  relationId: string;
  changes: Record<string, { old: any; new: any }>;
  timestamp: Timestamp;
}

// Configuration Events
interface ConfigurationDriftDetected {
  eventType: 'ConfigurationDriftDetected';
  dn: string;
  attributeName: string;
  desiredValue: any;
  actualValue: any;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  timestamp: Timestamp;
}

interface ConfigurationSynchronized {
  eventType: 'ConfigurationSynchronized';
  dn: string;
  attributeCount: number;
  result: 'SUCCESS' | 'PARTIAL' | 'FAILED';
  timestamp: Timestamp;
}
```

## Domain Services

### TopologyService

```typescript
interface TopologyService {
  /**
   * Get the current topology graph for a subnetwork
   */
  getTopology(subNetworkDn: DistinguishedName): Promise<TopologyGraph>;

  /**
   * Find shortest path between two elements
   */
  findPath(
    sourceDn: DistinguishedName,
    targetDn: DistinguishedName,
    edgeTypes?: TopologyEdgeType[]
  ): Promise<TopologyPath>;

  /**
   * Get neighbors within N hops
   */
  getNeighborhood(
    centerDn: DistinguishedName,
    maxHops: number
  ): Promise<TopologyGraph>;

  /**
   * Validate topology consistency
   */
  validateTopology(graphId: string): Promise<ValidationResult>;
}

interface TopologyPath {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  totalHops: number;
  pathCost?: number;
}
```

### InventorySyncService

```typescript
interface InventorySyncService {
  /**
   * Trigger full inventory synchronization for a managed element
   */
  syncElement(dn: DistinguishedName): Promise<SyncResult>;

  /**
   * Sync configuration attributes only
   */
  syncConfiguration(dn: DistinguishedName): Promise<SyncResult>;

  /**
   * Discover new elements via O1 interface
   */
  discoverElements(subNetworkDn: DistinguishedName): Promise<DiscoveryResult>;

  /**
   * Get sync status for an element
   */
  getSyncStatus(dn: DistinguishedName): Promise<SyncStatus>;
}

interface DiscoveryResult {
  discovered: DistinguishedName[];
  updated: DistinguishedName[];
  removed: DistinguishedName[];
  errors: DiscoveryError[];
}
```

### ANRService (Automatic Neighbor Relations)

```typescript
interface ANRService {
  /**
   * Create a neighbor relation manually
   */
  createNeighborRelation(
    sourceCellDn: DistinguishedName,
    targetCellDn: DistinguishedName,
    options?: NeighborOptions
  ): Promise<NeighborRelation>;

  /**
   * Update neighbor relation attributes
   */
  updateNeighborRelation(
    relationId: NeighborRelationId,
    updates: Partial<NeighborRelation>
  ): Promise<NeighborRelation>;

  /**
   * Block/unblock a neighbor relation
   */
  setNeighborBlocked(
    relationId: NeighborRelationId,
    blocked: boolean,
    reason?: string
  ): Promise<void>;

  /**
   * Get optimized neighbor list for a cell
   */
  getOptimizedNeighbors(
    cellDn: DistinguishedName
  ): Promise<NeighborRecommendation[]>;
}
```

## Repository Interfaces

```typescript
interface ManagedElementRepository {
  findByDn(dn: DistinguishedName): Promise<ManagedElement | null>;
  findByType(type: ManagedElementType): Promise<ManagedElement[]>;
  findByParent(parentDn: DistinguishedName): Promise<ManagedElement[]>;
  findInArea(geofence: GeoFence): Promise<ManagedElement[]>;
  save(element: ManagedElement): Promise<void>;
  delete(dn: DistinguishedName): Promise<void>;
}

interface TopologyGraphRepository {
  findById(graphId: string): Promise<TopologyGraph | null>;
  findBySubNetwork(subNetworkDn: DistinguishedName): Promise<TopologyGraph>;
  save(graph: TopologyGraph): Promise<void>;
  addNode(graphId: string, node: TopologyNode): Promise<void>;
  addEdge(graphId: string, edge: TopologyEdge): Promise<void>;
  removeNode(graphId: string, nodeId: string): Promise<void>;
  removeEdge(graphId: string, edgeId: string): Promise<void>;
}

interface NeighborRelationRepository {
  findById(id: NeighborRelationId): Promise<NeighborRelation | null>;
  findBySourceCell(cellDn: DistinguishedName): Promise<NeighborRelation[]>;
  findByTargetCell(cellDn: DistinguishedName): Promise<NeighborRelation[]>;
  findBlocked(): Promise<NeighborRelation[]>;
  save(relation: NeighborRelation): Promise<void>;
  delete(id: NeighborRelationId): Promise<void>;
}

interface ConfigurationItemRepository {
  findByDn(dn: DistinguishedName): Promise<ConfigurationItem[]>;
  findDrifted(): Promise<ConfigurationItem[]>;
  findPendingSync(): Promise<ConfigurationItem[]>;
  save(item: ConfigurationItem): Promise<void>;
  updateSyncResult(itemId: string, result: SyncResult): Promise<void>;
}
```

## Anti-Corruption Layer

### O1 Interface ACL (NETCONF/YANG)

```typescript
interface O1InterfaceACL {
  /**
   * Transform domain model to NETCONF edit-config request
   */
  toNetconfEditConfig(element: ManagedElement): NetconfRequest;

  /**
   * Transform NETCONF get-config response to domain model
   */
  fromNetconfGetConfig(response: NetconfResponse): ManagedElement;

  /**
   * Handle NETCONF notifications
   */
  handleNotification(notification: NetconfNotification): DomainEvent;

  /**
   * Build YANG filter from DN
   */
  buildYangFilter(dn: DistinguishedName): string;
}
```

### Graph Database ACL (RuVector/Cypher)

```typescript
interface GraphDatabaseACL {
  /**
   * Transform domain TopologyGraph to Cypher CREATE statements
   */
  toCypherCreate(graph: TopologyGraph): string[];

  /**
   * Transform Cypher query result to domain TopologyGraph
   */
  fromCypherResult(result: CypherResult): TopologyGraph;

  /**
   * Build Cypher path query
   */
  buildPathQuery(
    sourceDn: DistinguishedName,
    targetDn: DistinguishedName,
    edgeTypes: TopologyEdgeType[]
  ): string;
}
```

## Module Structure

```
network-inventory/
├── domain/
│   ├── aggregates/
│   │   ├── ManagedElement.ts
│   │   ├── TopologyGraph.ts
│   │   └── ConfigurationItem.ts
│   ├── entities/
│   │   ├── NRCellDU.ts
│   │   ├── GNBDUFunction.ts
│   │   └── NeighborRelation.ts
│   ├── value-objects/
│   │   ├── DistinguishedName.ts
│   │   ├── NRCellIdentity.ts
│   │   ├── GeoLocation.ts
│   │   └── AttributeValue.ts
│   ├── events/
│   │   └── index.ts
│   └── services/
│       ├── TopologyService.ts
│       ├── InventorySyncService.ts
│       └── ANRService.ts
├── application/
│   ├── commands/
│   │   ├── CreateManagedElementCommand.ts
│   │   ├── SyncInventoryCommand.ts
│   │   └── CreateNeighborRelationCommand.ts
│   ├── queries/
│   │   ├── GetTopologyQuery.ts
│   │   ├── FindPathQuery.ts
│   │   └── GetDriftedConfigsQuery.ts
│   └── handlers/
│       └── index.ts
├── infrastructure/
│   ├── repositories/
│   │   ├── PostgresManagedElementRepository.ts
│   │   ├── RuVectorTopologyRepository.ts
│   │   └── PostgresConfigurationRepository.ts
│   ├── acl/
│   │   ├── O1InterfaceACL.ts
│   │   └── GraphDatabaseACL.ts
│   └── clients/
│       ├── NetconfClient.ts
│       └── RuVectorClient.ts
└── api/
    ├── TopologyAPI.ts
    ├── InventoryAPI.ts
    └── ConfigurationAPI.ts
```
