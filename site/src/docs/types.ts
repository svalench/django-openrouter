export type CalloutKind = 'info' | 'warning' | 'danger' | 'tip'

export type Block =
  | { type: 'p'; text: string }
  | { type: 'h3'; text: string }
  | { type: 'code'; lang: string; title?: string; code: string }
  | { type: 'list'; ordered?: boolean; items: string[] }
  | { type: 'table'; head: string[]; rows: string[][] }
  | { type: 'callout'; kind: CalloutKind; title?: string; text: string }
  | { type: 'steps'; items: { title: string; text: string }[] }
  | { type: 'image'; src: string; alt: string; caption?: string }

export interface DocSection {
  id: string
  group: string
  title: string
  /** short lead under the H1 */
  lead?: string
  blocks: Block[]
}

export interface DocsContent {
  meta: {
    name: string
    tagline: string
    version: string
    github: string
    pypi: string
  }
  nav: {
    searchPlaceholder: string
    searchEmpty: string
    onThisPage: string
    copied: string
    copy: string
    editGithub: string
    prev: string
    next: string
    heroBadge: string
    heroCta: string
    heroGithub: string
    builtWith: string
    license: string
  }
  ui: {
    theme: string
    language: string
    openMenu: string
    closeMenu: string
  }
  sections: DocSection[]
}
