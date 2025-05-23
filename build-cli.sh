#!/bin/bash

echo "Building Bakaláři MCP Server - CLI Version (stdio transport)"
echo "================================================================"

docker build -f Dockerfile.cli -t mirecekd/bakalari-mcp-server:cli -t mirecekd/bakalari-mcp-server:latest .

echo ""
echo "Build completed!"
echo "CLI Version tags:"
echo "  - mirecekd/bakalari-mcp-server:cli"
echo "  - mirecekd/bakalari-mcp-server:latest"
echo ""
echo "Usage:"
echo "  docker run --rm -i mirecekd/bakalari-mcp-server:cli --user YOUR_USER --password YOUR_PASSWORD --url https://YOUR_SCHOOL.bakalari.cz"
