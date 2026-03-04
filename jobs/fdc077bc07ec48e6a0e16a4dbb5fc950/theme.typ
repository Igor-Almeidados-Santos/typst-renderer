#set text(lang: "pt")

#let color-from(value, fallback) = {
  if value == none {
    fallback
  } else if type(value) == array and value.len() == 3 {
    rgb(value.at(0, default: 0), value.at(1, default: 0), value.at(2, default: 0))
  } else {
    fallback
  }
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
  let primary = color-from(meta.at("brand_primary", default: none), rgb(0x1E, 0x3A, 0x8A))
  let secondary = color-from(meta.at("brand_secondary", default: none), rgb(0x0F, 0x76, 0x6E))
  let accent = color-from(meta.at("brand_accent", default: none), rgb(0xF5, 0x9E, 0x0B))
  let ink = color-from(meta.at("brand_ink", default: none), rgb(0x0B, 0x12, 0x20))
  let muted = color-from(meta.at("brand_muted", default: none), rgb(0x47, 0x55, 0x69))
  let line = color-from(meta.at("brand_line", default: none), rgb(0xCB, 0xD5, 0xE1))
  let paper = color-from(meta.at("brand_paper", default: none), rgb(0xFF, 0xFF, 0xFF))
  let tint = color-from(meta.at("brand_tint", default: none), rgb(0xF1, 0xF5, 0xF9))

  let body = color-from(meta.at("color_body", default: meta.at("brand_ink", default: none)), ink)
  let heading = color-from(meta.at("color_heading", default: meta.at("brand_primary", default: none)), primary)
  let heading_muted = color-from(
    meta.at("color_heading_muted", default: meta.at("brand_muted", default: none)),
    muted,
  )
  let heading_rule = color-from(
    meta.at("color_heading_rule", default: meta.at("brand_accent", default: none)),
    accent,
  )

  let code_bg = color-from(meta.at("color_code_bg", default: none), rgb(0x0D, 0x11, 0x17))
  let code_text = color-from(meta.at("color_code_text", default: none), rgb(0xE6, 0xED, 0xF6))
  let code_border = color-from(meta.at("color_code_border", default: none), rgb(0x1F, 0x29, 0x37))
  let code_header_bg = color-from(meta.at("color_code_header_bg", default: none), rgb(0x11, 0x18, 0x27))
  let code_header_text = color-from(meta.at("color_code_header_text", default: none), rgb(0x93, 0xC5, 0xFD))

  let table_header_bg = color-from(
    meta.at("color_table_header_bg", default: meta.at("brand_tint", default: none)),
    tint,
  )
  let table_header_text = color-from(
    meta.at("color_table_header_text", default: meta.at("color_heading", default: none)),
    heading,
  )
  let table_body_bg = color-from(
    meta.at("color_table_body_bg", default: meta.at("brand_paper", default: none)),
    paper,
  )
  let table_body_text = color-from(
    meta.at("color_table_body_text", default: meta.at("color_body", default: none)),
    body,
  )

  let font_body = font-stack(meta.at("font_body", default: none), "New Computer Modern", "Libertinus Serif")
  let font_title = font-stack(meta.at("font_title", default: none), "New Computer Modern", "Libertinus Serif")
  let font_heading = font-stack(
    meta.at("font_heading", default: meta.at("font_title", default: none)),
    "New Computer Modern",
    "Libertinus Serif",
  )
  let font_mono = font-stack(meta.at("font_mono", default: none), "New Computer Modern", "Libertinus Serif")

  (
    primary: primary,
    secondary: secondary,
    accent: accent,
    ink: ink,
    muted: muted,
    line: line,
    paper: paper,
    tint: tint,
    body: body,
    heading: heading,
    heading_muted: heading_muted,
    heading_rule: heading_rule,
    code_bg: code_bg,
    code_text: code_text,
    code_border: code_border,
    code_header_bg: code_header_bg,
    code_header_text: code_header_text,
    table_header_bg: table_header_bg,
    table_header_text: table_header_text,
    table_body_bg: table_body_bg,
    table_body_text: table_body_text,
    font_body: font_body,
    font_title: font_title,
    font_heading: font_heading,
    font_mono: font_mono,
  )
}

#let apply-page-style(b, book-title, chapter-label, body) = {
  set page(
    width: 210mm,
    height: 297mm,
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

  set text(font: b.font_body, size: 11pt, fill: b.body)
  set par(justify: true, leading: 0.62em)
  set heading(numbering: "1.")
  body
}

#let heading-block(b, level, title) = {
  let size = if level <= 1 { 18pt } else if level == 2 { 14pt } else { 12pt }
  let color = if level <= 2 { b.heading } else { b.heading_muted }

  heading(
    level: level,
    [#text(font: b.font_heading, size: size, weight: "bold", fill: color)[#title]],
  )
}

#let toc-list-block(b, items) = [
  #set par(justify: false, leading: 0.55em)
  #for item in items [
    #block(inset: (left: 3mm, right: 0mm, top: 1.5mm, bottom: 1.5mm))[
      #text(font: b.font_body, size: 11pt, fill: b.body)[#item]
    ]
  ]
]

#let toc-table-fallback(b, caption, rows) = [
  #if caption != none [
    #text(font: b.font_heading, size: 11pt, weight: "bold", fill: b.heading_muted)[#caption]
    #v(1.5mm)
  ]
  #set par(justify: false, leading: 0.55em)
  #for row in rows [
    #let line = if type(row) == array { row.join(" - ") } else { str(row) }
    #block(inset: (left: 3mm, right: 0mm, top: 1.2mm, bottom: 1.2mm))[
      #text(font: b.font_body, size: 11pt, fill: b.body)[#line]
    ]
  ]
]

#let list-block(b, items) = [
  #for item in items [
    - #text(font: b.font_body, fill: b.body)[#item]
  ]
]

#let theme-value(theme, key) = {
  if type(theme) == dictionary {
    theme.at(key, default: none)
  } else {
    none
  }
}

#let cover(b, meta, title, subtitle, author, date, edition, blurb, bullets) = [
  #set page(
    width: 210mm,
    height: 297mm,
    margin: (top: 0mm, bottom: 0mm, left: 0mm, right: 0mm),
    header: none,
    footer: none,
  )
  #let cover_path = meta.at("cover_image_path", default: none)

  #if cover_path != none [
    #image(cover_path, width: 210mm, height: 297mm, fit: "cover")
  ] else [
    #rect(width: 210mm, height: 297mm, fill: b.ink)
  ]

  #v(22mm)
  #block(inset: (left: 18mm, right: 18mm, top: 0mm, bottom: 0mm))[
    #text(font: b.font_title, size: 28pt, weight: "bold", fill: white)[#title]
    #v(3mm)
    #text(font: b.font_title, size: 12pt, fill: b.tint)[#subtitle]
    #v(6mm)
    #text(font: b.font_title, size: 10pt, fill: b.tint)[Autor: #author]
    #v(1.5mm)
    #text(font: b.font_title, size: 10pt, fill: b.tint)[#date]
    #v(1.5mm)
    #text(font: b.font_title, size: 10pt, fill: b.tint)[#safe(edition, "Edicao 1")]
    #v(8mm)
    #text(font: b.font_title, weight: "bold", fill: b.tint)[Sobre este livro]
    #v(2mm)
    #text(fill: b.tint)[#blurb]
    #v(4mm)
    #for item in bullets [
      - #text(fill: b.tint)[#item]
    ]
  ]
  #pagebreak()
]

#let chapter-cover(b, chapter-number, chapter-title) = [
  #set page(
    width: 210mm,
    height: 297mm,
    margin: (top: 0mm, bottom: 0mm, left: 0mm, right: 0mm),
    fill: b.tint,
    header: none,
    footer: none,
  )
  #rect(width: 210mm, height: 50mm, fill: b.primary)
  #v(18mm)
  #block(width: 170mm, inset: (left: 20mm, right: 20mm, top: 0mm, bottom: 0mm))[
    #set text(font: b.font_heading, fill: b.body)
    #text(size: 11pt, fill: b.heading_muted)[Capitulo #chapter-number]
    #v(3mm)
    #text(size: 22pt, weight: "bold", fill: b.heading)[#chapter-title]
    #v(6mm)
    #line(length: 60mm, stroke: (paint: b.heading_rule, thickness: 2pt))
  ]
  #v(10mm)
  #rect(width: 210mm, height: 6mm, fill: b.heading_rule)
  #pagebreak()
]

#let part-open(b, part-number, part-title) = [
  #set page(
    width: 210mm,
    height: 297mm,
    margin: (top: 0mm, bottom: 0mm, left: 0mm, right: 0mm),
    fill: b.paper,
    header: none,
    footer: none,
  )
  #rect(width: 210mm, height: 18mm, fill: b.tint)
  #v(34mm)
  #block(width: 170mm, inset: (left: 20mm, right: 20mm, top: 0mm, bottom: 0mm))[
    #set text(font: b.font_heading, fill: b.body)
    #text(size: 10pt, fill: b.heading_muted)[Parte #part-number]
    #v(3mm)
    #text(size: 18pt, weight: "bold", fill: b.heading)[#part-title]
    #v(6mm)
    #line(length: 50mm, stroke: (paint: b.heading_rule, thickness: 1.6pt))
  ]
  #pagebreak()
]

#let paragraph-block(b, value) = [#par[#text(font: b.font_body, fill: b.body)[#value]]]

#let code-block(b, lang, content, theme: (:)) = [
  #let code_surface = color-from(theme-value(theme, "bg"), b.code_bg)
  #let code_border = color-from(theme-value(theme, "border"), b.code_border)
  #let code_header = color-from(theme-value(theme, "header_bg"), b.code_header_bg)
  #let code_header_text = color-from(theme-value(theme, "header_text"), b.code_header_text)
  #let code_ink = color-from(theme-value(theme, "text"), b.code_text)
  #let code_line_number = color-from(theme-value(theme, "line_number"), rgb(0x6B, 0x72, 0x80))
  #let lines = content.split("\n")

  #block(
    inset: 0pt,
    radius: 5pt,
    stroke: (paint: code_border, thickness: 0.8pt),
    fill: code_surface,
    clip: true,
  )[
    #block(
      inset: (left: 12pt, right: 12pt, top: 5pt, bottom: 5pt),
      fill: code_header,
    )[
      #text(font: b.font_mono, size: 8pt, weight: "bold", fill: code_header_text)[#lang]
    ]
    #block(
      inset: (left: 12pt, right: 12pt, top: 9pt, bottom: 9pt),
    )[
      #set par(justify: false, leading: 0.48em)
      #for (idx, line) in lines.enumerate() [
        #text(font: b.font_mono, size: 8pt, fill: code_line_number)[#str(idx + 1)]
        #h(9pt)
        #text(font: b.font_mono, size: 9pt, fill: code_ink)[#line]
        #linebreak()
      ]
    ]
  ]
]

#let table-block(b, caption, columns, rows) = {
  if columns.len() == 0 {
    [
      #block(
        inset: 8pt,
        stroke: (paint: b.line, thickness: 0.7pt),
        fill: b.table_body_bg,
      )[
        #text(font: b.font_body, fill: b.table_body_text)[Tabela omitida: columns ausentes.]
      ]
    ]
  } else {
    [
      #figure(
        caption: if caption == none { none } else { [#caption] },
      )[
        #table(
          columns: columns.len(),
          stroke: (paint: b.line, thickness: 0.7pt),
          fill: (x, y) => if y == 0 { b.table_header_bg } else { b.table_body_bg },
          inset: (x: 6pt, y: 5pt),
          align: left,
          ..columns.map(c => [#text(font: b.font_heading, size: 10pt, weight: "bold", fill: b.table_header_text)[#c]]),
          ..rows.flatten().map(cell => [#text(fill: b.table_body_text)[#cell]]),
        )
      ]
    ]
  }
}

#let render-blocks(b, blocks, toc: false) = [
  #for block in blocks {
    let t = block.at("type", default: "")

    if t == "heading" {
      let level = block.at("level", default: 1)
      let text = block.at("text", default: "")
      heading-block(b, level, text)

    } else if t == "paragraph" {
      paragraph-block(b, block.at("text", default: ""))

    } else if t == "list" {
      let items = block.at("items", default: ())
      if toc { toc-list-block(b, items) } else { list-block(b, items) }

    } else if t == "code" {
      if toc {
        paragraph-block(b, block.at("content", default: ""))
      } else {
        let block_theme = if block.at("theme", default: none) != none {
          block.at("theme", default: none)
        } else {
          block.at("tema", default: (:))
        }
        code-block(
          b,
          block.at("lang", default: "txt"),
          block.at("content", default: ""),
          theme: block_theme,
        )
      }

    } else if t == "table" {
      if toc {
        toc-table-fallback(b, block.at("caption", default: none), block.at("rows", default: ()))
      } else {
        table-block(
          b,
          block.at("caption", default: none),
          block.at("columns", default: ()),
          block.at("rows", default: ()),
        )
      }

    } else if t == "pagebreak" {
      pagebreak()
    }

    v(3mm)
  }
]
