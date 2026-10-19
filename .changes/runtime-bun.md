---
impacto: nada_mudou
secao: alterado
titulo: O sistema e o processo de fundo passam a rodar no Bun, e respondem mais rápido
---

O sistema e o processo de fundo que atende pelos agentes passam a rodar no Bun em vez
do Node. Nas medições com os mesmos limites de memória de uma instalação, as páginas
e a API responderam quase duas vezes mais requisições por segundo, com a resposta mais
lenta caindo pela metade, e o processo de fundo sobe três vezes mais rápido e ocupa
cerca de 30% menos memória quando está parado. Sob carga muito alta, o sistema usa mais
memória do que antes, dentro do limite que a instalação já reserva para ele. Nada muda
na tela nem no que você configura, e a atualização é a de sempre (`bash update.sh`).
O atendimento por voz segue como estava.
