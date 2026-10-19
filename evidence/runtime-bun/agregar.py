#!/usr/bin/env python3
"""Agrega bruto/ em resumo.json e resumo-tabelas.md: mediana das rodadas por
runtime e a variação do Bun sobre o Node. Uso: python3 agregar.py (desta pasta)."""
import glob, json, os, re, statistics as st

AQUI = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(AQUI, "bruto")
med = lambda xs: st.median(xs) if xs else None


def var(n, b, menor_melhor):
    if not n or b is None:
        return ""
    d = (b - n) / n * 100
    melhor = d < 0 if menor_melhor else d > 0
    return f"{d:+.1f}% {'✅' if melhor else '❌'}"


resumo, md = {}, []

# ---- app ----
rotas = sorted({re.sub(r"^(node|bun)-\d+", "", os.path.basename(f)).replace(".oha.json", "")
                for f in glob.glob(f"{B}/app/*.oha.json")})
app = {}
for rt in ("node", "bun"):
    starts = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/app/{rt}-*.start.json"))]
    fins = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/app/{rt}-*.fim.json"))]
    a = {"rodadas": len(starts),
         "partida_ms": med([s["partida_ms"] for s in starts]),
         "rss_ocioso_mb": med([s["rss_ocioso_kb"] / 1024 for s in starts]),
         "rss_pos_carga_mb": med([f["rss_pos_carga_kb"] / 1024 for f in fins]), "rotas": {}}
    for r in rotas:
        oh = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/app/{rt}-*{r}.oha.json"))]
        pi = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/app/{rt}-*{r}.pico.json"))]
        a["rotas"][r] = {
            "rps": med([o["summary"]["requestsPerSec"] for o in oh]),
            "p50_ms": med([o["latencyPercentiles"]["p50"] * 1000 for o in oh]),
            "p99_ms": med([o["latencyPercentiles"]["p99"] * 1000 for o in oh]),
            "sucesso": min(o["summary"]["successRate"] for o in oh),
            "status": [o["statusCodeDistribution"] for o in oh],
            "rss_pico_mb": med([p["rss_pico_kb"] / 1024 for p in pi]),
        }
    app[rt] = a
resumo["app"] = app

n, b = app["node"], app["bun"]
md += ["## App (Next standalone `server.js`)", "",
       f"Mediana de {n['rodadas']} rodadas por runtime, alternadas.", "",
       "| Métrica | Node 22 | Bun 1.4 | Variação |", "|---|---:|---:|---:|",
       f"| Partida até o 1º 200 em `/` (ms) | {n['partida_ms']:.0f} | {b['partida_ms']:.0f} | {var(n['partida_ms'], b['partida_ms'], True)} |",
       f"| RSS ocioso após partida (MB) | {n['rss_ocioso_mb']:.0f} | {b['rss_ocioso_mb']:.0f} | {var(n['rss_ocioso_mb'], b['rss_ocioso_mb'], True)} |",
       f"| RSS após toda a carga (MB) | {n['rss_pos_carga_mb']:.0f} | {b['rss_pos_carga_mb']:.0f} | {var(n['rss_pos_carga_mb'], b['rss_pos_carga_mb'], True)} |", ""]
md += ["| Rota | req/s Node | req/s Bun | Δ req/s | p50 Node | p50 Bun | p99 Node | p99 Bun | Δ p99 | RSS pico Node | RSS pico Bun |",
       "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for r in rotas:
    x, y = n["rotas"][r], b["rotas"][r]
    nome = "/" if r == "_raiz" else "JS estático (`/_next/static/…`)" if r.startswith("__next") else f"`{r.replace('_', '/')}`"
    md.append(f"| {nome} | {x['rps']:.0f} | {y['rps']:.0f} | {var(x['rps'], y['rps'], False)} "
              f"| {x['p50_ms']:.1f} | {y['p50_ms']:.1f} | {x['p99_ms']:.1f} | {y['p99_ms']:.1f} | {var(x['p99_ms'], y['p99_ms'], True)} "
              f"| {x['rss_pico_mb']:.0f} | {y['rss_pico_mb']:.0f} |")
md.append("")

# ---- app em contêiner (limites de produção) ----
ctr = {}
for rt in ("node", "bun"):
    starts = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/container/ctr-{rt}-*.start.json"))]
    if not starts:
        continue
    fins = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/container/ctr-{rt}-*.fim.json"))]
    c = {"rodadas": len(starts),
         "partida_ms": med([s["partida_ms"] for s in starts]),
         "mem_ocioso_mb": med([s["mem_ocioso_bytes"] / 2**20 for s in starts]),
         "mem_pico_mb": med([f["mem_pico_bytes"] / 2**20 for f in fins]),
         "oom_killed": [f["estado"]["oom_killed"] for f in fins],
         "reinicios": [f["estado"]["reinicios"] for f in fins], "rotas": {}}
    for r in rotas:
        oh = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/container/ctr-{rt}-*{r}.oha.json"))]
        if oh:
            c["rotas"][r] = {"rps": med([o["summary"]["requestsPerSec"] for o in oh]),
                             "p99_ms": med([o["latencyPercentiles"]["p99"] * 1000 for o in oh]),
                             "sucesso": min(o["summary"]["successRate"] for o in oh),
                             "status": [o["statusCodeDistribution"] for o in oh]}
    ctr[rt] = c
resumo["app_container"] = ctr
if len(ctr) == 2:
    n, b = ctr["node"], ctr["bun"]
    md += ["## App em contêiner com os limites de produção (`mem_limit: 768m`, 2 CPUs, Linux)", "",
           f"A imagem construída por cada Dockerfile. Mediana de {n['rodadas']} rodadas.", "",
           "| Métrica | Node 22 | Bun 1.4 | Variação |", "|---|---:|---:|---:|",
           f"| Partida até o 1º 200 (ms) | {n['partida_ms']:.0f} | {b['partida_ms']:.0f} | {var(n['partida_ms'], b['partida_ms'], True)} |",
           f"| Memória do contêiner ociosa (MB) | {n['mem_ocioso_mb']:.0f} | {b['mem_ocioso_mb']:.0f} | {var(n['mem_ocioso_mb'], b['mem_ocioso_mb'], True)} |",
           f"| Pico de memória do contêiner (MB) | {n['mem_pico_mb']:.0f} | {b['mem_pico_mb']:.0f} | {var(n['mem_pico_mb'], b['mem_pico_mb'], True)} |",
           f"| Morto por falta de memória (por rodada) | {n['oom_killed']} | {b['oom_killed']} | |"]
    for r in rotas:
        if r in n["rotas"] and r in b["rotas"]:
            x, y = n["rotas"][r], b["rotas"][r]
            nome = "/" if r == "_raiz" else f"`{r.replace('_', '/')}`"
            md.append(f"| {nome} req/s | {x['rps']:.0f} | {y['rps']:.0f} | {var(x['rps'], y['rps'], False)} |")
            md.append(f"| {nome} p99 (ms) | {x['p99_ms']:.1f} | {y['p99_ms']:.1f} | {var(x['p99_ms'], y['p99_ms'], True)} |")
    md.append("")

# ---- resistência: 3 min de /login, 100 conexões, mesmos limites ----
res = {}
for rt in ("node", "bun"):
    fs_ = glob.glob(f"{B}/resistencia/ctr-{rt}-*.fim.json")
    oh = glob.glob(f"{B}/resistencia/ctr-{rt}-*_login.oha.json")
    if not fs_ or not oh:
        continue
    f, o = json.load(open(fs_[0])), json.load(open(oh[0]))
    amostras = [int(x) for x in open(glob.glob(f"{B}/resistencia/ctr-{rt}-*_login.mem")[0]).read().split() if x.strip()]
    res[rt] = {"rps": o["summary"]["requestsPerSec"], "p99_ms": o["latencyPercentiles"]["p99"] * 1000,
               "sucesso": o["summary"]["successRate"], "status": o["statusCodeDistribution"],
               "erros": o.get("errorDistribution"), "mem_pico_mb": f["mem_pico_bytes"] / 2**20,
               "mem_final_carga_mb": amostras[-1] / 2**20 if amostras else None, "estado": f["estado"]}
resumo["resistencia"] = res
if len(res) == 2:
    n, b = res["node"], res["bun"]
    md += ["## Resistência: 3 min de `/login` a 100 conexões, no contêiner de 768 MB", "",
           "| Métrica | Node 22 | Bun 1.4 | Variação |", "|---|---:|---:|---:|",
           f"| req/s | {n['rps']:.0f} | {b['rps']:.0f} | {var(n['rps'], b['rps'], False)} |",
           f"| p99 (ms) | {n['p99_ms']:.0f} | {b['p99_ms']:.0f} | {var(n['p99_ms'], b['p99_ms'], True)} |",
           f"| Taxa de sucesso | {n['sucesso']:.4f} | {b['sucesso']:.4f} | |",
           f"| Pico de memória do contêiner (MB) | {n['mem_pico_mb']:.0f} | {b['mem_pico_mb']:.0f} | {var(n['mem_pico_mb'], b['mem_pico_mb'], True)} |",
           f"| Memória no fim da carga (MB) | {n['mem_final_carga_mb']:.0f} | {b['mem_final_carga_mb']:.0f} | |",
           f"| Morto por falta de memória | {n['estado']['oom_killed']} | {b['estado']['oom_killed']} | |", ""]

# ---- memória anônima (o que de fato leva ao OOM; cache de arquivo o kernel devolve) ----
anon = {}
for rt in ("node", "bun", "bun-smol", "bun-ram768"):
    a = os.path.join(B, "anon", f"{rt}.amostras")
    if not os.path.exists(a):
        continue
    serie = [int(x) for x in re.findall(r"anon=(\d+)", open(a).read())]
    o = json.load(open(os.path.join(B, "anon", f"{rt}.oha.json")))
    anon[rt] = {"anon_max_mb": max(serie), "anon_estavel_mb": med(serie[len(serie) // 2:]),
                "rps": o["summary"]["requestsPerSec"], "p99_ms": o["latencyPercentiles"]["p99"] * 1000}
resumo["memoria_anonima"] = anon
if "node" in anon and "bun" in anon:
    rotulo = {"node": "Node 22", "bun": "Bun 1.4", "bun-smol": "Bun 1.4 `--smol`",
              "bun-ram768": "Bun 1.4 `BUN_JSC_forceRAMSize=768MB`"}
    md += ["## Memória anônima sob carga (2 min de `/login`, 100 conexões, contêiner de 768 MB)", "",
           "`memory.stat anon` do cgroup, amostrado a cada 1 s. É a memória que leva ao OOM; o cache de arquivo o kernel devolve sob pressão.", "",
           "| Configuração | anon estável (MB) | anon máx. (MB) | req/s | p99 (ms) |", "|---|---:|---:|---:|---:|"]
    for rt, v in anon.items():
        md.append(f"| {rotulo[rt]} | {v['anon_estavel_mb']:.0f} | {v['anon_max_mb']} | {v['rps']:.0f} | {v['p99_ms']:.0f} |")
    md.append("")

# ---- worker ----
wk = {}
for rt in ("node", "bun"):
    js = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/worker/worker-{rt}-*.json")) if not f.endswith(".oha.json")]
    if not js:
        continue
    om = [json.load(open(f)) for f in sorted(glob.glob(f"{B}/worker/worker-{rt}-*.metrics.oha.json"))]
    wk[rt] = {k: med([j[k] for j in js]) for k in
              ("partida_ms", "rss_5s_kb", "rss_ocioso_med_kb", "rss_ocioso_max_kb", "cpu_ocioso_60s_s", "rss_pos_metrics_kb", "sigterm_ms")}
    wk[rt]["codigos_saida"] = [j["codigo_saida"] for j in js]
    wk[rt]["metrics_rps"] = med([o["summary"]["requestsPerSec"] for o in om])
    wk[rt]["rodadas"] = len(js)
resumo["worker"] = wk
if len(wk) == 2:
    n, b = wk["node"], wk["bun"]
    mb = lambda kb: kb / 1024
    md += ["## Worker (`workers/agent-worker/main.ts`)", "",
           f"Node: `node --import tsx` (como o Dockerfile.worker). Bun: `bun main.ts`, sem tsx. Mediana de {n['rodadas']} rodadas.", "",
           "| Métrica | Node 22 | Bun 1.4 | Variação |", "|---|---:|---:|---:|",
           f"| Partida até o `/healthz` responder (ms) | {n['partida_ms']:.0f} | {b['partida_ms']:.0f} | {var(n['partida_ms'], b['partida_ms'], True)} |",
           f"| RSS 5 s após partida (MB) | {mb(n['rss_5s_kb']):.0f} | {mb(b['rss_5s_kb']):.0f} | {var(n['rss_5s_kb'], b['rss_5s_kb'], True)} |",
           f"| RSS médio em 60 s ociosos (MB) | {mb(n['rss_ocioso_med_kb']):.0f} | {mb(b['rss_ocioso_med_kb']):.0f} | {var(n['rss_ocioso_med_kb'], b['rss_ocioso_med_kb'], True)} |",
           f"| CPU gasta em 60 s ociosos (s) | {n['cpu_ocioso_60s_s']:.2f} | {b['cpu_ocioso_60s_s']:.2f} | {var(n['cpu_ocioso_60s_s'], b['cpu_ocioso_60s_s'], True)} |",
           f"| `/metrics` (consulta ao Postgres), req/s | {n['metrics_rps']:.0f} | {b['metrics_rps']:.0f} | {var(n['metrics_rps'], b['metrics_rps'], False)} |",
           f"| SIGTERM até sair (ms) | {n['sigterm_ms']:.0f} | {b['sigterm_ms']:.0f} | |",
           f"| Código de saída no SIGTERM | {n['codigos_saida']} | {b['codigos_saida']} | |", ""]

# ---- imagens ----
imgs = os.path.join(B, "imagens.json")
if os.path.exists(imgs):
    resumo["imagens"] = im = json.load(open(imgs))
    md += ["## Imagens Docker (linux/arm64, descomprimidas)", "", "| Imagem | Node 22 | Bun 1.4 | Variação |", "|---|---:|---:|---:|"]
    for nome, v in im.items():
        md.append(f"| {nome} | {v['node_mb']:.0f} MB | {v['bun_mb']:.0f} MB | {var(v['node_mb'], v['bun_mb'], True)} |")
    md.append("")

json.dump(resumo, open(os.path.join(AQUI, "resumo.json"), "w"), indent=2, ensure_ascii=False)
open(os.path.join(AQUI, "resumo-tabelas.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
