# Medical Notes Processing Suite

A comprehensive system for processing medical notes using AI/ML, featuring concurrent processing, historical context integration, and structured data extraction. The application processes clinical notes from Elasticsearch, extracts structured information using Claude AI models, and pushes processed data to downstream systems.

## Features

- **Concurrent Processing**: Process multiple medical notes in parallel with configurable worker pools
- **Historical Context**: Automatically fetches and includes previous patient visits for enhanced context
- **Structured Data Extraction**: Extracts structured data from unstructured medical notes using Claude AI models
- **Rate Limiting**: Built-in AWS Bedrock rate limiting to prevent API throttling
- **Token Tracking**: Comprehensive token usage tracking and cost monitoring
- **Error Handling**: Robust error handling with detailed logging and status tracking
- **FastAPI Web Server**: RESTful API for processing notes via HTTP endpoints
- **CLI Interface**: Command-line interface for batch processing and system management
- **Elasticsearch Integration**: Full integration with Elasticsearch for data storage and retrieval
- **Data Flattening**: Optional nested data structure flattening for better querying

## Architecture

The application consists of several key components:

- **Main Orchestrator** (`main.py`): Entry point for CLI operations and concurrent batch processing
- **FastAPI Application** (`medical_notes/service/app.py`): Web server for HTTP API endpoints
- **Medical Notes Processor** (`medical_notes/service/medical_notes_processor.py`): Core processing logic
- **Concurrent Job Manager** (`medical_notes/service/concurrent_job_manager.py`): Manages concurrent processing with worker pools
- **Rate Limiter** (`medical_notes/service/rate_limiter.py`): AWS Bedrock API rate limiting
- **Token Tracker** (`medical_notes/service/token_tracker.py`): Tracks AI model token usage and costs
- **Elasticsearch Repository** (`medical_notes/repository/elastic_search.py`): Data access layer for Elasticsearch

## Prerequisites

- Python 3.11
- Elasticsearch cluster access
- AWS account with Bedrock access
- External API access (for pushing processed notes)

## Installation

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd notes_digest_structured
   ```

2. **Create a virtual environment** (if not already created):
   ```bash
   python3.11 -m venv venv
   ```

3. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The application uses environment variables for configuration. Create a `.env` file in the project root with the following variables:

### AWS Configuration
```bash
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_ACCESS=your_aws_secret_key
AWS_REGION=us-east-1
```

### Claude Model Configuration (optional, defaults provided)
```bash
CLAUDE_OPUS_4_1=us.anthropic.claude-opus-4-1-20250805-v1:0
CLAUDE_HAIKU_4_5=us.anthropic.claude-haiku-4-5-20251001-v1:0
CLAUDE_SONNET_3_5=us.anthropic.claude-3-5-sonnet-20241022-v2:0
CLAUDE_HAIKU_3_5=us.anthropic.claude-3-5-haiku-20241022-v1:0
```

### Elasticsearch Configuration
```bash
ES_URL=https://your-elasticsearch-cluster.com
ES_ENCODED_AUTH=your_base64_encoded_auth
ES_USER=elastic
ES_PASSWORD=your_password

# Elasticsearch Indices
ES_INDEX_CLINICAL_NOTES=tiamd_prod_clinical_notes
ES_INDEX_PROCESSED_NOTES=tiamd_prod_processed_notes
ES_INDEX_NOTES_DIGEST=tiamd_prod_notes_digest
ES_INDEX_TOKEN_USAGE=tiamd_prod_token_usage
```

### API Configuration
```bash
API_BASE_URL=https://your-api-endpoint.com
API_NOTE_HEADER_TOKEN=your_api_token
```

### Processing Configuration
```bash
# Number of previous visits to include in historical context
N_PREVIOUS_VISITS=1

# Enable/disable data structure flattening
ENABLE_DATA_FLATTENING=true
```

### Concurrency Configuration
```bash
# Maximum concurrent notes to process
MAX_CONCURRENT_NOTES=10

# Maximum queue size before rejecting requests
MAX_QUEUE_SIZE=100

# Processing timeout per note (seconds)
NOTE_PROCESSING_TIMEOUT=1200

# AWS Bedrock rate limit (requests per second)
BEDROCK_RATE_LIMIT_RPS=50

# Elasticsearch bulk batch size
ES_BULK_BATCH_SIZE=200
```

## Usage

### Command-Line Interface

#### Process a single note:
```bash
python main.py --note-id <note_id>
```

#### Process multiple notes concurrently:
```bash
python main.py --note-ids <note_id1> <note_id2> <note_id3>
```

#### Process with explicit concurrency flag:
```bash
python main.py --note-id <note_id> --concurrent
```

#### Check system status:
```bash
python main.py --action status
```

#### Health check:
```bash
python main.py --action health
```

### Web Server (FastAPI)

#### Start the web server:
```bash
python main.py server
# or
uvicorn medical_notes.service.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/notes-processor`.

#### API Endpoints

- **POST** `/process/note` - Process a single note
- **POST** `/process/notes` - Process multiple notes concurrently
- **GET** `/status` - Get system status and statistics
- **GET** `/status/job/{job_id}` - Get status of a specific job
- **GET** `/debug/config` - Get configuration summary (masked)

## Processing Flow

1. **Validation**: Check if note exists and hasn't been processed
2. **Data Fetching**: Retrieve note data from Elasticsearch
3. **Extraction**: Extract note type and patient MRN from raw data
4. **Historical Context**: Fetch previous patient visits (if MRN available)
5. **Data Processing**: Extract structured data using Claude AI models
6. **Data Storage**: Push processed data to Elasticsearch indices
7. **API Push**: Submit processed data to external API
8. **Status Update**: Update note status in clinical notes index
9. **Tracking**: Record timestamps and token usage

## Project Structure

```
notes_digest_structured/
├── main.py                          # Main entry point and CLI orchestrator
├── requirements.txt                 # Python dependencies
├── medical_notes/
│   ├── __init__.py
│   ├── config/
│   │   └── config.py               # Centralized configuration
│   ├── prompts/
│   │   └── all_prompts.py           # AI prompts for processing
│   ├── repository/
│   │   └── elastic_search.py      # Elasticsearch data access layer
│   ├── routes/
│   │   ├── process_routes.py       # Processing API endpoints
│   │   ├── status_routes.py        # Status API endpoints
│   │   └── debug_routes.py         # Debug API endpoints
│   ├── service/
│   │   ├── app.py                  # FastAPI application
│   │   ├── medical_notes_processor.py  # Core processing logic
│   │   ├── concurrent_job_manager.py   # Concurrent job management
│   │   ├── rate_limiter.py        # Rate limiting
│   │   ├── token_tracker.py        # Token usage tracking
│   │   └── note_type_extractor.py # Note type extraction
│   └── utils/
│       ├── clean_output.py         # Output cleaning utilities
│       ├── data_flattening.py      # Data structure flattening
│       ├── invoke_claude.py        # Claude AI integration
│       ├── timestamp_utils.py      # Timestamp utilities
│       └── timestamp_validation.py # Timestamp validation
└── venv/                           # Virtual environment (gitignored)
```

## Key Components

### Concurrent Job Manager
Manages concurrent processing with a thread pool executor. Features:
- Configurable worker pool size
- Job queue with size limits
- Job status tracking
- Automatic retry and error handling

### Rate Limiter
Implements token bucket algorithm for AWS Bedrock API rate limiting:
- Configurable requests per second
- Automatic token replenishment
- Request queuing when rate limit exceeded

### Token Tracker
Tracks AI model usage and costs:
- Per-section token counting
- Cost calculation based on model pricing
- Elasticsearch storage for usage analytics
- Summary reports

### Medical Notes Processor
Core processing engine:
- Structured data extraction
- SOAP note generation
- Notes digest creation
- Error handling and recovery

## Elasticsearch Indices

The application uses four main Elasticsearch indices:

1. **tiamd_prod_clinical_notes**: Source clinical notes
2. **tiamd_prod_processed_notes**: Processed notes with structured data
3. **tiamd_prod_notes_digest**: Flattened digest summaries
4. **tiamd_prod_token_usage**: Token usage and cost tracking

## Error Handling

The application implements comprehensive error handling:

- **404**: Note not found in index
- **409**: Note already processed (conflict)
- **422**: Unprocessable Entity (missing required data)
- **403**: External API rejected request
- **500**: Internal Server Error (processing failures)

Failed notes are pushed to `processed_notes` index with `processingIssues` populated for debugging.

## Development

### Running Tests
```bash
pytest
```

### Code Style
The project follows PEP 8 style guidelines. Consider using:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

### Adding New Features

1. Add configuration variables to `medical_notes/config/config.py`
2. Implement business logic in `medical_notes/service/`
3. Add API routes in `medical_notes/routes/`
4. Update this README with new features

## Troubleshooting

### Common Issues

1. **Elasticsearch Connection Errors**
   - Verify `ES_URL` and authentication credentials
   - Check network connectivity to Elasticsearch cluster

2. **AWS Bedrock Rate Limiting**
   - Adjust `BEDROCK_RATE_LIMIT_RPS` if hitting rate limits
   - Check AWS service quotas

3. **Processing Timeouts**
   - Increase `NOTE_PROCESSING_TIMEOUT` for large notes
   - Check Elasticsearch performance

4. **Token Usage Issues**
   - Monitor token usage in Elasticsearch `token_usage` index
   - Review cost reports in token tracker

## License

[Add your license information here]

## Support

[Add support contact information here]
