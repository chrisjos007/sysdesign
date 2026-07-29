"""Turns an admin's free-text scenario into a gradeable Python coding
challenge (title, prompt, starter code, stdin/stdout test cases) using the
Gemini API — or, if the scenario doesn't have enough in it to generate a
well-defined question, asks the admin clarifying questions instead of
guessing.

Uses a single structured-output call whose JSON schema is a discriminated
union (`status`: "needs_clarification" | "ready") so the model itself does
double duty as the completeness check and the generator. See
`docs/coding_challenges.md`-style notes in CONTEXT.md for the full design
rationale (why Gemini REST + why stdin/stdout grading).
"""
import json
import os

import requests

GEMINI_API_URL_TMPL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
DEFAULT_MODEL = 'gemini-3.6-flash'

# A discriminated union: the model must return either a NeedsClarification
# object or a Ready object, chosen via `anyOf` (same pattern Google's own
# docs use for conditional/classification schemas).
RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'result': {
            'anyOf': [
                {
                    'type': 'object',
                    'title': 'NeedsClarification',
                    'description': 'The scenario does not yet have enough information to generate a well-defined, gradeable coding question.',
                    'properties': {
                        'status': {'type': 'string', 'enum': ['needs_clarification']},
                        'missing_items': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': "Short labels for what's missing, e.g. 'input format', 'expected output', 'worked example', 'edge cases'.",
                        },
                        'clarifying_questions': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': '1-5 short, specific questions to ask the admin so the scenario can be turned into a testable question.',
                        },
                    },
                    'required': ['status', 'missing_items', 'clarifying_questions'],
                },
                {
                    'type': 'object',
                    'title': 'Ready',
                    'description': 'The scenario has enough information; here is the generated coding challenge.',
                    'properties': {
                        'status': {'type': 'string', 'enum': ['ready']},
                        'title': {'type': 'string', 'description': "Short challenge title, e.g. 'Rate Limiter: Token Bucket'."},
                        'prompt': {
                            'type': 'string',
                            'description': (
                                'Full problem statement shown to the learner, written as GitHub-Flavored '
                                'Markdown: use "## " headers for sections (e.g. Task, Input Format, Output '
                                'Format, Example), fenced ``` code blocks for literal example stdin/stdout, '
                                '`backtick spans` for inline literals/types, **bold** for emphasis, and '
                                'bullet/numbered lists where helpful. Must still cover the task, the exact '
                                'stdin input format, the exact stdout output format, and at least one worked '
                                'example — the Markdown is a formatting layer on top of that same content, '
                                'not a replacement for it.'
                            ),
                        },
                        'constraints': {'type': 'string', 'description': 'Constraints and edge cases, plain text.'},
                        'starter_code': {
                            'type': 'string',
                            'description': 'A short Python 3 starter stub (comments + a skeleton reading from stdin and printing to stdout) — not a working solution.',
                        },
                        'difficulty': {'type': 'integer', 'minimum': 1, 'maximum': 5},
                        'test_cases': {
                            'type': 'array',
                            'minItems': 4,
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'stdin': {'type': 'string'},
                                    'expected_output': {'type': 'string'},
                                    'is_sample': {
                                        'type': 'boolean',
                                        'description': 'True for the 1-2 example cases shown to the learner up front; false for cases that stay hidden and count only toward grading.',
                                    },
                                },
                                'required': ['stdin', 'expected_output', 'is_sample'],
                            },
                        },
                    },
                    'required': ['status', 'title', 'prompt', 'constraints', 'starter_code', 'difficulty', 'test_cases'],
                },
            ],
        },
    },
    'required': ['result'],
}


class LLMError(RuntimeError):
    """Raised for anything that stops us from getting a usable structured
    response back — missing API key, network failure, non-200, or a
    response that doesn't parse as the expected JSON shape."""


def _build_prompt(scenario_text, concept, difficulty_hint):
    concept_line = f'"{concept.title}" — {concept.summary}' if concept else '(no specific concept selected — treat this as a general system-design/algorithms exercise)'
    difficulty_line = f'Suggested difficulty (1=easy .. 5=hard): {difficulty_hint}' if difficulty_hint else ''
    return f"""You are helping an instructor turn a short scenario description into a Python 3 coding exercise for a gamified system-design interview-prep app. Learners submit a full Python program; it is graded by feeding each test case's text to stdin and comparing stdout, trimmed, to the expected output.

This exercise will be attached to this existing concept in the app: {concept_line}
Prefer connecting the exercise to the system-design/system-logic idea behind that concept (an algorithm, data structure, or component behind it — e.g. rate limiting, consistent hashing, an LRU cache, leader election, a scaled-down piece of a real system) rather than a generic textbook problem, UNLESS the admin's scenario clearly asks for something more general — either is fine as long as it ends up a well-specified, gradeable programming exercise.

Admin's scenario / instructions:
\"\"\"{scenario_text}\"\"\"
{difficulty_line}

Step 1 — decide if the scenario has ENOUGH information to generate a well-defined, testable question. It needs, at minimum:
1. A clear task: what the learner's program must actually do.
2. A concrete input format (what exactly is fed via stdin) and output format (what exactly must be printed to stdout).
3. Enough detail to derive at least 4 correct, unambiguous test cases (stdin -> expected stdout), including at least one edge case.

If any of that is missing, too vague, or would force you to invent a load-bearing design decision the admin didn't specify (e.g. an unstated algorithm choice that changes the expected output), respond with status "needs_clarification" and ask 1-5 short, specific questions. Do not silently guess at requirements that would change what counts as a correct answer.

Step 2 — if it IS enough (even if the admin was terse — infer standard, unambiguous conventions where that's genuinely safe, e.g. reading whitespace-separated integers), respond with status "ready" and produce:
- title: short and specific.
- prompt: the full problem statement — task, exact input format, exact output format, and at least one fully worked example — written so a learner could implement it with no other context. Format it as GitHub-Flavored Markdown: "## " headers to separate sections (Task / Input Format / Output Format / Example), fenced ``` code blocks for literal example stdin/stdout, `backtick spans` for inline literals/types, **bold** for emphasis, lists where helpful. This is a formatting requirement on top of the content requirements above, not instead of them.
- constraints: edge cases and limits.
- starter_code: a short Python 3 stub (comments + I/O skeleton only, not a solution).
- difficulty: 1-5.
- test_cases: at least 4 stdin/expected_output pairs, covering the worked example plus edge cases. Mark 1-2 as is_sample=true (shown to the learner up front); the rest stay hidden for grading. Every expected_output must be EXACTLY what a correct Python 3 program would print (compared after trimming trailing whitespace/newlines), and must be internally consistent with the prompt and with every other test case."""


def generate_coding_challenge(scenario_text, concept=None, difficulty_hint=None, timeout=60):
    """Returns a dict: either
      {"status": "needs_clarification", "missing_items": [...], "clarifying_questions": [...]}
    or
      {"status": "ready", "title": ..., "prompt": ..., "constraints": ..., "starter_code": ...,
       "difficulty": int, "test_cases": [{"stdin", "expected_output", "is_sample"}, ...]}
    Raises LLMError if the API can't be reached or its response can't be used.
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise LLMError(
            "GEMINI_API_KEY isn't set. Get a free key at https://aistudio.google.com/apikey, "
            "add it to .env as GEMINI_API_KEY=..., and restart the app."
        )
    model = os.environ.get('GEMINI_MODEL', DEFAULT_MODEL)
    url = GEMINI_API_URL_TMPL.format(model=model)

    payload = {
        'contents': [{'parts': [{'text': _build_prompt(scenario_text, concept, difficulty_hint)}]}],
        'generationConfig': {
            'responseMimeType': 'application/json',
            'responseSchema': RESPONSE_SCHEMA,
        },
    }

    try:
        resp = requests.post(url, params={'key': api_key}, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise LLMError(f"Couldn't reach the Gemini API: {exc}") from exc

    if resp.status_code != 200:
        raise LLMError(f'Gemini API error ({resp.status_code}): {resp.text[:800]}')

    try:
        data = resp.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        parsed = json.loads(text)['result']
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise LLMError(f"Couldn't parse Gemini's response as the expected JSON shape: {exc}") from exc

    if parsed.get('status') not in ('needs_clarification', 'ready'):
        raise LLMError(f"Gemini returned an unexpected status: {parsed.get('status')!r}")

    return parsed
