#!/bin/bash
# SearXNG Search Script
# Usage: search.sh "query" [num_results]

SEARXNG_URL="http://192.168.31.147:9900"
QUERY="${1:-test}"
NUM="${2:-5}"

# URL encode the query
ENCODED_QUERY=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")

# Search and format results
curl -s "${SEARXNG_URL}/search?q=${ENCODED_QUERY}&format=json" | \
  jq -r --argjson n "$NUM" '.results[:$n] | to_entries[] | "\(.key + 1). \(.value.title)\n   URL: \(.value.url)\n   \(.value.content[:200])...\n"'
