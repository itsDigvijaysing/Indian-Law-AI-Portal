#!/bin/bash
# Test runner for Indian Law AI Portal — issues real HTTP calls and shows results.

set -u
BASE=http://localhost:8000
YEL=$'\e[33m'; RST=$'\e[0m'

hr() { printf '%.s-' {1..72}; echo; }

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

# --- Citations & grounding (local-Perplexity behavior) ---

probe "8.0 citations: exact section retrieval" POST /api/v1/query '{"query":"What does Section 420 IPC say about cheating?"}'
# Expect: answer contains [n] markers; retrieval_sources[0] should be Indian_Penal_Code_1860 / Section 420 (or 415-420 range)

probe "8.1 citations: answer carries [n] markers" POST /api/v1/query '{"query":"What is the punishment for theft under IPC?"}'
# Expect: [1]-style markers in answer; every marker id present in retrieval_sources; cited:true on those entries

probe "8.2 grounding: refusal on non-legal query" POST /api/v1/query '{"query":"What is the best recipe for biryani?"}'
# Expect: answer starts "The provided legal documents do not contain sufficient information..."; confidence <= 0.2

probe "8.3 admin: re-process skips ingested docs" POST /api/v1/admin/documents/process '{"file_paths":["Indian_Penal_Code_1860.pdf"]}'
# Expect: processed 0, skipped 1

# --- New-domain routing (25-doc corpus) ---

probe "8.4 route: cheque bounce → Commercial" POST /api/v1/query '{"query":"What is the punishment for cheque bounce under Section 138?"}'
# Expect: detected_category "Commercial", cites Negotiable Instruments Act Section 138

probe "8.5 route: Hindu divorce → Family" POST /api/v1/query '{"query":"What are the grounds for divorce under the Hindu Marriage Act?"}'
# Expect: detected_category "Family", cites Hindu Marriage Act Section 13

probe "8.6 route: cybercrime → Digital" POST /api/v1/query '{"query":"What does the IT Act say about hacking a computer system?"}'
# Expect: detected_category "Digital", cites Information Technology Act

probe "8.7 era split: murder cites both BNS and IPC" POST /api/v1/query '{"query":"What is the punishment for murder?"}'
# Expect: retrieval_sources include both BNS (post-2024) and IPC (pre-2024); answer notes the 1 July 2024 cut-over

hr
echo "${YEL}>>> 9.0 streaming query (SSE)${RST}"
echo "    POST /api/v1/query/stream"
curl -N -s -m 120 -X POST "$BASE/api/v1/query/stream" -H 'Content-Type: application/json' \
  -d '{"query":"What is Article 21 of the Constitution?"}' \
  | grep -c "^event: token" | xargs -I{} echo "token events received: {}"
# Expect: sources event first, then dozens of token events, then done

hr
echo "Done."
