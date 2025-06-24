#!/bin/bash

echo "Building Bakaláři MCP Server - CLI Version (stdio transport)"
echo "================================================================"

docker build -f Dockerfile.cli -t mirecekd/bakalari-mcp:cli -t mirecekd/bakalari-mcp:latest .

echo ""
echo "Build completed!"
echo "CLI Version tags:"
echo "  - mirecekd/bakalari-mcp:cli"
echo "  - mirecekd/bakalari-mcp:latest"
echo ""
echo "Usage:"
echo "  docker run --rm -i mirecekd/bakalari-mcp:cli --user YOUR_USER --password YOUR_PASSWORD --url https://YOUR_SCHOOL.bakalari.cz"
