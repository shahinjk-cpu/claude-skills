import type { Config, NeedName, SkillName } from './types.ts'

export type Classify = (text: string, labels: readonly string[]) => Promise<string>

/**
 * Asks the classifier once per need, in parallel. Returns the needs answered `match` before the budget ends,
 * in the order of `needs`. A rejected call or a call still running at the end counts as no match.
 */
export async function classifyPrompt(
  prompt: string,
  needs: Record<NeedName, string>,
  classify: Classify,
  timeout: (ms: number) => Promise<void>,
  budgetMs = 1500,
): Promise<NeedName[]> {
  const matched = new Set<NeedName>()
  const calls = Object.entries(needs).map(async ([name, description]) => {
    try {
      const answer = await classify(`Need: ${description}\n\nPrompt: ${prompt}`, ['match', 'no-match'])
      if (answer === 'match') matched.add(name)
    } catch {
      // A failing classifier call means no new need for this prompt.
    }
  })
  await Promise.race([Promise.all(calls), timeout(budgetMs)])
  return Object.keys(needs).filter((name) => matched.has(name))
}

/** Skills with `always`, plus skills whose `need` is active, in config order, then `extra` (skills a rule fired or saw loaded). */
export function neededSkills(config: Config, active: Record<NeedName, unknown>, extra: readonly SkillName[] = []): SkillName[] {
  const named = Object.entries(config.skills)
    .filter(([, rule]) => rule.always === true || (rule.need !== undefined && rule.need in active))
    .map(([name]) => name)
  return [...named, ...extra.filter((name) => !named.includes(name))]
}
