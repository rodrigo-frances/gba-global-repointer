# GBA Mapeador e Substituidor Global de Ponteiros

Esta é uma ferramenta de linha de comando avançada, desenvolvida em Python, para resolver o problema de atualização de ponteiros em projetos de romhacking para Game Boy Advance (GBA).

## Propósito da Ferramenta

Esta ferramenta foi desenvolvida sob medida para resolver um desafio complexo encontrado durante o projeto de tradução da ROM de **Medabots (GBA)**. No entanto, sua arquitetura foi projetada para ser flexível, podendo ser adaptada para outros projetos de romhacking de GBA que enfrentam problemas similares.

O desafio central que esta ferramenta soluciona é a atualização de ponteiros de memória que não estão localizados em uma única tabela sequencial, mas sim espalhados por diversas áreas da ROM.

O fluxo de trabalho consiste em três etapas principais:

1.  **Mapeamento:** A ferramenta analisa a ROM original e a ROM traduzida em busca de marcadores de texto customizáveis (ex: `00FB`, `02FB`). Com base na localização desses marcadores, ela cria um mapa de correspondência inteligente, associando cada "ponteiro antigo" ao seu respectivo "ponteiro novo".
2.  **Busca Global:** Com o mapa criado, o script varre **toda** a ROM traduzida em busca de cada um dos "ponteiros antigos" identificados.
3.  **Substituição Global:** Onde quer que uma ocorrência de um "ponteiro antigo" seja encontrada, ela é substituída pelo seu "ponteiro novo" correspondente, corrigindo a referência de memória de forma precisa.

Embora nascida da necessidade específica do projeto Medabots, a ferramenta é poderosa para qualquer cenário onde a atualização manual de ponteiros dispersos se torna inviável.

## Pré-requisitos

* **Python 3.6+** instalado e adicionado ao PATH do sistema.

## Guia de Uso

### **AVISO CRÍTICO: RISCO DE CORRUPÇÃO DE DADOS**

**ATENÇÃO:** Esta ferramenta realiza uma operação de "buscar e substituir" em **TODO** o arquivo da ROM. Se uma sequência de bytes que corresponde a um "ponteiro antigo" (ex: `1E 92 41 08`) aparecer em um local que **NÃO** é um ponteiro (como parte de dados gráficos ou código), ela também será substituída, o que pode corromper a ROM. **SEMPRE FAÇA BACKUP DA SUA ROM TRADUZIDA ANTES DE EXECUTAR ESTE SCRIPT**.

### **Executando a Ferramenta**

Use o terminal ou prompt de comando para executar o script.

**Sintaxe do Comando:**
```bash
python global_repointer.py [original_rom] [translated_rom] [original_scan_start] [translated_scan_start] [target_bytes_list] [OPÇÕES]
```

### **Descrição dos Argumentos**

#### Argumentos Obrigatórios:
* `original_rom`: Caminho para o arquivo da sua ROM original.
* `translated_rom`: Caminho para a sua ROM já com os scripts traduzidos. **Este é o arquivo que será modificado**.
* `original_scan_start`: Offset (hex) de início da busca na ROM original.
* `translated_scan_start`: Offset (hex) de início da busca na ROM traduzida.
* `target_bytes_list`: Lista de marcadores (hex) que referenciam os ponteiros, separados por vírgula. Ex: `"00FB,02FB,04FB"`, onde "FB" é o ponteiro.

#### Argumentos Opcionais:
* `--original_scan_end` (`-ose`): Offset (hex) de fim da busca na ROM original (altamente recomendado).
* `--translated_scan_end` (`-tse`): Offset (hex) de fim da busca na ROM traduzida (altamente recomendado).
* `--offset-in-sequence`: Deslocamento dentro do marcador encontrado. O padrão é `1` (otimizado para o caso `XXFB` -> `FB`).
* `--no-base`: Desativa a adição da base GBA (`0x08000000`) ao calcular os ponteiros.
* `--quiet` (`-q`): Reduz as informações exibidas no console.

### **Exemplo Prático**

```bash
python global_repointer.py "medabots_original.gba" "medabots_traduzido.gba" 120000 350000 "00FB,02FB,04FB" -ose 13FFFF -tse 36FFFF --offset-in-sequence 1
```
Este comando mapeia os ponteiros entre `0x120000-0x13FFFF` na ROM original e `0x350000-0x36FFFF` na ROM traduzida e, em seguida, substitui todas as ocorrências dos ponteiros antigos pelos novos em todo o arquivo `medabots_traduzido.gba`.

## Arquivo de Log

A ferramenta gera um log detalhado chamado `global_repointer_log.txt`, contendo todos os parâmetros usados, o mapa de ponteiros "DE -> PARA" e um relatório de cada substituição individual realizada, permitindo uma auditoria completa da operação.