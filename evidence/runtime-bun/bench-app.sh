#!/usr/bin/env bash
# Uso: bench-app.sh <node|bun> <rodada> <dir-standalone> <env-file> <saida-dir>
# Mede o MESMO artefato (.next/standalone/server.js) sob os dois runtimes:
# partida a frio, RSS ocioso, vazão/latência por rota, RSS de pico sob carga.
set -uo pipefail
RT=$1; R=$2; DIR=$3; ENVF=$4; OUT=$5
PORT=3999
ROTAS=(${ROTAS:-/ /login /api/v1/health})
DUR=${DUR:-15s}; CONC=${CONC:-50}
mkdir -p "$OUT"; tag="$RT-$R"

set -a; . "$ENVF"; set +a
export PORT HOSTNAME=127.0.0.1 NODE_ENV=production KEEP_ALIVE_TIMEOUT=125000

case $RT in
  node) BIN=(fnm exec --using=22 node server.js) ;;
  bun)  BIN=(bun server.js) ;;
esac

rss() { ps -o rss= -p "$1" 2>/dev/null | tr -d ' '; }   # KiB
cpu() { ps -o time= -p "$1" 2>/dev/null | tr -d ' '; }

t0=$(python3 -c 'import time;print(time.time())')
(cd "$DIR" && exec "${BIN[@]}") > "$OUT/$tag.server.log" 2>&1 &
PID=$!
# fnm exec faz fork: mede o processo do runtime, não o wrapper
until code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/") && [ "$code" = 200 ]; do
  kill -0 $PID 2>/dev/null || { echo "servidor morreu"; tail -20 "$OUT/$tag.server.log"; exit 1; }
  sleep 0.02
done
t1=$(python3 -c 'import time;print(time.time())')
RPID=$(lsof -tiTCP:$PORT -sTCP:LISTEN | head -1)
sleep 2
echo "{\"rt\":\"$RT\",\"rodada\":$R,\"partida_ms\":$(python3 -c "print(round(($t1-$t0)*1000))"),\"rss_ocioso_kb\":$(rss $RPID)}" > "$OUT/$tag.start.json"

for rota in "${ROTAS[@]}"; do
  nome=$(echo "$rota" | tr '/' '_'); [ "$nome" = _ ] && nome=_raiz
  oha --no-tui -z 3s -c "$CONC" "http://127.0.0.1:$PORT$rota" --output-format quiet >/dev/null 2>&1  # aquecimento
  pico=0
  ( while kill -0 $RPID 2>/dev/null; do r=$(rss $RPID); echo "$r"; sleep 0.2; done ) > "$OUT/$tag$nome.rss" &
  AMOS=$!
  oha --no-tui -z "$DUR" -c "$CONC" "http://127.0.0.1:$PORT$rota" --output-format json > "$OUT/$tag$nome.oha.json" 2>/dev/null
  kill $AMOS 2>/dev/null; wait $AMOS 2>/dev/null
  pico=$(sort -n "$OUT/$tag$nome.rss" | tail -1)
  echo "{\"rota\":\"$rota\",\"rss_pico_kb\":$pico}" > "$OUT/$tag$nome.pico.json"
done

sleep 3
echo "{\"rss_pos_carga_kb\":$(rss $RPID),\"cpu_total\":\"$(cpu $RPID)\"}" > "$OUT/$tag.fim.json"
kill $RPID $PID 2>/dev/null; wait $PID 2>/dev/null
echo "ok $tag"
