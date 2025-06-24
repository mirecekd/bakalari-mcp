#!/bin/bash

# Build script for Bakaláři MCP Server - HTTP Streaming version

set -e

echo "Building Bakaláři MCP Server - HTTP Streaming version..."

# Build Docker image
docker build -f Dockerfile.http -t mirecekd/bakalari-mcp:http .

echo "Build completed successfully!"
echo "Image: mirecekd/bakalari-mcp:http"
echo ""
echo "To run the HTTP streaming server:"
echo "  Local:  docker run -p 8806:8806 mirecekd/bakalari-mcp:http --user YOUR_USERNAME --password YOUR_PASSWORD --url https://your-school.bakalari.cz"
echo "  GHCR:   docker run -p 8806:8806 ghcr.io/mirecekd/bakalari-mcp:latest-http --user YOUR_USERNAME --password YOUR_PASSWORD --url https://your-school.bakalari.cz"
echo ""
echo "HTTP streaming server will be available at: http://localhost:8806"
