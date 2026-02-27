// templates/livro_tecnico_v2/theme.typ

#set text(lang: "pt")

// ---- Helpers ----
#let color-from(value, fallback) = {
  if value == none { fallback }
  else { rgb(value) }
}

#let safe(value, fallback) = {
  if value == none { fallback } else { value }
}

// ---- Brand (paleta + fontes) ----
#let brand(meta) = {
  // Você passa strings hex em metadata.brand.* (ex: "#1E3A8A")
  let primary   = color-from(meta.at("brand_primary",   default: none), rgb("#1E3A8A"))
  let secondary = color-from(meta.at("brand_secondary", default: none), rgb("#0F766E"))
  let accent    = color-from(meta.at("brand_accent",    default: none), rgb("#F59E0B"))
  let ink       = color-from(meta.at("brand_ink",       default: none), rgb("#0B1220"))
  let muted     = color-from(meta.at("brand_muted",     default: none), rgb("#475569"))
  let line      = color-from(meta.at("brand_line",      default: none), rgb("#CBD5E1"))
  let paper     = color-from(meta.at("brand_paper",     default: none), rgb("#FFFFFF"))
  let tint      = color-from(meta.at("brand_tint",      default: none), rgb("#F1F5F9"))

  let font_body  = safe(meta.at("font_body",  default: none), "Liberation Serif")
  let font_title = safe(meta.at("font_title", default: none), "Liberation Sans")
  let font_mono  = safe(meta.at("font_mono",  default: none), "Liberation Mono")

  (
    primary: primary,
    secondary: secondary,
    accent: accent,
    ink: ink,
    muted: muted,
    line: line,
    paper: paper,
    tint: tint,
    font_body: font_body,
    font_title: font_title,
    font_mono: font_mono,
  )
}

// ---- Page defaults ----
#let apply-page-style(b, book-title, chapter-label) = {
  #set page(
    width: 210mm,
    height: 297mm,
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

  #set text(font: b.font_body, size: 11pt, fill: b.ink)
  #set par(justify: true, leading: 0.62em)
  #set heading(numbering: "1.", font: b.font_title, fill: b.ink)
}

// ---- Components ----
#let cover(b, title, subtitle, author, date, edition, blurb, bullets) = [
  // Capa sem margens, visual mais “livro”
  #set page(width: 210mm, height: 297mm, margin: (0mm, 0mm, 0mm, 0mm), header: none, footer: none)
  #set text(font: b.font_title, fill: b.paper)

  // Fundo: geometria/ilustração gerada (sem assets externos)
  #rect(
    width: 210mm, height: 297mm,
    fill: b.ink
  )

  // Faixas e elementos geométricos
  #rect(width: 210mm, height: 85mm, fill: b.primary)
  #rect(width: 210mm, height: 6mm, y: 85mm, fill: b.accent)
  #rect(width: 210mm, height: 90mm, y: 207mm, fill: b.secondary)

  // “Selo” discreto
  #rect(
    width: 42mm, height: 16mm,
    x: 210mm - 52mm, y: 16mm,
    radius: 3mm,
    fill: b.tint,
    stroke: (paint: b.paper, thickness: 0.8pt)
  )
  #text(
    font: b.font_title,
    size: 9pt,
    fill: b.ink
  )[
    #align(center)[#safe(edition, "Edicao 1")]
  ]

  // Título/Subtítulo
  #block(width: 170mm, x: 20mm, y: 38mm)[
    #text(size: 26pt, weight: "bold", fill: b.paper)[#title]
    #v(4mm)
    #text(size: 12.5pt, fill: b.tint)[#subtitle]
  ]

  // Autor + data
  #block(width: 170mm, x: 20mm, y: 138mm)[
    #text(size: 10.5pt, fill: b.tint)[Autor: #author]
    #v(2mm)
    #text(size: 10.5pt, fill: b.tint)[#date]
  ]

  // Orelha simulada (texto curto + bullets)
  #block(width: 170mm, x: 20mm, y: 220mm)[
    #set text(font: b.font_body, size: 10.5pt, fill: b.paper)
    #text(weight: "bold")[Sobre este livro]
    #v(2mm)
    #text(fill: b.tint)[#blurb]
    #v(4mm)
    #text(weight: "bold")[O que voce vai dominar]
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
    #set text(font: b.font_title, fill: b.ink)
    #text(size: 11pt, fill: b.muted)[Capitulo #chapter-number]
    #v(3mm)
    #text(size: 22pt, weight: "bold")[#chapter-title]
    #v(6mm)
    #line(length: 60mm, stroke: (paint: b.accent, thickness: 2pt))
  ]
  // Elemento gráfico discreto
  #rect(width: 210mm, height: 6mm, y: 120mm, fill: b.accent)
  #pagebreak()
]

#let part-open(b, part-number, part-title) = [
  #set page(header: none, footer: none)
  #rect(width: 210mm, height: 297mm, fill: b.paper)
  #rect(width: 210mm, height: 18mm, fill: b.tint)
  #block(width: 170mm, x: 20mm, y: 52mm)[
    #set text(font: b.font_title, fill: b.ink)
    #text(size: 10pt, fill: b.muted)[Parte #part-number]
    #v(3mm)
    #text(size: 18pt, weight: "bold")[#part-title]
    #v(6mm)
    #line(length: 50mm, stroke: (paint: b.primary, thickness: 1.6pt))
  ]
  #pagebreak()
]

// Conteúdo
#let paragraph-block(text) = [#par[#text]]

#let code-block(b, lang, content) = [
  #block(
    inset: 8pt,
    radius: 4pt,
    stroke: (paint: b.line, thickness: 0.8pt),
    fill: b.tint
  )[
    #text(font: b.font_mono, size: 9pt, fill: b.ink)[#content]
  ]
]

#let callout(b, title, body, kind) = {
  let bar = if kind == "warning" { b.accent } else if kind == "success" { b.secondary } else { b.primary }
  [
    #block(
      inset: 10pt,
      radius: 5pt,
      stroke: (paint: b.line, thickness: 0.8pt),
      fill: b.paper
    )[
      #rect(width: 100%, height: 3pt, fill: bar)
      #v(4pt)
      #text(font: b.font_title, size: 10.5pt, weight: "bold", fill: b.ink)[#title]
      #v(3pt)
      #text(font: b.font_body, size: 10.5pt, fill: b.ink)[#body]
    ]
  ]
}

#let table-block(b, caption, columns, rows) = [
  #figure(
    caption: if caption == none { none } else { [#caption] }
  )[
    #table(
      columns: columns.len(),
      stroke: (paint: b.line, thickness: 0.7pt),
      fill: (x, y) => if y == 0 { b.tint } else { b.paper },
      inset: (x: 6pt, y: 5pt),
      align: left,
      ..columns.map(c => [#text(font: b.font_title, size: 10pt, weight: "bold")[#c]]),
      ..rows.flatten().map(cell => [#cell]),
    )
  ]
]