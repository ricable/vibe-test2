/**
 * Consensus Protocols for Swarm Coordination
 *
 * Implements multiple consensus algorithms for distributed decision-making:
 * - Raft: Leader-based consensus (f < n/2 failure tolerance)
 * - Byzantine (BFT): Multi-stage voting (f < n/3 failure tolerance)
 * - Gossip: Epidemic information sharing
 * - Majority: Simple quorum-based voting
 * - Weighted: Expert-weighted voting
 *
 * @module consensus/protocols
 */

const EventEmitter = require('events');

/**
 * Consensus States
 */
const ConsensusState = {
  IDLE: 'idle',
  PROPOSING: 'proposing',
  VOTING: 'voting',
  COMMITTED: 'committed',
  ABORTED: 'aborted'
};

/**
 * Base Consensus Protocol
 */
class BaseConsensusProtocol extends EventEmitter {
  constructor(options = {}) {
    super();
    this.id = options.id || `consensus-${Date.now()}`;
    this.nodes = new Map();
    this.proposals = new Map();
    this.state = ConsensusState.IDLE;
    this.currentTerm = 0;

    this.config = {
      timeout: options.timeout || 5000,
      retries: options.retries || 3
    };
  }

  /**
   * Register a node in the consensus group
   */
  registerNode(nodeId, nodeInfo) {
    this.nodes.set(nodeId, {
      id: nodeId,
      ...nodeInfo,
      lastSeen: Date.now(),
      status: 'active'
    });
    this.emit('node:registered', { nodeId });
  }

  /**
   * Remove a node from the consensus group
   */
  removeNode(nodeId) {
    this.nodes.delete(nodeId);
    this.emit('node:removed', { nodeId });
  }

  /**
   * Get active node count
   */
  getActiveNodeCount() {
    return [...this.nodes.values()].filter(n => n.status === 'active').length;
  }

  /**
   * Propose a value for consensus
   * To be implemented by subclasses
   */
  async propose(value) {
    throw new Error('propose() must be implemented by subclass');
  }

  /**
   * Vote on a proposal
   * To be implemented by subclasses
   */
  async vote(proposalId, vote) {
    throw new Error('vote() must be implemented by subclass');
  }
}

/**
 * Raft Consensus Protocol
 * Leader-based consensus with strong consistency
 */
class RaftConsensus extends BaseConsensusProtocol {
  constructor(options = {}) {
    super(options);

    this.role = 'follower'; // follower, candidate, leader
    this.leaderId = null;
    this.votedFor = null;
    this.log = [];
    this.commitIndex = -1;
    this.lastApplied = -1;

    // Leader state
    this.nextIndex = new Map();
    this.matchIndex = new Map();

    // Timing
    this.electionTimeout = options.electionTimeout ||
      Math.random() * 150 + 150; // 150-300ms
    this.heartbeatInterval = options.heartbeatInterval || 50;

    this.electionTimer = null;
    this.heartbeatTimer = null;
  }

  /**
   * Start the Raft node
   */
  start() {
    this.resetElectionTimer();
    this.emit('started');
  }

  /**
   * Stop the Raft node
   */
  stop() {
    if (this.electionTimer) clearTimeout(this.electionTimer);
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.emit('stopped');
  }

  /**
   * Reset election timer
   */
  resetElectionTimer() {
    if (this.electionTimer) clearTimeout(this.electionTimer);

    this.electionTimer = setTimeout(() => {
      this.startElection();
    }, this.electionTimeout);
  }

  /**
   * Start leader election
   */
  async startElection() {
    this.currentTerm++;
    this.role = 'candidate';
    this.votedFor = this.id;

    let votes = 1; // Vote for self
    const majority = Math.floor(this.nodes.size / 2) + 1;

    this.emit('election:started', { term: this.currentTerm });

    // Request votes from all nodes
    const votePromises = [...this.nodes.keys()]
      .filter(nodeId => nodeId !== this.id)
      .map(nodeId => this.requestVote(nodeId));

    const results = await Promise.allSettled(votePromises);

    for (const result of results) {
      if (result.status === 'fulfilled' && result.value.voteGranted) {
        votes++;
      }
    }

    if (votes >= majority && this.role === 'candidate') {
      this.becomeLeader();
    } else {
      this.role = 'follower';
      this.resetElectionTimer();
    }
  }

  /**
   * Request vote from a node
   */
  async requestVote(nodeId) {
    // Simulate RPC
    this.emit('vote:requested', { nodeId, term: this.currentTerm });

    // In production, this would be actual network call
    return {
      term: this.currentTerm,
      voteGranted: true
    };
  }

  /**
   * Become leader
   */
  becomeLeader() {
    this.role = 'leader';
    this.leaderId = this.id;

    // Initialize leader state
    for (const nodeId of this.nodes.keys()) {
      this.nextIndex.set(nodeId, this.log.length);
      this.matchIndex.set(nodeId, -1);
    }

    // Start heartbeats
    this.heartbeatTimer = setInterval(() => {
      this.sendHeartbeats();
    }, this.heartbeatInterval);

    this.emit('leader:elected', { leaderId: this.id, term: this.currentTerm });
  }

  /**
   * Send heartbeats to all followers
   */
  async sendHeartbeats() {
    if (this.role !== 'leader') return;

    for (const nodeId of this.nodes.keys()) {
      if (nodeId !== this.id) {
        this.appendEntries(nodeId, []);
      }
    }
  }

  /**
   * Append entries RPC
   */
  async appendEntries(nodeId, entries) {
    this.emit('heartbeat:sent', { nodeId });
    return { success: true, term: this.currentTerm };
  }

  /**
   * Propose a value (client request)
   */
  async propose(value) {
    if (this.role !== 'leader') {
      throw new Error('Not the leader');
    }

    const entry = {
      term: this.currentTerm,
      index: this.log.length,
      value,
      timestamp: Date.now()
    };

    this.log.push(entry);

    // Replicate to followers
    const majority = Math.floor(this.nodes.size / 2) + 1;
    let replicated = 1;

    for (const nodeId of this.nodes.keys()) {
      if (nodeId !== this.id) {
        const result = await this.appendEntries(nodeId, [entry]);
        if (result.success) {
          replicated++;
          this.matchIndex.set(nodeId, entry.index);
        }
      }
    }

    if (replicated >= majority) {
      this.commitIndex = entry.index;
      this.emit('committed', { entry });
      return { success: true, entry };
    }

    return { success: false, reason: 'Failed to reach majority' };
  }
}

/**
 * Byzantine Fault Tolerant Consensus
 * Tolerates f < n/3 faulty nodes
 */
class ByzantineConsensus extends BaseConsensusProtocol {
  constructor(options = {}) {
    super(options);

    this.prepares = new Map();
    this.commits = new Map();
    this.view = 0;
    this.primaryId = null;

    this.config.f = options.f || Math.floor((options.nodeCount || 4) / 3);
  }

  /**
   * Calculate quorum size (2f + 1)
   */
  getQuorum() {
    return 2 * this.config.f + 1;
  }

  /**
   * Get primary for current view
   */
  getPrimary() {
    const nodes = [...this.nodes.keys()];
    return nodes[this.view % nodes.length];
  }

  /**
   * Propose a value (PRE-PREPARE phase)
   */
  async propose(value) {
    const proposalId = `proposal-${Date.now()}`;

    if (this.id !== this.getPrimary()) {
      throw new Error('Only primary can propose');
    }

    const proposal = {
      id: proposalId,
      view: this.view,
      value,
      timestamp: Date.now(),
      phase: 'pre-prepare'
    };

    this.proposals.set(proposalId, proposal);
    this.state = ConsensusState.PROPOSING;

    // Broadcast PRE-PREPARE
    this.emit('pre-prepare', { proposal });

    // Move to PREPARE phase
    return this.prepare(proposalId);
  }

  /**
   * PREPARE phase
   */
  async prepare(proposalId) {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) throw new Error('Proposal not found');

    proposal.phase = 'prepare';
    this.prepares.set(proposalId, new Set([this.id]));

    // Broadcast PREPARE
    this.emit('prepare', { proposalId, nodeId: this.id });

    // Wait for quorum
    return this.waitForQuorum(proposalId, 'prepare');
  }

  /**
   * Receive PREPARE message
   */
  async receivePrepare(proposalId, nodeId) {
    let prepares = this.prepares.get(proposalId);
    if (!prepares) {
      prepares = new Set();
      this.prepares.set(proposalId, prepares);
    }

    prepares.add(nodeId);

    // Check if quorum reached
    if (prepares.size >= this.getQuorum()) {
      this.emit('prepare:quorum', { proposalId });
      return this.commit(proposalId);
    }
  }

  /**
   * COMMIT phase
   */
  async commit(proposalId) {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) throw new Error('Proposal not found');

    proposal.phase = 'commit';
    this.commits.set(proposalId, new Set([this.id]));

    // Broadcast COMMIT
    this.emit('commit', { proposalId, nodeId: this.id });

    // Wait for quorum
    return this.waitForQuorum(proposalId, 'commit');
  }

  /**
   * Receive COMMIT message
   */
  async receiveCommit(proposalId, nodeId) {
    let commits = this.commits.get(proposalId);
    if (!commits) {
      commits = new Set();
      this.commits.set(proposalId, commits);
    }

    commits.add(nodeId);

    // Check if quorum reached
    if (commits.size >= this.getQuorum()) {
      const proposal = this.proposals.get(proposalId);
      this.state = ConsensusState.COMMITTED;
      this.emit('committed', { proposal });
      return { success: true, proposal };
    }
  }

  /**
   * Wait for quorum
   */
  async waitForQuorum(proposalId, phase) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Timeout waiting for ${phase} quorum`));
      }, this.config.timeout);

      const handler = (data) => {
        if (data.proposalId === proposalId) {
          clearTimeout(timeout);
          resolve(data);
        }
      };

      this.once(`${phase}:quorum`, handler);
    });
  }

  /**
   * View change (leader failure recovery)
   */
  async viewChange() {
    this.view++;
    this.primaryId = this.getPrimary();
    this.emit('view:changed', { view: this.view, primary: this.primaryId });
  }
}

/**
 * Gossip Protocol
 * Epidemic information sharing for eventual consistency
 */
class GossipProtocol extends BaseConsensusProtocol {
  constructor(options = {}) {
    super(options);

    this.state = new Map(); // Key-value state
    this.vectorClock = new Map();
    this.fanout = options.fanout || 3; // Number of nodes to gossip to
    this.gossipInterval = options.gossipInterval || 100;
    this.gossipTimer = null;
  }

  /**
   * Start gossiping
   */
  start() {
    this.gossipTimer = setInterval(() => {
      this.gossip();
    }, this.gossipInterval);
    this.emit('started');
  }

  /**
   * Stop gossiping
   */
  stop() {
    if (this.gossipTimer) {
      clearInterval(this.gossipTimer);
    }
    this.emit('stopped');
  }

  /**
   * Update local state
   */
  async propose(key, value) {
    // Increment vector clock
    const clock = this.vectorClock.get(this.id) || 0;
    this.vectorClock.set(this.id, clock + 1);

    // Update state
    this.state.set(key, {
      value,
      version: this.vectorClock.get(this.id),
      nodeId: this.id,
      timestamp: Date.now()
    });

    this.emit('state:updated', { key, value });
    return { success: true };
  }

  /**
   * Gossip state to random nodes
   */
  async gossip() {
    const nodes = [...this.nodes.keys()].filter(n => n !== this.id);

    // Select random nodes (fanout)
    const targets = this.selectRandom(nodes, this.fanout);

    for (const nodeId of targets) {
      await this.sendGossip(nodeId);
    }
  }

  /**
   * Send gossip to a node
   */
  async sendGossip(nodeId) {
    const digest = this.getStateDigest();
    this.emit('gossip:sent', { nodeId, digest });

    // In production, this would send actual message
    return { success: true };
  }

  /**
   * Receive gossip from another node
   */
  async receiveGossip(digest, fromNode) {
    const updates = [];

    for (const [key, theirEntry] of digest) {
      const ourEntry = this.state.get(key);

      if (!ourEntry || this.isNewer(theirEntry, ourEntry)) {
        this.state.set(key, theirEntry);
        updates.push({ key, value: theirEntry.value });
      }
    }

    if (updates.length > 0) {
      this.emit('state:merged', { updates, fromNode });
    }
  }

  /**
   * Check if entry A is newer than entry B
   */
  isNewer(a, b) {
    if (a.version > b.version) return true;
    if (a.version === b.version && a.timestamp > b.timestamp) return true;
    return false;
  }

  /**
   * Get state digest
   */
  getStateDigest() {
    return new Map(this.state);
  }

  /**
   * Select random elements from array
   */
  selectRandom(arr, count) {
    const shuffled = [...arr].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, Math.min(count, arr.length));
  }

  /**
   * Get current state
   */
  getState() {
    const result = {};
    for (const [key, entry] of this.state) {
      result[key] = entry.value;
    }
    return result;
  }
}

/**
 * Majority Voting Consensus
 * Simple quorum-based voting (n/2 + 1)
 */
class MajorityConsensus extends BaseConsensusProtocol {
  constructor(options = {}) {
    super(options);
    this.votes = new Map();
  }

  /**
   * Get majority threshold
   */
  getMajority() {
    return Math.floor(this.nodes.size / 2) + 1;
  }

  /**
   * Propose a value for voting
   */
  async propose(value) {
    const proposalId = `proposal-${Date.now()}`;

    const proposal = {
      id: proposalId,
      value,
      timestamp: Date.now(),
      votes: { approve: 0, reject: 0 }
    };

    this.proposals.set(proposalId, proposal);
    this.votes.set(proposalId, new Map());
    this.state = ConsensusState.PROPOSING;

    this.emit('proposal:created', { proposal });

    // Self-vote
    await this.vote(proposalId, 'approve');

    return { proposalId, proposal };
  }

  /**
   * Vote on a proposal
   */
  async vote(proposalId, voteValue, nodeId = this.id) {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) throw new Error('Proposal not found');

    const proposalVotes = this.votes.get(proposalId);
    if (proposalVotes.has(nodeId)) {
      throw new Error('Node already voted');
    }

    proposalVotes.set(nodeId, voteValue);
    proposal.votes[voteValue]++;

    this.emit('vote:received', { proposalId, nodeId, vote: voteValue });

    // Check for majority
    if (proposal.votes.approve >= this.getMajority()) {
      this.state = ConsensusState.COMMITTED;
      this.emit('committed', { proposal });
      return { success: true, result: 'approved', proposal };
    }

    if (proposal.votes.reject >= this.getMajority()) {
      this.state = ConsensusState.ABORTED;
      this.emit('aborted', { proposal });
      return { success: true, result: 'rejected', proposal };
    }

    return { success: true, result: 'pending' };
  }
}

/**
 * Weighted Voting Consensus
 * Expert-weighted voting (e.g., Queen 3x weight)
 */
class WeightedConsensus extends BaseConsensusProtocol {
  constructor(options = {}) {
    super(options);
    this.weights = new Map();
    this.defaultWeight = options.defaultWeight || 1;
    this.votes = new Map();
  }

  /**
   * Set node weight
   */
  setWeight(nodeId, weight) {
    this.weights.set(nodeId, weight);
  }

  /**
   * Get node weight
   */
  getWeight(nodeId) {
    return this.weights.get(nodeId) || this.defaultWeight;
  }

  /**
   * Get total weight
   */
  getTotalWeight() {
    let total = 0;
    for (const nodeId of this.nodes.keys()) {
      total += this.getWeight(nodeId);
    }
    return total;
  }

  /**
   * Get weighted majority threshold
   */
  getMajority() {
    return Math.floor(this.getTotalWeight() / 2) + 1;
  }

  /**
   * Propose a value for weighted voting
   */
  async propose(value) {
    const proposalId = `proposal-${Date.now()}`;

    const proposal = {
      id: proposalId,
      value,
      timestamp: Date.now(),
      votes: { approve: 0, reject: 0 },
      weightedVotes: { approve: 0, reject: 0 }
    };

    this.proposals.set(proposalId, proposal);
    this.votes.set(proposalId, new Map());
    this.state = ConsensusState.PROPOSING;

    this.emit('proposal:created', { proposal });

    return { proposalId, proposal };
  }

  /**
   * Vote with weight
   */
  async vote(proposalId, voteValue, nodeId = this.id) {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) throw new Error('Proposal not found');

    const proposalVotes = this.votes.get(proposalId);
    if (proposalVotes.has(nodeId)) {
      throw new Error('Node already voted');
    }

    const weight = this.getWeight(nodeId);
    proposalVotes.set(nodeId, { vote: voteValue, weight });

    proposal.votes[voteValue]++;
    proposal.weightedVotes[voteValue] += weight;

    this.emit('vote:received', {
      proposalId,
      nodeId,
      vote: voteValue,
      weight
    });

    // Check for weighted majority
    if (proposal.weightedVotes.approve >= this.getMajority()) {
      this.state = ConsensusState.COMMITTED;
      this.emit('committed', { proposal });
      return { success: true, result: 'approved', proposal };
    }

    const remainingWeight = this.getTotalWeight() -
      proposal.weightedVotes.approve - proposal.weightedVotes.reject;

    if (proposal.weightedVotes.reject + remainingWeight < this.getMajority()) {
      this.state = ConsensusState.ABORTED;
      this.emit('aborted', { proposal });
      return { success: true, result: 'rejected', proposal };
    }

    return { success: true, result: 'pending' };
  }
}

/**
 * Consensus Factory
 * Creates appropriate consensus protocol based on requirements
 */
class ConsensusFactory {
  static create(type, options = {}) {
    switch (type.toLowerCase()) {
      case 'raft':
        return new RaftConsensus(options);
      case 'byzantine':
      case 'bft':
        return new ByzantineConsensus(options);
      case 'gossip':
        return new GossipProtocol(options);
      case 'majority':
        return new MajorityConsensus(options);
      case 'weighted':
        return new WeightedConsensus(options);
      default:
        throw new Error(`Unknown consensus type: ${type}`);
    }
  }

  /**
   * Get recommended protocol based on requirements
   */
  static recommend(requirements) {
    const { failureTolerance, consistency, latency, security } = requirements;

    if (security === 'high' || failureTolerance === 'byzantine') {
      return 'byzantine';
    }

    if (consistency === 'eventual' && latency === 'low') {
      return 'gossip';
    }

    if (consistency === 'strong') {
      return 'raft';
    }

    if (requirements.weighted) {
      return 'weighted';
    }

    return 'majority';
  }
}

module.exports = {
  ConsensusState,
  BaseConsensusProtocol,
  RaftConsensus,
  ByzantineConsensus,
  GossipProtocol,
  MajorityConsensus,
  WeightedConsensus,
  ConsensusFactory
};
