#import "theme.typ": brand, apply-page-style, cover, chapter-cover, part-open, heading-block, render-blocks

#let data = json("input.json")
#let meta = data.at("metadata", default: (:))
#let content = data.at("content", default: ())

#let b = brand(meta)

#let book_title     = meta.at("book_title", default: meta.at("title", default: "Sem titulo"))
#let title          = meta.at("title", default: book_title)
#let subtitle       = meta.at("subtitle", default: "")
#let author         = meta.at("author", default: "Mestre Andre")
#let date           = meta.at("date", default: "")
#let edition        = meta.at("edition", default: "Edicao 1")
#let mode           = meta.at("mode", default: "part") // cover | toc | part

#let chapter_number = meta.at("chapter_number", default: none)
#let chapter_title  = meta.at("chapter_title",  default: none)
#let part_number    = meta.at("part_number",    default: none)
#let part_title     = meta.at("part_title",     default: none)

#let chapter_label = {
  if chapter_number == none or part_number == none { "" }
  else { "Capitulo " + str(chapter_number) + " - Parte " + str(part_number) }
}

// COVER
#if mode == "cover" [
  #let blurb = meta.at("blurb", default: "Um livro tecnico com profundidade, foco em aplicacao e padrao editorial profissional.")
  #let bullets = meta.at("bullets", default: (
    "Modelos mentais corretos para producao",
    "Arquitetura e fluxos aplicaveis",
    "Checklist profissional e boas praticas",
    "Erros comuns e como evitar",
  ))
  #cover(b, meta, title, subtitle, author, date, edition, blurb, bullets)
]

// TOC
#if mode == "toc" [
  #apply-page-style(b, book_title, "Sumario", [
    #heading-block(b, 1, "Sumario")
    #v(2mm)

    #if content.len() == 0 [
      #outline()
    ] else [
      #render-blocks(b, content, toc: true)
    ]
  ])
]

// PART
#if mode == "part" [
  #if chapter_number != none and chapter_title != none and part_number == 1 [
    #chapter-cover(b, chapter_number, chapter_title)
  ]

  #if part_number != none and part_title != none [
    #part-open(b, part_number, part_title)
  ]

  #apply-page-style(b, book_title, chapter_label, [
    #heading-block(b, 2, "Nesta parte")
    #v(1mm)
    #outline()
    #pagebreak()
    #render-blocks(b, content)
  ])
]
