# Typst Renderer

API HTTP para gerar PDFs com Typst a partir de payloads JSON.

O projeto expoe uma API em FastAPI que recebe um documento estruturado, escolhe um template em `templates/`, executa `typst compile` localmente e devolve uma URL publica para o PDF gerado. Tambem suporta upload de capa e uso de capa por base64 ou URL externa.

## Visao geral

Este repositorio foi desenhado para um fluxo simples de renderizacao:

1. O cliente envia um payload JSON com `template_id`, `document` e opcoes.
2. A API cria um job unico em `jobs/<uuid>/`.
3. Os arquivos do template escolhido sao copiados para o job.
4. O `input.json` do job e gerado com base no payload recebido.
5. O binario `typst` e executado para compilar `main.typ`.
6. O PDF final e copiado para `storage/<uuid>.pdf`.
7. A API retorna a URL publica em `/files/<uuid>.pdf`.

## Funcionalidades

- Renderizacao sincrona de PDFs usando Typst CLI.
- Catalogo de templates via `GET /templates`.
- Upload de imagem de capa via `POST /upload-cover`.
- Suporte a `cover_image_base64` e `cover_image_url` dentro do payload.
- Exposicao de arquivos gerados em `/files`.
- Exposicao de imagens de capa em `/assets`.
- Validacao leve do documento com retorno de `warnings`.
- Documentacao automatica do FastAPI em `/docs` e `/redoc`.

## Templates disponiveis

Atualmente o projeto possui estes templates:

- `livro_tecnico_v1`
- `livro_tecnico_v2`

O endpoint `GET /templates` retorna a lista de templates encontrados no diretorio `templates/` e define o template padrao com esta prioridade:

1. `livro_tecnico_v2`
2. `livro_tecnico_v1`
3. Primeiro diretorio encontrado, em ordem alfabetica

## Estrutura do projeto

```text
app/
  main.py
  models.py
  renderer.py
assets/
jobs/
storage/
templates/
  livro_tecnico_v1/
    main.typ
    theme.typ
  livro_tecnico_v2/
    main.typ
    theme.typ
payload.json
payload_wrapped.json
requirements.txt
```

- `app/main.py`: define a API, endpoints e arquivos estaticos.
- `app/models.py`: schemas Pydantic dos requests e responses.
- `app/renderer.py`: pipeline de validacao, preparo do job e chamada ao Typst.
- `templates/`: templates Typst versionados.
- `jobs/`: artefatos temporarios de cada renderizacao.
- `storage/`: PDFs finais servidos pela API.
- `assets/`: imagens de capa enviadas via upload.

## Pre-requisitos

- Python 3.10+ recomendado.
- `typst` instalado e acessivel no `PATH`.
- Permissao de escrita para `jobs/`, `storage/` e `assets/`.

Observacao: o projeto nao faz instalacao automatica do Typst. O binario precisa existir no ambiente em que a API roda.

## Instalacao

No PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Dependencias Python do projeto:

- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `python-multipart`

## Executando localmente

Exemplo com PowerShell:

```powershell
$env:PUBLIC_BASE_URL = "http://127.0.0.1:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Se `PUBLIC_BASE_URL` nao for definido, o projeto usa `http://127.0.0.1:8000` como valor padrao para montar as URLs retornadas.

Rotas uteis apos subir o servico:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/templates`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

Importante: embora exista um arquivo `.env` no repositorio, a aplicacao nao carrega variaveis automaticamente desse arquivo. Se quiser usar `PUBLIC_BASE_URL`, exporte a variavel no shell antes de iniciar o `uvicorn`.

## Endpoints

| Metodo | Rota | Descricao |
| --- | --- | --- |
| `GET` | `/health` | Verifica se a API esta ativa. |
| `GET` | `/templates` | Lista os templates disponiveis e informa o padrao. |
| `POST` | `/generate-cover-image` | Gera uma arte editorial de capa em PNG e retorna uma URL publica. |
| `POST` | `/upload-cover` | Faz upload de uma capa (`png`, `jpg`, `jpeg`, `webp`). |
| `POST` | `/upload-cover-openai` | Recebe `openaiFileIdRefs` do ChatGPT Actions e salva a capa. |
| `POST` | `/render-pdf` | Gera um PDF a partir de um payload direto. |
| `POST` | `/render-pdf-wrapped` | Gera um PDF a partir de um payload aninhado em `payload`. |
| `GET` | `/files/{nome}` | Serve um PDF gerado em `storage/`. |
| `GET` | `/assets/{nome}` | Serve uma imagem enviada para `assets/`. |

### `GET /health`

Resposta esperada:

```json
{
  "status": "ok"
}
```

### `GET /templates`

Resposta esperada:

```json
{
  "templates": ["livro_tecnico_v1", "livro_tecnico_v2"],
  "default": "livro_tecnico_v2"
}
```

### `POST /upload-cover`

Aceita upload `multipart/form-data` e retorna:

Campos de arquivo aceitos:

- `file`
- `cover`
- `image`
- `arquivo`

```json
{
  "success": true,
  "cover_image_url": "http://127.0.0.1:8000/assets/cover_minha-capa_20260228153000.png",
  "filename": "cover_minha-capa_20260228153000.png"
}
```

Formatos aceitos:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`

### `POST /upload-cover-openai`

Endpoint pensado para ChatGPT Actions quando a imagem foi gerada no proprio chat.

Ele recebe `openaiFileIdRefs`, baixa o arquivo a partir do `download_link`, salva em `assets/` e retorna a mesma estrutura de resposta de `/upload-cover`.

Se `openaiFileIdRefs` vier vazio, a API responde com `400` e uma mensagem explicando que a Action foi chamada sem uma imagem anexada na conversa.

### `POST /generate-cover-image`

Endpoint para gerar uma arte de fundo de capa sem depender de upload.

Na implementacao atual, ele usa um adaptador de provider:

- sem configuracao extra, gera localmente uma arte editorial geometrica e salva em `assets/`
- se `OPENAI_API_KEY` estiver definido, tenta usar a OpenAI Image API (`gpt-image-1` por padrao)
- se `COVER_IMAGE_PROVIDER_URL` estiver definido, tenta usar um provider HTTP externo
- se o provider externo falhar, cai automaticamente no gerador local

Exemplo de request:

```json
{
  "book_title": "JavaScript Estruturado",
  "subtitle": "Do codigo desorganizado a aplicacao bem estruturada",
  "visual_concept": "editorial tecnico moderno, geometrico",
  "illustration_brief": "formas geometricas abstratas e linhas estruturais",
  "palette": {
    "brand_primary": "#1F3A5F",
    "brand_secondary": "#2D6A8A",
    "brand_accent": "#F59E0B",
    "brand_ink": "#0B1220",
    "brand_muted": "#64748B",
    "brand_line": "#1E293B",
    "brand_tint": "#E6F0FF"
  },
  "typography": {
    "font_title": "Inter",
    "font_body": "Source Sans 3",
    "font_mono": "JetBrains Mono"
  }
}
```

Exemplo de response:

```json
{
  "success": true,
  "image_url": "http://127.0.0.1:8000/assets/cover_generated-javascript-estruturado_20260228153000.png",
  "mime_type": "image/png",
  "prompt_used": "Create a professional book cover background illustration only..."
}
```

Configuracao opcional do provider externo:

- `COVER_IMAGE_PROVIDER`: `openai`, `http` ou `local`
- `OPENAI_API_KEY`: habilita o provider nativo da OpenAI
- `OPENAI_API_BASE_URL`: base URL da OpenAI ou de um gateway compativel (padrao: `https://api.openai.com`)
- `OPENAI_IMAGE_MODEL`: modelo da OpenAI para imagem (padrao: `gpt-image-1`)
- `OPENAI_IMAGE_TIMEOUT`: timeout em segundos para a chamada da OpenAI
- `OPENAI_IMAGE_QUALITY`: `auto`, `low`, `medium` ou `high`
- `OPENAI_IMAGE_BACKGROUND`: `auto`, `opaque` ou `transparent`
- `OPENAI_IMAGE_COMPRESSION`: 0 a 100 para `jpeg` e `webp`
- `COVER_IMAGE_PROVIDER_URL`: URL HTTP do provider de imagem
- `COVER_IMAGE_PROVIDER_API_KEY`: token Bearer opcional para esse provider
- `COVER_IMAGE_PROVIDER_TIMEOUT`: timeout em segundos para a chamada externa

Prioridade de selecao do provider:

1. `COVER_IMAGE_PROVIDER=openai`, ou `OPENAI_API_KEY` definido sem `COVER_IMAGE_PROVIDER`
2. `COVER_IMAGE_PROVIDER=http` ou `COVER_IMAGE_PROVIDER_URL` definido
3. gerador local procedural

### `POST /render-pdf`

Formato:

```json
{
  "template_id": "livro_tecnico_v2",
  "document": {
    "metadata": {},
    "content": []
  },
  "options": {
    "paper_size": "A4",
    "pdf_standard": "1.7"
  }
}
```

### `POST /render-pdf-wrapped`

Formato:

```json
{
  "template_id": "livro_tecnico_v2",
  "payload": {
    "document": {
      "metadata": {},
      "content": []
    },
    "options": {
      "paper_size": "A4",
      "pdf_standard": "1.7"
    }
  }
}
```

Resposta de sucesso para ambos:

```json
{
  "success": true,
  "file_url": "http://127.0.0.1:8000/files/8f4d6e0d4f0c4f7f9f35c9ad0f4e20d1.pdf",
  "warnings": []
}
```

## Formato do documento

O campo `document` deve ser um objeto com:

- `metadata`: informacoes do documento e configuracoes do template.
- `content`: lista de blocos renderizados em ordem.

### Blocos de `content` suportados hoje

Os templates atuais aceitam estes tipos de bloco:

- `heading`
- `paragraph`
- `list`
- `code`
- `table`
- `pagebreak`

Exemplo:

```json
{
  "metadata": {
    "title": "Guia de Integracao",
    "subtitle": "Fluxo de renderizacao",
    "author": "Equipe X"
  },
  "content": [
    { "type": "heading", "level": 1, "text": "Introducao" },
    { "type": "paragraph", "text": "Este documento foi gerado pela API." },
    { "type": "list", "items": ["Item A", "Item B"] },
    { "type": "code", "lang": "bash", "content": "typst compile main.typ output.pdf" },
    {
      "type": "table",
      "caption": "Exemplo",
      "columns": ["Campo", "Descricao"],
      "rows": [
        ["title", "Titulo do documento"],
        ["author", "Autor principal"]
      ]
    },
    { "type": "pagebreak" }
  ]
}
```

### Validacoes e `warnings`

Antes de renderizar, a API faz validacoes simples e pode retornar `warnings` como:

- `metadata.title` e `metadata.book_title` ausentes
- `metadata.author` ausente
- `content` nao e uma lista
- tabela sem `columns`
- linhas de tabela com quantidade de colunas diferente do cabecalho

Esses avisos nao bloqueiam a geracao do PDF por si so. Eles sao retornados no campo `warnings`.

## Campos de metadata usados pelos templates

### Campos basicos

- `title`
- `book_title`
- `subtitle`
- `author`
- `date`
- `edition`

### Controle de modo no `livro_tecnico_v2`

O template `livro_tecnico_v2` interpreta `metadata.mode` com estes valores:

- `cover`: gera apenas a capa
- `toc`: gera uma pagina de sumario
- `part`: gera conteudo de uma parte do livro

Campos adicionais aceitos pelo `livro_tecnico_v2`:

- `chapter_number`
- `chapter_title`
- `part_number`
- `part_title`
- `blurb`
- `bullets`

### Personalizacao visual no `livro_tecnico_v2`

O tema tambem aceita configuracoes de marca em `metadata`:

- `brand_primary`
- `brand_secondary`
- `brand_accent`
- `brand_ink`
- `brand_muted`
- `brand_line`
- `brand_paper`
- `brand_tint`
- `font_body`
- `font_title`
- `font_mono`

### Capa via payload

O renderizador suporta duas formas de definir capa direto no JSON:

- `metadata.cover_image_base64`
- `metadata.cover_image_url`

Quando algum desses campos e fornecido com sucesso, a API salva a imagem dentro do job e injeta automaticamente `metadata.cover_image_path` para uso do template.

Importante:

- `livro_tecnico_v1` nao renderiza imagem de capa.
- Para a imagem aparecer no `livro_tecnico_v2`, use `metadata.mode: "cover"`.
- O backend detecta automaticamente se o base64 enviado e PNG, JPEG ou WEBP e salva com a extensao correta.

## Exemplos de uso

### Renderizando com o payload de exemplo do repositorio

O arquivo `payload_wrapped.json` ja traz um exemplo de chamada para `/render-pdf-wrapped`.

No PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/render-pdf-wrapped" `
  -ContentType "application/json" `
  -Body (Get-Content .\payload_wrapped.json -Raw)
```

### Fazendo upload de capa

Com `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/upload-cover" ^
  -F "file=@capa.png"
```

Depois, use a `cover_image_url` retornada no `metadata` do documento.

## Pipeline interno de renderizacao

Para cada chamada de render:

1. A API verifica se o template existe.
2. Um diretorio unico e criado em `jobs/<uuid>/`.
3. Os arquivos de primeiro nivel do template sao copiados para esse job.
4. A capa e salva no job, se existir.
5. O `input.json` e escrito dentro do job.
6. O comando `typst compile main.typ output.pdf` e executado no diretorio do job.
7. O PDF final e copiado para `storage/<uuid>.pdf`.

## Limitacoes atuais

- A renderizacao e sincrona e bloqueia a requisicao ate o Typst terminar.
- Nao existe autenticacao, autorizacao ou rate limit.
- Nao existe limpeza automatica de `jobs/`, `storage/` ou `assets/`.
- O campo `options.paper_size` existe no schema, mas nao e usado na compilacao atual.
- Apenas `options.pdf_standard` e repassado para o comando Typst.
- O copiado de templates considera apenas arquivos no primeiro nivel do diretorio do template. Subpastas nao sao copiadas.
- `cover_image_url` depende de acesso de rede do servidor para baixar a imagem externa.
- Erros de compilacao do Typst retornam como `500` com `stdout` e `stderr` no detalhe.

## Boas praticas de operacao

- Execute atras de um proxy reverso se precisar expor publicamente.
- Ajuste `PUBLIC_BASE_URL` para a URL real do ambiente.
- Monitore o crescimento de `jobs/`, `storage/` e `assets/`.
- Valide o payload no cliente antes de chamar a API.
- Trate o campo `warnings` como sinal de qualidade do documento, nao apenas como detalhe cosmetico.

## Desenvolvimento e manutencao

- A forma mais simples de explorar a API e abrir `/docs`.
- `payload_wrapped.json` e um bom ponto de partida para testes manuais.
- `payload.json` existe no repositorio, mas atualmente esta vazio.
- O projeto depende do binario externo `typst`; falhas de ambiente normalmente aparecem durante a chamada de render.

## Solucao de problemas

### Erro "`typst` nao reconhecido"

O binario Typst nao esta instalado ou nao esta no `PATH` do processo.

### URLs apontando para `127.0.0.1` em ambiente remoto

Defina `PUBLIC_BASE_URL` antes de subir a API.

### Erro ao usar `cover_image_url`

Verifique se:

- a URL e publica
- o servidor consegue acessar a internet
- o host remoto responde dentro do timeout da aplicacao

### Upload rejeitado

O endpoint de upload aceita apenas `png`, `jpg`, `jpeg` e `webp`.

## Licenca

Nenhuma licenca esta declarada atualmente neste repositorio.
