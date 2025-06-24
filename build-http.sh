#!/bin/bash

# Build script for Bakaláři MCP Server - HTTP Streaming version

set -e

echo "Building Bakaláři MCP Server - HTTP Streaming version..."

# Build Docker image
docker build -f Dockerfile.http -t mirecekd/bakalari-mcp-server:http .

echo "Build completed successfully!"
echo "Image: mirecekd/bakalari-mcp-server:http"
echo ""
echo "To run the HTTP streaming server:"
echo "docker run -p 8806:8806 mirecekd/bakalari-mcp-server:http --user YOUR_USERNAME --password YOUR_PASSWORD --url https://your-school.bakalari.cz"
echo ""
echo "Or with environment variables:"
echo "docker run -p 8806:8806 -e BAKALARI_USER=username -e BAKALARI_PASSWORD=password -e BAKALARI_URL=https://school.bakalari.cz mirecekd/bakalari-mcp-server:http"
