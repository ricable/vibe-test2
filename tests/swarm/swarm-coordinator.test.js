/**
 * Tests for Swarm Coordinator
 *
 * @jest-environment node
 */

const {
  SwarmCoordinator,
  TopologyType,
  AgentRole,
  StrategyType,
  createSwarm,
  createDevelopmentSwarm,
  SwarmBuilder
} = require('../../src/swarm');

describe('SwarmCoordinator', () => {
  let swarm;

  beforeEach(() => {
    swarm = new SwarmCoordinator({
      id: 'test-swarm',
      topology: TopologyType.HIERARCHICAL_MESH,
      strategy: StrategyType.SPECIALIZED,
      maxAgents: 10
    });
  });

  afterEach(async () => {
    if (swarm.initialized) {
      await swarm.shutdown();
    }
  });

  describe('initialization', () => {
    it('should initialize with default configuration', async () => {
      const result = await swarm.initialize();

      expect(result.success).toBe(true);
      expect(result.swarmId).toBe('test-swarm');
      expect(swarm.initialized).toBe(true);
    });

    it('should not reinitialize if already initialized', async () => {
      await swarm.initialize();
      await swarm.initialize(); // Second call should be no-op

      expect(swarm.initialized).toBe(true);
    });

    it('should set correct topology', () => {
      expect(swarm.topology).toBe(TopologyType.HIERARCHICAL_MESH);
    });

    it('should set correct strategy', () => {
      expect(swarm.strategy).toBe(StrategyType.SPECIALIZED);
    });
  });

  describe('agent management', () => {
    beforeEach(async () => {
      await swarm.initialize();
    });

    it('should spawn a single agent', async () => {
      const result = await swarm.spawnAgent({
        role: AgentRole.CODER,
        priority: 'high'
      });

      expect(result.success).toBe(true);
      expect(result.agentId).toBeDefined();
      expect(swarm.agents.size).toBe(1);
    });

    it('should spawn multiple agents in batch', async () => {
      const configs = [
        { role: AgentRole.CODER },
        { role: AgentRole.TESTER },
        { role: AgentRole.REVIEWER }
      ];

      const results = await swarm.spawnAgentsBatch(configs);

      expect(results.length).toBe(3);
      expect(swarm.agents.size).toBe(3);
      results.forEach(r => expect(r.success).toBe(true));
    });

    it('should respect max agents limit', async () => {
      const limitedSwarm = new SwarmCoordinator({ maxAgents: 2 });
      await limitedSwarm.initialize();

      await limitedSwarm.spawnAgent({ role: AgentRole.CODER });
      await limitedSwarm.spawnAgent({ role: AgentRole.TESTER });

      await expect(
        limitedSwarm.spawnAgent({ role: AgentRole.REVIEWER })
      ).rejects.toThrow('Maximum agent limit');

      await limitedSwarm.shutdown();
    });

    it('should set queen as first queen agent', async () => {
      await swarm.spawnAgent({
        role: AgentRole.QUEEN,
        priority: 'critical',
        weight: 3
      });

      expect(swarm.queen).toBeDefined();
      expect(swarm.queen.role).toBe(AgentRole.QUEEN);
    });

    it('should stop an agent', async () => {
      const { agentId } = await swarm.spawnAgent({ role: AgentRole.CODER });

      const result = await swarm.stopAgent(agentId);

      expect(result.success).toBe(true);
      expect(swarm.agents.has(agentId)).toBe(false);
    });

    it('should return error when stopping non-existent agent', async () => {
      const result = await swarm.stopAgent('non-existent');

      expect(result.success).toBe(false);
      expect(result.reason).toBe('Agent not found');
    });
  });

  describe('task management', () => {
    beforeEach(async () => {
      await swarm.initialize();
      await swarm.spawnAgent({ role: AgentRole.CODER, priority: 'high' });
    });

    it('should submit a task', async () => {
      const result = await swarm.submitTask({
        description: 'Implement feature X',
        priority: 'normal'
      });

      expect(result.success).toBe(true);
      expect(result.taskId).toBeDefined();
      expect(result.agentId).toBeDefined();
    });

    it('should route task to appropriate agent', async () => {
      await swarm.spawnAgent({ role: AgentRole.TESTER });

      const codeTask = await swarm.submitTask({
        description: 'Implement login feature',
        priority: 'high'
      });

      const testTask = await swarm.submitTask({
        description: 'Write tests for authentication',
        priority: 'high'
      });

      expect(codeTask.routing.domain).toBe('code');
      expect(testTask.routing.domain).toBe('test');
    });

    it('should complete a task', async () => {
      const { taskId, agentId } = await swarm.submitTask({
        description: 'Test task',
        priority: 'normal'
      });

      const result = await swarm.completeTask(taskId, { success: true });

      expect(result.success).toBe(true);

      const agent = swarm.agents.get(agentId);
      expect(agent.status).toBe('idle');
      expect(agent.metrics.tasksCompleted).toBe(1);
    });

    it('should track failed tasks', async () => {
      const { taskId, agentId } = await swarm.submitTask({
        description: 'Failing task',
        priority: 'normal'
      });

      await swarm.completeTask(taskId, { success: false, error: 'Test error' });

      const agent = swarm.agents.get(agentId);
      expect(agent.metrics.tasksFailed).toBe(1);
    });
  });

  describe('topology management', () => {
    beforeEach(async () => {
      await swarm.initialize();
    });

    it('should update topology', async () => {
      const result = await swarm.updateTopology(TopologyType.MESH);

      expect(result.success).toBe(true);
      expect(swarm.topology).toBe(TopologyType.MESH);
    });
  });

  describe('metrics', () => {
    beforeEach(async () => {
      await swarm.initialize();
      await swarm.spawnAgent({ role: AgentRole.CODER });
    });

    it('should return comprehensive metrics', async () => {
      const metrics = swarm.getMetrics();

      expect(metrics).toHaveProperty('swarm');
      expect(metrics).toHaveProperty('agents');
      expect(metrics).toHaveProperty('memory');
      expect(metrics).toHaveProperty('sona');
      expect(metrics).toHaveProperty('ooda');
    });

    it('should calculate agent utilization', async () => {
      await swarm.submitTask({ description: 'Test task' });

      const metrics = swarm.getMetrics();

      expect(metrics.swarm.agentUtilization).toBeGreaterThan(0);
    });
  });

  describe('swarm state', () => {
    beforeEach(async () => {
      await swarm.initialize();
    });

    it('should return complete swarm state', async () => {
      await swarm.spawnAgent({ role: AgentRole.CODER });
      await swarm.submitTask({ description: 'Test' });

      const state = swarm.getSwarmState();

      expect(state.id).toBe('test-swarm');
      expect(state.topology).toBe(TopologyType.HIERARCHICAL_MESH);
      expect(state.strategy).toBe(StrategyType.SPECIALIZED);
      expect(state.agentCount).toBe(1);
      expect(state.activeTaskCount).toBe(1);
    });
  });

  describe('broadcast', () => {
    beforeEach(async () => {
      await swarm.initialize();
      await swarm.spawnAgent({ role: AgentRole.CODER });
    });

    it('should broadcast message to all agents', async () => {
      const messages = [];
      swarm.on('message:broadcast', (data) => messages.push(data));

      await swarm.broadcast({ type: 'announcement', content: 'Test' });

      expect(messages.length).toBe(1);
    });
  });

  describe('shutdown', () => {
    it('should shutdown cleanly', async () => {
      await swarm.initialize();
      await swarm.spawnAgent({ role: AgentRole.CODER });

      const result = await swarm.shutdown();

      expect(result.success).toBe(true);
      expect(swarm.initialized).toBe(false);
      expect(swarm.agents.size).toBe(0);
    });
  });
});

describe('Factory Functions', () => {
  describe('createSwarm', () => {
    it('should create swarm with options', () => {
      const swarm = createSwarm({
        topology: TopologyType.MESH,
        maxAgents: 20
      });

      expect(swarm.topology).toBe(TopologyType.MESH);
      expect(swarm.maxAgents).toBe(20);
    });
  });

  describe('createDevelopmentSwarm', () => {
    it('should create pre-configured development swarm', async () => {
      const swarm = await createDevelopmentSwarm();

      expect(swarm.initialized).toBe(true);
      expect(swarm.agents.size).toBe(6); // Queen, Coder, Tester, Reviewer, Researcher, Architect

      await swarm.shutdown();
    });
  });

  describe('SwarmBuilder', () => {
    it('should build swarm with fluent API', async () => {
      const swarm = await new SwarmBuilder()
        .withTopology(TopologyType.HIERARCHICAL)
        .withStrategy(StrategyType.BALANCED)
        .withMaxAgents(8)
        .addQueen()
        .addCoder()
        .addTester()
        .build();

      expect(swarm.topology).toBe(TopologyType.HIERARCHICAL);
      expect(swarm.strategy).toBe(StrategyType.BALANCED);
      expect(swarm.agents.size).toBe(3);

      await swarm.shutdown();
    });
  });
});
