# Puddle MCP

An MCP (Model Context Protocol) server for Puddle.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Dhruv-Limbani/puddle-mcp.git
cd puddle-mcp
```

### 2. Install uv (Python package & environment manager)

If you don't have `uv` installed, follow the [installation guide](https://docs.astral.sh/uv/getting-started/installation/).

For macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install dependencies

```bash
uv sync
```

This automatically creates a virtual environment at `.venv` and installs all dependencies.

### 4. Configure environment variables

Create a `.env` file in the project root with the following structure:

```env
API_KEY=pud_mc9p0k2xL8q5vR3jN7wH2bY6tF4mG8nS1cD5eP9w
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/puddle
GEMINI_API_KEY=your_gemini_api_key_here
```

**Environment Variables:**
- `API_KEY`: API key for authentication (generate a secure random key)
- `DATABASE_URL`: PostgreSQL database URL with asyncpg driver
- `GEMINI_API_KEY`: Google Gemini API key for AI features

### 5. Activate the virtual environment (optional, for manual work)

```bash
source .venv/bin/activate
```

## Running the Server

### Start the development server with auto-reload

```bash
uvicorn server:app --reload --port 8002
```

### Use the MCP Inspector to test the connection and tools

```bash
npx @modelcontextprotocol/inspector
```
