import { readFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'dsh-stl-to-editable-part'
export const inject = ['skills']

const skillName = 'stl-to-editable-part'
const skillPath = fileURLToPath(new URL(`./skills/${skillName}/SKILL.md`, import.meta.url))
const markdown = readFileSync(skillPath, 'utf8')
const sections = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]+)$/.exec(markdown)
const description = sections?.[1].match(/^description:[ \t]+(.+)$/m)?.[1].trim()

if (!description || !sections[2].trim()) {
  throw new Error(`${name}: bundled SKILL.md must have a description and instructions`)
}

export function apply(ctx) {
  ctx.skills.register({
    name: skillName,
    description,
    source: 'bundled',
    provider: name,
    path: skillPath,
    resourceBase: { kind: 'directory', path: dirname(skillPath) },
    content: sections[2].trim()
  })
}
