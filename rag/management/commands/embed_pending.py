"""Backfill embeddings for chunks that were ingested without vectors.

Usage:
    python manage.py embed_pending [--batch 64]

This is useful if documents were ingested while the embedder was unavailable.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from documents.models import Chunk
from rag.services.embedder import embed_texts


class Command(BaseCommand):
    help = "Compute embeddings for all chunks where is_embedded=False."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--batch", type=int, default=64, help="Batch size")

    def handle(self, *args, **options) -> None:
        batch_size = options["batch"]

        total = Chunk.objects.filter(is_embedded=False).count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("All chunks are already embedded. Nothing to do."))
            return

        self.stdout.write(f"Embedding {total} pending chunks (batch={batch_size}) ...")
        processed = 0

        while True:
            ids = list(
                Chunk.objects.filter(is_embedded=False)
                .order_by("id")
                .values_list("id", flat=True)[:batch_size]
            )
            if not ids:
                break

            chunks = list(Chunk.objects.filter(id__in=ids))
            vectors = embed_texts([c.text for c in chunks])

            for chunk, vector in zip(chunks, vectors, strict=False):
                chunk.vector = json.dumps(vector)
                chunk.is_embedded = True

            Chunk.objects.bulk_update(chunks, ["vector", "is_embedded"])
            processed += len(chunks)
            self.stdout.write(f"  ✓ {processed}/{total} embedded")

        self.stdout.write(self.style.SUCCESS(f"Done. Embedded {processed} chunks total."))
