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

```bash

pip install mula

## se aparecerem mensagens que a pasta ~/.local/bin não está no PATH
echo "export PATH=$PATH:~/.local/bin" >> ~/.bashrc
```

## Configurando acesso ao curso

### Modo rápido

```bash
mula -u <usuario> -p <senha> -i <numero_do_curso> -d <fup | ed | poo> list
```

Para obter o número do curso, basta olhar o último número na URL do seu curso do moodle.

![image](https://gist.github.com/assets/4747652/f6f81a28-d3dc-4d30-ac20-e90ff85ddcdd)

Se não passar o parâmetro -p ou --password, a senha será perguntada de forma interativa.

Agora basta dar um `mula -u <usuario> -p <senha> -i <indice_do_curso> -d <fup | ed | poo> list` para listar o conteúdo do seu curso.

## Facilitando acesso

### Alias

Você pode criar um alias para o comando, para não precisar passar os parâmetros toda vez.

```bash
#arquivo .bashrc
alias meucurso='mula -u seu_login -p sua_senha -i indice_do_curso -d fup'

#exemplo
alias fupisfun='mula -u 00427166322 -p minha_senha -i 3 -d fup'
```

Então, basta dar um `meucurso list` para listar o conteúdo do seu curso.

### Arquivo de configuração

Se preferir, pode salvar os dados em um arquivo de configuração.

```json
{
    "username": "seu_login",
    "password": "sua_senha",
    "index": "indice_do_curso",
    "database": "fup | ed | poo",
}
```

Se não adicionar o password, o script vai perguntar sua senha em cada operação. Agora basta dar um:

```bash
mula -c arquivo.json list
```

## Listando estrutura de um curso

Supondo que você criou o alias `meucurso`, vamos continuar os exemplos com ele.

Para saber se está funcionando, você pode listar as questões do seu curso.

``` bash
meucurso list
```

## Adicionando

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

- `--content` ou `-c` para atualizar o conteúdo das questões pelo conteúdo do repositório remoto
- `--duedate 2021:5:28:11:30` para definir o horário de fechamento da atividade, ou `0` para desabilitar
- `--exec` para habilitar as opções de execução (run, avaliate, debug)
- `--visible <0 | 1>` para mostrar ou esconder a questões.
- `--maxfiles 3` para definir o número máximo de arquivos que o aluno pode enviar.

Exemplos:

``` bash
# esconder todas as questões da sessão 3
meucurso update -s 3 --visible 0

# atualizar o conteúdo de todas as questões do curso usando o repositório remoto e também mudar o máximo de arquivos para 5
meucurso update --all --content --maxfiles 5

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
