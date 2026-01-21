/**
 * Agentic Reasoning Swarm - Main Entry Point
 *
 * A comprehensive framework for autonomous development swarms implementing:
 * - Three dimensions of agentic reasoning (Foundational, Self-Evolving, Structured)
 * - OODA Loop decision cycles
 * - SONA (Self-Optimizing Neural Architecture) intelligence
 * - Hierarchical mesh coordination with consensus protocols
 * - MoE (Mixture of Experts) task routing
 *
 * @module swarm
 */

// Core reasoning components
const { OODALoop, OODAState, GOAPPlanner } = require('./reasoning/ooda-loop');

// Neural intelligence
const { SONAEngine, SONAStage, VerdictType, ReasoningBank } = require('./neural/sona-engine');

// Consensus protocols
const {
  ConsensusState,
  RaftConsensus,
  ByzantineConsensus,
  GossipProtocol,
  MajorityConsensus,
  WeightedConsensus,
  ConsensusFactory
} = require('./consensus/protocols');

// Memory management
const { PatternStore, TableType, EventType, LRUCache } = require('./memory/pattern-store');

// Swarm coordination
const {
  SwarmCoordinator,
  TopologyType,
  AgentRole,
  StrategyType,
  AgentConfig,
  MixtureOfExpertsRouter
} = require('./agents/swarm-coordinator');

/**
 * Create a fully configured swarm instance
 * @param {Object} options - Configuration options
 * @returns {SwarmCoordinator} Configured swarm coordinator
 */
function createSwarm(options = {}) {
  const swarm = new SwarmCoordinator({
    topology: options.topology || TopologyType.HIERARCHICAL_MESH,
    strategy: options.strategy || StrategyType.SPECIALIZED,
    maxAgents: options.maxAgents || 15,
    consensusProtocol: options.consensusProtocol || 'raft',
    ...options
  });

  return swarm;
}

/**
 * Create a pre-configured development swarm
 * Includes: Queen, Coder, Tester, Reviewer, Researcher, Architect
 */
async function createDevelopmentSwarm(options = {}) {
  const swarm = createSwarm({
    id: 'dev-swarm',
    topology: TopologyType.HIERARCHICAL_MESH,
    strategy: StrategyType.SPECIALIZED,
    maxAgents: 15,
    ...options
  });

  await swarm.initialize();

  // Spawn core development agents
  const agents = [
    { role: AgentRole.QUEEN, priority: 'critical', weight: 3, capabilities: ['coordination', 'planning', 'consensus'] },
    { role: AgentRole.CODER, priority: 'high', capabilities: ['implementation', 'debugging', 'refactoring'] },
    { role: AgentRole.TESTER, priority: 'high', capabilities: ['testing', 'tdd', 'mocking'] },
    { role: AgentRole.REVIEWER, priority: 'high', capabilities: ['code-review', 'security', 'best-practices'] },
    { role: AgentRole.RESEARCHER, priority: 'normal', capabilities: ['research', 'analysis', 'documentation'] },
    { role: AgentRole.ARCHITECT, priority: 'high', capabilities: ['design', 'architecture', 'patterns'] }
  ];

  await swarm.spawnAgentsBatch(agents);

  return swarm;
}

/**
 * Create a security-focused swarm
 * Includes specialized security agents with Byzantine consensus
 */
async function createSecuritySwarm(options = {}) {
  const swarm = createSwarm({
    id: 'security-swarm',
    topology: TopologyType.HIERARCHICAL,
    strategy: StrategyType.SPECIALIZED,
    consensusProtocol: 'byzantine',
    maxAgents: 10,
    ...options
  });

  await swarm.initialize();

  const agents = [
    { role: AgentRole.QUEEN, priority: 'critical', weight: 3, capabilities: ['coordination', 'threat-assessment'] },
    { role: AgentRole.SECURITY, priority: 'critical', capabilities: ['vulnerability-scanning', 'cve-detection', 'penetration-testing'] },
    { role: AgentRole.REVIEWER, priority: 'high', capabilities: ['security-review', 'code-audit'] },
    { role: AgentRole.CODER, priority: 'normal', capabilities: ['remediation', 'secure-coding'] }
  ];

  await swarm.spawnAgentsBatch(agents);

  return swarm;
}

/**
 * Swarm Builder - Fluent API for swarm configuration
 */
class SwarmBuilder {
  constructor() {
    this.config = {
      topology: TopologyType.HIERARCHICAL_MESH,
      strategy: StrategyType.SPECIALIZED,
      maxAgents: 15,
      consensusProtocol: 'raft',
      agents: []
    };
  }

  withTopology(topology) {
    this.config.topology = topology;
    return this;
  }

  withStrategy(strategy) {
    this.config.strategy = strategy;
    return this;
  }

  withMaxAgents(max) {
    this.config.maxAgents = max;
    return this;
  }

  withConsensus(protocol) {
    this.config.consensusProtocol = protocol;
    return this;
  }

  addAgent(role, options = {}) {
    this.config.agents.push({ role, ...options });
    return this;
  }

  addQueen(options = {}) {
    return this.addAgent(AgentRole.QUEEN, { priority: 'critical', weight: 3, ...options });
  }

  addCoder(options = {}) {
    return this.addAgent(AgentRole.CODER, { priority: 'high', ...options });
  }

  addTester(options = {}) {
    return this.addAgent(AgentRole.TESTER, { priority: 'high', ...options });
  }

  addReviewer(options = {}) {
    return this.addAgent(AgentRole.REVIEWER, { priority: 'high', ...options });
  }

  addResearcher(options = {}) {
    return this.addAgent(AgentRole.RESEARCHER, { priority: 'normal', ...options });
  }

  addArchitect(options = {}) {
    return this.addAgent(AgentRole.ARCHITECT, { priority: 'high', ...options });
  }

  addSecurity(options = {}) {
    return this.addAgent(AgentRole.SECURITY, { priority: 'critical', ...options });
  }

  async build() {
    const swarm = createSwarm(this.config);
    await swarm.initialize();

    if (this.config.agents.length > 0) {
      await swarm.spawnAgentsBatch(this.config.agents);
    }

    return swarm;
  }
}

/**
 * Quick start helper - creates and initializes a swarm with sensible defaults
 */
async function quickStart(taskDescription, options = {}) {
  const swarm = await createDevelopmentSwarm(options);

  // Submit the initial task
  const result = await swarm.submitTask({
    description: taskDescription,
    priority: options.priority || 'normal'
  });

  return { swarm, taskResult: result };
}

// Export all modules
module.exports = {
  // Factory functions
  createSwarm,
  createDevelopmentSwarm,
  createSecuritySwarm,
  quickStart,

  // Builder
  SwarmBuilder,

  // Reasoning
  OODALoop,
  OODAState,
  GOAPPlanner,

  // Neural
  SONAEngine,
  SONAStage,
  VerdictType,
  ReasoningBank,

  // Consensus
  ConsensusState,
  ConsensusFactory,
  RaftConsensus,
  ByzantineConsensus,
  GossipProtocol,
  MajorityConsensus,
  WeightedConsensus,

  // Memory
  PatternStore,
  TableType,
  EventType,
  LRUCache,

  // Coordination
  SwarmCoordinator,
  TopologyType,
  AgentRole,
  StrategyType,
  AgentConfig,
  MixtureOfExpertsRouter
};
