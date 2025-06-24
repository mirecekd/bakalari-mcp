#!/bin/bash

echo "Building All Bakaláři MCP Server Versions"
echo "=========================================="
echo ""

echo "1. Building CLI Version (stdio transport)..."
echo "---------------------------------------------"
docker build -f Dockerfile.cli -t mirecekd/bakalari-mcp:cli -t mirecekd/bakalari-mcp:latest .

echo ""
echo "2. Building Proxy Version (HTTP transport)..."
echo "----------------------------------------------"
docker build -f Dockerfile.proxy -t mirecekd/bakalari-mcp:proxy -t mirecekd/bakalari-mcp-proxy .

echo ""
echo "3. Building HTTP Streaming Version (HTTP streaming transport)..."
echo "---------------------------------------------------------------"
docker build -f Dockerfile.http -t mirecekd/bakalari-mcp:http .

echo ""
echo "✅ All builds completed!"
echo "========================"
echo ""
echo "Available images:"
echo "  CLI Version:"
echo "    - mirecekd/bakalari-mcp:cli"
echo "    - mirecekd/bakalari-mcp:latest"
echo "  Proxy Version:"
echo "    - mirecekd/bakalari-mcp:proxy"
echo "    - mirecekd/bakalari-mcp-proxy"
echo "  HTTP Streaming Version:"
echo "    - mirecekd/bakalari-mcp:http"
echo ""
echo "Usage examples:"
echo "  CLI (stdio):     docker run --rm -i mirecekd/bakalari-mcp:cli --user USER --password PASS --url URL"
echo "  Proxy (HTTP):    docker run -e BAKALARI_USER=USER -e BAKALARI_PASSWORD=PASS -e BAKALARI_URL=URL -p 8805:8805 mirecekd/bakalari-mcp:proxy"
echo "  HTTP Streaming:  docker run -p 8806:8806 mirecekd/bakalari-mcp:http --user USER --password PASS --url URL"
