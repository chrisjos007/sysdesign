"""Shared by the seed_content and seed_curriculum commands: writes chapter
dicts (the shape of seed_content.REFERENCE_CHAPTERS and of
curriculum.curriculum_chapters()) into Chapter, Concept, Question and Choice
rows."""
from .models import Chapter, Choice, Concept, Question


def sync_questions(concept, questions, difficulty=1):
    """Updates a concept's quiz bank in place, keyed by prompt, so re-seeding
    keeps question and choice rows and the attempts that point at them.
    Questions no longer listed are deleted, with their attempts."""
    keep = []
    for data in questions:
        question, _ = Question.objects.update_or_create(
            concept=concept, prompt=data['prompt'], defaults={
                'kind': data.get('kind', Question.MCQ), 'explanation': data.get('explanation', ''),
                'difficulty': data.get('difficulty', difficulty),
            },
        )
        keep.append(question.pk)
        for order, (text, correct) in enumerate(data['choices']):
            Choice.objects.update_or_create(
                question=question, order=order, defaults={'text': text, 'is_correct': correct},
            )
        question.choices.filter(order__gte=len(data['choices'])).delete()
    concept.questions.exclude(pk__in=keep).delete()
    return len(keep)


def seed_chapters(chapters, books, topics):
    """Creates or updates each chapter and its one concept. `books` and
    `topics` map slugs to saved rows. Returns the chapter ids, concept ids
    and number of questions written, so a caller can clean up the rest."""
    chapter_ids, concept_ids, question_count = set(), set(), 0
    for data in chapters:
        chapter, _ = Chapter.objects.update_or_create(
            book=books[data['book']], slug=data['slug'], defaults={
                'title': data['title'], 'order': data['order'], 'unlock_level': data['unlock_level'],
                'summary': data['summary'], 'topic': topics[data['topic']], 'difficulty': data['difficulty'],
            },
        )
        content = data['concept']
        concept, _ = Concept.objects.update_or_create(
            chapter=chapter, slug=content['slug'], defaults={
                'title': content['title'], 'order': 1, 'summary': content['summary'],
                'source_note': content['source_note'], 'notes_sections': content.get('notes', []),
                'curriculum': content.get('curriculum', {}),
            },
        )
        chapter_ids.add(chapter.id)
        concept_ids.add(concept.id)
        question_count += sync_questions(concept, content['questions'], data['difficulty'])
    return chapter_ids, concept_ids, question_count
