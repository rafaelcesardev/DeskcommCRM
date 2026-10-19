#!/usr/bin/env bash
# Uso: bench-container.sh <node|bun> <rodada> <env-file-docker> <saida-dir>
# A imagem de produção (bunbench/app:<rt>) com os limites do compose de
# produção (mem_limit 768m) e 2 CPUs, como uma VPS pequena. Mede vazão e
# latência por rota, pico de memória do contêiner (cgroup) e se o kernel
# matou o processo por falta de memória (OOMKilled / reinício).
set -uo pipefail
RT=$1; R=$2; ENVF=$3; OUT=$4
ROTAS=(${ROTAS:-/ /login /api/v1/health})
DUR=${DUR:-15s}; CONC=${CONC:-50}; PORT=3996
mkdir -p "$OUT"; tag="ctr-$RT-$R"; NOME=bunbench-ctr

docker rm -f $NOME >/dev/null 2>&1
t0=$(python3 -c 'import time;print(time.time())')
docker run -d --name $NOME --memory 768m --memory-swap 768m --cpus 2 \
  --env-file "$ENVF" -p $PORT:3000 "bunbench/app:$RT" >/dev/null
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$PORT/)" = 200 ]; do sleep 0.05; done
t1=$(python3 -c 'import time;print(time.time())')
sleep 2
mem() { docker exec $NOME cat /sys/fs/cgroup/memory.current 2>/dev/null; }
echo "{\"rt\":\"$RT\",\"rodada\":$R,\"partida_ms\":$(python3 -c "print(round(($t1-$t0)*1000))"),\"mem_ocioso_bytes\":$(mem)}" > "$OUT/$tag.start.json"

for rota in "${ROTAS[@]}"; do
  nome=$(echo "$rota" | tr '/' '_'); [ "$nome" = _ ] && nome=_raiz
  oha --no-tui -z 3s -c "$CONC" "http://127.0.0.1:$PORT$rota" --output-format quiet >/dev/null 2>&1
  ( while true; do mem; sleep 0.25; done ) > "$OUT/$tag$nome.mem" 2>/dev/null &
  AMOS=$!
  oha --no-tui -z "$DUR" -c "$CONC" "http://127.0.0.1:$PORT$rota" --output-format json > "$OUT/$tag$nome.oha.json" 2>/dev/null
  kill $AMOS 2>/dev/null; wait $AMOS 2>/dev/null
done
# memory.peak é o pico que o cgroup viu durante a vida inteira do contêiner.
pico=$(docker exec $NOME cat /sys/fs/cgroup/memory.peak 2>/dev/null || echo null)
estado=$(docker inspect $NOME --format '{"oom_killed":{{.State.OOMKilled}},"reinicios":{{.RestartCount}},"rodando":{{.State.Running}}}')
echo "{\"mem_pico_bytes\":$pico,\"mem_fim_bytes\":$(mem || echo null),\"estado\":$estado}" > "$OUT/$tag.fim.json"
docker logs $NOME > "$OUT/$tag.log" 2>&1
docker rm -f $NOME >/dev/null
echo "ok $tag $(cat "$OUT/$tag.fim.json")"
