# mula - Moodle Update for Lazy Admins

<!-- toc -->
- [Instalação](#instalação)
- [Configurando acesso ao curso](#configurando-acesso-ao-curso)
  - [Modo rápido](#modo-rápido)
- [Facilitando acesso](#facilitando-acesso)
  - [Alias](#alias)
  - [Arquivo de configuração](#arquivo-de-configuração)
- [Listando estrutura de um curso](#listando-estrutura-de-um-curso)
- [Adicionando](#adicionando)
  - [Utilizando labels](#utilizando-labels)
  - [Atualizando atividades em bloco](#atualizando-atividades-em-bloco)
- [Integração com repositórios TKO](#integração-com-repositórios-tko)
- [Removendo](#removendo)
<!-- toc -->

## Vídeo de Apresentação (4 min)

[![image](https://gist.github.com/assets/4747652/d3fc3448-8766-41e9-8416-a3fae6044e3b)](https://youtu.be/BB8-IkU2X6U)

## Instalação

### Instalação no Windows

Abra o power shell como administrador e execute o comando:

```bash
pip install mula
```

### Instalação no Linux

```bash

pip install mula

## se aparecerem mensagens que a pasta ~/.local/bin não está no PATH
echo "export PATH=$PATH:~/.local/bin" >> ~/.bashrc
```

## Configurando acesso ao curso

### Modo rápido

```bash
# fazer autenticação e salvar credenciais
mula auth

# listar seus cursos
mula courses

# criar um alias para um curso
mula alias <nome_do_alias> <id_do_curso>

# listar um curso
mula list -c <alias ou id_do_curso>

# adicionar questões usando um repositório local
mula add -c <alias> -r <repo> sessao:label sessao:label ...
# exemplo
# mula add -c meu_curso -r ./repositorio 3:monica 5:opala 7:baruel

# add e update salvam parâmetros e andamento no cache do Mula; para retomar:
mula resume

# também pode passar --threads na execução inicial
mula add -c <alias> -r <repo> --threads 4 3:labs/carro

# o update seguie o mesmo modelo do add, mas ao invés de adicionar questões
# você precisa informar o que quer atualizar
# --id <ids> para atualizar questões específicas
# --section <índices> para atualizar seções
# --all para atualizar todas as questões do curso
# --label <labels> para atualizar questões específicas
# --dry-run mostra as atividades selecionadas, sem alterá-las
# exemplo: mula update -c meu_curso --all --dry-run

# E também pode escolher o que quer atualizar
# --info para atualizar as informações da questão
# --lang para enviar os arquivos de rascunho
# --duedate para atualizar a data de fechamento
# --exec para habilitar as opções de execução (run, avaliate, debug)
# --visible para mostrar ou esconder a questões.
# --maxfiles para definir o número máximo de arquivos que o aluno pode enviar.

```

Para conferir a sintaxe completa de qualquer comando, use `mula <comando> --help`.
Seleções de `update`, `rm` e `down` usam exatamente uma opção entre `--all`,
`--id`, `--label` e `--section`. Para retomar o último `add` ou `update`, use `mula resume`
sem argumentos. Índices de seção começam em zero, como exibidos
por `mula list -c <curso>`.

## Integração com repositórios TKO

Para publicar tarefas TKO, use um clone local do repositório de conteúdo. O
caminho relativo da pasta da tarefa é a chave usada pelo Mula e também é
gravado no título da atividade Moodle:

```text
@labs/carro Carro
```

O Mula procura os artefatos Moodle dentro da pasta da tarefa:

```text
<repositorio>/<task-path>/.cache/README.html
<repositorio>/<task-path>/.cache/tests.vpl
<repositorio>/<task-path>/.cache/starter/<linguagem>/
```

Se eles não existirem, o Mula executa automaticamente:

```bash
tko task build <task-path> --moodle <url-do-repositorio>
```

A URL é derivada do `origin` GitHub do clone e a linguagem enviada como
rascunho é escolhida com `--lang`:

```bash
mula add -c meu_curso -r /repositorios/curso -l py 3:labs/carro
mula update -c meu_curso -r /repositorios/curso --info -l py --label labs/carro
```

O fluxo atual não usa mais `.cache/mapi.json`. O `--repo` deve apontar para a
raiz do clone; targets absolutos ou caminhos contendo `..` não são aceitos.

## Acompanhamento e retomada

Os comandos `add` e `update` salvam automaticamente o contexto e o andamento
da última execução em `operation.json`, dentro de `platformdirs.user_cache_path("mula")` — normalmente
`~/.cache/mula/operation.json` no Linux. O JSON é aberto no VS Code para acompanhar
o progresso, e a execução começa imediatamente. Se o VS Code não puder ser
aberto, o Mula avisa e continua.

Para retomar, basta executar:

```bash
mula resume
```

Esse comando recupera o Moodle, o ID do curso, o caminho absoluto do repositório,
as alterações, a linguagem, as threads e o timeout salvos. As credenciais são
obtidas da configuração atual e não são armazenadas no JSON. Não são aceitos
argumentos ou substituições de parâmetros, inclusive `--timeout` global.

Tarefas `TODO` e `FAIL` são retomadas; tarefas `DONE` e `SKIP` são preservadas.
Se não houver pendências, o comando informa isso e encerra. Um novo `add` ou `update`
com atividades selecionadas substitui o acompanhamento anterior, mesmo que seja
de outro comando ou curso. `--dry-run`, seleção vazia e erros de parâmetros não substituem
o arquivo. Use um processo de `add`, `update` ou `resume` por vez. O arquivo aberto
serve para acompanhar o progresso; não o edite enquanto a execução estiver ativa.

`add` e `update` não aceitam mais `--create` nem `--follow`, e não importam
arquivos antigos `follow.csv`. Se ainda existir apenas o JSON anterior
`update.json`, `mula resume` consegue lê-lo e passa a gravar em `operation.json`.

### Adicionando atividades

O `add` recebe o curso com `-c`, o caminho do repositório local com `-r` e os targets como
`LABEL` ou `SEÇÃO:LABEL`. Por exemplo:

```bash
mula add -c meu_curso -r ./repositorio 5:labs/carro
```

O curso (`--course` / `-c`) e o repositório (`--repo` / `-r`) são obrigatórios.
Escolha targets ou `--from-readme`, que são mutuamente exclusivos.
`--section N` / `-S N` define a seção padrão (inicialmente `0`);
um prefixo `N:` no target substitui esse padrão. Targets repetidos na mesma
seção são tratados uma única vez. Se a label já existir nessa seção, a atividade
é atualizada.

O título e a descrição vêm do repositório. Por padrão, o prazo fica desabilitado
(`--duedate 0`), o máximo de arquivos é `5`, e Run, Evaluate e Debug são habilitados.
Use `--no-exec` para manter as opções de execução sem alterações.
`--lang LANG` / `-l LANG` envia os arquivos iniciais da linguagem.
`--visible 0` esconde a atividade; `--visible 1` mostra. Sem essa opção, o Mula
mantém o valor definido pelo Moodle.

```bash
# publicar duas tarefas usando a mesma seção
mula add -c meu_curso -r ./repositorio -S 3 -l py labs/carro labs/bicicleta

# conferir os targets sem publicar nem substituir o acompanhamento
mula add -c meu_curso -r ./repositorio --dry-run 3:labs/carro 5:labs/bicicleta

# retomar as tarefas pendentes da última execução de add ou update
mula resume
```

### Importando a organização de um repositório

`--from-readme` lê os grupos `## Título <!-- @marcador -->` do `README.md`
na raiz do repositório. Cada grupo ativo ocupa uma seção consecutiva, começando
em `--section` (padrão `0`). Grupos com `active=0` são ignorados; grupos ativos
vazios também ocupam uma seção. As seções precisam existir no Moodle: o comando
não cria nem renomeia seções.

Links locais em listas, como `labs/carro/README.md`, viram a label `labs/carro`.
Tarefas marcadas com `[x]` e `[ ]` são incluídas. Repetições dentro do mesmo grupo
são eliminadas, e todos os arquivos e destinos são validados antes da publicação.

```bash
# conferir grupos, seções reais do curso, labels e totais
mula add -c meu_curso -r ~/dropbox/gits/fup/arcade --from-readme -S 1 -l py --dry-run

# publicar a distribuição conferida
mula add -c meu_curso -r ~/dropbox/gits/fup/arcade --from-readme -S 1 -l py
```

O Arcade possui 10 grupos ativos com 222 tarefas nessa organização. Use `-s 1`
para reservar a seção geral (`0`). O padrão de uma thread preserva a ordem de
publicação; com várias threads essa ordem não é garantida. `mula resume` usa as
labels e seções salvas em `operation.json`, sem reler o índice do repositório.

### Atualizando atividades em bloco

O comando segue o formato:

```bash
mula update -c CURSO SELEÇÃO ALTERAÇÕES [OPÇÕES]
```

Escolha exatamente uma seleção:

| Opção | Atividades selecionadas |
| --- | --- |
| `--all` / `-A` | Todos os VPLs do curso |
| `--id ID` / `-I ID` | IDs específicos; repita a opção para vários IDs |
| `--label LABEL` / `-L LABEL` | Labels exatas; repita a opção para várias labels |
| `--section ÍNDICE` / `-S ÍNDICE` | VPLs da seção; índices começam em zero |

A forma recomendada para vários valores é repetir a opção, por exemplo
`--id 123 --id 456` ou `--section 0 --section 2`. A sintaxe anterior
`--id 123 456` e `--section 0 2` também é aceita.

Informe uma ou mais alterações (elas podem ser combinadas):

| Opção | Efeito / dependência |
| --- | --- |
| `--info` | Atualiza título e descrição; exige `--repo DIR` |
| `--lang LANG` / `-l LANG` | Envia os arquivos iniciais da linguagem, como `py`; exige `--info` |
| `--duedate YYYY:MM:DD:HH:MM` | Define uma data válida de fechamento; `0` desabilita o prazo |
| `--visible 0\|1` | Esconde (`0`) ou mostra (`1`) as atividades |
| `--maxfiles N` | Define o máximo de arquivos, respeitando a quantidade de arquivos preservados |
| `--exec` | Habilita Run, Evaluate e Debug |

O repositório é informado com `--repo DIR` / `-r DIR`. Se a pasta correspondente
à label não existir, o Mula também tenta `labs/key`.

Use `--dry-run` para conferir as atividades pendentes sem alterar o Moodle nem
gravar arquivos. Nesse modo, alterações e `--repo` são opcionais.
Uma execução nova grava o andamento e os parâmetros em `operation.json` no cache
do Mula. Use `mula resume` para retomar as pendências com os mesmos parâmetros.
`--threads N` / `-t N` define os trabalhadores simultâneos (padrão: `1`).
O timeout é uma opção global e aparece antes do subcomando:
`mula --timeout 30 update -c meu_curso --all --visible 0 --threads 4`.
As opções globais `-t` e `--timeout` definem o timeout; depois de `update`,
`-t` significa `--threads`.

```bash
# conferir todas as atividades selecionadas
mula update -c meu_curso --all --dry-run

# esconder atividades de duas seções
mula update -c meu_curso --section 0 --section 3 --visible 0

# atualizar conteúdo e arquivos iniciais, mudando o limite de arquivos
mula update -c meu_curso --all --info -r ./repositorio --lang py --maxfiles 5

# mudar o prazo de atividades específicas
mula update -c meu_curso --id 123 --id 456 --duedate 2026:10:15:23:59

# retomar as atividades pendentes da última operação, sem repetir os parâmetros
mula resume
```

## Removendo

``` bash
# para remover todos os VPLs da seção 4
mula rm -c meu_curso --section 4

# para remover as questões passando os IDS
mula rm -c meu_curso --id 19234 18234

# para remover TODOS os vpls do curso
mula rm -c meu_curso --all
```

## Gerenciando seções do curso

O subcomando `section` permite adicionar uma seção ao final do curso, renomear
uma seção existente ou removê-la. Os índices são os mesmos exibidos por
`mula list` e começam em zero.

```bash
mula section add -c meu_curso --name "Labs"
mula section rename -c meu_curso --index 2 --name "Laboratórios"
mula section remove -c meu_curso --index 2
```

A remoção pede confirmação e apaga também as atividades dentro da seção. Use
`--yes` para confirmar sem prompt.

No `mula add`, use `--drop` para ignorar chaves que já existem na seção de destino,
em vez de atualizá-las. As tarefas ignoradas aparecem como `SKIP` no acompanhamento;
a opção também é preservada por `mula resume`. Use `--dry-run` para conferir.

```sh
mula add -c meu_curso -r ./repositorio -S 1 --drop labs/carro labs/bicicleta
```
