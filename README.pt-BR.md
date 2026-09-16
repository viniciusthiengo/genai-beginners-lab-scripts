# Generative AI for Beginners — scripts prontos para usar

[English](README.md) · [Español](README.es.md) · **Português (Brasil)**

O curso "Generative AI for Beginners" descreve `generate.py`, `chat.py`, `mini_rag.py` e
`tools_demo.py` apenas como pseudocódigo. Estas são versões que funcionam, construídas a partir desses
esboços, mais um ajudante para os exercícios de avaliação. Elas só precisam de Python e de um SDK: do
jeito que estão, chamam a API da Anthropic pelo pacote oficial `anthropic`, usando o modelo que você
definir no `.env.local`. Para usar outro provedor, veja [Usar outro provedor](#usar-outro-provedor).

**Rodam de primeira, com exemplos neutros.** Para usar o seu próprio domínio (artigos de um blog, uma
loja de carros, um app para clínicas médicas, …), edite as partes marcadas com **`YOUR TASK`** (passo 6).

> O código, os comentários e os arquivos de exemplo estão em inglês. Os documentos de exemplo são de
> uma empresa inventada, por isso as perguntas de exemplo também estão em inglês.

| Arquivo | O que faz |
|---|---|
| `generate.py` | Resume um documento: valida a entrada → monta o prompt → chama o modelo com limite de saída → confere o `stop_reason` → valida a saída |
| `chat.py` | Chat de 8 turnos com uma regra de persona (≤ N caracteres); mantém o histórico inteiro, corta ou resume |
| `mini_rag.py` | Busca BM25 em um `.txt`; cita `[Source N]`; não chama o modelo quando nada é relevante |
| `tools_demo.py` | Duas ferramentas de exemplo (calculadora, conversor de moedas); valida os argumentos; o loop para após 6 rodadas |
| `build_eval_config.py` | Transforma um pequeno arquivo de casos no `eval-config.json` que o `run_eval.py` do curso lê |
| `eval-cases-day1.json`, `eval-cases-day3.json` | Arquivos de casos de exemplo para as avaliações do Dia 1 e do Dia 3 |
| `run.sh` | Carrega sua chave e seu modelo do `.env.local` só durante aquele comando e então executa o script |
| `example-document.txt`, `example-document-2.txt` | Dois documentos de uma empresa inventada, as entradas de exemplo |
| `chat-turns.txt` | As 8 mensagens de exemplo para o `chat.py` |

## O curso, dia a dia

| Dia | Exercício | O que você usa |
|---|---|---|
| 1 | Ex. 1 — auditoria de adequação | Nenhum código |
| 1 | Ex. 2 — orçamento de tokens e custo | O `estimate_tokens.py` do curso: `./run.sh estimate_tokens.py my-document.txt` (grátis); acrescente `--exact --model <id>` para a contagem real |
| 1 | Ex. 3 — escolher um modelo com a sua própria avaliação | `build_eval_config.py` + `eval-cases-day1.json`, e depois o `run_eval.py` do curso uma vez por modelo (passo 5) |
| 2 | Ex. 1 — iterar um prompt e depois atacá-lo | Um app de chat. O `generate.py --dry-run` mostra como o seu prompt final é montado |
| 2 | Ex. 2 — single shot defensivo | `generate.py` (passo 4) |
| 2 | Ex. 3 — estado do chat e corte do histórico | `chat.py` + `chat-turns.txt` (passo 4) |
| 2 | Ex. 4 — respostas fundamentadas | `mini_rag.py` + o seu `.txt` (passo 4) |
| 2 | Ex. 5 — definir e validar uma ferramenta | `tools_demo.py` (passo 4) |
| 3 | Ex. 1 — diagnosticar a abordagem | Nenhum código |
| 3 | Ex. 2 — imagem com seed fixa | Um gerador de imagens com opção de seed (não incluído) |
| 3 | Ex. 3 — registro de riscos e avaliação adversarial | `build_eval_config.py` + `eval-cases-day3.json`, que testa o próprio prompt do `generate.py`, e depois o `run_eval.py` com `--repeat 3` nos casos de recusa e injeção (passo 5) |
| 3 | Ex. 4 — os quatro estados de falha | Nenhum código. As mensagens de status do `generate.py` são um bom ponto de partida |

**Os scripts do próprio curso.** O `estimate_tokens.py` e o `run_eval.py` vêm com o curso (veja o
`SCRIPTS.md` dele) e não estão incluídos aqui. Copie os dois para esta pasta; o `run.sh` executa os
dois como os outros. Eles têm o próprio modelo padrão: passe `--model` para o `estimate_tokens.py`; o
`run_eval.py` pega o modelo do `eval-config.json`, que o `build_eval_config.py` preenche com o seu `MODEL`.

## 1. O que você precisa

- Python 3.9 ou mais recente (testado no 3.9.6). Confira com `python3 --version`.
- Uma API key **com créditos** e o id do modelo que você vai usar. Do jeito que estão, os scripts
  precisam de uma chave da Anthropic; para outro provedor, veja [Usar outro provedor](#usar-outro-provedor).
  Uma assinatura de app de chat é outro produto e não inclui créditos de API.

## 2. Instalação (macOS / Linux / WSL)

```bash
cd genai-beginners-lab-scripts
python3 -m venv .venv                          # o run.sh espera o venv exatamente aqui
.venv/bin/pip install -r requirements.txt
cp .env.example .env.local                     # depois abra o .env.local: cole sua chave e o id em MODEL
chmod +x run.sh
# depois copie para esta pasta o estimate_tokens.py e o run_eval.py do curso
```

## 3. Teste a instalação de graça (sem chave, sem custo)

Rode tudo de dentro desta pasta:

```bash
./run.sh generate.py example-document.txt --dry-run   # mostra o prompt exato
./run.sh chat.py chat-turns.txt --dry-run             # respostas simuladas, 0 chamadas cobradas
./run.sh mini_rag.py example-document.txt --show-chunks
./run.sh mini_rag.py example-document.txt "What happens to my open files when the workstation locks?" --retrieve-only
./run.sh tools_demo.py --validation-demo              # argumentos inválidos, sem chamar o modelo
./run.sh build_eval_config.py eval-cases-day3.json    # gera o eval-config.json (precisa do MODEL)
```

Se esses funcionarem, a instalação está certa.

## 4. Faça os labs do Dia 2 com o exemplo (cobrado)

O `run.sh` mostra `note: … makes billed model calls` antes de qualquer comando que custe dinheiro.

```bash
# generate.py — os três resultados + uma falha forçada
./run.sh generate.py example-document.txt                        # normal
./run.sh generate.py --text ''                                   # vazio (rejeitado, sem chamada)
python3 -c 'print("word " * 13000)' | ./run.sh generate.py -     # longo demais (rejeitado, sem chamada)
./run.sh generate.py example-document.txt --max-tokens 20        # cortado: stop_reason max_tokens

# chat.py — as três estratégias de corte do histórico
./run.sh chat.py chat-turns.txt
./run.sh chat.py chat-turns.txt --max-turns 3
./run.sh chat.py chat-turns.txt --max-turns 3 --summarize

# mini_rag.py — está no documento, falta o detalhe, sem palavras em comum, sem relação
./run.sh mini_rag.py example-document.txt \
  "What happens to my open files when the workstation locks?" \
  "Is an overtime exception paid at a higher hourly rate?" \
  "How long can my laptop stay awake before it kicks me out?" \
  "What water temperature is best for brewing green tea?"

# tools_demo.py
./run.sh tools_demo.py "What is 15% of 4,000, and what is that in euros?"
```

**Uma execução "normal" ainda pode ser rejeitada de vez em quando.** Ou o passo 5 pega um resumo
acima do limite (`The summary is … characters, over the 240-character limit`), ou o filtro de
segurança da API bloqueia o pedido por engano (`status: refusal`, com uma linha `category:`). Nos
nossos testes, o exemplo foi aceito em 19 de 20 execuções. Nos dois casos são as checagens fazendo o
trabalho delas, não bugs: rode de novo e registre isso no seu relatório do lab.

Todos os scripts aceitam `--model <id>` (padrão: o `MODEL` do `.env.local`) para testar outro modelo,
e `--effort` (padrão `low`; use `--effort none` se o seu modelo rejeitar esse parâmetro). Defina
`PRICE_INPUT_PER_MTOK` e `PRICE_OUTPUT_PER_MTOK` no `.env.local` para ver quanto custa cada execução.
Com um modelo que custa US$5 / US$25 por milhão de tokens de entrada / saída, medimos: `generate.py`
≈ US$0,03 para um documento de 12.000 caracteres (menos com o exemplo), `chat.py` US$0,01–0,04 por
execução, `mini_rag.py` ≤ US$0,02 para as quatro perguntas, `tools_demo.py` ≈ US$0,015. O passo 4
inteiro custa menos de US$0,20 a esse preço.

## 5. Faça uma avaliação (Dias 1 e 3, cobrado)

O `build_eval_config.py` é grátis: ele só gera a config. O `run_eval.py` faz as chamadas e grava cada
saída num arquivo Markdown para você pontuar à mão.

```bash
# Dia 3 — o conjunto adversarial, contra o próprio prompt do generate.py
./run.sh build_eval_config.py eval-cases-day3.json                               # → eval-config.json
./run.sh run_eval.py eval-config.json --out results.md                           # 6 chamadas
./run.sh build_eval_config.py eval-cases-day3.json --only R1,I1 --out eval-config-repeat.json
./run.sh run_eval.py eval-config-repeat.json --repeat 3 --out results-repeat.md   # recusa + injeção, 3 vezes cada

# Dia 1 — o mesmo conjunto de testes em dois modelos; só o modelo muda
./run.sh build_eval_config.py eval-cases-day1.json --model <modelo-a> --out eval-config-a.json
./run.sh build_eval_config.py eval-cases-day1.json --model <modelo-b> --out eval-config-b.json
./run.sh run_eval.py eval-config-a.json --repeat 3 --out results-a.md
./run.sh run_eval.py eval-config-b.json --repeat 3 --out results-b.md
```

- O `eval-cases-day3.json` tem `"prompt_from": "generate.py"`: a avaliação envia exatamente o que a
  sua feature envia. Mude o prompt no `generate.py` e gere a config de novo.
- O `eval-cases-day1.json` tem `system` e `prompt_template` próprios, escritos no arquivo de casos.
- Cada caso informa a entrada como `"input"` (texto direto) ou `"input_file"` (um arquivo ou uma lista,
  que são unidos). O `"replace": [["antigo", "novo"]]` opcional troca um texto que aparece exatamente
  uma vez (uma variante de viés, ou uma injeção inserida depois de uma âncora), e o `"append"`
  acrescenta texto no final.
- Com os casos de exemplo, cada rodada do `run_eval.py` custou cerca de US$0,04 a US$5 / US$25 por
  milhão de tokens.

## 6. Adapte ao seu domínio

Os labs avaliam a **sua** tarefa. Todo ponto de edição está marcado; liste todos com:

```bash
grep -n "YOUR TASK" *.py *.txt
```

| Arquivo | O que mudar | Artigos de um blog | Loja de carros | App para clínicas |
|---|---|---|---|---|
| `generate.py` | O bloco `YOUR TASK` do topo: `ROLE`, `AUDIENCE`, `DOCUMENT`, `MAX_SUMMARY_CHARS`, `BULLETS` / `MAX_BULLET_CHARS`, `IDEAL_OUTPUT`, `MIN_CHARS` / `MAX_CHARS` | um professor resumindo um artigo para alunos | um vendedor resumindo um anúncio de carro para quem vai comprar o primeiro | uma recepcionista resumindo uma política da clínica para pacientes |
| `chat.py` | O bloco `YOUR TASK`: `SYSTEM` (a persona), `RULE_MAX_CHARS`, `USER_LABEL`, `ASSISTANT_LABEL` | o bot de atendimento aos leitores do blog | o assistente de WhatsApp da loja | o assistente da recepção (nunca dá orientação médica) |
| `chat-turns.txt` | As 8 mensagens. Mantenha a estrutura explicada no topo do arquivo | um leitor perguntando sobre um post | um cliente perguntando sobre o pedido #5521 | um paciente remarcando uma consulta |
| `mini_rag.py` | Passe o seu próprio `.txt` (sem mexer no código). Se não estiver em inglês, adicione stopwords e traduza a resposta padrão nas marcas `YOUR TASK` | a política de comentários do blog | as regras da garantia | a política de cancelamento |
| `tools_demo.py` | O bloco `YOUR TASK` acima de `TOOLS`: adicione uma definição, uma função `validate_…` e uma `run_…`, e registre as duas no `DISPATCH` | `search_posts(tag)` | `check_stock(model, year)` | `find_open_slots(specialty, date)` |
| `eval-cases-day1.json` | Seu próprio `system`, `prompt_template` e 5 casos: 2 comuns, 1 de borda, 1 ambíguo, 1 que não deve ser respondido | dois artigos colados juntos como caso de borda | um anúncio sem preço, quando o prompt pede preços | um texto sem nenhuma regra da clínica |
| `eval-cases-day3.json` | Seus 6 casos: 2 normais, 1 de borda, 1 para recusar, 1 injeção, 1 viés. O prompt vem do `generate.py` | o e-mail particular de um leitor como caso para recusar | um anúncio com uma instrução escondida | a mesma política com só um nome trocado |

**Seus próprios documentos:** salve como `.txt` em UTF-8, com um assunto completo por parágrafo e uma
linha em branco entre os parágrafos. Depois use no lugar dos exemplos:

```bash
./run.sh generate.py my-document.txt --dry-run      # confira o prompt antes, de graça
./run.sh generate.py my-document.txt
./run.sh mini_rag.py my-document.txt --show-chunks  # confira os chunks, de graça
./run.sh mini_rag.py my-document.txt "uma pergunta que o documento responde" "uma que ele não responde"
```

Dica: use `--retrieve-only` para calibrar o `--min-score` no seu documento, de graça, antes de
qualquer execução cobrada.

## Usar outro provedor

Cada script fala com o modelo em um único lugar, marcado com `YOUR PROVIDER` (liste com
`grep -n "YOUR PROVIDER" *.py`). Para trocar, por exemplo para uma API compatível com a da OpenAI:

1. Troque `anthropic` no `requirements.txt` pelo SDK do seu provedor e, em cada script, a criação do
   cliente (`anthropic.Anthropic()`) e as classes de erro (`anthropic.APIError`, …).
2. Em cada chamada `YOUR PROVIDER`, envie o mesmo system prompt, as mensagens e o `max_tokens`, e
   converta a resposta para o que o script lê: o texto, o uso de tokens e o motivo de parada. Os
   scripts decidem pelo `end_turn`, `max_tokens`, `tool_use` e `refusal`; uma API compatível com a da
   OpenAI chama esses motivos de `stop`, `length`, `tool_calls` e `content_filter`.
3. No `tools_demo.py`, converta também as definições das ferramentas (`input_schema` → o campo de
   schema do seu provedor) e envie os resultados das ferramentas no formato dele.
4. Use `--effort none` se o seu provedor não tiver algo equivalente. No `chat.py`,
   `count_system_tokens()` usa um endpoint exclusivo da Anthropic: adapte ou faça ele retornar `None`.

O `run_eval.py` e o `estimate_tokens.py` do curso também chamam a API da Anthropic: adapte as chamadas
deles do mesmo jeito, ou rode os seus casos à mão no app de chat do seu provedor.

## 7. Windows (PowerShell, sem WSL)

O `run.sh` é um script bash, então defina a chave e o modelo você mesmo, só para a janela atual:

```powershell
cd genai-beginners-lab-scripts
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sua-chave"              # valem até você fechar esta janela
$env:MODEL = "id-do-seu-modelo"
.venv\Scripts\python generate.py example-document.txt
.venv\Scripts\python chat.py chat-turns.txt --max-turns 3
.venv\Scripts\python build_eval_config.py eval-cases-day3.json
.venv\Scripts\python run_eval.py eval-config.json --out results.md
Remove-Item Env:ANTHROPIC_API_KEY, Env:MODEL      # quando terminar
```

## 8. Problemas comuns

| Erro | Causa e solução |
|---|---|
| `No model set…` / `error: no model set…` | O `MODEL` no `.env.local` está vazio ou ainda diz `REPLACE_ME`. Cole o id do modelo que está na documentação do seu provedor, ou use `--model`. |
| `404 … not_found_error … model` | Esse id de modelo não existe ou a sua chave não pode usá-lo. Copie exatamente da documentação do seu provedor. |
| `401 … API key is invalid.` / `The API key was rejected` | A chave foi revogada ou está digitada errada. Crie uma nova e cole no `.env.local`. |
| `400 … anthropic-workspace-id is required` | Sua chave da Anthropic está vinculada à sua identidade. Descomente `ANTHROPIC_CUSTOM_HEADERS` no `.env.local` e coloque seu id `wrkspc_…`. |
| `credit balance is too low` | Compre créditos no console do seu provedor. Alguns exigem saldo positivo até para os endpoints gratuitos. |
| `error: paste a real key into …/.env.local first` | O `ANTHROPIC_API_KEY` no `.env.local` ainda diz `REPLACE_ME`. |
| `error: no such script: …/run_eval.py` | Copie para esta pasta o `run_eval.py` (e o `estimate_tokens.py`) do curso. |
| `error: case …: '…' must occur exactly once in the input` | O texto `old` de um par `replace` não está naquela entrada, ou aparece mais de uma vez. Copie exatamente e deixe-o único. |
| `This script needs the SDK` | Rode pelo `./run.sh`, ou instale no venv: `.venv/bin/pip install -r requirements.txt`. |
| `No such file or directory: .venv/bin/python` | Crie o venv dentro desta pasta (passo 2). |
| `That … could not be processed.` (`status: refusal`) | O filtro de segurança da API bloqueou o pedido, às vezes por engano. Rode de novo; se continuar, deixe o `IDEAL_OUTPUT` mais neutro ou teste outro documento. |
| `That looks like a title or a link…` | Seu documento é menor que o `MIN_CHARS` do `generate.py`. Cole o texto completo ou diminua o limite. |
| Toda pergunta no `mini_rag.py` volta sem resposta | O `--min-score` está alto demais para o seu documento, ou o idioma dele precisa de stopwords. Calibre com `--retrieve-only`. |

## Proteja sua chave

- **Nunca faça commit nem compartilhe o `.env.local`.** Ele já está no `.gitignore`.
- **Não coloque `export` da sua API key no `~/.zshrc` nem no `~/.bashrc`.** Outras ferramentas da sua
  máquina que leem a mesma variável (assistentes de código com IA, outros scripts) passariam a usá-la
  e a cobrá-la sem avisar. O `run.sh` evita isso: a chave só existe enquanto o comando roda.

## Licença

MIT. Veja o arquivo [LICENSE](LICENSE).
