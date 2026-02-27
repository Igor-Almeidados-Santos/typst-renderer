#import "theme.typ": cover, paragraph-block, code-block, table-block

#let data = json("input.json")

#let metadata = data.at("metadata", default: (:))
#let content = data.at("content", default: ())

#let title = metadata.at("title", default: "Sem título")
#let subtitle = metadata.at("subtitle", default: "")
#let author = metadata.at("author", default: "Autor não informado")

#cover(title, subtitle, author)

#for block in content {
  #let t = block.at("type", default: "")

  #if t == "heading" {
    #let level = block.at("level", default: 1)
    #let text = block.at("text", default: "")

    #if level == 1 [
      = #text
    ] else if level == 2 [
      == #text
    ] else if level == 3 [
      === #text
    ] else [
      ==== #text
    ]
  }

  #if t == "paragraph" {
    #paragraph-block(block.at("text", default: ""))
  }

  #if t == "list" {
    #let items = block.at("items", default: ())
    #for item in items [
      - #item
    ]
  }

  #if t == "code" {
    #code-block(block.at("lang", default: "txt"), block.at("content", default: ""))
  }

  #if t == "table" {
    #table-block(
      block.at("caption", default: none),
      block.at("columns", default: ()),
      block.at("rows", default: ()),
    )
  }

  #if t == "pagebreak" {
    #pagebreak()
  }

  #v(4mm)
}