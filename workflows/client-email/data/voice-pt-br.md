# Realização Tonal pt-BR — Email a Clientes

Carregar quando o email for em português (Brasil). Os princípios universais ficam em `voice-principles.md`; aqui ficam apenas as escolhas de registro e exemplos antes/depois que não sobrevivem à tradução.

## Cumprimentos e Fechamentos

- **Abertura:** nomes diretos + saudação informal-profissional. "João e Carlos, boa tarde." Não "Prezados senhores."
- **Fechamento:** "Abraço," seguido de linha em branco e nome próprio. "Atenciosamente" é formal demais para a maioria dos contextos B2B brasileiros tech/inovação.

## Pessoa Verbal

- **Default:** "vocês" (segunda pessoa do plural, registro próximo). NÃO usar "o senhor / a senhora" exceto em contexto de hierarquia muito acentuada (juiz, autoridade pública).
- **"a gente" e "nós" são intercambiáveis** dentro do mesmo email — escolher pela cadência da frase. "A gente vai precisar..." e "Nós vamos precisar..." podem coexistir.
- **Subjuntivo para propostas e hedges.** "Poderíamos ajudar", "ficaria à disposição", "podem haver". Indica abertura à negociação sem perder propósito.

## Vocabulário e Convenções

- **Termos em inglês integrados ao biz brasileiro mantêm-se.** "POC" (não "prova de conceito" — embora aceitável), "fallback", "ponto focal", "(cced)", "lock-in", "follow-up", "kick-off", "matching", "dashboard". Traduzir essas palavras estrangeiriza o tom em vez de aproximá-lo.
- **POC é feminino:** "a POC", "a POC operacional". Nunca "o POC".
- **Siglas com tradução pt-BR completa, não em inglês.** "Contas a receber" (não "AR"), "contas a pagar" (não "AP"), "fluxo de caixa" (não "cashflow"). Exceção: termos consagrados em inglês sem equivalente natural ("API", "tool-call").
- **Datas em formato brasileiro.** "15/5", "30/6", "2026-04-29". Não "May 15", não "5/15".
- **Verbos do cotidiano sobre corporatês.** "Deixo abaixo" beats "submeto à apreciação". "Avançar" beats "endereçar". "Conversar" beats "manter diálogo". "Topa marcar?" beats "Seria possível agendarmos?".

## Conectores e Pontuação

- **Em-dash existe, mas raramente.** Parênteses são o default para asides, atribuições e meta-explicações curtas. Em-dash apenas quando há ruptura real de tom, lista curta dentro de uma frase, ou ênfase forte.
- **Dois-pontos para introduzir listas e parâmetros.** "Parâmetros:", "Segurança:", "Fluxo proposto:". Cria expectativa imediata da estrutura que vem.
- **Travessão (—) e parênteses não competem.** Cada um tem função. Parênteses para informação lateral neutra; travessão para inflexão de pensamento.

## Calibração de Relação

O registro pt-BR varia com a temperatura da relação. Imperativo direto e fórmulas curtas pressupõem confiança aquecida — usados cedo demais, soam invasivos.

| Estágio | Default | Exemplos permitidos |
|---|---|---|
| Primeiro email direto a essa pessoa | Subjuntivo permissivo / condicional | "podem nos enviar", "se puderem sugerir uma janela", "valeria receber" |
| Segundo email em diante (após resposta calorosa) | Subjuntivo + imperativo direto coexistem | "manda quando puder", "sugere janela", "topa avançar?" |
| Relação consolidada (multi-thread, intimidade explícita) | Imperativo direto é o default | "Sugiram qualquer janela — nos adaptamos", "Topa marcar?" |

Pessoas distintas dentro da mesma empresa têm relações distintas. Quatro reuniões com o ponto focal estratégico NÃO autorizam imperativo direto com o ponto focal operacional que entra na thread como destinatário pela primeira vez. Calibrar por pessoa, nunca por empresa.

**Espelhamento permitido.** Se o destinatário usa imperativo direto com você primeiro, você pode espelhar — a relação aceitou esse registro do lado dele.

### Exemplo de mau calibração

Contexto: primeiro email direto a um destinatário operacional, após ele responder a um email anterior endereçado ao ponto focal estratégico (com quem havia relação consolidada).

**Antes (imperativo direto, mal calibrado):**
> Material: quando puder, manda as empresas modelo. (...) Sugere janela nas próximas duas semanas — nos adaptamos.

**Depois (subjuntivo permissivo, calibrado):**
> Material: quando puderem, podem nos enviar as empresas modelo. (...) Se puderem sugerir uma janela nas próximas duas semanas, a gente se adapta.

Mesma intenção, calibrada à temperatura real da relação com aquela pessoa.

## Padrões de Compromisso pt-BR

- **"Sem custo" / "sem lock-in"** — frases curtas e diretas. Evitar "isenção de cobrança" ou "ausência de cláusula de exclusividade".
- **"Topa marcar?" / "Topa avançar?"** — convite informal-mas-profissional, comum em B2B brasileiro tech. Use quando há um ponto focal claro a quem dirigir.
- **"Nos adaptamos a vocês"** beats "Nos colocamos à disposição da agenda de vocês". Mais curto, mais propositivo, menos servil.
- **"Sugiram qualquer janela"** (imperativo direto) beats "Se puderem sugerir uma janela" (subjuntivo cerimonioso) — quando a relação já permite.

## Exemplos Antes/Depois

Os exemplos abaixo são de uma iteração real, anonimizada. Ilustram princípios — não copiar literalmente.

### 1 — Abertura (auto-flagelação cortada)

**Antes:**
> Boa tarde. Saímos da reunião de 16/04 com uma constatação: passamos boa parte do tempo apresentando o que [a empresa] pode fazer de modo geral, e tempo de menos no que vocês de fato precisam resolver. Esse email é uma correção de rota.

**Depois:**
> João e Carlos, boa tarde.
>
> Na reunião de 16/04 entendemos que a dor mais latente onde poderíamos ajudar é a conciliação de contas a receber via Pix/TED.

**Cortes:** auto-flagelação ("passamos tempo de menos no que vocês precisam"), meta-narrativa ("correção de rota"), restateamento implícito do que o cliente disse. **Adições:** nomes diretos, agência ("entendemos"), foco direto na dor.

### 2 — Item de Fluxo (sub-bullets dobrados em prosa)

**Antes:**
> 4. A analista revisa no dashboard, aprova ou ajusta.
>   - No início imaginamos que vocês vão querer revisar a maioria/totalidade, até ganhar confiança no nosso sistema
>   - Tendo confiança, o analista pode revisar somente as com indicação de menor confiança pelo sistema

**Depois:**
> 4. O analista revisa conciliações no dashboard e aprova ou ajusta. No início imaginamos revisão total até vocês ganharem confiança no sistema; depois, só as de menor confiança indicada.

**Princípio:** sub-bullet só sobrevive quando carrega informação substantiva (decisão aberta, opção real). Quando o sub-bullet só esclarece, vira prosa em uma frase.

### 3 — Parâmetros (tabela markdown → bullets)

**Antes:**
> | Item | Compromisso |
> |------|-------------|
> | **Duração** | 6 semanas, com início previsto na próxima semana |
> | **Custo** | Zero. Integralmente custeado por nós |

**Depois:**
> Parâmetros da POC:
> - Duração: cerca de 6 semanas, com início até 15/5 e POC operacional até 30/6.
> - Custo para o cliente: zero. POC integralmente custeada por nós.

**Cortes:** tabela markdown (quebra em Gmail) → bullets simples. Negrito markdown → label-com-dois-pontos. Datas vagas ("próxima semana") → datas concretas.

### 4 — Próximo Passo (prescrição da reunião + cerimônia cortadas)

**Antes:**
> Para garantir que a POC fique operacional até o final de maio, precisamos avançar com uma reunião de fechamento de escopo na próxima semana. Saímos dessa reunião com o escopo da POC fechado em uma página: dados, métrica, prazo, papéis. Algumas decisões precisam ser co-construídas com vocês, não impostas por nós. Sugiram qualquer janela nas próximas duas semanas — nos encaixamos.

**Depois:**
> Para garantir que a POC fique operacional até 30/6, precisamos avançar na definição de escopo nas próximas duas a três semanas — algumas decisões estratégicas (regras implícitas dos analistas, identificação do pagador, forma de devolução) precisam ser co-construídas antes do início. Sugiram qualquer janela nas próximas duas semanas e nos adaptamos a vocês.

**Cortes:** prescrição do resultado da reunião ("saímos com X em uma página") soa salesy. Frase "não impostas por nós" é preachy. **Trocas:** "nos encaixamos" → "nos adaptamos a vocês" (mais propositivo, menos servil); em-dash compactando cláusula subordinada em vez de dois períodos separados.

### 5 — Bloco Técnico (antecipar a pergunta óbvia)

**Antes:**
> Os dados são replicados para o nosso ambiente (bucket por cliente, hashed, isolado, não exposto à internet).

**Depois:**
> Os dados ficam em armazenamento privado (bucket por cliente, hashed, isolado, sem endpoint público), acessíveis apenas via dashboard autenticado.

**Princípio:** "não exposto à internet" gera "como acessam então?" na cabeça do leitor técnico. "Sem endpoint público + acessíveis via dashboard autenticado" responde à pergunta antes que apareça. Imprecisão técnica convida escrutínio; precisão entrega confiança.

### 6 — Oferta sem Auto-Justificação

**Antes:**
> Carlos, isso é o resumo. O Felipe (no CC) está à disposição para uma call dedicada de segurança — esse formato vai render muito mais que qualquer documento que a gente escreva sozinho. Topa marcar?

**Depois:**
> O Felipe (cced) está à disposição para uma call dedicada de segurança.

**Cortes:** justificar por que a call é melhor que doc ("vai render mais que qualquer doc que a gente escreva sozinho") chama atenção para a ausência do doc, como se fosse defesa preventiva. A oferta da call se sustenta pelo que é. **Nota:** "Topa marcar?" foi cortado aqui porque o destinatário direto (Carlos) saiu do CC; quando há ponto focal claro, "Topa marcar?" funciona bem como CTA.

## Técnica de Cortes Iterativos — Lente pt-BR

Mesma técnica do workflow universal, com foco em cortes específicos do registro pt-BR:

| Pass | Foco pt-BR específico |
|------|----------------------|
| 1 — Estrutura | Cortar seções "O que entendemos / O que ouvimos de vocês". Sub-bullets viram prosa em uma frase. Tabelas markdown viram bullets. |
| 2 — Redundância | Comentários "tendo escutado de vocês" — o artefato (fallback, exit clause, escopo focado) é a prova da escuta. Headers `## Comentários sobre...` viram labels diretos ou somem. |
| 3 — Cerimônia | "Esse formato vai render mais que..." — corte. "Não imposto por nós" — corte. "Se puderem" → "Sugiram". CTAs sem alvo claro viram afirmações factuais. "Nos encaixamos" → "nos adaptamos a vocês". |

Resultado típico: redução de 35-45% em palavras sem perda de ação ou tom.
