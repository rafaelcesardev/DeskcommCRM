# Verificações de comportamento: Node 22 × Bun 1.4.3

O que foi conferido além dos números. Cada item diz o que foi feito e o que saiu.
Máquina: Apple M5 (10 núcleos, 16 GB), macOS; contêineres no OrbStack (Linux arm64).
Base: `upstream/main` em `77fb59fae`.

## App (Next standalone)

| Verificação | Como | Resultado |
|---|---|---|
| Mesmas respostas | `/`, `/login`, `/app`, `/api/v1/health` nos dois runtimes | Status idênticos: 200, 200, 307, 503 (o 503 é a falta de WAHA, igual nos dois); JSON do health igual |
| Mesmo HTML | `/` descomprimido; payload RSC (`self.__next_f`) concatenado | Payload idêntico (10.986 caracteres) e HTML fora dele idêntico. **Muda o fatiamento**: o Node manda o RSC em 1 `<script>`, o Bun em 10 |
| Custo do fatiamento | Bytes por resposta no `oha` (gzip) | HTML ~22% maior pela rede no Bun (`/` 6.124 → 7.480 B; `/login` 12.536 → 15.067 B): o stream fatiado comprime pior |
| `KEEP_ALIVE_TIMEOUT` respeitado (proteção contra 502 atrás do Caddy/Traefik) | `sonda-keepalive.py`: socket ocioso 8 s e reuso | Com `125000`: 200 nos dois. Controle sem a variável: os dois derrubam o socket, então a sonda enxerga o defeito |
| Fuso e `Intl` | Data, data em São Paulo, moeda BRL, tempo relativo, lista, ordenação, plural, espanhol, dentro das imagens | Saída idêntica; os dois em UTC (nem `node:22-alpine` nem `oven/bun:1.4.3-alpine` trazem `tzdata`) |
| Contêiner sobe como na VPS | `docker run` da imagem Bun | `/` 200, `/app` 307 (o sinal do runbook de deploy), PID 1 `bun server.js` como `nextjs`, `ffmpeg` presente |
| Extração de PDF pelo módulo empacotado | `scripts/sonda-pdf-na-imagem.mjs` (a sonda do `publish-image.yml`) | `VEREDITO=GREEN` nas duas imagens |
| Binários nativos | `import()` de `sharp`, `@napi-rs/canvas`, `pdfjs-dist` nas duas imagens | Comportamento idêntico (inclusive as mesmas faltas do binário do canvas no build arm64 local, que já existem no upstream) |
| Instrumentação `nodejs` do Next | Linha `[telemetria]` do `sentry.server.config` no boot | Aparece nos dois, então `NEXT_RUNTIME` vale `nodejs` sob Bun |

## Worker

| Verificação | Como | Resultado |
|---|---|---|
| Boot e healthz | `bun workers/agent-worker/main.ts` com Postgres e Redis locais | `/healthz` `{"status":"ok","db":"ok",...,"event_log_drain":{"carregado":true}}` |
| SIGTERM drena (#2823) | `bench-worker.sh` (3 rodadas) e `tests/unit/worker-pid1-drena-envio-em-voo.test.ts` com launcher `bun` | Saída 0 em todas; o ensaio de 6 s de envio em voo passa |
| Laço do event_log carrega na imagem (#648) | `scripts/sonda-do-laco-de-event-log.ts` com `--entrypoint bun` | `{"ok":true,...,"carregado":true}`, igual ao Node |
| Gate de boot do CI sem banco | `docker run` da imagem com `SUPABASE_DB_URL` inexistente | Mesma morte nos dois: `boot falhou: connect ECONNREFUSED 127.0.0.1:5432` (o padrão que o `publish-image.yml` aceita) |
| Teto de memória do filho do PDF | Filho com `--max-old-space-size=160` alocando sem parar | Node morre em `heap limit`; **Bun ignora a flag e passa de 2,4 GB**. Por isso o vigia de RSS |
| Vigia de RSS (Linux) | Imagem do worker Bun, `lib/` desta branch montado, teto de 30 MB | `PdfExtractError: o processo de extração passou do teto de memória (30 MB de RSS)`; a extração seguinte funciona |
| Sabotagem do vigia | Mesma execução com `const vigia = false` | Nenhum erro: o filho cresce sem teto, e o teste novo cai nas 2 asserções de erro, como previsto |
| RSS de base do filho de extração | `/usr/bin/time -l` extraindo as fixtures | Node ~116–121 MB; Bun ~100–102 MB. Daí o teto padrão `heapMb + 96` = 256 MB |

## Achado fora do escopo (defeito no `upstream/main`, independente do Bun)

`estrategiaPadrao()` em `lib/ai/rag/extractors/pdf.ts` só reconhece o `tsx` por um
caminho com barra (`/tsx/`). Desde a #2823 (13/10/2026) o `CMD` do worker é
`node --import tsx`, cujo `process.execArgv` é `["--import","tsx"]`, sem barra.
Resultado medido: sob o `CMD` atual a estratégia é `em-processo` e o processo
extrai a fixture com **439 MB de RSS**, num contêiner de `mem_limit: 512m`. É o
cenário do incidente de 15/09 (313 reinícios). Os testes não pegam porque só
cobrem a forma do `pnpm exec tsx` e o CLI do `tsx`. Nesta branch o worker passa a
rodar sob Bun e o defeito some da imagem, mas ele merece issue ou PR próprio.
