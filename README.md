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
mula list <nome_do_alias ou id_do_curso>

# adicionar questões usando repositório remoto fup | ed | poo
mula add -c <alias> -r <repositorio> sessao:label sessao:label ...
# exemplo
# mula add -c meu_fup -r fup 3:monica 5:opala 7:baruel

# adicionar questões usando repositório local
mula add -c <alias> -f <folder> sessao:label sessao:label ...
# exemplo
# mula add -c meu_fup -f arcade/base 3:monica 5:opala 7:baruel

# uma ação de add ou update gera automaticamente um arquivo follow.csv onde você pode
# acompanhar o andamento da publicação das questões, se tiver que retomar o processo
# você pode usar o comando mula --follow <arquivo> para continuar o processo
mula add -c <alias> -f <folder> --follow follow.csv

# também pode passar --threads para usar múltiplas threads
mula add -c <alias> -f <folder> --follow follow.csv --threads 4

# o update seguie o mesmo modelo do add, mas ao invés de adicionar questões
# você precisa informar o que quer atualizar
# --ids <ids> para atualizar questões específicas
# --sections <ids> para atualizar todas as questões de uma seção
# --all para atualizar todas as questões do curso
# --label <labels> para atualizar questões específicas

# E também pode escolher o que quer atualizar
# --info para atualizar as informações da questão
# --drafts para enviar os arquivos de rascunho
# --duedate para atualizar a data de fechamento
# --exec para habilitar as opções de execução (run, avaliate, debug)
# --visible para mostrar ou esconder a questões.
# --maxfiles para definir o número máximo de arquivos que o aluno pode enviar.

```

## Create e Follow

Nos comandos de adicionar e atualizar questões, você pode usar a opção `--follow` para criar um arquivo CSV com o andamento do processo. Você pode usar esse arquivo para continuar o processo de adição ou atualização de questões.

Esse arquivo é criado automaticamente quando você usa o comando `add` ou `update`. Caso queira apenas criar o arquivo, você pode usar o comando `--create` para criar o arquivo CSV sem adicionar ou atualizar imediatamente as questões.

Analizando o arquivo criado, você pode decidir quais ações devem ser feitas (TODO), quais quer pular(SKIP), quais deram erro(FAIL) e quais foram concluídas(DONE).

Olhando o arquivo durante a execução, é possível ver o andamento das threads em tempo real.

Também é possível definir manualmente qual a label cadas arquivo vai utilizar no update para atualizar a questão, caso a questão antiga esteja num modelo sem a label ou a label tenha sido alterada.

```bash

### Utilizando labels

O procedimento padrão para inserção é utilizando as questões do repositório remoto configurado no arquivo de configurações. Para FUP, o repositório padrão está no [github](https://github.com/qxcodefup/arcade#qxcodefup).

Para enviar as questão `A idade de Dona @monica` e `@opala bebedor` para a seção 5 do seu curso do moodle use:

``` bash
meucurso add -s 5 monica opala

# ou utilizando o modo compacto

meucurso add 5:monica 5:opala
```

Ou enviar questões para diferentes seções utilizando o modo compacto

``` bash
meucurso add 5:002 6:003 
```

O comando `add` tem várias opções de personalização.

``` bash
  -s SECTION, --section SECTION
  -d DUEDATE, --duedate DUEDATE
                        duedate 0 to disable or duedate yyyy:m:d:h:m
  -m MAXFILES, --maxfiles MAXFILES
                        max student files
  -v VISIBLE, --visible VISIBLE
                        make entry visible 1 or 0
```

### Atualizando atividades em bloco

Você pode atualizar todas as questões de uma seção com o comando `update`.

``` bash
meucurso update <quais problemas> <o que queres atualizar>
```

Quais problemas pode ser

- `--all` ou `-a` para todas as questões do curso
- `--sections 4` ou `-s 4` para todas as questões da seção 4
- `--labels monica opala` ou `-l monica opala` para as questão de label monica e opala

Opções podem ser

- `--info` para atualizar o conteúdo das questões pelo conteúdo do repositório remoto
- `--duedate 2021:5:28:11:30` para definir o horário de fechamento da atividade, ou `0` para desabilitar
- `--exec` para habilitar as opções de execução (run, avaliate, debug)
- `--visible <0 | 1>` para mostrar ou esconder a questões.
- `--maxfiles 3` para definir o número máximo de arquivos que o aluno pode enviar.

Exemplos:

``` bash
# esconder todas as questões da sessão 3
meucurso update -s 3 --visible 0

# atualizar o conteúdo de todas as questões do curso usando o repositório remoto e também mudar o máximo de arquivos para 5
meucurso update --all --info --maxfiles 5 --remote [fup | ed | poo]
#vode tambem pode utilizar um repositorio local ai seria --folder ./local do arquivo

# mudar a data de fechamento das questões da seção 4
meucurso update -s 4 --duedate 2021:5:28:11:30
```

## Removendo

``` bash
# para remover todos os vpls da seção 4
$ meucurso rm -s 4

# para remover as questões passando os IDS
$ meucurso rm -i 19234 18234 19234

# para remover TODOS os vpls do curso
$ meucurso rm --all
```
