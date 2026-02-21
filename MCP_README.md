# DataLens MCP Server

This is a Model Context Protocol (MCP) server that exposes DataLens database inspection capabilities to AI assistants like Claude Desktop. It reuses the existing DataLens backend connection logic.

## Prerequisites

1.  **Python Environment**: Ensure you are using the same Python environment as the DataLens backend.
2.  **Dependencies**: Install the required packages:
    ```bash
    pip install -r Backend/requirements.txt
    ```
3.  **Configuration**: Ensure your `Backend/.env` file is set up correctly with `DATABASE_URL`.

## Installation for Claude Desktop

To use this MCP server with Claude Desktop, you need to add it to your configuration file.

1.  **Locate Config File**:
    *   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
    *   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

2.  **Add Configuration**:
    Copy the contents of `claude_desktop_config.json` (generated in the root of this repo) into your Claude configuration file.

    *Make sure the paths in `claude_desktop_config.json` match your actual project location.*

    ```json
    {
      "mcpServers": {
        "datalens-mcp": {
          "command": "python", // Or full path to python.exe
          "args": [
            "D:/DataLens/DataLens/Backend/mcp_server.py"
          ],
          "env": {
            "PYTHONPATH": "D:/DataLens/DataLens/Backend"
          }
        }
      }
    }
    ```

## Available Tools

The server exposes the following tools:

*   `describe_schema()`: Returns a list of all tables and columns.
*   `get_primary_keys(table_name)`: Returns the primary key of a table.
*   `get_foreign_keys(table_name)`: Returns outgoing foreign keys.
*   `get_table_relationships(table_name)`: Returns both incoming and outgoing relationships.

## Testing manually

You can run the server in your terminal to verify it starts (it uses stdio, so it will wait for input):

```bash
cd Backend
python mcp_server.py
```
