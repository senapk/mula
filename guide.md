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
mula add -c meu_curso -f /repositorios/curso -d py 3:labs/carro
mula update -c meu_curso -f /repositorios/curso -d py --label labs/carro
```

O título enviado ao Moodle recebe a chave `@labs/carro`, permitindo localizar a
mesma atividade em atualizações posteriores.
