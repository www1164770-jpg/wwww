// The API is the source of truth for the question graph.  Keeping traversal
// helpers beside the UI makes the Vue page configuration-driven and testable.
export const QUESTIONNAIRE_VERSION = 3;

export function questionById(config, questionId) {
  return config?.questions?.[questionId] || null;
}

export function visibleQuestion(config, questionId, answers = {}) {
  const question = questionById(config, questionId);
  if (!question) return null;
  const optionsWhen = question.optionsWhen || {};
  let allowed = null;
  Object.entries(optionsWhen).forEach(([sourceId, conditions]) => {
    const selected = Array.isArray(answers[sourceId]) ? answers[sourceId] : [answers[sourceId]];
    const values = selected.flatMap((value) => conditions?.[value] || []);
    if (values.length) {
      const nextAllowed = new Set(values);
      allowed = allowed ? new Set([...allowed].filter((value) => nextAllowed.has(value))) : nextAllowed;
    }
  });
  if (!allowed) return question;
  return { ...question, options: question.options.filter((option) => allowed.has(option.value)) };
}

export function optionByValue(config, questionId, value) {
  return questionById(config, questionId)?.options?.find(
    (option) => option.value === value,
  );
}

export function nextQuestionId(config, questionId, value, answers = {}) {
  const question = questionById(config, questionId);
  const values = Array.isArray(value) ? value : [value];
  const nextWhen = question?.nextWhen || {};
  for (const [sourceId, choices] of Object.entries(nextWhen)) {
    const sourceValue = answers?.[sourceId];
    if (sourceValue && choices?.[sourceValue]) return choices[sourceValue];
  }
  const selected = question?.options?.find((option) => values.includes(option.value));
  if (selected?.next) return selected.next;
  return question?.next || "";
}

export function estimateRemainingQuestions(config, questionId, answers) {
  // The exact count only becomes known as choices are made. Give the user a
  // calm, useful estimate rather than implying every path has the same length.
  let currentId = questionId;
  let remaining = 0;
  const visited = new Set();
  while (currentId && !visited.has(currentId) && remaining < 8) {
    visited.add(currentId);
    remaining += 1;
    const selected = answers[currentId];
    if (!selected) return Math.max(remaining + 3, 1);
    const next = nextQuestionId(config, currentId, selected, answers);
    if (!next) break;
    currentId = next;
  }
  return Math.max(remaining, 1);
}
