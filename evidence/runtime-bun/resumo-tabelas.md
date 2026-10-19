## App (Next standalone `server.js`)

Mediana de 3 rodadas por runtime, alternadas.

| Métrica | Node 22 | Bun 1.4 | Variação |
|---|---:|---:|---:|
| Partida até o 1º 200 em `/` (ms) | 2813 | 2407 | -14.4% ✅ |
| RSS ocioso após partida (MB) | 275 | 270 | -1.9% ✅ |
| RSS após toda a carga (MB) | 1231 | 884 | -28.2% ✅ |

| Rota | req/s Node | req/s Bun | Δ req/s | p50 Node | p50 Bun | p99 Node | p99 Bun | Δ p99 | RSS pico Node | RSS pico Bun |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| JS estático (`/_next/static/…`) | 6551 | 10757 | +64.2% ✅ | 6.8 | 4.4 | 13.5 | 9.9 | -26.5% ✅ | 1592 | 1067 |
| `/api/v1/health` | 671 | 1492 | +122.3% ✅ | 71.9 | 30.9 | 184.0 | 76.2 | -58.6% ✅ | 1593 | 1032 |
| `/login` | 278 | 465 | +67.1% ✅ | 175.4 | 102.8 | 307.2 | 166.8 | -45.7% ✅ | 654 | 738 |
| / | 343 | 661 | +93.0% ✅ | 141.4 | 73.2 | 202.4 | 118.9 | -41.3% ✅ | 630 | 691 |

## App em contêiner com os limites de produção (`mem_limit: 768m`, 2 CPUs, Linux)

A imagem construída por cada Dockerfile. Mediana de 3 rodadas.

| Métrica | Node 22 | Bun 1.4 | Variação |
|---|---:|---:|---:|
| Partida até o 1º 200 (ms) | 1287 | 1495 | +16.2% ❌ |
| Memória do contêiner ociosa (MB) | 309 | 331 | +7.3% ❌ |
| Pico de memória do contêiner (MB) | 456 | 679 | +48.9% ❌ |
| Morto por falta de memória (por rodada) | [False, False, False] | [False, False, False] | |
| `/api/v1/health` req/s | 522 | 1372 | +162.7% ✅ |
| `/api/v1/health` p99 (ms) | 219.6 | 106.6 | -51.5% ✅ |
| `/login` req/s | 387 | 709 | +83.2% ✅ |
| `/login` p99 (ms) | 221.1 | 119.8 | -45.8% ✅ |
| / req/s | 503 | 977 | +94.1% ✅ |
| / p99 (ms) | 171.4 | 92.4 | -46.1% ✅ |

## Resistência: 3 min de `/login` a 100 conexões, no contêiner de 768 MB

| Métrica | Node 22 | Bun 1.4 | Variação |
|---|---:|---:|---:|
| req/s | 390 | 732 | +87.5% ✅ |
| p99 (ms) | 423 | 221 | -47.7% ✅ |
| Taxa de sucesso | 1.0000 | 1.0000 | |
| Pico de memória do contêiner (MB) | 442 | 762 | +72.4% ❌ |
| Memória no fim da carga (MB) | 326 | 643 | |
| Morto por falta de memória | False | False | |

## Memória anônima sob carga (2 min de `/login`, 100 conexões, contêiner de 768 MB)

`memory.stat anon` do cgroup, amostrado a cada 1 s. É a memória que leva ao OOM; o cache de arquivo o kernel devolve sob pressão.

| Configuração | anon estável (MB) | anon máx. (MB) | req/s | p99 (ms) |
|---|---:|---:|---:|---:|
| Node 22 | 285 | 307 | 399 | 318 |
| Bun 1.4 | 551 | 573 | 718 | 230 |
| Bun 1.4 `--smol` | 547 | 574 | 731 | 223 |
| Bun 1.4 `BUN_JSC_forceRAMSize=768MB` | 550 | 574 | 720 | 231 |

## Worker (`workers/agent-worker/main.ts`)

Node: `node --import tsx` (como o Dockerfile.worker). Bun: `bun main.ts`, sem tsx. Mediana de 3 rodadas.

| Métrica | Node 22 | Bun 1.4 | Variação |
|---|---:|---:|---:|
| Partida até o `/healthz` responder (ms) | 2924 | 994 | -66.0% ✅ |
| RSS 5 s após partida (MB) | 261 | 156 | -40.4% ✅ |
| RSS médio em 60 s ociosos (MB) | 217 | 155 | -28.6% ✅ |
| CPU gasta em 60 s ociosos (s) | 0.41 | 0.26 | -36.6% ✅ |
| `/metrics` (consulta ao Postgres), req/s | 3707 | 3947 | +6.5% ✅ |
| SIGTERM até sair (ms) | 50 | 49 | |
| Código de saída no SIGTERM | [0, 0, 0] | [0, 0, 0] | |

## Imagens Docker (linux/arm64, descomprimidas)

| Imagem | Node 22 | Bun 1.4 | Variação |
|---|---:|---:|---:|
| app | 928 MB | 841 MB | -9.4% ✅ |
| worker | 3639 MB | 1902 MB | -47.7% ✅ |

