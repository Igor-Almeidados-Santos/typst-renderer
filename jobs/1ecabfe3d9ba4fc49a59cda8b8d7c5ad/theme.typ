#set text(lang: "pt")
#set page(
  width: 210mm,
  height: 297mm,
  margin: (top: 22mm, bottom: 22mm, left: 22mm, right: 22mm),
)

#set par(justify: true, leading: 0.62em)
#set heading(numbering: "1.")
#set text(font: "Liberation Serif", size: 11pt)

#let cover(title, subtitle, author) = [
  #set page(
    margin: (top: 0mm, bottom: 0mm, left: 0mm, right: 0mm)
  )

  #align(center + horizon, block(width: 100%, height: 100%)[
    #v(25%)
    #text(size: 24pt, weight: "bold")[#title]
    #v(8mm)
    #text(size: 13pt, fill: rgb("#444"))[#subtitle]
    #v(20mm)
    #text(size: 11pt)[#author]
  ])

  #pagebreak()
]

#let paragraph-block(text) = [
  #par[#text]
]

#let code-block(lang, content) = [
  #block(
    inset: 8pt,
    radius: 4pt,
    stroke: luma(220),
    fill: luma(248)
  )[
    #text(font: "Liberation Mono", size: 9pt)[#content]
  ]
]

#let table-block(caption, columns, rows) = [
  #if caption != none [
    #figure(
      caption: [#caption]
    )[
      #table(
        columns: columns.len(),
        stroke: luma(180),
        fill: (x, y) => if y == 0 { luma(235) } else { white },
        ..columns.map(c => [*#c*]),
        ..rows.flatten().map(cell => [#cell]),
      )
    ]
  ] else [
    #table(
      columns: columns.len(),
      stroke: luma(180),
      fill: (x, y) => if y == 0 { luma(235) } else { white },
      ..columns.map(c => [*#c*]),
      ..rows.flatten().map(cell => [#cell]),
    )
  ]
]