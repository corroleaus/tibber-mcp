# tibber-mcp MCP Server

An MCP server for interacting with the Tibber API. This server provides tools to access energy consumption, production, pricing, and real-time data from Tibber homes from MCP hosts e.g Claude desktop.

## Features

### Tools

The server provides several tools for interacting with Tibber data:

- **list-homes**: List all Tibber homes and their basic information
- **get-consumption**: Get energy consumption data for a specific home
- **get-production**: Get energy production data for a specific home
- **get-price-info**: Get current and upcoming electricity prices
- **get-realtime**: Get latest real-time power readings
- **get-historic**: Get historical data with custom resolution
- **get-price-forecast**: Get detailed price forecasts for today and tomorrow

Each tool provides detailed information about energy usage, costs, and pricing to help monitor and optimize energy consumption.

## Requirements

- Python 3.13 or higher
- Tibber API access token

## Configuration

### Environment Variables

- `TIBBER_TOKEN`: Your Tibber API access token (required)

### Server Configuration

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>

  ```
  "mcpServers": {
    "tibber-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/tibber-mcp",
        "run",
        "tibber-mcp"
      ]
    }
  }
  ```

</details>

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /Users/pontuspohl/workspace/ktc/prototypes/tibber-mcp run tibber-mcp
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.
