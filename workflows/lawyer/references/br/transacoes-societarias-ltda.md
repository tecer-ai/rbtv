# Transacoes Societarias — Sociedade Limitada (LTDA)

**Base legal principal:** Codigo Civil (Lei 10.406/2002) [1], arts. 997-1.087
**Legislacao complementar:** Lei 6.404/1976 (LSA, regencia supletiva) [2], CPC art. 606 [3]
**Ultima atualizacao:** 2026-04-03
**Fonte primaria:** Pesquisa juridica completa em `../research/compra-quotas-ltda/resultado-pesquisa-compra-quotas-ltda.md`

---

## 1. Quadro Legal

A LTDA e regida pelo CC arts. 1.052-1.087 [1], com aplicacao supletiva das regras da sociedade simples (arts. 997-1.038) [1]. O STJ reconhece que contrato social e acordo de quotistas tem primazia sobre as regras dispositivas do CC para saida e valuation.

**Cessao de quotas:** Na omissao do contrato social, a cessao a terceiro e permitida salvo oposicao de titulares de mais de 1/4 do capital social (art. 1.057 CC) [1].

**Resolucao em relacao a um socio:** Retirada voluntaria (art. 1.029) [1], exclusao judicial (art. 1.030) [1], exclusao extrajudicial (art. 1.085) [1].

---

## 2. Mecanismos de Saida

### 2.1 Direito de Retirada (Recesso)

| Campo | Detalhe |
|-------|---------|
| Base legal | Arts. 1.029 e 1.031 CC [1] |
| Prazo de notificacao | 60 dias de antecedencia (sociedade de prazo indeterminado) |
| Apuracao de haveres | Balanco de determinacao, pagamento em 90 dias (art. 1.031) [1] |
| Risco principal | Descapitalizacao da empresa com a regra padrao |
| Mitigacao | Acordo de quotistas pode definir metodo alternativo de valuation e prazo de pagamento estendido |

### 2.2 Exclusao Extrajudicial por Justa Causa

| Campo | Detalhe |
|-------|---------|
| Base legal | Art. 1.085 CC [1] |
| Requisitos cumulativos | (1) Socio minoritario, (2) justa causa por falta grave, (3) previsao no contrato social, (4) quorum maioria absoluta, (5) contraditorio previo |
| Jurisprudencia STJ | REsp 1.286.708/PR [4], REsp 2.170.665/DF [5] - rejeita mera quebra de affectio societatis como fundamento |
| Decisao marco 2025 | STJ validou exclusao via acordo de quotistas mesmo sem previsao no contrato social [6] |
| Limitacao 50/50 | Inaplicavel - nenhum socio detem mais da metade do capital |

**Atencao:** Reducao de esforco operacional NAO configura "falta grave" na jurisprudencia. Este mecanismo nao resolve o risco de socio inativo.

### 2.3 Call Option e Put Option

| Campo | Detalhe |
|-------|---------|
| Base legal | Art. 425 CC (contratos atipicos) [1] |
| Call option | Direito de obrigar o outro a vender quotas, atrelado a eventos-gatilho |
| Put option | Direito de obrigar o outro a comprar quotas |
| Gatilhos tipicos | Dedicacao abaixo do minimo acordado, descumprimento de obrigacoes, mudanca de controle |
| Precificacao | Definir metodo previamente (FCD, multiplos EBITDA, valor contabil com desagio) |

**Melhor uso:** Atrelar a metricas objetivas de dedicacao operacional. Resolve diretamente o risco do socio "carona".

### 2.4 Clausula Shotgun (Buy or Sell)

| Campo | Detalhe |
|-------|---------|
| Base legal | Art. 425 CC (contratos atipicos) [1] |
| Mecanismo | Socio A propoe preco por quota. Socio B decide: compra as quotas de A ou vende as suas a A, pelo mesmo preco |
| Prazo tipico | 15-30 dias para resposta |
| Risco | Assimetria financeira - socio com mais liquidez pode usar de forma predatoria |
| Mitigacao | Prever garantias de pagamento, limite de frequencia de ativacao |

**Melhor uso:** Resolucao de impasses estrategicos (deadlocks) em sociedades 50/50. O mecanismo mais simetrico e justo.

### 2.5 Vesting Reverso

| Campo | Detalhe |
|-------|---------|
| Base legal | Art. 425 CC (contratos atipicos) [1]. Art. 1.055 par. 2 CC proibe integralizacao por servicos [1] |
| Mecanismo | Quotas ja emitidas; acordo preve recompra das nao-vestidas por valor nominal se socio sair antes do prazo |
| Periodo tipico | 36-48 meses, com ou sem cliff |
| Tributacao | Possivel incidencia de ganho de capital na transferencia |

**Melhor uso:** Alinhamento entre esforco e participacao ao longo do tempo. Protege contra saida prematura.

---

## 3. Analise Comparativa

| Mecanismo | Simetria | Complexidade | Protecao ao ativo | Recomendacao |
|-----------|----------|-------------|-------------------|--------------|
| Retirada (Recesso) | Sim | Baixa | Baixa (descapitalizacao) | Personalizar valuation e prazo |
| Exclusao extrajudicial | Sim | Alta (risco judicial) | Media | Inadequado para socio inativo |
| Call/Put Option | Sim | Media | Alta | Recomendado |
| Shotgun | Sim | Baixa | Alta | Recomendado |
| Vesting Reverso | Sim | Alta | Alta | Considerar |

---

## 4. Protecoes Complementares

### 4.1 Nao-Competicao

| Campo | Detalhe |
|-------|---------|
| Validade | Plenamente valida entre socios |
| Limite temporal STJ | Ate 2 anos apos saida |
| Requisitos | (1) Delimitacao temporal, (2) geografica, (3) compensacao financeira, (4) legitimo interesse, (5) especificidade |
| Clausula penal | Multa contratual facilita comprovacao de dano |

### 4.2 Dedicacao e Exclusividade

Legislacao NAO presume exclusividade de socios em LTDA. Acordo de quotistas deve definir:
- Carga horaria minima
- Responsabilidades especificas
- Dedicacao exclusiva (se aplicavel)

Descumprimento serve como gatilho para Call Option.

### 4.3 Valuation Alternativo

A regra padrao do CC (art. 1.031 - balanco de determinacao em 90 dias) [1] pode descapitalizar a empresa. O STJ reconhece personalizacao livre [7].

| Metodo | Descricao |
|--------|-----------|
| Fluxo de Caixa Descontado (FCD) | Reflete valor de mercado baseado em projecoes futuras |
| Multiplos de EBITDA | Benchmark de mercado para o setor |
| Valor contabil com desagio | Para saidas por descumprimento (ex: 20-30% de desagio) |

**Prazo de pagamento:** Substituir 90 dias por parcelamento (24-36 meses) para proteger o caixa.

---

## 5. Acordo de Quotistas vs. Contrato Social

| Aspecto | Contrato Social | Acordo de Quotistas |
|---------|----------------|---------------------|
| Registro | Obrigatorio na Junta Comercial | Registro na sede da sociedade (art. 118 LSA por analogia) [2] |
| Publicidade | Publico | Pode ser confidencial |
| Oponibilidade | Erga omnes | Inter partes (com excecoes via art. 118 LSA) [2] |
| Flexibilidade | Alteracao exige quorum legal | Alteracao conforme acordo entre as partes |
| Melhor para | Clausulas estruturais (capital, objeto, administracao) | Mecanismos de governanca (vesting, call/put, shotgun, non-compete) |

Para regencia supletiva pela LSA (art. 1.053 par. unico CC) [1], o acordo de quotistas ganha enforceabilidade reforcada por analogia ao art. 118 da Lei 6.404/1976 [2].

---

## 6. Arquitetura Recomendada (Cenario 50/50)

Tres camadas:

1. **Call Options atreladas a gatilhos de dedicacao** - Metricas claras de envolvimento operacional. Descumprimento ativa direito de compra com valuation pre-definido e pagamento parcelado.
2. **Cessao automatica de PI + Nao-Competicao** - Protecao de ativos intangiveis. Non-compete de 24 meses pos-saida.
3. **Shotgun como valvula de escape** - Para impasses estrategicos irresoluveis. Separacao rapida com precificacao justa pelo mercado interno dos socios.

---

## 7. Topicos Adjacentes

| Topico | Referencia |
|--------|-----------|
| Ganho de capital na venda de quotas | IRPF sobre diferenca entre valor de alienacao e custo de aquisicao |
| Responsabilidade residual | Socio cedente responde solidariamente por obrigacoes anteriores por ate 2 anos apos averbacao da cessao (art. 1.003, par. unico, CC) [1] |
| Quotas em tesouraria | LTDA pode adquirir quotas do retirante sem reducao de capital |
| Mediacao e arbitragem | Clausula compromissoria no acordo para evitar litigios publicos |
| Direito de preferencia (ROFO/ROFR) | Art. 1.057 CC [1] - socios tem preferencia na cessao de quotas |

---

## Fontes

**Legislacao**

[1] Codigo Civil - Lei 10.406/2002 (compilado) — https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm
[2] Lei 6.404/1976 (Lei das Sociedades por Acoes) — https://www.planalto.gov.br/ccivil_03/leis/l6404consol.htm
[3] CPC - Lei 13.105/2015 — https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm

**Jurisprudencia**

[4] STJ REsp 1.286.708/PR - Exclusao por justa causa
[5] STJ REsp 2.170.665/DF - Requisitos de falta grave para exclusao
[6] STJ 2025 - Exclusao via acordo de quotistas sem previsao contratual

**Doutrina e Comentarios**

[7] Conjur 2024 (Caldeira/Romeiro) - Personalizacao de valuation em acordo de quotistas
[8] Migalhas 2025 (Ramos) - Non-compete entre socios
[9] Migalhas 2026 (Fonseca) - Exclusao extrajudicial requisitos
[10] Aurum 2024 (Botti) - Vesting reverso em LTDA

**Pesquisa Completa**

Todas as fontes primarias com analise detalhada: `../research/compra-quotas-ltda/resultado-pesquisa-compra-quotas-ltda.md`
