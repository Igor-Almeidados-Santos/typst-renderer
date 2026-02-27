// templates/livro_tecnico_v2/main.typ
#import "theme.typ": brand, apply-page-style, cover, chapter-cover, part-open, paragraph-block, code-block, callout, table-block

#let data = json("input.json")
#let meta = data.at("metadata", default: (:))
#let content = data.at("content", default: ())

#let b = brand(meta)

// Metadados principais
#let book_title    = meta.at("book_title", default: meta.at("title", default: "Sem titulo"))
#let title         = meta.at("title", default: book_title)
#let subtitle      = meta.at("subtitle", default: "")
#let author        = meta.at("author", default: "Mestre Andre")
#let date          = meta.at("date", default: "")
#let edition       = meta.at("edition", default: "Edicao 1")
#let mode          = meta.at("mode", default: "part") // cover | toc | part

#let chapter_number = meta.at("chapter_number", default: none)
#let chapter_title  = meta.at("chapter_title",  default: none)
#let part_number    = meta.at("part_number",    default: none)
#let part_title     = meta.at("part_title",     default: none)

#let chapter_label = {
  if chapter_number == none or part_number == none {
    ""
  } else {
    "Capitulo " + str(chapter_number) + " - Parte " + str(part_number)
  }
}

// --- MODE: COVER ---
#if mode == "cover" {
  // Blurb e bullets opcionais para orelha
  let blurb = meta.at("blurb", default: "Um livro tecnico com profundidade, foco em aplicacao e padrao editorial profissional.")
  let bullets = meta.at("bullets", default: (
    "Modelos mentais corretos para producao",
    "Arquitetura e fluxos aplicaveis",
    "Checklist profissional e boas praticas",
    "Erros comuns e como evitar",
  ))

  cover(b, title, subtitle, author, date, edition, blurb, bullets)
}

// --- MODE: TOC ---
#if mode == "toc" {
  apply-page-style(b, book_title, "Sumario")
  = Sumario
  #v(2mm)
  // O outline usa headings gerados como headings reais no documento
  #outline()
}

// --- MODE: PART (capitulo/parte) ---
#if mode == "part" {
  apply-page-style(b, book_title, chapter_label)

  // Capa do capitulo apenas na Parte 1
  if chapter_number != none and chapter_title != none and part_number == 1 {
    chapter-cover(b, chapter_number, chapter_title)
  }

  // Abertura da parte
  if part_number != none and part_title != none {
    part-open(b, part_number, part_title)
  }

  // Sumario interno da parte
  == Nesta parte
  #v(1mm)
  #outline()
  #pagebreak()

  // Conteudo
  for block in content {
    let t = block.at("type", default: "")

    if t == "heading" {
      let level = block.at("level", default: 1)
      let text = block.at("text", default: "")
      heading(level: level, [#text])

    } else if t == "paragraph" {
      paragraph-block(block.at("text", default: ""))

    } else if t == "list" {
      let items = block.at("items", default: ())
      [
        #for item in items [
          - #item
        ]
      ]

    } else if t == "code" {
      code-block(b, block.at("lang", default: "txt"), block.at("content", default: ""))

    } else if t == "table" {
      table-block(b, block.at("caption", default: none), block.at("columns", default: ()), block.at("rows", default: ()))

    } else if t == "callout" {
      // Opcional: se você quiser, seu GPT pode emitir blocos callout
      // { "type":"callout", "title":"...", "body":"...", "kind":"info|warning|success" }
      callout(
        b,
        block.at("title", default: "Nota"),
        block.at("body", default: ""),
        block.at("kind", default: "info")
      )

    } else if t == "pagebreak" {
      pagebreak()
    }

    v(3mm)
  }
}