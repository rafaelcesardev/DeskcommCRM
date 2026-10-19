# Runtime Bun 1.4 no lugar do Node 22: medição

Pergunta: trocar o runtime de produção de Node 22 para Bun 1.4 deixa o DeskcommCRM
mais rápido e mais leve? Base medida: `upstream/main` em `77fb59fae` (19/10/2026).

## Resposta curta

| | App (Next standalone) | Worker (agent-engine) |
|---|---|---|
| Velocidade | **Muito mais rápido**: +83% a +163% de req/s e p99 46–52% menor no contêiner de produção | Partida 66% mais rápida; `/metrics` +6% |
| Memória ociosa | Praticamente igual (+7% no contêiner) | **28–40% menor** |
| Memória sob carga pesada | **Quase o dobro**: anônima estável 551 MB contra 285 MB (100 conexões) | Não medido sob carga de turnos |
| Imagem | 928 → 841 MB (−9%) | 3,64 → 1,90 GB (−48%, a maior parte por ser multi-stage, não pelo Bun) |
| Comportamento | Igual (status, HTML, `Intl`, fuso, keep-alive, PDF empacotado) | Igual (healthz, SIGTERM drena, laço do event_log), com uma ressalva tratada: o teto de memória do filho do PDF |

**Mais rápido: sim, por larga margem. Mais leve: só no worker.** No app, o Bun
troca memória por velocidade: sob carga pesada ele usa o dobro de memória anônima,
e nem `--smol` nem `BUN_JSC_forceRAMSize` mudam isso. No contêiner de 768 MB ele não
foi morto em nenhuma execução, mas no teste de resistência o cgroup chegou a
762 MB (cache incluso) e a anônima a 573 MB.

## Onde estão os dados

| Arquivo | O quê |
|---|---|
| `resumo-tabelas.md` | Todas as tabelas, geradas por `agregar.py` |
| `resumo.json` | As mesmas medianas em JSON |
| `verificacoes.md` | O que foi conferido além dos números (comportamento, sabotagem, achado no upstream) |
| `bruto/app/` | App nativo no macOS: 3 rodadas × 2 runtimes × 4 rotas (JSON do `oha`, RSS amostrado, logs) |
| `bruto/worker/` | Worker nativo: 3 rodadas × 2 runtimes |
| `bruto/container/` | Imagens de produção com `--memory 768m --cpus 2`: 3 rodadas × 2 runtimes × 3 rotas |
| `bruto/resistencia/` | 3 min de `/login` a 100 conexões, um por runtime |
| `bruto/anon/` | Memória anônima do cgroup sob carga, incluindo as tentativas `--smol` e `forceRAMSize` |
| `bruto/imagens.json`, `bruto/build-node.time.txt` | Tamanho das imagens; tempo e memória do `next build` |
| `bench-app.sh`, `bench-worker.sh`, `bench-container.sh`, `sonda-keepalive.py` | Os scripts, para refazer |

Para regenerar as tabelas: `python3 evidence/runtime-bun/agregar.py`.

## Como foi medido

- **Mesmo artefato nos dois runtimes.** Um `next build` (Node 22.23.3) gera o
  `.next/standalone`; o mesmo `server.js` roda com `node` e com `bun`. O worker roda
  como o `Dockerfile.worker` o roda: `node --import tsx` contra `bun main.ts`.
- **Ambiente de instalação fresca**: Supabase local com o `baseline.sql`, owner
  criado pelo `bootstrap-owner.ts`, Redis + `serverless-redis-http` como na VPS,
  sem WAHA (o `/api/v1/health` responde 503 nos dois, igual), `SENTRY_DSN=off`.
- **Carga**: `oha` (Rust, fora dos dois runtimes), 3 s de aquecimento e 15 s de
  medição a 50 conexões por rota. Rodadas **alternadas** (Node, Bun, Node, Bun…)
  para que ruído de fundo caia igual nos dois. Medianas de 3 rodadas.
- **Contêiner**: as imagens construídas por cada Dockerfile, com o `mem_limit` do
  `docker-compose.prod.yml` (768 MB) e 2 CPUs.

## Limites desta medição (o que NÃO está provado)

- **Máquina**: Apple M5 (10 núcleos, 16 GB). Contêineres no OrbStack (Linux arm64,
  VM de 8 GB). Não é uma VPS x86 da HostGator; a relação entre os runtimes deve se
  manter, os números absolutos não.
- **As medições em contêiner rodaram com o Mac em DarkWake** (tela desligada, de
  madrugada), seguro pelo `caffeinate`, sem repouso no meio, conferido no
  `pmset -g log`. Node e Bun rodaram alternados nas mesmas condições: a comparação
  vale, os absolutos ficam abaixo de uma máquina plenamente acordada. As medições
  nativas (app e worker) terminaram antes do primeiro repouso da noite (03:32).
- **Só páginas públicas e rotas de API**: `/`, `/login`, `/api/v1/health` e um JS
  estático. Nenhuma tela autenticada (Inbox, CRM) foi medida sob carga.
- **Worker sem carga de turnos de IA.** Medido ocioso, no `/metrics` e no
  desligamento. Não houve turno de agente, envio de WhatsApp nem drenagem real.
- **HTML ~22% maior pela rede no Bun**: o stream RSC sai em 10 pedaços em vez de 1
  e o gzip comprime pior (conteúdo idêntico; ver `verificacoes.md`).
- **voice-agent não foi migrado**: áudio em tempo real com Asterisk e a OpenAI não
  tinha como ser provado aqui. Segue em Node.
- **Não rodados**: `pnpm test:db`, `pnpm test:e2e`, `pnpm test:shell`, e o e2e
  servido pelo Bun (o CI sobe o e2e com `next start` em Node, então o `e2e` verde não
  prova o runtime da imagem).

## Recomendação para o PR

1. **Worker primeiro, sozinho.** Ganha em tudo que foi medido (partida, memória,
   CPU ociosa, imagem) e não tem contra medido. Traz o teto de memória do filho do PDF
   sob Bun, já provado em Linux com sabotagem.
2. **App como decisão do mantenedor, com a troca escrita no PR.** Velocidade de
   quase 2×, contra o dobro de memória anônima sob carga pesada dentro de um
   orçamento de RAM fixo (a VPS do cliente divide 768 MB do app com o WAHA, o worker
   e o resto). Para um CRM de uma empresa pequena, a carga de 100 conexões
   simultâneas é rara, e ocioso os dois empatam; mas é o mantenedor quem conhece o
   tráfego real das instalações.
3. **Abrir à parte o defeito do `estrategiaPadrao()`** (ver `verificacoes.md`): ele
   existe no `upstream/main` hoje, com Node, independente desta migração.
