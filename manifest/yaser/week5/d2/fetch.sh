#!/bin/bash
set -e
kubectl port-forward -n llmops svc/yaser-alert-inbox 8081:8080 >/tmp/pf.log 2>&1 &
PF_PID=$!
sleep 2
curl -s http://localhost:8081/ | python3 -m json.tool > evaluation.json
kill $PF_PID
echo "Saved $(date): $(python3 -c 'import json;print(len(json.load(open("evaluation.json"))))') records"
