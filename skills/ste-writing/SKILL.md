---
name: ste-writing
description: The public ASD-STE100 (Simplified Technical English) writing rules in actionable form. Use when writing echo artifact prose (intent, spec, plan, research), commit and PR text, review summaries, or Jira comments. Keeps echo prose short, clear, and consistent. Applies to prose only, never to code.
---

# ste-writing

Simplified Technical English (ASD-STE100) is a controlled-language standard for clear
technical prose. Apply these public writing rules so echo prose stays short, direct, and
consistent. This skill states the public rules only. It does not reproduce the proprietary
approved-word dictionary; get the dictionary and the full standard from
[asd-ste100.org](https://www.asd-ste100.org).

## Scope boundary (read first)
- Apply STE to prose only: the sentences a reader reads.
- Never rewrite code, file paths, commands, flags, ticket ids, identifiers, function names,
  or literal output. Keep these exact, even inside a sentence.
- Keep every echo policy token exact: the `TICKET: ` commit prefix, the `Ticket: <id>` body
  line, and the Co-Authored-By trailer. STE guides the prose around them, not the tokens.

## Words
- Use one word for one meaning. Do not give a word a second sense.
- Use a word in one part of speech only. Do not use a noun as a verb.
- Use the approved sense of a word; avoid synonyms. Say "start", not "initiate" or "begin".
- Use simple, specific words. Replace a long word with a short word that means the same.
- Keep technical names and technical verbs that the domain needs; they are allowed.
- Do not use a word that is not needed. Remove filler.

## Verbs
- Use the active voice. Name who does the action.
- Use the imperative for instructions ("Run the test").
- Use only the simple tenses: the present, the past, and the future. Avoid the progressive
  (-ing) form as the main verb.
- Do not drop a verb to make a sentence shorter. Every sentence needs a verb.
- Use the past participle as an adjective ("the approved plan"), not to build complex tenses.

## Sentences
- Keep an instruction sentence to 20 words or fewer.
- Keep a descriptive sentence to 25 words or fewer.
- Write one idea per sentence. Split a long sentence into two.
- Put the main idea first, then the detail.
- Use connecting words ("and", "then", "because") to show how ideas relate.
- Do not use a sentence that is only a heading dressed as prose.

## Procedures
- Write one instruction per sentence. Give one action per step.
- Start each step with the command verb.
- State two actions in one sentence only when the reader does them at the same time.
- Use a vertical list for a set of conditions or a set of parallel items.

## Warnings and cautions
- Put the warning or the caution before the step it applies to.
- Start with a clear, direct command that says what to do or what not to do.
- State the hazard and the result in plain words. Keep it short.

## Punctuation and spelling
- Use consistent, dictionary spelling throughout.
- Keep one topic per paragraph. Keep a paragraph to six sentences or fewer.
- Use the hyphen the same way every time.
- Do not use a slash ("/") to mean "and" or "or". Write the word.
- No em dashes. Use a period, a comma, or parentheses instead.

Load this skill from any echo flow that writes prose: the four artifact templates, the
ship and address-review commit and PR text, the review summary, and Jira comments.
