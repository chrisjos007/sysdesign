from django.core.management.base import BaseCommand
from django.db import transaction

from learn.curriculum import ENGINEERING_NOTES, TOPICS, curriculum_chapters
from learn.models import Book, Topic
from learn.seeding import seed_chapters


class Command(BaseCommand):
    help = ('Add or update every curriculum lesson and case study without deleting other content. '
            'seed_content does the same and also removes content that is no longer defined.')

    @transaction.atomic
    def handle(self, *args, **options):
        book, _ = Book.objects.update_or_create(slug=ENGINEERING_NOTES['slug'], defaults=ENGINEERING_NOTES)
        topics = {}
        for data in TOPICS:
            topics[data['slug']], _ = Topic.objects.update_or_create(slug=data['slug'], defaults=data)
        chapter_ids, _, question_count = seed_chapters(curriculum_chapters(), {book.slug: book}, topics)
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(chapter_ids)} curriculum lessons and case studies with {question_count} questions.'
        ))
