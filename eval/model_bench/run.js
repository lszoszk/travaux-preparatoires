export const meta = {
  name: 'model-bench',
  description: 'Put the fixed benchmark items (eval/model_bench/items.json) to each model and return their answers',
  phases: [{ title: 'Answer', detail: 'each model, four tasks, batches of items' }],
}
// args: { items: path of a COPY of items.json (the model must not be pointed at gold.json), models: ["opus", "sonnet", ...] }
const SPEAKER = { type: 'object', properties: { answers: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, speaker: { type: 'string', description: 'surname as printed, in capitals' }, delegation: { type: 'string', description: 'delegation as printed, country in full' } },
  required: ['id', 'speaker', 'delegation'] } } }, required: ['answers'] }
const VOTE = { type: 'object', properties: { answers: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, outcome: { type: 'string', enum: ['adopted', 'rejected', 'not_stated'] },
  yes: { type: ['integer', 'null'] }, no: { type: ['integer', 'null'] }, abstentions: { type: ['integer', 'null'] } },
  required: ['id', 'outcome', 'yes', 'no', 'abstentions'] } } }, required: ['answers'] }
const SPONSOR = { type: 'object', properties: { answers: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, proposers: { type: 'array', items: { type: 'string' }, description: 'delegations, as the passage names them, in full' } },
  required: ['id', 'proposers'] } } }, required: ['answers'] }
const TAG = { type: 'object', properties: { answers: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, about: { type: 'boolean' } }, required: ['id', 'about'] } } }, required: ['answers'] }

const TASKS = [
  { task: 'speaker', size: 10, schema: SPEAKER, prompt: (a, b) =>
    `Read ${args.items} (a JSON array). Take the items whose "task" is "speaker", numbered ${a} to ${b} among them (0-based, in file order). For each, open the page image (Read tool, field "image") and find the speech that opens with the words in "opening" (the opening words are OCR and may be garbled; the image decides). Give the speaker's surname as printed (capitals) and the delegation as printed (country in full). Use only that file and the images. Return one answer per item with its exact "id".` },
  { task: 'vote', size: 14, schema: VOTE, prompt: (a, b) =>
    `Read ${args.items} (a JSON array). Take the items whose "task" is "vote", numbered ${a} to ${b} among them (0-based, in file order). Each has a "passage" from a UN summary record (OCR, so figures may be garbled) and a "subject". Report the vote on that subject: outcome (adopted or rejected; not_stated if the passage does not say), and the numbers of votes in favour, against and abstentions (null where the passage does not give a number). The figures are given as "by X votes to Y": for an adopted proposal X is the number in favour and Y against; for a rejected one the larger side is against, so "rejected by 8 votes to 7" is 7 in favour and 8 against. Give the numbers of the vote on the subject named, not another vote in the passage. Use only that file. Return one answer per item with its exact "id".` },
  { task: 'sponsor', size: 10, schema: SPONSOR, prompt: (a, b) =>
    `Read ${args.items} (a JSON array). Take the items whose "task" is "sponsor", numbered ${a} to ${b} among them (0-based, in file order). Each has a "passage" from a UN summary record and a "document" symbol the passage refers to. Say which delegation or delegations proposed that document (amendment, draft, resolution) according to the passage, naming each delegation in full (e.g. "United Kingdom of Great Britain and Northern Ireland", "Union of Soviet Socialist Republics"). Use only that file. Return one answer per item with its exact "id".` },
  { task: 'tag', size: 20, schema: TAG, prompt: (a, b) =>
    `Read ${args.items} (a JSON array). Take the items whose "task" is "tag", numbered ${a} to ${b} among them (0-based, in file order). Each has a "passage" (a speech from a UN drafting record, OCR text) "context_before" (the heading or the chair's line that precedes it in the record, if any) and "tagged_as" (an article of the UDHR, ICCPR or ICESCR). Say whether the speech is about that article: about = true if its subject is the article's subject, false if it is about something else (another article, the order of work, the instrument as a whole). Use only that file. Return one answer per item with its exact "id".` },
]
const COUNTS = { speaker: 29, vote: 27, sponsor: 30, tag: 40 }

const jobs = []
for (const model of args.models) for (const t of TASKS) {
  for (let a = 0; a < COUNTS[t.task]; a += t.size) {
    const b = Math.min(a + t.size, COUNTS[t.task]) - 1
    jobs.push(() => agent(t.prompt(a, b), { label: `${model}:${t.task} ${a}`, phase: 'Answer', model, schema: t.schema })
      .then(r => ({ model, task: t.task, answers: r ? r.answers : null })))
  }
}
const out = (await parallel(jobs)).filter(Boolean)
const by = {}
for (const o of out) for (const x of (o.answers || [])) ((by[o.model] ||= {})[o.task] ||= []).push(x)
return by
