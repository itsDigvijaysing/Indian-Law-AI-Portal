#!/bin/bash
# Test runner for Indian Law AI Portal — issues real HTTP calls and shows results.

set -u
BASE=http://localhost:8000
PASS=0; FAIL=0
RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; RST=$'\e[0m'

hr() { printf '%.s-' {1..72}; echo; }

check() {
  local name="$1"; local cond="$2"
  if eval "$cond"; then
    echo "${GRN}PASS${RST} $name"
    PASS=$((PASS+1))
  else
    echo "${RED}FAIL${RST} $name"
    FAIL=$((FAIL+1))
  fi
}

probe() {
  local label="$1"; local method="$2"; local path="$3"; local body="${4:-}"
  hr; echo "${YEL}>>> $label${RST}"; echo "    $method $path"
  if [ -n "$body" ]; then echo "    body: $body"; fi
  if [ "$method" = "GET" ]; then
    curl -s -m 60 "$BASE$path"
  else
    curl -s -m 120 -X "$method" "$BASE$path" -H 'Content-Type: application/json' -d "$body"
  fi
  echo
}

probe "1.0 health/live"      GET  /health/live
probe "1.1 health/ready"     GET  /health/ready
probe "1.2 health/"          GET  /health/

probe "2.0 statistics"       GET  /api/v1/admin/statistics

probe "2.1 documents/list"   GET  /api/v1/admin/documents/list

probe "3.0 list agents"      GET  /api/v1/agents

probe "4.0 validate criminal" POST /api/v1/validate '{"query":"What is the punishment for theft under IPC?"}'
probe "4.1 validate civil"    POST /api/v1/validate '{"query":"How can I file a civil suit for breach of contract?"}'
probe "4.2 validate constitutional" POST /api/v1/validate '{"query":"What are the fundamental rights under Article 21?"}'
probe "4.3 validate too short"   POST /api/v1/validate '{"query":"hi"}'

probe "5.0 query: criminal — theft (IPC)" POST /api/v1/query '{"query":"What is the punishment for theft under IPC?"}'
probe "5.1 query: criminal — BNS murder" POST /api/v1/query '{"query":"What does the Bharatiya Nyaya Sanhita say about murder?"}'
probe "5.2 query: civil — limitation period" POST /api/v1/query '{"query":"What is the limitation period for filing a civil suit?"}'
probe "5.3 query: constitutional — Article 21" POST /api/v1/query '{"query":"Explain the right to life under Article 21 of the Indian Constitution"}'
probe "5.4 query: general — what is law" POST /api/v1/query '{"query":"What does the law say about plea bargaining?"}'

probe "6.0 edge: empty query" POST /api/v1/query '{"query":""}'
probe "6.1 edge: 1 char"      POST /api/v1/query '{"query":"a"}'
probe "6.2 edge: gibberish"   POST /api/v1/query '{"query":"asdf qwerty zxcv mnbv"}'
probe "6.3 edge: non-legal"   POST /api/v1/query '{"query":"What is the recipe for chocolate cake?"}'
probe "6.4 edge: very long"   POST /api/v1/query "$(python3 -c 'import json; print(json.dumps({"query":"What is theft? "*60}))')"

probe "7.0 advanced query (explain reasoning)" POST /api/v1/query/advanced '{"query":"What is the punishment for theft?","explain_reasoning":true,"fusion_queries":3}'
probe "7.1 advanced query (filtered to Constitution)" POST /api/v1/query/advanced '{"query":"What are fundamental rights?","filters":{"document_types":["Constitution_of_India"]}}'

hr
echo "Done."
