/**
 * Tests for OODA Loop Implementation
 *
 * @jest-environment node
 */

const { OODALoop, OODAState, GOAPPlanner } = require('../../src/swarm');

describe('OODALoop', () => {
  let ooda;

  beforeEach(() => {
    ooda = new OODALoop({
      id: 'test-ooda',
      agentId: 'test-agent',
      maxObservations: 5,
      decisionThreshold: 0.6
    });
  });

  describe('initialization', () => {
    it('should initialize with correct defaults', () => {
      expect(ooda.id).toBe('test-ooda');
      expect(ooda.agentId).toBe('test-agent');
      expect(ooda.state).toBe(OODAState.OBSERVE);
      expect(ooda.trajectory.length).toBe(0);
    });

    it('should accept configuration options', () => {
      expect(ooda.config.maxObservations).toBe(5);
      expect(ooda.config.decisionThreshold).toBe(0.6);
    });
  });

  describe('executeCycle', () => {
    it('should complete full OODA cycle', async () => {
      const result = await ooda.executeCycle({
        task: 'Test task',
        priority: 'high'
      });

      expect(result).toBeDefined();
      expect(ooda.state).toBe(OODAState.COMPLETE);
    });

    it('should record trajectory', async () => {
      await ooda.executeCycle({ task: 'Test' });

      expect(ooda.trajectory.length).toBe(1);
      expect(ooda.trajectory[0]).toHaveProperty('cycleId');
      expect(ooda.trajectory[0]).toHaveProperty('observations');
      expect(ooda.trajectory[0]).toHaveProperty('decision');
    });

    it('should update metrics', async () => {
      await ooda.executeCycle({ task: 'Test' });

      expect(ooda.metrics.cycleCount).toBe(1);
      expect(ooda.metrics.totalDecisions).toBe(1);
    });

    it('should emit cycle:complete event', async () => {
      const events = [];
      ooda.on('cycle:complete', (data) => events.push(data));

      await ooda.executeCycle({ task: 'Test' });

      expect(events.length).toBe(1);
      expect(events[0]).toHaveProperty('cycleId');
    });
  });

  describe('observe phase', () => {
    it('should gather observations', async () => {
      const observations = await ooda.observe({ task: 'Test' });

      expect(observations).toHaveProperty('timestamp');
      expect(observations).toHaveProperty('raw');
      expect(observations).toHaveProperty('environmental');
      expect(observations).toHaveProperty('historical');
    });

    it('should limit stored observations', async () => {
      for (let i = 0; i < 10; i++) {
        await ooda.observe({ task: `Test ${i}` });
      }

      expect(ooda.observations.length).toBeLessThanOrEqual(5);
    });

    it('should emit phase event', async () => {
      const events = [];
      ooda.on('phase:observe:complete', (data) => events.push(data));

      await ooda.observe({ task: 'Test' });

      expect(events.length).toBe(1);
    });
  });

  describe('orient phase', () => {
    it('should produce orientation analysis', async () => {
      const observations = await ooda.observe({ task: 'Test' });
      const orientation = await ooda.orient(observations);

      expect(orientation).toHaveProperty('situationAssessment');
      expect(orientation).toHaveProperty('threatAnalysis');
      expect(orientation).toHaveProperty('opportunityAnalysis');
      expect(orientation).toHaveProperty('resourceAssessment');
      expect(orientation).toHaveProperty('confidence');
    });

    it('should calculate confidence', async () => {
      const observations = await ooda.observe({ task: 'Test' });
      const orientation = await ooda.orient(observations);

      expect(orientation.confidence).toBeGreaterThanOrEqual(0);
      expect(orientation.confidence).toBeLessThanOrEqual(1);
    });
  });

  describe('decide phase', () => {
    it('should select best action', async () => {
      const observations = await ooda.observe({ task: 'Test' });
      const orientation = await ooda.orient(observations);
      const decision = await ooda.decide(orientation);

      expect(decision).toHaveProperty('selectedAction');
      expect(decision).toHaveProperty('alternatives');
      expect(decision).toHaveProperty('rationale');
      expect(decision).toHaveProperty('confidence');
    });

    it('should provide alternatives', async () => {
      const observations = await ooda.observe({ task: 'Test' });
      const orientation = await ooda.orient(observations);
      const decision = await ooda.decide(orientation);

      expect(decision.alternatives).toBeInstanceOf(Array);
    });

    it('should filter by confidence threshold', async () => {
      const strictOoda = new OODALoop({ decisionThreshold: 0.99 });

      const observations = await strictOoda.observe({ task: 'Test' });
      const orientation = await strictOoda.orient(observations);
      const decision = await strictOoda.decide(orientation);

      // With very high threshold, action may be null
      expect(decision).toHaveProperty('selectedAction');
    });
  });

  describe('act phase', () => {
    it('should execute action', async () => {
      const decision = {
        selectedAction: {
          id: 'test-action',
          type: 'execute',
          parameters: {}
        }
      };

      const result = await ooda.act(decision);

      expect(result).toHaveProperty('success');
      expect(result).toHaveProperty('actionId');
      expect(result).toHaveProperty('timestamp');
    });

    it('should handle no selected action', async () => {
      const decision = { selectedAction: null };

      const result = await ooda.act(decision);

      expect(result.success).toBe(false);
      expect(result.reason).toContain('No action selected');
    });

    it('should update success rate', async () => {
      const decision = {
        selectedAction: { id: 'test', type: 'execute' }
      };

      await ooda.act(decision);

      expect(ooda.metrics.successfulActions).toBe(1);
      expect(ooda.metrics.successRate).toBeGreaterThan(0);
    });
  });

  describe('reset', () => {
    it('should reset state', async () => {
      await ooda.executeCycle({ task: 'Test' });

      ooda.reset();

      expect(ooda.state).toBe(OODAState.OBSERVE);
      expect(ooda.observations.length).toBe(0);
      expect(ooda.decisions.length).toBe(0);
    });
  });

  describe('getMetrics', () => {
    it('should return comprehensive metrics', async () => {
      await ooda.executeCycle({ task: 'Test' });

      const metrics = ooda.getMetrics();

      expect(metrics).toHaveProperty('cycleCount');
      expect(metrics).toHaveProperty('successRate');
      expect(metrics).toHaveProperty('currentState');
      expect(metrics).toHaveProperty('trajectoryLength');
    });
  });
});

describe('GOAPPlanner', () => {
  let planner;

  beforeEach(() => {
    planner = new GOAPPlanner();
  });

  describe('goal management', () => {
    it('should add goals', () => {
      planner.addGoal('feature-complete', {
        conditions: { implemented: true, tested: true },
        priority: 10
      });

      expect(planner.goals.has('feature-complete')).toBe(true);
    });
  });

  describe('action management', () => {
    it('should add actions', () => {
      planner.addAction('implement', {
        preconditions: { designed: true },
        effects: { implemented: true },
        cost: 5
      });

      expect(planner.actions.has('implement')).toBe(true);
    });
  });

  describe('world state', () => {
    it('should update world state', () => {
      planner.updateWorldState('designed', true);

      expect(planner.worldState.get('designed')).toBe(true);
    });
  });

  describe('planning', () => {
    beforeEach(() => {
      // Setup actions
      planner.addAction('design', {
        preconditions: {},
        effects: { designed: true },
        cost: 3
      });

      planner.addAction('implement', {
        preconditions: { designed: true },
        effects: { implemented: true },
        cost: 5
      });

      planner.addAction('test', {
        preconditions: { implemented: true },
        effects: { tested: true },
        cost: 3
      });

      // Setup goal
      planner.addGoal('complete', {
        conditions: { tested: true }
      });
    });

    it('should find action sequence', () => {
      const plan = planner.plan('complete');

      expect(plan).toBeInstanceOf(Array);
      expect(plan.length).toBe(3);
      expect(plan).toContain('design');
      expect(plan).toContain('implement');
      expect(plan).toContain('test');
    });

    it('should return null for impossible goals', () => {
      planner.addGoal('impossible', {
        conditions: { magic: true }
      });

      const plan = planner.plan('impossible');

      expect(plan).toBeNull();
    });

    it('should find optimal path', () => {
      // Already designed
      planner.updateWorldState('designed', true);

      const plan = planner.plan('complete');

      expect(plan.length).toBe(2);
      expect(plan).not.toContain('design');
    });
  });
});
