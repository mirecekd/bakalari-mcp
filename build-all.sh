#!/bin/bash

echo "Building All Bakaláři MCP Server Versions"
echo "=========================================="
echo ""

echo "1. Building CLI Version (stdio transport)..."
echo "---------------------------------------------"
docker build -f Dockerfile.cli -t mirecekd/bakalari-mcp-server:cli -t mirecekd/bakalari-mcp-server:latest .

echo ""
echo "2. Building Proxy Version (HTTP transport)..."
echo "----------------------------------------------"
docker build -f Dockerfile.proxy -t mirecekd/bakalari-mcp-server:proxy -t mirecekd/bakalari-mcp-proxy .

echo ""
echo "✅ All builds completed!"
echo "========================"
echo ""
echo "Available images:"
echo "  CLI Version:"
echo "    - mirecekd/bakalari-mcp-server:cli"
echo "    - mirecekd/bakalari-mcp-server:latest"
echo "  Proxy Version:"
echo "    - mirecekd/bakalari-mcp-server:proxy"
echo "    - mirecekd/bakalari-mcp-proxy"
echo ""
echo "Usage examples:"
echo "  CLI (stdio):  docker run --rm -i mirecekd/bakalari-mcp-server:cli --user USER --password PASS --url URL"
echo "  Proxy (HTTP): docker run -e BAKALARI_USER=USER -e BAKALARI_PASSWORD=PASS -e BAKALARI_URL=URL -p 8805:8805 mirecekd/bakalari-mcp-server:proxy"
