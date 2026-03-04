#set text(lang: "pt")

#let color-from(value, fallback) = {
  if value == none { fallback } else { rgb(value) }
}

#let safe(value, fallback) = {
  if value == none or value == "" { fallback } else { value }
}

#let font-stack(value, fallback-1, fallback-2) = {
  let chosen = safe(value, none)
  if chosen == none {
    (fallback-1, fallback-2)
  } else {
    (chosen, fallback-1, fallback-2)
  }
}

#let brand(meta) = {
  let primary   = color-from(meta.at("brand_primary",   default: none), rgb("#1E3A8A"))
  let secondary = color-from(meta.at("brand_secondary", default: none), rgb("#0F766E"))
  let accent    = color-from(meta.at("brand_accent",    default: none), rgb("#F59E0B"))
  let ink       = color-from(meta.at("brand_ink",       default: none), rgb("#0B1220"))
  let muted     = color-from(meta.at("brand_muted",     default: none), rgb("#475569"))
  let line      = color-from(meta.at("brand_line",      default: none), rgb("#CBD5E1"))
  let paper     = color-from(meta.at("brand_paper",     default: none), rgb("#FFFFFF"))
  let tint      = color-from(meta.at("brand_tint",      default: none), rgb("#F1F5F9"))

  let body      = color-from(meta.at("color_body", default: meta.at("brand_ink", default: none)), ink)
  let heading   = color-from(meta.at("color_heading", default: meta.at("brand_primary", default: none)), primary)
  let heading-muted = color-from(
    meta.at("color_heading_muted", default: meta.at("brand_muted", default: none)),
    muted,
  )
  let heading-rule = color-from(
    meta.at("color_heading_rule", default: meta.at("brand_accent", default: none)),
    accent,
  )
  let code-bg = color-from(meta.at("color_code_bg", default: meta.at("brand_tint", default: none)), tint)
  let code-text = color-from(meta.at("color_code_text", default: meta.at("color_body", default: none)), body)
  let table-header-bg = color-from(
    meta.at("color_table_header_bg", default: meta.at("brand_tint", default: none)),
    tint,
  )
  let table-header-text = color-from(
    meta.at("color_table_header_text", default: meta.at("color_heading", default: none)),
    heading,
  )
  let table-body-bg = color-from(
    meta.at("color_table_body_bg", default: meta.at("brand_paper", default: none)),
    paper,
  )
  let table-body-text = color-from(
    meta.at("color_table_body_text", default: meta.at("color_body", default: none)),
    body,
  )

  let font_body = font-stack(meta.at("font_body", default: none), "Liberation Serif", "Noto Serif")
  let font_title = font-stack(meta.at("font_title", default: none), "Liberation Sans", "Noto Sans")
  let font_heading = font-stack(
    meta.at("font_heading", default: meta.at("font_title", default: none)),
    "Liberation Sans",
    "Noto Sans",
  )
  let font_mono = font-stack(meta.at("font_mono", default: none), "Liberation Mono", "Noto Sans Mono")

  (
    primary: primary, secondary: secondary, accent: accent,
    ink: ink, muted: muted, line: line, paper: paper, tint: tint,
    body: body, heading: heading, heading-muted: heading-muted, heading-rule: heading-rule,
    code-bg: code-bg, code-text: code-text,
    table-header-bg: table-header-bg, table-header-text: table-header-text,
    table-body-bg: table-body-bg, table-body-text: table-body-text,
    font_body: font_body, font_title: font_title, font_heading: font_heading, font_mono: font_mono,
  )
}

#let apply-page-style(b, book-title, chapter-label) = {
  #set page(
    width: 210mm, height: 297mm,
    fill: b.paper,
    margin: (top: 20mm, bottom: 18mm, left: 22mm, right: 22mm),
    header: [
      #text(font: b.font_title, size: 9pt, fill: b.muted)[#book-title]
      #h(1fr)
      #text(font: b.font_title, size: 9pt, fill: b.muted)[#chapter-label]
      #line(length: 100%, stroke: (paint: b.line, thickness: 0.6pt))
    ],
    footer: [
      #text(font: b.font_title, size: 9pt, fill: b.muted)[#chapter-label]
      #h(1fr)
      #text(font: b.font_title, size: 9pt, fill: b.muted)[#counter(page)]
    ],
  )

  #set text(font: b.font_body, size: 11pt, fill: b.body)
  #set par(justify: true, leading: 0.62em)
  #set heading(numbering: "1.")
}

#let heading-block(b, level, title) = {
  let size = if level <= 1 { 18pt } else if level == 2 { 14pt } else { 12pt }
  let color = if level <= 2 { b.heading } else { b.heading-muted }

  heading(
    level: level,
    [#text(font: b.font_heading, size: size, weight: "bold", fill: color)[#title]],
  )
}

#let cover(b, meta, title, subtitle, author, date, edition, blurb, bullets) = [
  #set page(width: 210mm, height: 297mm, margin: (0mm, 0mm, 0mm, 0mm), header: none, footer: none)

  let cover-path = meta.at("cover_image_path", default: none)

  // Fundo: se existir cover.png, usa imagem; senão usa composição geométrica
  if cover-path != none {
    #image(cover-path, width: 210mm, height: 297mm, fit: "cover")
    // Overlay para legibilidade (escurece)
    #rect(width: 210mm, height: 297mm, fill: rgba(0,0,0,120))
    // Faixa superior e acentos
    #rect(width: 210mm, height: 70mm, fill: rgba(0,0,0,90))
    #rect(width: 210mm, height: 5mm, y: 70mm, fill: b.accent)
  } else {
    #rect(width: 210mm, height: 297mm, fill: b.ink)
    #rect(width: 210mm, height: 85mm, fill: b.primary)
    #rect(width: 210mm, height: 6mm, y: 85mm, fill: b.accent)
    #rect(width: 210mm, height: 90mm, y: 207mm, fill: b.secondary)
  }

  // Selo edição
  #rect(
    width: 42mm, height: 16mm,
    x: 210mm - 52mm, y: 16mm,
    radius: 3mm,
    fill: b.tint,
    stroke: (paint: white, thickness: 0.8pt)
  )
  #block(x: 210mm - 52mm, y: 16mm, width: 42mm, height: 16mm)[
    #align(center + middle)[
      #text(font: b.font_title, size: 9pt, fill: b.ink)[#safe(edition, "Edicao 1")]
    ]
  ]

  // Título/Subtítulo
  #block(width: 175mm, x: 18mm, y: 44mm)[
    #text(font: b.font_title, size: 28pt, weight: "bold", fill: white)[#title]
    #v(4mm)
    #text(font: b.font_title, size: 12.5pt, fill: b.tint)[#subtitle]
  ]

  // Autor + data
  #block(width: 175mm, x: 18mm, y: 142mm)[
    #text(font: b.font_title, size: 10.5pt, fill: b.tint)[Autor: #author]
    #v(2mm)
    #text(font: b.font_title, size: 10.5pt, fill: b.tint)[#date]
  ]

  // Orelha
  #block(width: 175mm, x: 18mm, y: 220mm)[
    #set text(font: b.font_body, size: 10.5pt, fill: white)
    #text(font: b.font_title, weight: "bold")[Sobre este livro]
    #v(2mm)
    #text(fill: b.tint)[#blurb]
    #v(4mm)
    #text(font: b.font_title, weight: "bold")[O que voce vai dominar]
    #v(2mm)
    #for item in bullets [
      - #text(fill: b.tint)[#item]
    ]
  ]

  #pagebreak()
]

#let chapter-cover(b, chapter-number, chapter-title) = [
  #set page(header: none, footer: none)
  #rect(width: 210mm, height: 297mm, fill: b.tint)
  #rect(width: 210mm, height: 50mm, fill: b.primary)
  #block(width: 170mm, x: 20mm, y: 68mm)[
    #set text(font: b.font_heading, fill: b.body)
    #text(size: 11pt, fill: b.heading-muted)[Capitulo #chapter-number]
    #v(3mm)
    #text(size: 22pt, weight: "bold", fill: b.heading)[#chapter-title]
    #v(6mm)
    #line(length: 60mm, stroke: (paint: b.heading-rule, thickness: 2pt))
  ]
  #rect(width: 210mm, height: 6mm, y: 120mm, fill: b.heading-rule)
  #pagebreak()
]

#let part-open(b, part-number, part-title) = [
  #set page(header: none, footer: none)
  #rect(width: 210mm, height: 297mm, fill: b.paper)
  #rect(width: 210mm, height: 18mm, fill: b.tint)
  #block(width: 170mm, x: 20mm, y: 52mm)[
    #set text(font: b.font_heading, fill: b.body)
    #text(size: 10pt, fill: b.heading-muted)[Parte #part-number]
    #v(3mm)
    #text(size: 18pt, weight: "bold", fill: b.heading)[#part-title]
    #v(6mm)
    #line(length: 50mm, stroke: (paint: b.heading-rule, thickness: 1.6pt))
  ]
  #pagebreak()
]

#let paragraph-block(b, text) = [#par[#text(font: b.font_body, fill: b.body)[#text]]]

#let code-block(b, lang, content) = [
  #block(
    inset: 8pt,
    radius: 4pt,
    stroke: (paint: b.line, thickness: 0.8pt),
    fill: b.code-bg
  )[
    #text(font: b.font_mono, size: 9pt, fill: b.code-text)[#content]
  ]
]

#let table-block(b, caption, columns, rows) = [
  #figure(
    caption: if caption == none { none } else { [#caption] }
  )[
    #table(
      columns: columns.len(),
      stroke: (paint: b.line, thickness: 0.7pt),
      fill: (x, y) => if y == 0 { b.table-header-bg } else { b.table-body-bg },
      inset: (x: 6pt, y: 5pt),
      align: left,
      ..columns.map(c => [#text(font: b.font_heading, size: 10pt, weight: "bold", fill: b.table-header-text)[#c]]),
      ..rows.flatten().map(cell => [#text(fill: b.table-body-text)[#cell]]),
    )
  ]
]
