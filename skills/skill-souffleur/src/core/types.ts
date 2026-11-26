export type SkillName = string
export type NeedName = string
export type Match = { tools: string[]; paths?: string[] }
export type Origin = 'user' | 'project'
export type SkillRule = {
  /** Set by the parser from the file the entry came from; never read from JSON. */
  from: Origin
  always?: boolean
  startup?: 'injected'
  need?: NeedName
  gate?: Match
  duty?: { after: Match; evidence: { tool: string; command?: string } }
}
export type Mode = 'observe' | 'enforce'
export type Config = {
  mode: Mode
  skills: Record<SkillName, SkillRule>
  needs: Record<NeedName, string>
  /** Absolute project roots whose gates and duties may deny. Only the user file sets it. */
  trustProjects: string[]
  /** Only the user file holds these. */
  rules: Rule[]
  notes: Note[]
  learn: { skills: boolean }
  /** The need names the user file defines: proposals may name only these. */
  userNeeds?: string[]
}

/**
 * A check with a trace Souffleur can see, in one of three kinds: `before` + `skill` (the skill is loaded before a matching call),
 * `before` + `field` (a matching call carries the field), `after` + `evidence` (evidence follows a matching call).
 * `source` is `user`, `slip` or `skill:<name>`. `where` is a main repository root.
 */
export type Rule = {
  id: string
  where?: string
  source: string
  before?: Match
  skill?: SkillName
  field?: string
  after?: Match
  evidence?: { tool: string; command?: string }
}
/** A standing instruction. Never checked. Without `need` it goes into the system prompt section, with `need` into the prompt context. */
export type Note = { id: string; text: string; need?: NeedName; where?: string; source: string }
