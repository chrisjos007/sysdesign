"""Checks for the rules in docs/learning/CONTENT_STANDARDS.md: no named
third-party study books in the product, quiz choices that don't give the
answer away by their length or wording, and one of three levels on every
piece of content."""
import hashlib
import json
import re
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .curriculum import DNS_TCP_TLS_CHAPTER, LEARNING_DIR, LEVEL_DIFFICULTY, LEVELS, TOPICS, STAGE_TOPICS
from .curriculum_questions import QUESTIONS
from .management.commands.seed_content import REFERENCE_CHAPTERS
from .management.commands.seed_games import BIT_BUDGET_CHALLENGES, FLAW_CHALLENGES, RING_CHALLENGES
from .models import (
    BitBudgetChallenge, Book, Chapter, Choice, Concept, DesignChallenge, FlawChallenge, FlawPart, FlawReason, MatchingPair,
    OrderingStep, Question, QuorumChallenge, RingChallenge, Topic, TrafficChallenge,
)

ROOT = Path(__file__).resolve().parent.parent

# Fingerprints of the titles, authors and publishers of the study books the
# earliest content drew on. Only hashes are kept, so the repository never
# names them: each is the first 16 hex digits of the SHA-256 of the name,
# lowercased, with apostrophes dropped and other punctuation turned into
# single spaces. To add one, hash the name the same way (see _normalize).
SOURCE_NAME_FINGERPRINTS = {
    '938da404df743c6d', 'edb8ea204b967002', '7bf9f45e3dadef84', '13cffaeb7469eed0',
    'f16d1129cb166289', 'cadea8258394072a', '4a2df29236566810', 'cf13fe2cff28343e',
    'fb4683e1bc592e05', '4e3dfdbdff3c2a20', '9846bb9be77686fc',
}
LONGEST_NAME_WORDS = 3

# Repository text a learner or a buyer of the product could read.
SCANNED_SUFFIXES = {'.md', '.py', '.html', '.js', '.json', '.css', '.toml', '.txt'}
SCANNED_PATHS = ['docs', 'learn', 'config', '.claude/agents', '.codex/agents', 'README.md', 'PRODUCT.md',
                 'DESIGN.md', 'CONTEXT.md', 'DEPLOYMENT.md', 'AGENTS.md']
SKIPPED_PARTS = {'__pycache__', 'node_modules'}

# Option-length rule: the longest choice may be at most this many times the
# shortest, unless the two are within SHORT_SLACK characters (short numeric
# answers such as "10" and "0.004").
MAX_LENGTH_RATIO = 1.5
SHORT_SLACK = 15
# The right answer can be the single longest choice now and then, but not as
# a habit: at most this share of single-answer questions.
MAX_SHARE_RIGHT_IS_LONGEST = 0.4


def _normalize(text):
    text = text.lower().replace('’', "'").replace("'", '')
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def _named_sources(text):
    """Fingerprints of the protected names that appear in `text`."""
    words = _normalize(text).split()
    found = set()
    for n in range(1, LONGEST_NAME_WORDS + 1):
        for i in range(len(words) - n + 1):
            digest = hashlib.sha256(' '.join(words[i:i + n]).encode()).hexdigest()[:16]
            if digest in SOURCE_NAME_FINGERPRINTS:
                found.add(digest)
    return found


def _scanned_files():
    for entry in SCANNED_PATHS:
        path = ROOT / entry
        files = [path] if path.is_file() else path.rglob('*') if path.is_dir() else []
        for f in files:
            if f.is_file() and f.suffix in SCANNED_SUFFIXES and not SKIPPED_PARTS & set(f.parts):
                yield f


def _balanced(lengths):
    shortest, longest = min(lengths), max(lengths)
    return longest <= max(shortest * MAX_LENGTH_RATIO, shortest + SHORT_SLACK)


def _all_question_banks():
    banks = dict(QUESTIONS)
    banks['sd-01'] = DNS_TCP_TLS_CHAPTER['concept']['questions']
    for chapter in REFERENCE_CHAPTERS:
        banks[chapter['concept']['slug']] = chapter['concept']['questions']
    return banks


class SourceNameTests(SimpleTestCase):
    def test_fingerprints_match_the_normalized_form(self):
        digest = hashlib.sha256(_normalize('Example   Book-Title’s').encode()).hexdigest()[:16]
        self.assertEqual(_normalize('Example   Book-Title’s'), 'example book titles')
        self.assertEqual(_named_sources('see Example Book-Title’s'), set())
        self.assertNotIn(digest, SOURCE_NAME_FINGERPRINTS)

    def test_repository_text_names_no_study_book(self):
        offenders = []
        for f in _scanned_files():
            if _named_sources(f.read_text(encoding='utf-8', errors='ignore')):
                offenders.append(str(f.relative_to(ROOT)))
        self.assertEqual(offenders, [])


class SeededTextNamesNoStudyBookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=StringIO())
        call_command('seed_games', stdout=StringIO())

    def test_seeded_text_names_no_study_book(self):
        for model in (Book, Topic, Chapter, Concept, Question, Choice, DesignChallenge, MatchingPair, OrderingStep,
                      FlawChallenge, FlawPart, FlawReason, TrafficChallenge, QuorumChallenge, RingChallenge,
                      BitBudgetChallenge):
            text = json.dumps(list(model.objects.values()), default=str, ensure_ascii=False)
            self.assertEqual(_named_sources(text), set(), model.__name__)


class QuizChoiceBalanceTests(SimpleTestCase):
    def test_choices_in_every_question_are_similar_in_length(self):
        for bank, questions in _all_question_banks().items():
            for q in questions:
                lengths = [len(text) for text, _ in q['choices']]
                self.assertTrue(_balanced(lengths), f'{bank}: {q["prompt"]} {lengths}')

    def test_right_answer_is_not_habitually_the_longest(self):
        single = longest = 0
        for questions in _all_question_banks().values():
            for q in questions:
                if q.get('kind', Question.MCQ) != Question.MCQ:
                    continue
                single += 1
                lengths = [len(text) for text, _ in q['choices']]
                right = next(len(text) for text, correct in q['choices'] if correct)
                longest += right == max(lengths) and lengths.count(right) == 1
        self.assertLessEqual(longest / single, MAX_SHARE_RIGHT_IS_LONGEST, f'{longest} of {single}')

    def test_yes_no_answers_are_not_given_away_by_polarity(self):
        # If the right answer opens with "Yes" or "No", a wrong answer must too.
        for bank, questions in _all_question_banks().items():
            for q in questions:
                if q.get('kind', Question.MCQ) != Question.MCQ:
                    continue
                right = next(text for text, correct in q['choices'] if correct)
                opener = re.match(r'(Yes|No)\b', right)
                if opener:
                    wrong = [text for text, correct in q['choices'] if not correct]
                    self.assertTrue(any(w.startswith(opener.group(1)) for w in wrong), f'{bank}: {q["prompt"]}')

    def test_game_choices_are_similar_in_length(self):
        for spec in FLAW_CHALLENGES:
            for part in spec['boxes'] + spec['arrows']:
                if 'flaw' in part:
                    self.assertTrue(_balanced([len(r) for r in part['flaw']]), part['key'])
        for spec in RING_CHALLENGES + BIT_BUDGET_CHALLENGES:
            for stage in spec['stages']:
                for question in stage.get('questions', []):
                    self.assertTrue(_balanced([len(o) for o in question['options']]), question['ask'])


class LevelTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.catalogue = json.loads((LEARNING_DIR / 'catalogue.json').read_text(encoding='utf-8'))

    def test_every_stage_and_item_has_one_of_three_levels(self):
        self.assertEqual(LEVELS, ('beginner', 'intermediate', 'advanced'))
        stage_levels = {s['id']: s['level'] for s in self.catalogue['stages']}
        self.assertTrue(set(stage_levels.values()) <= set(LEVELS))
        for item in self.catalogue['items']:
            self.assertIn(item['level'], LEVELS, item['id'])
            self.assertEqual(item['level'], stage_levels[item['stage']], item['id'])

    def test_levels_never_go_down_along_the_path(self):
        stage_order = {s['id']: s['order'] for s in self.catalogue['stages']}
        lessons = sorted((i for i in self.catalogue['items'] if i['type'] == 'lesson'),
                         key=lambda i: (stage_order[i['stage']], i['order']))
        ranks = [LEVEL_DIFFICULTY[i['level']] for i in lessons]
        self.assertEqual(ranks, sorted(ranks))

    def test_documents_state_their_level(self):
        for item in self.catalogue['items']:
            text = (LEARNING_DIR / item['path']).read_text(encoding='utf-8')
            self.assertIn(f"ID: {item['id']} | Level: {item['level'].capitalize()} |", text, item['id'])

    def test_stage_topics_are_titled_with_their_level(self):
        stage_levels = {s['id']: s['level'] for s in self.catalogue['stages']}
        titles = {t['slug']: t['title'] for t in TOPICS}
        for stage, topic in STAGE_TOPICS.items():
            self.assertTrue(titles[topic].startswith(stage_levels[stage].capitalize() + ':'), titles[topic])

    def test_reference_chapters_have_a_level(self):
        for chapter in REFERENCE_CHAPTERS:
            self.assertIn(chapter['difficulty'], LEVEL_DIFFICULTY.values(), chapter['slug'])
