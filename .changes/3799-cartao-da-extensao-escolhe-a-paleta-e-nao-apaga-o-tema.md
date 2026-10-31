---
impacto: capacidade_nova
secao: corrigido
titulo: O cartão da extensão instalada passa a escolher a paleta do tema, e salvar a configuração não apaga mais o tema da organização
---

Até aqui, o tema de uma extensão só podia ser ligado pela API: em Extensões não havia campo para isso, e a organização ativava uma extensão de tema sem ver o tema. Pior: quem tinha ligado o tema pela API e depois mudava «Densidade dos cards» e salvava perdia o tema sem aviso, porque a tela mandava só os campos que ela mostra e a configuração inteira era substituída.

Agora, quando o manifesto da extensão declara um tema, o cartão mostra o campo «Paleta da extensão», com «Nenhuma (padrão do produto)» e a paleta que o pacote oferece. Ao salvar, o produto já aparece com as cores novas, sem recarregar a página. Salvar a configuração preserva tudo o que a tela não edita, inclusive um tema gravado antes. Extensão sem tema não ganha campo nenhum. Nada muda para quem opera a VPS.

Contribuição de @webtecnica (#3799), a partir do relato de @franklinferre (#3792).
