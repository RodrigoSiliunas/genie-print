# 🧞 Genie Print

> **Tira print, cola o caminho. Sem dança.**

![Genie Print banner](docs/screenshots/genie-print-output.png)

## O problema

Você programa via SSH com **[Claude Code](https://claude.com/claude-code)** rodando no servidor remoto. Tira um print da tela local pra mostrar pro Claude. Mas o print fica preso no clipboard do desktop — o terminal SSH não tem como acessar.

A "solução" tradicional é uma dança de 6 passos: abrir Paint, colar, salvar, abrir outra janela do explorador de arquivos, fazer upload via SFTP/SCP/rsync, lembrar do caminho remoto, copiar manualmente, colar como `@/path/...`. Toda. Vez.

## A ponte

**Genie Print** automatiza o caminho inteiro:

```
Win+Shift+S → bitmap no clipboard
   │
   ▼  detecta automaticamente
Genie renomeia (Image #N.png) e faz SCP pro seu host SSH
   │
   ▼
@/remote/path/Image #7.png   ← já no seu clipboard
   │
   ▼  Ctrl+V no terminal onde o Claude Code está
@/remote/path/Image #7.png   ← Claude reconhece como referência
```

Resultado: **`Win+Shift+S`** → **`Ctrl+V`**. Dois atalhos do início ao fim.

## Features

- 🧙 **Wizard interativo** — configure em 4 perguntas, defaults lembrados entre execuções
- 📋 **Modo clipboard** — Win+Shift+S, Snipping Tool, qualquer ferramenta que copia bitmap
- 📁 **Modo pasta** — Lightshot, Print Screen → Paint → salvar, etc.
- 🚀 **SCP automático** — usa seu `~/.ssh/config`, zero credenciais hardcoded
- 🎯 **Renomeia bonito** — `Image #1.png`, `Image #2.png`, sem timestamps confusos
- 📎 **Output no clipboard** — `@/path/Image #N.png` pronto pra colar no Claude Code
- 🎨 **UX caprichada** — banner ASCII, cores, emojis, path destacado pra triple-click selecionar
- 🔄 **Sync em lote** — manda tudo da pasta de uma vez, com resolução de conflito
- 🪟 **Multi-plataforma** — Windows (primário), Linux, macOS
- ✅ **84 testes** cobrindo o pipeline inteiro + 3 e2e contra SSH real (opt-in)

## Quickstart

### Pré-requisitos

1. **Python 3.11+** ([instale `uv`](https://docs.astral.sh/uv/) ou Python tradicional)
2. **Um host configurado em `~/.ssh/config`** que aceite SCP. Exemplo:

   ```
   Host myserver
       HostName seu-servidor.com
       User seu-usuario
       IdentityFile ~/.ssh/sua-chave
   ```

3. **Linux/macOS apenas:** `xclip` (X11) ou `wl-clipboard` (Wayland) para as features de clipboard. Sem eles, o folder watcher continua funcionando 100%.

### Instalação

```bash
git clone https://github.com/<seu-usuario>/genie-print.git
cd genie-print
```

### Rodando (a maneira fácil)

**Windows:** duplo-clique em `genie-print.bat` (ou rode no PowerShell).

**Linux / macOS:**
```bash
chmod +x genie-print.sh
./genie-print.sh
```

O launcher cria o virtualenv automaticamente na primeira execução, instala dependências e abre o wizard. Próximas execuções pulam direto pro wizard.

## Tutorial completo

### 1. Primeira execução — o wizard

Rode `genie-print.bat` (ou `.sh`). Aparece o banner e o wizard pergunta:

```
   Host SSH (alias em ~/.ssh/config) [myserver] › 
   Pasta de destino no remoto [/path/to/remote/screenshots] › 
   Pasta local pra monitorar [Images] › 

   Como rodar?
     ● [1] Watcher completo — clipboard (Win+Shift+S) + pasta local — recomendado
       [2] Watcher só pasta — só monitora a pasta local
       [3] Sync único — envia tudo o que ja esta na pasta e sai
   Sua escolha [1] › 

   Dry-run? (nao envia de verdade) [s/N] › 

   Resumo:
     Host       myserver
     Destino    /path/to/remote/screenshots
     Pasta      Images
     Modo       Watcher completo
     Dry-run    NAO

   Confirmar e iniciar? [S/n] › 
```

Aperte Enter pra aceitar defaults ou digite valores. Da próxima vez ele lembra tudo via `.imgwatcher-wizard.json`.

### 2. Tira um print

`Win + Shift + S`, seleciona uma área, solta. O bitmap vai pro clipboard.

### 3. Magia

Em menos de 1 segundo, o terminal mostra:

```
   📸  Nova imagem clipboard-1778710121892.png
       ✏️   clipboard-1778710121892.png → Image #1.png
       ⬆️   Enviando para myserver...

   ✅  Upload concluído

   Imagem:  Image #1.png  (28.4 KB)
   Host:    myserver

   📋  Cole no Claude Code dentro do SSH:

@/path/to/remote/screenshots/Image #1.png

   ✨  Caminho (com @) copiado pro clipboard — só dar Ctrl+V no Claude Code!
```

### 4. Cola no Claude Code

No terminal SSH onde o Claude Code está rodando: **`Ctrl+V`** (ou `Cmd+V` no macOS). Cola `@/path/to/remote/screenshots/Image #1.png`. O Claude Code reconhece o `@` como referência a arquivo e carrega a imagem.

Pronto. 4 passos descritos, mas só dois atalhos: `Win+Shift+S` e `Ctrl+V`.

## Modos

Genie Print tem três modos, escolhidos no wizard ou via flags:

### 🌟 Watcher completo (recomendado)

Monitora a pasta local **E** o clipboard. Pega prints de qualquer fonte:

```bash
./genie-print.sh --host myserver --dest /remote/path --clipboard
```

- ✅ Win+Shift+S (clipboard)
- ✅ Snipping Tool (clipboard)
- ✅ Lightshot, Greenshot (salvam em arquivo)
- ✅ Print Screen → Paint → salvar (arquivo)

### 📁 Watcher só pasta

Monitora só a pasta. Útil se você não quer que o programa fique de olho no clipboard:

```bash
./genie-print.sh --host myserver --dest /remote/path
```

### 📦 Sync único

Envia tudo o que já está na pasta e sai. Bom pra processar um backlog:

```bash
./genie-print.sh --host myserver --dest /remote/path --sync
```

Se algum arquivo já existir no remoto, ele pergunta o que fazer:

```
  Image #1.png ja existe em myserver:/remote/path.
  [S]obrescrever, [I]gnorar, [T]odos, [N]enhum, [A]bortar:
```

## `AGENTS.md` no remoto

Na primeira vez que o Genie Print roda contra um destino, ele envia um `AGENTS.md` pra pasta remota explicando pra qualquer agente de IA (Claude Code, Cursor, etc.) que esteja com acesso à pasta:

- o que esse diretório é
- como as imagens aparecem ali
- a convenção de numeração (`Image #N.<ext>`)
- como o usuário referencia elas (`@/path/Image #N.png`)
- o que **não** fazer (não comitar, não inferir semântica do número)

A operação é **idempotente**: se `AGENTS.md` já existir na pasta remota, o Genie Print não toca — sua versão customizada sobrevive pra sempre. Pra forçar reupload, delete o arquivo no remoto.

Pra desligar completamente, use `--no-agents-md` ou responda "n" no wizard.

## Flags

| Flag | O que faz |
|---|---|
| `--host` | Alias SSH do `~/.ssh/config` |
| `--dest` | Caminho remoto onde colocar as imagens |
| `--watch-dir` | Pasta local pra monitorar (padrão: `Images`) |
| `--sync` | Modo sync único: envia tudo e sai |
| `--clipboard` | Também monitora o clipboard do SO |
| `--dry-run` | Mostra o que faria, sem executar SCP/SSH |
| `--no-clipboard` | Não copia o `@path` pro clipboard ao final |
| `--no-agents-md` | Não envia o `AGENTS.md` de contexto pra pasta remota |
| `--no-color` | Desliga cores ANSI |
| `--no-banner` | Não imprime o banner ASCII |
| `--verbose` | Log em nível DEBUG |
| `--help` | Mostra ajuda |

Sem nenhum argumento, o wizard interativo é disparado.

## Linux / macOS

Funciona perfeitamente. O launcher `genie-print.sh` detecta automaticamente se está em Linux e avisa se faltar suporte de clipboard:

```bash
# Debian / Ubuntu
sudo apt install xclip                 # X11
sudo apt install wl-clipboard          # Wayland

# Arch
sudo pacman -S xclip                   # X11
sudo pacman -S wl-clipboard            # Wayland

# macOS — já vem com pbcopy/pbpaste, funciona out-of-the-box
```

Sem esses helpers (servidor headless, WSL sem display, etc.), o folder watcher continua funcionando — só as funções de clipboard ficam silenciosamente inativas.

## Caminhos no MINGW64 / Git Bash

No ambiente MINGW64, caminhos Unix como `/root/path` são convertidos automaticamente pra caminhos Windows. Pra contornar, use barras duplas:

```bash
# Em vez de:
./genie-print.sh --host myserver --dest /remote/path

# Use:
./genie-print.sh --host myserver --dest //remote//path
```

No PowerShell e no Linux nativo, esse problema não existe.

## Arquitetura

```
imgwatcher/
  cli.py               # argparse + dispatch
  wizard.py            # wizard interativo, persiste em .imgwatcher-wizard.json
  config.py            # extensões, regex, timeouts
  logging_setup.py     # stderr cp1252-safe via sys.stderr.reconfigure
  display.py           # cores ANSI, banner, copy-paste-ready blocks
  processor.py         # numeração, rename, wait-for-stable, threading.Lock
  transport.py         # SCPTransport com shlex.quote no SSH remoto
  watcher.py           # watchdog event-based + polling fallback
  clipboard_watcher.py # poll do PIL.ImageGrab → salva na watch_dir
  sync.py              # bulk uploader com batched exists-check + prompt de conflito
image_watcher.py       # shim de compat: from imgwatcher.cli import main; main()
tests/                 # 84 unit + 3 e2e opt-in
```

### Design highlights

- **Numbering é regex-derivado** (`Image #(\d+)`) — escaneia a pasta, pega `max + 1`. Sem contador persistente.
- **Lock em `ImageProcessor.rename`** evita race quando dois prints chegam simultâneos.
- **`wait_for_stable`** espera duas leituras consecutivas de tamanho idênticas antes de processar — sobrevive ao padrão "snipping tool cria arquivo, escreve em pedaços, finaliza".
- **`shlex.quote` em todos os comandos SSH** — caminho com `;`, espaço, ou backtick não vira injection no remoto.
- **Clipboard watcher só larga o arquivo** — folder watcher faz o rename + upload. Zero código duplicado.
- **`pyperclip.copy()` é best-effort** — falha silenciosa em ambientes headless.

## Desenvolvimento

```bash
# Instalar deps de dev
uv pip install -r requirements-dev.txt

# Suite unitária (sem rede, ~2s)
python -m pytest

# Teste único
python -m pytest tests/test_processor.py::test_next_number_with_gap

# E2E real contra um SSH (cria /tmp/genie-e2e-<uuid>/, faz SCP, limpa)
$env:LIVE_TEST_HOST = "myserver"          # PowerShell
$env:RUN_LIVE_TESTS = "1"
python -m pytest -m live

# Bash equivalente
LIVE_TEST_HOST=myserver RUN_LIVE_TESTS=1 python -m pytest -m live
```

A suite cobre numeração, rename (incluindo concorrência), transport (com testes de quoting de injection), sync com matriz completa de decisões de conflito, watcher modes, clipboard watcher (com FakeImage), wizard (com reader injetável), e CLI dispatch.

## Contribuindo

PRs são bem-vindos. Antes de mandar, rode `python -m pytest` e veja se passa. Adicione um teste pra qualquer comportamento novo. Se mexer no display, smoke test manual ajuda muito.

## Licença

[MIT](LICENSE) © 2026 Rodrigo Siliunas
