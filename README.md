# 3GPP Knowledge Graph - PostgreSQL Integration

This project integrates the 3GPP Knowledge Graph dataset from Hugging Face with PostgreSQL using `@ruvector/postgres-cli` for vector operations and graph analytics.

## Overview

The project downloads the 3GPP knowledge graph in GraphML format from the Hugging Face dataset `otellm/3gpp_knowledgeGraph` and loads it into a PostgreSQL database for efficient querying and analysis.

## Features

- Automated download of 3GPP knowledge graph from Hugging Face
- GraphML parsing and conversion to PostgreSQL schema
- Efficient storage with JSONB for flexible node/edge properties
- Indexed queries for fast graph traversal
- Integration with @ruvector/postgres-cli for vector operations

## Prerequisites

- Node.js (v14 or higher)
- PostgreSQL (v12 or higher)
- Internet connection for downloading the dataset

## Installation

1. Clone the repository and install dependencies:

```bash
npm install
```

2. Set up your environment variables:

```bash
cp .env.example .env
```

3. Edit `.env` with your PostgreSQL credentials:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=3gpp_knowledge_graph
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here

# Optional: For private Hugging Face datasets
HF_TOKEN=your_huggingface_token_here
```

## Usage

### Quick Start

Run the complete setup (download + load):

```bash
npm start
```

or

```bash
npm run setup
```

### Step-by-Step

1. Download the dataset only:

```bash
npm run download
```

2. Load data into PostgreSQL:

```bash
npm run load
```

## Database Schema

### Nodes Table

```sql
CREATE TABLE nodes (
  id VARCHAR(255) PRIMARY KEY,
  label TEXT,
  properties JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Edges Table

```sql
CREATE TABLE edges (
  id SERIAL PRIMARY KEY,
  source_id VARCHAR(255) REFERENCES nodes(id),
  target_id VARCHAR(255) REFERENCES nodes(id),
  label TEXT,
  properties JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Example Queries

### Find all nodes with specific properties

```sql
SELECT * FROM nodes
WHERE properties @> '{"type": "specification"}'
LIMIT 10;
```

### Find all edges of a specific type

```sql
SELECT * FROM edges
WHERE label = 'references'
LIMIT 10;
```

### Graph traversal - find connections

```sql
SELECT
  n1.label AS source_label,
  e.label AS relationship,
  n2.label AS target_label
FROM edges e
JOIN nodes n1 ON e.source_id = n1.id
JOIN nodes n2 ON e.target_id = n2.id
WHERE n1.id = 'your_node_id'
LIMIT 20;
```

### Search nodes by property value

```sql
SELECT * FROM nodes
WHERE properties->>'name' ILIKE '%5G%'
LIMIT 10;
```

## Using @ruvector/postgres-cli

The `@ruvector/postgres-cli` package provides advanced vector operations. You can use it for:

- Embedding generation for graph nodes
- Vector similarity search
- Semantic queries on the knowledge graph

Example usage with @ruvector/postgres-cli:

```javascript
const { RuvectorClient } = require('@ruvector/postgres-cli');

const client = new RuvectorClient({
  host: process.env.POSTGRES_HOST,
  port: process.env.POSTGRES_PORT,
  database: process.env.POSTGRES_DB,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD
});

// Your vector operations here
```

## Project Structure

```
.
├── index.js                 # Main integration script
├── download-dataset.js      # Hugging Face dataset downloader
├── load-to-postgres.js      # GraphML parser and PostgreSQL loader
├── package.json            # Project dependencies and scripts
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── data/                   # Downloaded GraphML files (created at runtime)
└── README.md               # This file
```

## Troubleshooting

### Connection Error

If you get a connection error:
- Verify PostgreSQL is running
- Check your credentials in `.env`
- Ensure the database exists (create it if needed)

### Dataset Download Issues

If the download fails:
- Check your internet connection
- Verify the dataset exists at: https://huggingface.co/datasets/otellm/3gpp_knowledgeGraph
- For private datasets, ensure `HF_TOKEN` is set correctly

### GraphML Parsing Errors

If parsing fails:
- Check the GraphML file format in the `data/` directory
- Verify the file isn't corrupted
- Check the console output for specific error details

## Dataset Information

- **Dataset**: otellm/3gpp_knowledgeGraph
- **Format**: GraphML
- **Source**: Hugging Face Datasets
- **URL**: https://huggingface.co/datasets/otellm/3gpp_knowledgeGraph

## Dependencies

- `@ruvector/postgres-cli` - Vector operations for PostgreSQL
- `@huggingface/hub` - Hugging Face dataset integration
- `pg` - PostgreSQL client
- `xml2js` - GraphML XML parsing
- `dotenv` - Environment variable management

## License

ISC

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
