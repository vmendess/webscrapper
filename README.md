# WebScrapper - Site Cloner com Playwright

Um script Python que faz o **clone completo de um website** em uma pasta local, incluindo todos os assets (imagens, CSS, vídeos, etc).

---

##  Pré-requisitos

- Python 3.7+
- pip (gerenciador de pacotes Python)

---

##  Como Executar

### 1️ Criar um Ambiente Virtual

```bash
python -m venv venv
```

### 2️ Ativar o Ambiente Virtual

**Windows:**
```bash
venv\Scripts\Activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3️ Instalar as Dependências

```bash
pip install -r requirements.txt
```

### 4️ Instalar os Navegadores do Playwright

```bash
playwright install
```

>  **Importante:** O `pip install playwright` instala apenas o código Python. O comando `playwright install` baixa os executáveis dos navegadores (Chromium, Firefox, WebKit).

### 5️ Executar o Script

**Opção A - Passar a URL como argumento:**
```bash
python main.py https://app.santthera.health/mpz/v5
```

**Opção B - O script vai solicitar a URL:**
```bash
python main.py
```

Insira a URL quando solicitado.

---

##  Saída

Após executar, será criada uma pasta com o nome `cloned_{dominio}` contendo:

```
cloned_app.santthera.health/
├── index.html
├── assets/
│   ├── img_0.png
│   ├── img_1.jpg
│   └── ...
└── css/
    └── styles.css
```

---

##  Lógica do `main.py` - Como Funciona com Playwright

O script utiliza **Playwright** (uma biblioteca de automação de navegador) para converter um website em arquivos estáticos. Aqui está o fluxo:

###  **Inicializar Playwright e Carregar a Página**
```python
browser = await p.chromium.launch(headless=True)
page = await context.new_page()
await page.goto(url, wait_until="networkidle")
```
- Abre um navegador **Chromium** (sem interface gráfica - headless)
- Acessa a URL fornecida
- Aguarda a página carregar completamente

###  **Executar Scroll para Carregar Conteúdo Lazy-Loaded**
```javascript
window.scrollBy(0, 300);  // Rola a página em 300px
```
- Muitos sites carregam imagens/conteúdo **sob demanda** (lazy loading)
- O script rola a página inteira para garantir que tudo seja carregado
- Aguarda 2 segundos para a página processar

###  **Coletar Todos os Assets (JavaScript)**

O script executa um **código JavaScript no navegador** para encontrar e mapear todos os recursos da página:

####  **Imagens**
- Encontra `<img>` tags e seus atributos `src` e `srcset`
- Processa imagens em `<picture>` tags

####  **Estilos CSS**
- Extrai CSS inline e de folhas de estilo
- Encontra URLs de `background-image` nos estilos

####  **Vídeos e Áudio**
- Coleta `<video>`, `<audio>` tags e fontes associadas

####  **Favicon**
- Captura o ícone do site

####  **Mapeamento de URLs**
```javascript
assetMap.set(resolvedUrl, {
    localPath: 'assets/img_0.png',
    originals: new Set()
});
```
- Cada asset é mapeado de sua **URL original** para um **caminho local**
- Exemplo: `https://example.com/img/foto.jpg` → `assets/img_0.png`

###  **Reescrever HTML e CSS**
```javascript
html = html.split(resolvedUrl).join(entry.localPath);
```
- Substitui todas as URLs absolutas pelas **URLs relativas locais**
- O HTML agora aponta para `assets/img_0.png` ao invés de URLs da internet

###  **Baixar Todos os Assets**
```python
resp = await context.request.get(asset["url"])
body = await resp.body()
file_path.write_bytes(body)
```
- Faz **requisições HTTP** para cada arquivo encontrado
- Salva os arquivos na pasta `assets/`
- Mostra progresso: `[1/150] OK assets/img_0.png (147.4 KB)`

###  **Salvar Arquivos Finais**
- **`index.html`** - Página HTML modificada com URLs relativas
- **`css/styles.css`** - Todos os estilos CSS consolidados
- **`assets/`** - Todas as imagens, vídeos, fontes, etc.

---

##  Fluxograma do Script

```
┌─────────────────────────────────────┐
│ 1. Criar pasta de saída             │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ 2. Abrir Playwright + carregar URL  │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ 3. Rolar a página (lazy loading)    │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ 4. Executar JavaScript para coletar │
│    imagens, CSS, vídeos, etc.       │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ 5. Reescrever URLs no HTML/CSS      │
│    (URLs absolutas → relativas)     │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ 6. Baixar todos os assets           │
│    (mostrar progresso)              │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│ 7. Salvar arquivos finais           │
│    (HTML, CSS, assets)              │
└─────────────────────────────────────┘
```

---

##  Estrutura do Código

| Componente | Responsabilidade |
|-----------|-----------------|
| **SCROLL_JS** | JavaScript que rola a página para carregar conteúdo lazy-loaded |
| **COLLECTOR_JS** | JavaScript que encontra e mapeia todos os assets da página |
| **main()** | Orquestra todo o processo de form planejado |
| **Playwright** | Chrome/Chromium automatizado para acessar a página |

---

##  Troubleshooting

###  "Playwright not installed"
```bash
pip install playwright
playwright install
```

###  "Executable doesn't exist at C:\...\chrome-headless-shell.exe"
```bash
playwright install chromium
```

###  "Timeout waiting for page to load"
- A página pode estar lenta
- Aumentar o `timeout` no código:
```python
await page.goto(url, wait_until="networkidle", timeout=120000)  # 120 segundos
```

###  "Failed to download asset"
- O servidor pode bloquear muitas requisições simultâneas
- O asset pode exigir cookies/sessão específica
- O asset pode ter sido removido (404)

---

##  Requirements.txt

```txt
playwright==1.58.0
pyee==13.0.1
greenlet==3.3.2
typing-extensions==4.15.0
```
