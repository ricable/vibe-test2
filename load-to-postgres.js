const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const xml2js = require('xml2js');
require('dotenv').config();

const DATA_DIR = path.join(__dirname, 'data');

// PostgreSQL connection pool
const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: process.env.POSTGRES_PORT || 5432,
  database: process.env.POSTGRES_DB || '3gpp_knowledge_graph',
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD
});

async function createTables() {
  const client = await pool.connect();
  try {
    console.log('Creating database tables...');

    // Create nodes table
    await client.query(`
      CREATE TABLE IF NOT EXISTS nodes (
        id VARCHAR(255) PRIMARY KEY,
        label TEXT,
        properties JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create edges table
    await client.query(`
      CREATE TABLE IF NOT EXISTS edges (
        id SERIAL PRIMARY KEY,
        source_id VARCHAR(255) REFERENCES nodes(id),
        target_id VARCHAR(255) REFERENCES nodes(id),
        label TEXT,
        properties JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create indexes for better query performance
    await client.query('CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_nodes_properties ON nodes USING GIN(properties)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_edges_properties ON edges USING GIN(properties)');

    console.log('✓ Tables created successfully');
  } finally {
    client.release();
  }
}

async function parseGraphML(filePath) {
  console.log(`Parsing GraphML file: ${filePath}`);

  const xmlData = fs.readFileSync(filePath, 'utf8');
  const parser = new xml2js.Parser();
  const result = await parser.parseStringPromise(xmlData);

  const graphml = result.graphml;
  const graph = graphml.graph[0];

  // Extract nodes and edges
  const nodes = graph.node || [];
  const edges = graph.edge || [];

  console.log(`Found ${nodes.length} nodes and ${edges.length} edges`);

  return { nodes, edges };
}

async function insertNodes(nodes) {
  const client = await pool.connect();
  try {
    console.log('Inserting nodes...');

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const nodeId = node.$.id;

      // Extract node properties
      const properties = {};
      const dataElements = node.data || [];

      dataElements.forEach(data => {
        const key = data.$.key;
        const value = data._;
        if (key && value) {
          properties[key] = value;
        }
      });

      // Extract label if available
      const label = properties.label || properties.name || nodeId;

      await client.query(
        'INSERT INTO nodes (id, label, properties) VALUES ($1, $2, $3) ON CONFLICT (id) DO UPDATE SET label = $2, properties = $3',
        [nodeId, label, JSON.stringify(properties)]
      );

      if ((i + 1) % 100 === 0) {
        console.log(`  Inserted ${i + 1}/${nodes.length} nodes`);
      }
    }

    console.log(`✓ Inserted all ${nodes.length} nodes`);
  } finally {
    client.release();
  }
}

async function insertEdges(edges) {
  const client = await pool.connect();
  try {
    console.log('Inserting edges...');

    for (let i = 0; i < edges.length; i++) {
      const edge = edges[i];
      const sourceId = edge.$.source;
      const targetId = edge.$.target;

      // Extract edge properties
      const properties = {};
      const dataElements = edge.data || [];

      dataElements.forEach(data => {
        const key = data.$.key;
        const value = data._;
        if (key && value) {
          properties[key] = value;
        }
      });

      // Extract label if available
      const label = properties.label || properties.type || 'relates_to';

      await client.query(
        'INSERT INTO edges (source_id, target_id, label, properties) VALUES ($1, $2, $3, $4)',
        [sourceId, targetId, label, JSON.stringify(properties)]
      );

      if ((i + 1) % 100 === 0) {
        console.log(`  Inserted ${i + 1}/${edges.length} edges`);
      }
    }

    console.log(`✓ Inserted all ${edges.length} edges`);
  } finally {
    client.release();
  }
}

async function loadGraphMLToPostgres() {
  try {
    // Find GraphML file in data directory
    const files = fs.readdirSync(DATA_DIR);
    const graphmlFile = files.find(f => f.endsWith('.graphml'));

    if (!graphmlFile) {
      throw new Error('No GraphML file found in data directory. Run download-dataset.js first.');
    }

    const filePath = path.join(DATA_DIR, graphmlFile);

    // Create tables
    await createTables();

    // Parse GraphML
    const { nodes, edges } = await parseGraphML(filePath);

    // Insert data
    await insertNodes(nodes);
    await insertEdges(edges);

    console.log('\n✓ Successfully loaded 3GPP knowledge graph into PostgreSQL!');
    console.log('\nYou can now query the data using:');
    console.log('  - SELECT * FROM nodes LIMIT 10;');
    console.log('  - SELECT * FROM edges LIMIT 10;');

  } catch (error) {
    console.error('Error loading data:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// Run if called directly
if (require.main === module) {
  loadGraphMLToPostgres();
}

module.exports = { loadGraphMLToPostgres, createTables };
