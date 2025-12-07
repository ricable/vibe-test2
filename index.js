const { downloadDataset } = require('./download-dataset');
const { loadGraphMLToPostgres } = require('./load-to-postgres');
require('dotenv').config();

async function main() {
  console.log('='.repeat(60));
  console.log('3GPP Knowledge Graph - PostgreSQL Integration');
  console.log('='.repeat(60));
  console.log('');

  try {
    // Step 1: Download dataset from Hugging Face
    console.log('Step 1: Downloading dataset from Hugging Face...');
    await downloadDataset();
    console.log('');

    // Step 2: Load data into PostgreSQL
    console.log('Step 2: Loading data into PostgreSQL...');
    await loadGraphMLToPostgres();
    console.log('');

    console.log('='.repeat(60));
    console.log('✓ Setup complete!');
    console.log('='.repeat(60));
    console.log('');
    console.log('Next steps:');
    console.log('1. Connect to your PostgreSQL database');
    console.log('2. Query the knowledge graph:');
    console.log('   - SELECT * FROM nodes WHERE properties @> \'{"type": "specification"}\';');
    console.log('   - SELECT * FROM edges WHERE label = \'references\';');
    console.log('3. Use @ruvector/postgres-cli for advanced vector operations');
    console.log('');

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    console.error('\nPlease check:');
    console.error('1. PostgreSQL is running and accessible');
    console.error('2. Database credentials in .env are correct');
    console.error('3. Internet connection for Hugging Face download');
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { main };
