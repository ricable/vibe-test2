const { Pool } = require('pg');
require('dotenv').config();

// PostgreSQL connection pool
const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: process.env.POSTGRES_PORT || 5432,
  database: process.env.POSTGRES_DB || '3gpp_knowledge_graph',
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD
});

async function runQuery(description, query, params = []) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Query: ${description}`);
  console.log(`${'='.repeat(60)}`);

  try {
    const result = await pool.query(query, params);
    console.log(`\nResults (${result.rows.length} rows):`);
    console.table(result.rows);
    return result.rows;
  } catch (error) {
    console.error('Error:', error.message);
  }
}

async function main() {
  console.log('3GPP Knowledge Graph - Example Queries\n');

  try {
    // Example 1: Count nodes and edges
    await runQuery(
      'Count total nodes',
      'SELECT COUNT(*) as total_nodes FROM nodes'
    );

    await runQuery(
      'Count total edges',
      'SELECT COUNT(*) as total_edges FROM edges'
    );

    // Example 2: Sample nodes
    await runQuery(
      'Sample 10 nodes',
      'SELECT id, label, properties FROM nodes LIMIT 10'
    );

    // Example 3: Sample edges with labels
    await runQuery(
      'Sample 10 edges with relationship types',
      'SELECT id, source_id, target_id, label FROM edges LIMIT 10'
    );

    // Example 4: Node degree distribution (most connected nodes)
    await runQuery(
      'Top 10 most connected nodes',
      `SELECT
        n.id,
        n.label,
        COUNT(e.id) as connection_count
      FROM nodes n
      LEFT JOIN edges e ON (n.id = e.source_id OR n.id = e.target_id)
      GROUP BY n.id, n.label
      ORDER BY connection_count DESC
      LIMIT 10`
    );

    // Example 5: Edge type distribution
    await runQuery(
      'Distribution of edge types',
      `SELECT
        label,
        COUNT(*) as count
      FROM edges
      GROUP BY label
      ORDER BY count DESC
      LIMIT 10`
    );

    // Example 6: Property keys in nodes
    await runQuery(
      'Common property keys in nodes',
      `SELECT
        jsonb_object_keys(properties) as property_key,
        COUNT(*) as usage_count
      FROM nodes
      GROUP BY property_key
      ORDER BY usage_count DESC
      LIMIT 10`
    );

    // Example 7: Search nodes by property
    console.log('\n' + '='.repeat(60));
    console.log('Query: Search for nodes containing "5G" in any property');
    console.log('='.repeat(60));
    const searchResult = await pool.query(
      `SELECT id, label, properties
      FROM nodes
      WHERE properties::text ILIKE '%5G%'
      LIMIT 10`
    );
    console.log(`\nResults (${searchResult.rows.length} rows):`);
    console.table(searchResult.rows);

    // Example 8: Graph traversal - 2-hop neighborhood
    const sampleNode = await pool.query('SELECT id FROM nodes LIMIT 1');
    if (sampleNode.rows.length > 0) {
      const nodeId = sampleNode.rows[0].id;
      await runQuery(
        `2-hop neighborhood from node: ${nodeId}`,
        `WITH first_hop AS (
          SELECT DISTINCT
            CASE
              WHEN e.source_id = $1 THEN e.target_id
              ELSE e.source_id
            END as node_id
          FROM edges e
          WHERE e.source_id = $1 OR e.target_id = $1
        ),
        second_hop AS (
          SELECT DISTINCT
            CASE
              WHEN e.source_id IN (SELECT node_id FROM first_hop) THEN e.target_id
              ELSE e.source_id
            END as node_id
          FROM edges e
          WHERE e.source_id IN (SELECT node_id FROM first_hop)
             OR e.target_id IN (SELECT node_id FROM first_hop)
        )
        SELECT n.id, n.label, '1-hop' as distance
        FROM nodes n
        WHERE n.id IN (SELECT node_id FROM first_hop)
        UNION
        SELECT n.id, n.label, '2-hop' as distance
        FROM nodes n
        WHERE n.id IN (SELECT node_id FROM second_hop)
        LIMIT 20`,
        [nodeId]
      );
    }

    console.log('\n' + '='.repeat(60));
    console.log('Query examples completed!');
    console.log('='.repeat(60));

  } catch (error) {
    console.error('Error running queries:', error.message);
  } finally {
    await pool.end();
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { runQuery };
