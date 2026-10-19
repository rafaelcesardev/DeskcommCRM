#!/usr/bin/env bash
# Uso: bench-worker.sh <node|bun> <rodada> <raiz-do-repo> <env-file> <saida-dir>
# Mede o worker do agent-engine como o Dockerfile.worker o roda: partida até o
# /healthz responder, RSS e CPU em 60 s de laços ociosos, vazão do /metrics
# (consulta ao Postgres) e o desligamento por SIGTERM (código de saída e tempo:
# é o caminho da #2823 — o sinal precisa cair no handler que drena os jobs).
set -uo pipefail
RT=$1; R=$2; ROOT=$3; ENVF=$4; OUT=$5
mkdir -p "$OUT"; tag="worker-$RT-$R"
set -a; . "$ENVF"; set +a
export HEALTH_PORT=8787 NODE_ENV=production

case $RT in
  node) BIN=(fnm exec --using=22 node --import tsx workers/agent-worker/main.ts) ;;
  bun)  BIN=(bun workers/agent-worker/main.ts) ;;
esac
rss() { ps -o rss= -p "$1" 2>/dev/null | tr -d ' '; }
agora() { python3 -c 'import time;print(time.time())'; }

t0=$(agora)
(cd "$ROOT" && exec "${BIN[@]}") > "$OUT/$tag.log" 2>&1 &
PID=$!
until curl -s -o /dev/null http://127.0.0.1:8787/healthz; do
  kill -0 $PID 2>/dev/null || { echo "worker morreu"; tail -20 "$OUT/$tag.log"; exit 1; }
  sleep 0.02
done
t1=$(agora)
WPID=$(lsof -tiTCP:8787 -sTCP:LISTEN | head -1)
sleep 5; rss5=$(rss $WPID); cpu0=$(ps -o time= -p $WPID | tr -d ' ')
( for _ in $(seq 1 300); do rss $WPID; sleep 0.2; done ) > "$OUT/$tag.rss"   # 60 s ociosos
cpu1=$(ps -o time= -p $WPID | tr -d ' ')
oha --no-tui -z 10s -c 10 http://127.0.0.1:8787/metrics --output-format json > "$OUT/$tag.metrics.oha.json" 2>/dev/null
rss_pos=$(rss $WPID)

ts=$(agora); kill -TERM $WPID
while kill -0 $WPID 2>/dev/null; do sleep 0.02; done
te=$(agora); wait $PID; code=$?
python3 - "$OUT/$tag.json" <<PY
import json,sys
amostras=[int(x) for x in open("$OUT/$tag.rss").read().split() if x.strip()]
def s(t):
    p=[float(x) for x in t.replace('-',':').split(':')]; v=0
    for x in p: v=v*60+x
    return v
json.dump({"rt":"$RT","rodada":$R,"partida_ms":round(($t1-$t0)*1000),
  "rss_5s_kb":$rss5,"rss_ocioso_max_kb":max(amostras),"rss_ocioso_med_kb":round(sum(amostras)/len(amostras)),
  "cpu_ocioso_60s_s":round(s("$cpu1")-s("$cpu0"),2),"rss_pos_metrics_kb":$rss_pos,
  "sigterm_ms":round(($te-$ts)*1000),"codigo_saida":$code}, open(sys.argv[1],"w"))
PY
echo "ok $tag"; cat "$OUT/$tag.json"; echo
