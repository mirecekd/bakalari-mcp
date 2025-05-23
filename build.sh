#!/bin/bash

echo "⚠️  This script is deprecated!"
echo "================================"
echo ""
echo "Please use the new specific build scripts:"
echo ""
echo "  ./build-cli.sh    - Build CLI version (stdio transport)"
echo "  ./build-proxy.sh  - Build Proxy version (HTTP transport)"
echo "  ./build-all.sh    - Build both versions"
echo ""
echo "For backward compatibility, building proxy version..."
echo ""

./build-proxy.sh
