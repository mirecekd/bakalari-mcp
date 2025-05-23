#!/bin/bash

cd /app/bakalari-mcp-server
mcp-proxy --port 8805 --host 0.0.0.0 -- python main.py --user "$BAKALARI_USER" --password "$BAKALARI_PASSWORD" --url "$BAKALARI_URL"
