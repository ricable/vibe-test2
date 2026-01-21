/**
 * Swarm Configuration - Default Settings for Agentic Reasoning Swarms
 *
 * This module provides configuration presets for different swarm deployment scenarios.
 *
 * @module config/swarm-config
 */

const { TopologyType, AgentRole, StrategyType } = require('../agents/swarm-coordinator');

/**
 * Default configuration for development swarms
 */
const developmentConfig = {
  // Swarm topology settings
  swarm: {
    topology: TopologyType.HIERARCHICAL_MESH,
    strategy: StrategyType.SPECIALIZED,
    maxAgents: 15,
    consensusProtocol: 'raft',
    consensusGating: true,
    antiDrift: true,
    parallelExecution: true,
    maxConcurrentTasks: 10,
    taskTimeout: 60000
  },

  // OODA Loop configuration
  ooda: {
    maxObservations: 10,
    orientationTimeout: 5000,
    decisionThreshold: 0.7,
    parallelActions: true,
    enablePatternMatching: true,
    trajectoryLimit: 100
  },

  // SONA Intelligence settings
  sona: {
    learningRate: 0.001,
    ewcLambda: 0.5,
    loraRank: 8,
    maxPatterns: 10000,
    retrievalK: 3,
    similarityThreshold: 0.7,
    consolidationInterval: 100,
    qualityDomains: ['code', 'creative', 'reasoning', 'chat', 'math']
  },

  // Memory configuration
  memory: {
    maxEvents: 10000,
    maxTrajectories: 1000,
    maxVerdicts: 5000,
    cacheSize: 100,
    enableQuantization: true,
    compressionLevel: 'medium'
  },

  // Agent configurations
  agents: {
    queen: {
      role: AgentRole.QUEEN,
      priority: 'critical',
      weight: 3,
      capabilities: ['coordination', 'planning', 'consensus', 'governance']
    },
    coder: {
      role: AgentRole.CODER,
      priority: 'high',
      weight: 1,
      capabilities: ['implementation', 'debugging', 'refactoring', 'tdd']
    },
    tester: {
      role: AgentRole.TESTER,
      priority: 'high',
      weight: 1,
      capabilities: ['testing', 'tdd', 'mocking', 'coverage-analysis']
    },
    reviewer: {
      role: AgentRole.REVIEWER,
      priority: 'high',
      weight: 2,
      capabilities: ['code-review', 'security', 'best-practices']
    },
    researcher: {
      role: AgentRole.RESEARCHER,
      priority: 'normal',
      weight: 1,
      capabilities: ['research', 'analysis', 'documentation', 'pattern-discovery']
    },
    architect: {
      role: AgentRole.ARCHITECT,
      priority: 'high',
      weight: 2,
      capabilities: ['design', 'architecture', 'patterns', 'system-design']
    },
    security: {
      role: AgentRole.SECURITY,
      priority: 'critical',
      weight: 2,
      capabilities: ['vulnerability-scanning', 'cve-detection', 'secure-coding']
    },
    devops: {
      role: AgentRole.DEVOPS,
      priority: 'normal',
      weight: 1,
      capabilities: ['deployment', 'ci-cd', 'infrastructure', 'monitoring']
    },
    performance: {
      role: AgentRole.PERFORMANCE,
      priority: 'normal',
      weight: 1,
      capabilities: ['profiling', 'optimization', 'benchmarking']
    }
  },

  // Consensus protocol settings
  consensus: {
    raft: {
      electionTimeout: [150, 300], // ms range
      heartbeatInterval: 50
    },
    byzantine: {
      f: 1, // Fault tolerance
      timeout: 5000
    },
    gossip: {
      fanout: 3,
      gossipInterval: 100
    }
  },

  // Performance targets
  performanceTargets: {
    oodaCycleTime: 100, // ms
    patternRetrieval: 0.1, // ms
    sonaAdaptation: 0.05, // ms
    routingAccuracy: 0.95, // 95%
    agentUtilization: 0.85, // 85%
    consensusLatency: 500, // ms
    memoryReduction: 0.5 // 50%
  }
};

/**
 * Configuration for small teams (1-5 agents)
 * Uses pure hierarchical topology for tight control
 */
const smallTeamConfig = {
  ...developmentConfig,
  swarm: {
    ...developmentConfig.swarm,
    topology: TopologyType.HIERARCHICAL,
    maxAgents: 5,
    antiDrift: true
  }
};

/**
 * Configuration for large teams (15+ agents)
 * Uses mesh topology with gossip consensus
 */
const largeTeamConfig = {
  ...developmentConfig,
  swarm: {
    ...developmentConfig.swarm,
    topology: TopologyType.MESH,
    maxAgents: 64,
    consensusProtocol: 'gossip'
  },
  memory: {
    ...developmentConfig.memory,
    maxEvents: 50000,
    maxTrajectories: 5000,
    cacheSize: 500
  }
};

/**
 * Configuration for security-focused deployments
 * Uses Byzantine fault tolerance
 */
const securityConfig = {
  ...developmentConfig,
  swarm: {
    ...developmentConfig.swarm,
    topology: TopologyType.HIERARCHICAL,
    maxAgents: 10,
    consensusProtocol: 'byzantine',
    consensusGating: true
  },
  consensus: {
    ...developmentConfig.consensus,
    byzantine: {
      f: 2, // Higher fault tolerance
      timeout: 10000
    }
  }
};

/**
 * Configuration presets map
 */
const presets = {
  development: developmentConfig,
  'small-team': smallTeamConfig,
  'large-team': largeTeamConfig,
  security: securityConfig
};

/**
 * Get configuration by preset name
 */
function getConfig(presetName = 'development') {
  return presets[presetName] || developmentConfig;
}

/**
 * Merge custom config with preset
 */
function mergeConfig(presetName, customConfig) {
  const baseConfig = getConfig(presetName);
  return deepMerge(baseConfig, customConfig);
}

/**
 * Deep merge utility
 */
function deepMerge(target, source) {
  const result = { ...target };

  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = deepMerge(target[key] || {}, source[key]);
    } else {
      result[key] = source[key];
    }
  }

  return result;
}

/**
 * Validate configuration
 */
function validateConfig(config) {
  const errors = [];

  // Validate swarm config
  if (config.swarm) {
    if (config.swarm.maxAgents > 64) {
      errors.push('maxAgents cannot exceed 64');
    }
    if (!Object.values(TopologyType).includes(config.swarm.topology)) {
      errors.push(`Invalid topology: ${config.swarm.topology}`);
    }
  }

  // Validate OODA config
  if (config.ooda) {
    if (config.ooda.decisionThreshold < 0 || config.ooda.decisionThreshold > 1) {
      errors.push('decisionThreshold must be between 0 and 1');
    }
  }

  // Validate SONA config
  if (config.sona) {
    if (config.sona.learningRate <= 0) {
      errors.push('learningRate must be positive');
    }
    if (config.sona.retrievalK < 1) {
      errors.push('retrievalK must be at least 1');
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

module.exports = {
  developmentConfig,
  smallTeamConfig,
  largeTeamConfig,
  securityConfig,
  presets,
  getConfig,
  mergeConfig,
  validateConfig
};
