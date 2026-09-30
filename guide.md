# Guide

## Nova máquina

- Instalar o uv e o python
- Criar o venv com o uv
  - uv venv
- source .venv/bin/activate
- uv run tko

## Para instalar os scripts

- uv run tko
- uv run feno

## Depois basta entrar no venv e rodar

- tko ou feno diretamente

## Gestao de dependencias

- uv add dependence
- pytest roda diretamente

## Publicação de tarefas TKO

O Mula consome um clone local do repositório TKO. Cada target é o caminho
relativo da pasta da atividade, por exemplo `labs/carro`. Ao publicar, ele
procura `README.html`, `tests.vpl` e `starter/<linguagem>` em `.cache`; caso
estejam ausentes, executa `tko build task <caminho> --moodle --check` a partir
da raiz do clone em cada leitura local; assim, o TKO também atualiza artefatos
existentes que estejam desatualizados. O `--check` reconstrói quando os
artefatos Moodle necessários não existem. Se faltar a pasta
`starter/<linguagem>` solicitada, o Mula executa o build sem `--check` para
garantir sua geração.

Exemplo:

```bash
mula add -c meu_curso -r /repositorios/curso -l py 3:labs/carro
mula update -c meu_curso -r /repositorios/curso --info -l py --label labs/carro
```

O título enviado ao Moodle recebe a chave `@labs/carro`, permitindo localizar a
mesma atividade em atualizações posteriores.

## Importar grupos do README

Use `mula add -c meu_curso -r /repositorios/curso --from-readme -S 1 -l py --dry-run`
para conferir a distribuição. Remova `--dry-run` para publicar.
Os grupos `## Título <!-- @marcador -->` ocupam seções consecutivas já existentes,
começando em `-S` (padrão `0`). `active=0` ignora o grupo; um grupo ativo vazio
ocupa uma seção. Links locais para tarefas em listas são incluídos tanto com
`[x]` quanto com `[ ]`. Não combine `--from-readme` com targets posicionais.
Uma thread preserva a ordem; várias threads podem alterar a ordem de criação.
A retomada usa a distribuição salva, sem reler o README.

## Retomar um add ou update

Os comandos `add` e `update` salvam seus parâmetros e o andamento em `operation.json` no cache do Mula
(obtido via `platformdirs`) e abre o arquivo no VS Code para acompanhamento.
Para retomar as tarefas pendentes da última execução, use `mula resume`, sem
argumentos. Um novo `add` ou `update` substitui o acompanhamento anterior; `--dry-run`
não grava arquivos. As opções `--create` e `--follow` foram removidas dos dois comandos.
