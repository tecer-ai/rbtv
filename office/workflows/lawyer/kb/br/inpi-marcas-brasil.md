# INPI — Registro de Marcas no Brasil (Self-Filing)

**Ultima atualizacao:** 2026-04-03
**Base legal:** Lei 9.279/1996 (Propriedade Industrial) [1]

---

## Autoatendimento

INPI nao exige advogado. Pessoa fisica ou juridica pode protocolar pedido diretamente via e-INPI e e-Marcas [2].

---

## Fluxo Resumido

1. Busca de anterioridade (pePI) [3]
2. Cadastro no e-INPI [4]
3. Emitir e pagar GRU [5]
4. Protocolar pedido no e-Marcas [6]
5. Acompanhar exame e oposicao

---

## 1. Busca de Anterioridade (Obrigatoria)

**Portal:** https://busca.inpi.gov.br/pePI/ [3]

| Tipo | Quando usar |
|------|-------------|
| **Exata** | Marca identica |
| **Radical** | Variacoes foneticas, substring (ex: "tecer" captura "tecer", "tecer+", "tecer software") |

Verificar: mesma classe Nice + especificacao sobreposta = conflito provavel. Especificacoes distintas na mesma classe podem coexistir (principio da especialidade, art. 124 c/c art. 129) [1].

---

## 2. Cadastro e-INPI

1. Acessar https://www.gov.br/inpi/pt-br/cadastro-no-e-inpi [4]
2. Cadastrar como **Cliente** (pessoa juridica ou fisica domiciliada no pais)
3. Guardar login e senha
4. Usar e-mail que monitora frequentemente — INPI envia intimacoes e avisos

---

## 3. GRU (Guia de Recolhimento da Uniao)

**Cada classe = um pedido separado = uma GRU.** Para 4 classes, emitir 4 GRUs [5].

| Codigo | Tipo | Quando usar |
|--------|------|-------------|
| **389** | Classificador padrao (especificacao pre-aprovada) | Atividade existe na lista Nice do INPI. Mais rapido, menor risco de exigencia. |
| **394** | Livre preenchimento | Atividade especifica nao esta na lista. Maior flexibilidade, maior risco de exigencia. |

**Desconto (ate 50%):** MEI, ME, EPP, pessoa fisica, entidades sem fins lucrativos. Comprovar no cadastro.

**Valores:** Verificar em https://www.gov.br/inpi/pt-br/servicos/marcas/custos [5] — tabela atualiza periodicamente.

**Ordem:** Pagar GRU **antes** de protocolar. Guardar o "Nosso Numero" da GRU — sera exigido no e-Marcas.

---

## 4. Classificacao Nice (Resumo para Tech/SaaS)

| Classe | Descricao | Exemplos |
|--------|-----------|----------|
| **9** | Software, hardware, dados | Software de gestao; plataformas SaaS; processamento de dados |
| **35** | Servicos de gestao empresarial | Consultoria em gestao; automacao de processos; assessoria comercial |
| **36** | Servicos financeiros | Informacao financeira; analise financeira; processamento de dados financeiros |
| **42** | Servicos de tecnologia | Desenvolvimento de software; computacao em nuvem; hospedagem; consultoria em TI |

Classes 1-34 = produtos. Classes 35-45 = servicos [7].

**Lista completa:** https://www.gov.br/inpi/pt-br/servicos/marcas/classificacao-marcas [7]

---

## 5. e-Marcas — Protocolar Pedido

**Portal:** https://www.gov.br/inpi/pt-br/servicos/marcas/e-marcas [6]

1. Login no e-Marcas com credenciais e-INPI
2. Inserir numero da GRU paga
3. **Apresentacao da marca:**
   - **Nominativa:** so texto (ex: TECER)
   - **Mista:** texto + logo
   - **Figurativa:** so desenho/simbolo
4. **Natureza:** Produto/Servico (ou Certificacao)
5. Preencher dados da marca exatamente como deseja proteger
6. Selecionar classe(s) e especificacoes:
   - Codigo 389: marcar itens da lista pre-aprovada
   - Codigo 394: redigir descricao manual
7. Protocolar e guardar comprovante

---

## 6. Apos o Protocolo

| Etapa | Prazo | Acao |
|-------|-------|------|
| Exame formal | ~30 dias | INPI verifica documentacao |
| Publicacao RPI | Apos deferimento formal | Revista da Propriedade Industrial (tercas-feiras) |
| **Oposicao** | **60 dias** apos publicacao (art. 158) [1] | Terceiros podem opor. Monitorar e-mail. |
| Exame de merito | ~18 meses (media) | INPI analisa anterioridades e especificacoes |
| Deferimento/Indeferimento | — | Se indeferido, prazo para recurso |

**Acompanhamento:** "Meus Pedidos" no e-INPI ou consulta por numero do processo no pePI [3].

---

## 7. Especificacoes — Boas Praticas

- **Evitar termos genericos:** "servicos em geral" gera exigencia
- **Ser especifico:** "Software de gestao financeira autonoma" > "software"
- **Usar linguagem da Classificacao Nice** quando possivel [7]
- **Principio da especialidade:** especificacoes distintas na mesma classe podem coexistir — diferenciar claramente da marca anterior se houver

---

## 8. Resposta a Exigencia

**Base legal:** Art. 159, Lei 9.279/1996 [1]

Quando o INPI identifica irregularidades ou necessidade de esclarecimentos, emite uma exigencia publicada na RPI.

| Campo | Detalhe |
|-------|---------|
| **Prazo** | 60 dias corridos a partir da publicacao na RPI |
| **Consequencia se nao responder** | Arquivamento definitivo do pedido (art. 157, Lei 9.279/1996) [1] |
| **Onde responder** | e-INPI, aba "Meus Pedidos", botao "Peticionar" |
| **GRU para resposta** | Codigo 389 (se houver custo) - verificar na tabela de retribuicoes [5] |
| **Formato** | Peticao respondendo ponto a ponto cada item da exigencia |

**Tipos comuns de exigencia:**

| Tipo | Causa | Como resolver |
|------|-------|---------------|
| Especificacao generica | Termos vagos ("servicos em geral") | Reescrever com linguagem Nice especifica [7] |
| Colidencia com marca anterior | INPI identificou marca similar na mesma classe | Argumentar especialidade (especificacoes distintas), apresentar acordo de coexistencia, ou restringir especificacoes |
| Problema documental | Dados incorretos, comprovante de ME/EPP ausente | Reenviar documentos corretos |
| Distintividade | Marca considerada generica ou descritiva (art. 124, VI) [1] | Argumentar carater distintivo, apresentar provas de uso |

---

## 9. Resposta a Oposicao

**Base legal:** Art. 158, Lei 9.279/1996 [1]

Quando um terceiro apresenta oposicao ao pedido de marca (dentro dos 60 dias apos publicacao na RPI):

| Campo | Detalhe |
|-------|---------|
| **Prazo para manifestacao** | 60 dias corridos apos intimacao |
| **Consequencia se nao responder** | O exame de merito prossegue, mas sem argumentos do requerente - INPI decide apenas com a oposicao |
| **Onde responder** | e-INPI, peticionamento vinculado ao processo |
| **GRU** | Verificar se ha custo na tabela de retribuicoes [5] |

**Estrutura da manifestacao:**

1. Qualificacao do requerente
2. Resumo do pedido (numero, marca, classe, especificacoes)
3. Analise ponto a ponto dos argumentos do oponente
4. Argumentos de defesa (principio da especialidade, coexistencia pacifica, ausencia de confusao)
5. Provas (se houver): uso anterior, registros em outras classes, documentos comerciais
6. Pedido de deferimento

---

## 10. Renovacao

**Base legal:** Art. 133, Lei 9.279/1996 [1]

| Campo | Detalhe |
|-------|---------|
| **Vigencia do registro** | 10 anos a partir da concessao (art. 133) [1] |
| **Prazo para renovar** | Ultimo ano de vigencia (entre o 9o e o 10o ano) |
| **Prazo extraordinario** | 6 meses apos expiracao, com retribuicao adicional (art. 133, par. 1o) [1] |
| **Consequencia se nao renovar** | Extincao do registro (art. 142, II) [1] |
| **GRU** | Codigo especifico para renovacao - verificar tabela de retribuicoes [5] |
| **Onde protocolar** | e-INPI, peticionamento vinculado ao numero do registro |

**Atencao:** Monitorar o prazo com antecedencia. INPI nao envia aviso de vencimento.

---

## 11. Transferencia e Cessao de Marca

**Base legal:** Art. 134, Lei 9.279/1996 [1]

| Campo | Detalhe |
|-------|---------|
| **Quem pode transferir** | Titular do registro ou pedido |
| **Requisito** | Cessionario deve ter atividade compativel com a marca |
| **Averbacao obrigatoria** | Transferencia so produz efeitos perante terceiros apos averbacao no INPI (art. 134) [1] |
| **Cessao de marcas semelhantes** | Art. 135: cessao deve abranger marcas iguais ou semelhantes relativas a produto/servico identico [1] |
| **GRU** | Codigo especifico para transferencia - verificar tabela [5] |

Relevante para transacoes societarias: se a empresa mudar de titularidade ou se a marca for cedida entre socios e empresa.

---

## 12. Marca Mista — Requisitos de Imagem

**Base:** Manual de Marcas Secao 3.05 [1], Secao 5.09 [9]

### Especificacoes Tecnicas

| Requisito | Valor |
|-----------|-------|
| Formato | JPG (raster) ou AI/EPS/SVG/PDF (vetor) |
| Resolucao | 300 DPI |
| Dimensoes | 945 x 945 pixels (moldura 8 cm x 8 cm) |
| Minimo raster | 1200 pixels no lado maior |
| Tamanho maximo | 2 MB |
| Modo de cor | RGB |
| Conteudo | Imagem unica, sem duplicacoes ou variacoes |
| Proibido | Simbolo (R), enderecos, telefones, texto promocional |

### Reivindicacao de Cores

**Regra critica:** Qualquer elemento colorido na imagem submetida — incluindo o fundo — e tratado como parte da marca registrada [1] [10] [11].

| Abordagem | Reivindicacao de cor? | Prova de uso aceita | Flexibilidade |
|-----------|----------------------|---------------------|---------------|
| **Escala de cinza/P&B em fundo branco** | Nao | Qualquer versao colorida | Total |
| **Versao colorida (ex: navy em branco)** | Sim | Deve corresponder as cores registradas | Restrita |
| **Versao colorida com fundo colorido** | Sim (inclui fundo) | Fundo colorido e parte da marca | Mais restrita |

**Recomendacao:** Protocolar em escala de cinza (preto sobre branco) para protecao mais ampla. A marca fica protegida independente das cores usadas na pratica.

**Risco de caducidade (Art. 143, Lei 9.279/96):** Marcas com reivindicacao de cor so toleram "modificacoes no grau de saturacao das cores" — nao substituicao de matiz [8]. Marcas sem reivindicacao de cor aceitam prova de uso "com aplicacao de quaisquer cores" [8].

### Tipografia Banal (Alerta)

O Manual de Marcas (Secao 5.09) lista "tipografia banal" como elemento figurativo **incapaz de conferir distintividade** [9]. Fontes comerciais padrao (Google Fonts, system fonts) nao atendem o limiar de "forma fantasiosa ou estilizada" exigido para marca mista.

**Consequencias praticas:**

| Situacao | Resultado |
|----------|-----------|
| Palavra distintiva + fonte padrao como mista | Aceita, mas protecao grafica nula — nominativa seria superior |
| Palavra fraca/descritiva + fonte padrao como mista | Risco de indeferimento — tipografia banal nao compensa fraqueza nominal |
| Palavra + logotipo/icone genuino como mista | Protecao plena — elemento grafico adiciona valor |

**Quando usar mista:** Somente quando o logo possui elementos graficos genuinos (icone, simbolo, lettering customizado, composicao distintiva alem de selecao de fonte).

---

## 13. Nominativa vs Mista — Estrategia

| Fator | Nominativa | Mista |
|-------|-----------|-------|
| Protege a palavra | Em qualquer forma visual | Apenas na composicao especifica |
| Flexibilidade de fonte/cor | Total | Presa a imagem registrada |
| Se rebrandar tipografia | Ainda protegida | Registro invalidado |
| Custo | Mesmo (GRU 389 ou 394) | Mesmo |
| Aprovacao | Exame mais rigoroso da palavra | Taxa de aprovacao mais alta quando ha elemento grafico real |

**Recomendacao para startups:** Protocolar nominativa primeiro (protecao ampla da palavra). Protocolar mista separadamente apenas quando existir logo com elemento grafico genuino.

---

## 14. Quando Considerar Advogado (Opcional)

- Anterioridades em mesma classe com especificacoes proximas
- Exigencia de argumentacao (coexistencia, distintividade)
- Recursos contra indeferimento
- Marca complexa (mista, tridimensional, certificacao)

---

## Fontes

**Legislacao**

[1] Lei 9.279/1996 (Propriedade Industrial) — https://www.planalto.gov.br/ccivil_03/leis/l9279.htm

**Portais Oficiais INPI**

[2] Guia basico de marcas — https://www.gov.br/inpi/pt-br/assuntos/marcas
[3] Busca de marcas (pePI) — https://busca.inpi.gov.br/pePI/
[4] Cadastro e-INPI — https://www.gov.br/inpi/pt-br/cadastro-no-e-inpi
[5] Custos e GRU — https://www.gov.br/inpi/pt-br/servicos/marcas/custos
[6] e-Marcas (protocolo de pedidos) — https://www.gov.br/inpi/pt-br/servicos/marcas/e-marcas
[7] Classificacao Nice — https://www.gov.br/inpi/pt-br/servicos/marcas/classificacao-marcas

**Manual de Marcas — Secoes Especificas**

[8] Caducidade (Secao 6.05) — https://manualdemarcas.inpi.gov.br/projects/manual/wiki/6%C2%B705_Caducidade
[9] Analise de distintividade (Secao 5.09) — https://manualdemarcas.inpi.gov.br/projects/manual/wiki/5%C2%B709_An%C3%A1lise_do_requisito_de_distintividade_do_sinal_marc%C3%A1rio
[10] Anotacoes e alteracoes diversas (Secao 09) — https://manualdemarcas.inpi.gov.br/projects/manual/wiki/09_Anota%C3%A7%C3%B5es_e_altera%C3%A7%C3%B5es_diversas

**Referencia Tecnica**

[11] Manual de Marcas do INPI — https://manualdemarcas.inpi.gov.br/

**Tabela de Retribuicoes**

[12] Portaria INPI/PR 10/2025 — custos atualizados desde 20/09/2025. Desconto ME: 50% (reduzido de 60%)
[13] INPI fixa descontos para nova tabela — https://www.gov.br/inpi/pt-br/central-de-conteudo/noticias/inpi-fixa-descontos-para-a-nova-tabela-de-retribuicoes-pelos-seus-servicos

**Pratica e Estrategia**

[14] Legis Marcas — marca mista — https://legismarcas.com.br/o-que-e-marca-mista/
[15] Marcas Ja — cores e fundos — https://marcasja.com.br/blog/logotipo-cores-fundos-e-letras/
[16] 123 Marcas — cores dos logotipos — https://123marcas.com.br/2020/12/cores-dos-logotipos-e-de-seus-fundos/
