# Audio-Aware Processing

O usuário comunica predominantemente por áudio com software de transcrição. Aplicar estas regras em TODA interação.

## Processamento de transcrição

| Regra | Detalhe |
|-------|---------|
| Autocorreções | Quando a transcrição contém padrões como "não, desculpa", "ou melhor", "na verdade" → usar apenas a versão FINAL |
| Datas e nomes | Antes de escrever em arquivos, apresentar tabela resumo de datas e nomes para confirmação |
| Batching | Em sessões longas (reviews, planejamento), acumular decisões e apresentar tabela de confirmação antes de executar — não processar item a item |
| Nomes desconhecidos | Se um nome não está no glossário e não faz sentido no contexto → flaggar imediatamente, não assumir |
| Números e datas ambíguas | "dia 21, dia 31, desculpa" → usar 31. Sempre usar a última versão quando há hesitação |
