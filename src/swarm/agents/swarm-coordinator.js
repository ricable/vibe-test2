/**
 * Swarm Coordinator - Unified Agent Orchestration
 *
 * Manages the hierarchical mesh of up to 64 specialized agents with:
 * - Dynamic topology switching
 * - Consensus-based decision gating
 * - MoE (Mixture of Experts) routing
 * - Anti-drift protocols
 *
 * Implements the "1 Message = All Operations" paradigm for optimal performance.
 *
 * @module agents/swarm-coordinator
 */

const EventEmitter = require('events');
const { OODALoop } = require('../reasoning/ooda-loop');
const { SONAEngine } = require('../neural/sona-engine');
const { ConsensusFactory } = require('../consensus/protocols');
const { PatternStore } = require('../memory/pattern-store');

/**
 * Swarm Topology Types
 */
const TopologyType = {
  HIERARCHICAL: 'hierarchical',
  HIERARCHICAL_MESH: 'hierarchical-mesh',
  MESH: 'mesh',
  RING: 'ring',
  STAR: 'star',
  HYBRID: 'hybrid'
};

/**
 * Agent Roles
 */
const AgentRole = {
  QUEEN: 'queen',
  COORDINATOR: 'coordinator',
  CODER: 'coder',
  TESTER: 'tester',
  REVIEWER: 'reviewer',
  RESEARCHER: 'researcher',
  ARCHITECT: 'architect',
  SECURITY: 'security',
  DEVOPS: 'devops',
  PERFORMANCE: 'performance',
  SCOUT: 'scout',
  WORKER: 'worker'
};

/**
 * Strategy Types
 */
const StrategyType = {
  SPECIALIZED: 'specialized',
  BALANCED: 'balanced',
  ADAPTIVE: 'adaptive'
};

/**
 * Agent Configuration Template
 */
class AgentConfig {
  constructor(options = {}) {
    this.id = options.id || `agent-${Date.now()}`;
    this.role = options.role || AgentRole.WORKER;
    this.capabilities = options.capabilities || [];
    this.priority = options.priority || 'normal';
    this.weight = options.weight || 1;
    this.status = 'idle';
    this.currentTask = null;
    this.metrics = {
      tasksCompleted: 0,
      tasksFailed: 0,
      avgCompletionTime: 0,
      successRate: 0
    };
  }
}

/**
 * Swarm Coordinator
 * Central orchestrator for multi-agent coordination
 */
class SwarmCoordinator extends EventEmitter {
  constructor(options = {}) {
    super();

    this.id = options.id || `swarm-${Date.now()}`;
    this.topology = options.topology || TopologyType.HIERARCHICAL_MESH;
    this.strategy = options.strategy || StrategyType.SPECIALIZED;
    this.maxAgents = options.maxAgents || 15;

    // Core components
    this.agents = new Map();
    this.queen = null;
    this.taskQueue = [];
    this.activeAasks = new Map();

    // Intelligence systems
    this.oodaLoop = new OODALoop({
      id: `${this.id}-ooda`,
      agentId: this.id
    });

    this.sonaEngine = new SONAEngine({
      id: `${this.id}-sona`
    });

    this.patternStore = new PatternStore({
      id: `${this.id}-memory`
    });

    // Consensus protocol (default: raft for anti-drift)
    this.consensus = ConsensusFactory.create(
      options.consensusProtocol || 'raft',
      { id: `${this.id}-consensus` }
    );

    // MoE Router for task-to-agent assignment
    this.moeRouter = new MixtureOfExpertsRouter();

    // Metrics
    this.metrics = {
      totalTasksProcessed: 0,
      avgProcessingTime: 0,
      agentUtilization: 0,
      consensusSuccessRate: 0,
      patternMatchRate: 0
    };

    // Configuration
    this.config = {
      consensusGating: options.consensusGating !== false,
      antiDrift: options.antiDrift !== false,
      parallelExecution: options.parallelExecution !== false,
      maxConcurrentTasks: options.maxConcurrentTasks || 10,
      taskTimeout: options.taskTimeout || 60000
    };

    this.initialized = false;
  }

  /**
   * Initialize the swarm
   */
  async initialize() {
    if (this.initialized) return;

    // Start consensus protocol
    if (this.consensus.start) {
      this.consensus.start();
    }

    // Register this coordinator as the queen node
    this.consensus.registerNode(this.id, {
      role: 'coordinator',
      weight: 3 // Queen has 3x voting weight
    });

    this.initialized = true;
    this.emit('initialized', { swarmId: this.id, topology: this.topology });

    return { success: true, swarmId: this.id };
  }

  /**
   * Spawn a new agent
   */
  async spawnAgent(config) {
    if (this.agents.size >= this.maxAgents) {
      throw new Error(`Maximum agent limit (${this.maxAgents}) reached`);
    }

    const agent = new AgentConfig(config);

    // Register with consensus
    this.consensus.registerNode(agent.id, {
      role: agent.role,
      weight: agent.weight
    });

    // Add to agents map
    this.agents.set(agent.id, agent);

    // If this is the first queen, set it
    if (agent.role === AgentRole.QUEEN && !this.queen) {
      this.queen = agent;
    }

    // Register capabilities with MoE router
    this.moeRouter.registerExpert(agent.id, agent.role, agent.capabilities);

    // Store pattern for this agent type
    await this.patternStore.storePattern({
      id: `agent-spawn-${agent.role}`,
      domain: 'agent-management',
      tags: ['spawn', agent.role],
      content: { role: agent.role, capabilities: agent.capabilities }
    });

    this.emit('agent:spawned', { agentId: agent.id, role: agent.role });

    return { success: true, agentId: agent.id };
  }

  /**
   * Spawn multiple agents in parallel (1 Message = All Operations)
   */
  async spawnAgentsBatch(configs) {
    const results = await Promise.all(
      configs.map(config => this.spawnAgent(config))
    );

    this.emit('agents:batch-spawned', {
      count: results.length,
      agents: results.map(r => r.agentId)
    });

    return results;
  }

  /**
   * Route a task to the optimal agent using MoE
   */
  async routeTask(task) {
    // Use SONA to find similar past patterns
    const patterns = await this.sonaEngine.retrieve(task);

    // Use MoE router to find best agent
    const routingResult = this.moeRouter.route(task, {
      patterns,
      availableAgents: this.getAvailableAgents()
    });

    return routingResult;
  }

  /**
   * Submit a task to the swarm
   */
  async submitTask(task) {
    const taskId = task.id || `task-${Date.now()}`;

    // Run OODA cycle for task planning
    const oodaResult = await this.oodaLoop.executeCycle({
      task,
      swarmState: this.getSwarmState()
    });

    // Route to optimal agent
    const routing = await this.routeTask(task);

    // If consensus gating is enabled, propose the task assignment
    if (this.config.consensusGating && task.requiresConsensus) {
      const proposal = await this.consensus.propose({
        type: 'task-assignment',
        taskId,
        agentId: routing.agentId,
        task
      });

      if (!proposal.success) {
        return { success: false, reason: 'Consensus not reached' };
      }
    }

    // Assign task to agent
    const agent = this.agents.get(routing.agentId);
    if (!agent) {
      return { success: false, reason: 'No available agent' };
    }

    agent.status = 'busy';
    agent.currentTask = taskId;

    this.activeAasks.set(taskId, {
      id: taskId,
      task,
      agentId: routing.agentId,
      startTime: Date.now(),
      status: 'running'
    });

    this.emit('task:assigned', { taskId, agentId: routing.agentId });

    return {
      success: true,
      taskId,
      agentId: routing.agentId,
      routing
    };
  }

  /**
   * Complete a task
   */
  async completeTask(taskId, result) {
    const taskInfo = this.activeAasks.get(taskId);
    if (!taskInfo) {
      return { success: false, reason: 'Task not found' };
    }

    const agent = this.agents.get(taskInfo.agentId);
    const completionTime = Date.now() - taskInfo.startTime;

    // Update agent metrics
    if (agent) {
      agent.status = 'idle';
      agent.currentTask = null;

      if (result.success) {
        agent.metrics.tasksCompleted++;
      } else {
        agent.metrics.tasksFailed++;
      }

      const total = agent.metrics.tasksCompleted + agent.metrics.tasksFailed;
      agent.metrics.successRate = agent.metrics.tasksCompleted / total;
      agent.metrics.avgCompletionTime =
        (agent.metrics.avgCompletionTime * (total - 1) + completionTime) / total;
    }

    // Record outcome with SONA for learning
    await this.sonaEngine.recordOutcome(taskId, result);

    // Store trajectory for future learning
    await this.patternStore.storeTrajectory({
      taskId,
      agentId: taskInfo.agentId,
      task: taskInfo.task,
      result,
      completionTime
    });

    this.activeAasks.delete(taskId);
    this.metrics.totalTasksProcessed++;

    this.emit('task:completed', { taskId, result, completionTime });

    return { success: true };
  }

  /**
   * Get available agents for task assignment
   */
  getAvailableAgents() {
    return [...this.agents.values()].filter(a => a.status === 'idle');
  }

  /**
   * Get swarm state
   */
  getSwarmState() {
    return {
      id: this.id,
      topology: this.topology,
      strategy: this.strategy,
      agentCount: this.agents.size,
      activeTaskCount: this.activeAasks.size,
      queuedTaskCount: this.taskQueue.length,
      metrics: this.metrics,
      agents: [...this.agents.values()].map(a => ({
        id: a.id,
        role: a.role,
        status: a.status,
        metrics: a.metrics
      }))
    };
  }

  /**
   * Update topology dynamically
   */
  async updateTopology(newTopology) {
    const oldTopology = this.topology;
    this.topology = newTopology;

    // Reconfigure consensus based on topology
    if (newTopology === TopologyType.HIERARCHICAL) {
      // Use Raft for hierarchical (strong leader)
      this.consensus = ConsensusFactory.create('raft');
    } else if (newTopology === TopologyType.MESH) {
      // Use gossip for mesh (eventual consistency)
      this.consensus = ConsensusFactory.create('gossip');
    }

    // Re-register all agents
    for (const agent of this.agents.values()) {
      this.consensus.registerNode(agent.id, {
        role: agent.role,
        weight: agent.weight
      });
    }

    this.emit('topology:changed', { from: oldTopology, to: newTopology });

    return { success: true };
  }

  /**
   * Broadcast message to all agents
   */
  async broadcast(message) {
    for (const agent of this.agents.values()) {
      this.emit('message:broadcast', { agentId: agent.id, message });
    }

    // Store in shared state
    await this.patternStore.writeSharedState(
      `broadcast/${Date.now()}`,
      message,
      { type: 'broadcast' }
    );
  }

  /**
   * Stop an agent
   */
  async stopAgent(agentId) {
    const agent = this.agents.get(agentId);
    if (!agent) {
      return { success: false, reason: 'Agent not found' };
    }

    // Remove from consensus
    this.consensus.removeNode(agentId);

    // Remove from MoE router
    this.moeRouter.removeExpert(agentId);

    // Remove from agents map
    this.agents.delete(agentId);

    this.emit('agent:stopped', { agentId });

    return { success: true };
  }

  /**
   * Shutdown the swarm
   */
  async shutdown() {
    // Stop all agents
    for (const agentId of this.agents.keys()) {
      await this.stopAgent(agentId);
    }

    // Stop consensus
    if (this.consensus.stop) {
      this.consensus.stop();
    }

    this.initialized = false;
    this.emit('shutdown');

    return { success: true };
  }

  /**
   * Get comprehensive metrics
   */
  getMetrics() {
    const agentMetrics = [...this.agents.values()].map(a => ({
      id: a.id,
      role: a.role,
      ...a.metrics
    }));

    const busyAgents = [...this.agents.values()].filter(a => a.status === 'busy').length;
    this.metrics.agentUtilization = busyAgents / Math.max(1, this.agents.size);

    return {
      swarm: this.metrics,
      agents: agentMetrics,
      memory: this.patternStore.getMetrics(),
      sona: this.sonaEngine.getMetrics(),
      ooda: this.oodaLoop.getMetrics()
    };
  }
}

/**
 * Mixture of Experts Router
 * Routes tasks to optimal agents based on task domain and agent capabilities
 */
class MixtureOfExpertsRouter {
  constructor() {
    this.experts = new Map();
    this.domainMapping = {
      'code': [AgentRole.CODER, AgentRole.ARCHITECT],
      'test': [AgentRole.TESTER],
      'review': [AgentRole.REVIEWER],
      'security': [AgentRole.SECURITY],
      'research': [AgentRole.RESEARCHER],
      'deploy': [AgentRole.DEVOPS],
      'performance': [AgentRole.PERFORMANCE],
      'general': [AgentRole.WORKER]
    };

    this.routingAccuracy = 0.95; // Target: 95%+ routing accuracy
  }

  /**
   * Register an expert (agent)
   */
  registerExpert(agentId, role, capabilities) {
    this.experts.set(agentId, {
      id: agentId,
      role,
      capabilities,
      load: 0,
      successRate: 1.0
    });
  }

  /**
   * Remove an expert
   */
  removeExpert(agentId) {
    this.experts.delete(agentId);
  }

  /**
   * Route task to optimal agent
   */
  route(task, context = {}) {
    const { patterns = [], availableAgents = [] } = context;

    // Detect task domain
    const domain = this.detectDomain(task);

    // Get candidate roles for this domain
    const candidateRoles = this.domainMapping[domain] || this.domainMapping.general;

    // Filter available agents by role
    const candidates = availableAgents.filter(agent =>
      candidateRoles.includes(agent.role)
    );

    if (candidates.length === 0) {
      // Fallback to any available agent
      return {
        agentId: availableAgents[0]?.id,
        domain,
        confidence: 0.5,
        reason: 'fallback-no-specialist'
      };
    }

    // Score candidates
    const scored = candidates.map(agent => ({
      agent,
      score: this.scoreCandidate(agent, task, patterns)
    }));

    // Sort by score
    scored.sort((a, b) => b.score - a.score);
    const best = scored[0];

    return {
      agentId: best.agent.id,
      domain,
      confidence: best.score,
      reason: `best-match-${best.agent.role}`,
      alternatives: scored.slice(1, 3).map(s => ({
        agentId: s.agent.id,
        score: s.score
      }))
    };
  }

  /**
   * Detect task domain
   */
  detectDomain(task) {
    const description = (task.description || task.prompt || '').toLowerCase();

    // Simple keyword matching (replace with ML classifier in production)
    if (description.includes('test') || description.includes('spec')) {
      return 'test';
    }
    if (description.includes('review') || description.includes('check')) {
      return 'review';
    }
    if (description.includes('security') || description.includes('vulnerability')) {
      return 'security';
    }
    if (description.includes('research') || description.includes('investigate')) {
      return 'research';
    }
    if (description.includes('deploy') || description.includes('release')) {
      return 'deploy';
    }
    if (description.includes('performance') || description.includes('optimize')) {
      return 'performance';
    }
    if (description.includes('implement') || description.includes('code') ||
        description.includes('build') || description.includes('create')) {
      return 'code';
    }

    return 'general';
  }

  /**
   * Score a candidate agent for a task
   */
  scoreCandidate(agent, task, patterns) {
    let score = 0.5;

    // Boost for matching past patterns
    const patternMatch = patterns.find(p =>
      p.metadata?.domain === this.detectDomain(task)
    );
    if (patternMatch) {
      score += 0.2 * patternMatch.similarity;
    }

    // Boost for high success rate
    score += agent.metrics?.successRate * 0.2 || 0;

    // Slight penalty for high load
    const expert = this.experts.get(agent.id);
    if (expert) {
      score -= expert.load * 0.1;
    }

    return Math.min(1, Math.max(0, score));
  }
}

module.exports = {
  SwarmCoordinator,
  TopologyType,
  AgentRole,
  StrategyType,
  AgentConfig,
  MixtureOfExpertsRouter
};
