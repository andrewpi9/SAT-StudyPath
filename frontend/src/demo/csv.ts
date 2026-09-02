/** CSV attempt parsing, ported from backend/app/services/bulk_import.py. */

import type { Difficulty } from '../api/types'
import type { DemoTopic } from './store'

const TRUE_VALUES = new Set(['true', 't', '1', 'yes', 'y', 'correct', 'c', 'right'])
const FALSE_VALUES = new Set(['false', 'f', '0', 'no', 'n', 'incorrect', 'i', 'wrong'])
const DIFFICULTIES: Difficulty[] = ['easy', 'medium', 'hard']

const ALIASES: Record<string, string> = {
  topic: 'topic',
  skill: 'topic',
  skill_name: 'topic',
  topic_id: 'topic_id',
  correct: 'correct',
  outcome: 'correct',
  result: 'correct',
  time_taken_seconds: 'time',
  time: 'time',
  seconds: 'time',
  difficulty: 'difficulty',
  days_ago: 'days_ago',
}

export const CSV_TEMPLATE =
  'topic,correct,time_taken_seconds,difficulty,days_ago\n' +
  'Linear functions,true,55,medium,2\n' +
  'Percentages,false,90,hard,2\n' +
  'Words in context,correct,40,easy,0\n'

export interface ParsedRow {
  topic_id: number
  correct: boolean
  difficulty: Difficulty
}

export interface ParseError {
  row: number
  message: string
}

function splitLine(line: string): string[] {
  return line.split(',').map((cell) => cell.trim())
}

export function parseCsv(
  text: string,
  topics: DemoTopic[],
): { rows: ParsedRow[]; errors: ParseError[] } {
  const lines = text.replace(/\r\n?/g, '\n').split('\n').filter((l) => l.trim().length > 0)
  const rows: ParsedRow[] = []
  const errors: ParseError[] = []
  if (lines.length === 0) return { rows, errors: [{ row: 0, message: 'The file appears to be empty.' }] }

  const header = splitLine(lines[0]).map((h) => ALIASES[h.toLowerCase()] ?? h.toLowerCase())
  const byName = new Map(topics.map((t) => [t.skill_name.toLowerCase(), t]))
  const byId = new Map(topics.map((t) => [t.id, t]))

  for (let i = 1; i < lines.length; i += 1) {
    const cells = splitLine(lines[i])
    const get = (key: string) => {
      const idx = header.indexOf(key)
      return idx >= 0 ? (cells[idx] ?? '') : ''
    }
    const lineNo = i + 1

    const topicRef = get('topic') || get('topic_id')
    if (!topicRef) {
      errors.push({ row: lineNo, message: "Missing 'topic'." })
      continue
    }
    let topic = byName.get(topicRef.toLowerCase())
    if (!topic && /^\d+$/.test(topicRef)) topic = byId.get(Number(topicRef))
    if (!topic) {
      errors.push({ row: lineNo, message: `Unknown topic '${topicRef}'.` })
      continue
    }

    const rawCorrect = get('correct').toLowerCase()
    let correct: boolean
    if (TRUE_VALUES.has(rawCorrect)) correct = true
    else if (FALSE_VALUES.has(rawCorrect)) correct = false
    else {
      errors.push({ row: lineNo, message: `'correct' must be true/false, got '${get('correct')}'.` })
      continue
    }

    const rawDifficulty = (get('difficulty') || 'medium').toLowerCase()
    if (!DIFFICULTIES.includes(rawDifficulty as Difficulty)) {
      errors.push({ row: lineNo, message: `'difficulty' must be easy/medium/hard, got '${rawDifficulty}'.` })
      continue
    }

    rows.push({ topic_id: topic.id, correct, difficulty: rawDifficulty as Difficulty })
  }

  return { rows, errors }
}
