#!/bin/bash

echo "Building Bakaláři MCP Server - Proxy Version (HTTP transport)"
echo "============================================================="

docker build -f Dockerfile.proxy -t mirecekd/bakalari-mcp-server:proxy -t mirecekd/bakalari-mcp-proxy .

echo ""
echo "Build completed!"
echo "Proxy Version tags:"
echo "  - mirecekd/bakalari-mcp-server:proxy"
echo "  - mirecekd/bakalari-mcp-proxy"
echo ""
echo "Usage:"
echo "  docker run -e BAKALARI_USER=YOUR_USER -e BAKALARI_PASSWORD=YOUR_PASSWORD -e BAKALARI_URL=https://YOUR_SCHOOL.bakalari.cz -p 8805:8805 mirecekd/bakalari-mcp-server:proxy"
echo ""
echo "HTTP server will be available at: http://localhost:8805"
