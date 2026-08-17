"""
workers/orchestrator.py

WorkflowOrchestrator v3.0 — Subscribes to EmbeddingGenerated ONLY.

Ordering guarantee: Persist -> Embed -> [THIS] -> Rank -> Route.
Never processes synthetic/hardcoded job data.
Never emits ApplicationSubmitted before Playwright evidence (Phase 5+).
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

from ai.memory.service import MemoryService
from automation.confidence import ConfidenceEngine, ApplicationDecision
from automation.notification import TelegramNotifier
from core.config.profile_loader import load_candidate_profile
from core.events.bus import InMemoryEventBus
from core.events.definitions import (
    EmbeddingGenerated,
    HumanApprovalRequested,
    JobDiscovered,    # kept for unit-test backward compat only
    JobRanked,
)
from core.models.candidate_profile import CandidateProfile
from intelligence.friction.scorer import FrictionScorer
from intelligence.ranking.eligibility import EligibilityGate
from intelligence.ranking.ranker import RankingAgent, RankingResult


class WorkflowOrchestrator:
    """
    Production handler: subscribes to EmbeddingGenerated.
    At that point: job exists in DB, embedding exists (or is empty -> fallback).
    Ordering is deterministic.
    """

    def __init__(
        self,
        event_bus: Optional[InMemoryEventBus] = None,
        profile: Optional[CandidateProfile] = None,
        memory: Optional[MemoryService] = None,
        notifier: Optional[TelegramNotifier] = None,
        job_repo=None,
        queue_repo=None,
        app_repo=None,
        sheets_sync_service=None,    # GoogleSheetsSyncService -- wired in Phase 3
        semantic_scorer=None,        # SemanticScorer -- wired in Phase 7
        ranking_agent: Optional[RankingAgent] = None,
    ):
        self.bus = event_bus or InMemoryEventBus()
        self.profile = profile or load_candidate_profile()
        self.memory = memory or MemoryService()
        self.notifier = notifier or TelegramNotifier()
        self.job_repo = job_repo
        self.queue_repo = queue_repo
        self.app_repo = app_repo
        self.sheets_sync_service = sheets_sync_service   # None until Phase 3 wires it
        self.semantic_scorer = semantic_scorer

        self.eligibility_gate = EligibilityGate(self.profile)
        self.ranker = ranking_agent or RankingAgent(self.profile, semantic_scorer=self.semantic_scorer)
        self.confidence_engine = ConfidenceEngine()
        self.friction_scorer = FrictionScorer()

        # PRODUCTION: subscribe to EmbeddingGenerated
        self.bus.subscribe("EmbeddingGenerated", self.handle_embedding_generated)

        # UNIT TEST COMPAT ONLY: keep JobDiscovered subscription for tests that
        # don't wire EmbeddingWorker. DO NOT add logic here.
        self.bus.subscribe("JobDiscovered", self._handle_job_discovered_test_only)

    # -- Production Handler ---------------------------------------------------

    async def handle_embedding_generated(self, event: EmbeddingGenerated) -> list[RankingResult]:
        """Main production handler. Job and embedding both exist at this point."""
        results: list[RankingResult] = []

        if event.entity_type != "job":
            return results

        if self.job_repo is None:
            raise RuntimeError(
                "WorkflowOrchestrator.handle_embedding_generated called without job_repo. "
                "Pass job_repo= when constructing WorkflowOrchestrator in production."
            )

        # 1. Fetch REAL job from DB
        job = await self.job_repo.get_by_id(event.entity_id)
        if not job:
            return results

        # 2. Idempotency guard -- skip if already routed for this job
        if self.app_repo:
            existing = await self.app_repo.get_by_user_and_job(
                user_id="user_default", job_id=job.id
            )
            if existing:
                return results

        # 3. Eligibility gate
        eligibility = self.eligibility_gate.check(job)
        if not eligibility.eligible:
            return results

        # 4. Friction scoring
        ats_name = str(job.source) if job.source else "unknown"
        friction_result = self.friction_scorer.score(ats_name=ats_name)

        # 5. Rank -- pass embedding_id from the event (may be "" -> semantic fallback)
        ranking = self.ranker.rank(job, embedding_id=event.embedding_id)
        results.append(ranking)

        # 6. Emit JobRanked
        await self.bus.publish(JobRanked(
            job_id=job.id, user_id="user_default", fit_score=ranking.overall_score
        ))

        # 7. Route
        decision = self.confidence_engine.decide(
            ranking, form_complexity=friction_result.score
        )

        if decision == ApplicationDecision.AUTO_APPLY:
            await self._route_auto_apply(job, ranking, friction_result)
        elif decision == ApplicationDecision.ASK_USER:
            await self._route_human_queue(job, ranking, friction_result)
        else:
            await self.notifier.send_message(
                f"<b>Review Required</b>\n"
                f"<b>Job:</b> {job.title} @ {job.company}\n"
                f"<b>Fit:</b> {int(ranking.overall_score * 100)}% (below threshold)"
            )

        return results

    async def _route_auto_apply(self, job, ranking, friction_result) -> None:
        """
        Create ApplicationORM(AUTOMATION_QUEUED). Do NOT emit ApplicationSubmitted.
        Playwright (Phase 5) runs the form, verifies evidence, then updates status
        and emits ApplicationSubmitted.
        """
        from core.models.application import Application, ApplicationStatus

        application = Application(
            user_id="user_default",
            job_id=job.id,
            status=ApplicationStatus.AUTOMATION_QUEUED,
            fit_rating=ranking.overall_score,
            source_channel="auto_apply",
        )
        if self.app_repo:
            application = await self.app_repo.create(application)

        await self.notifier.send_message(
            f"<b>Automation Queued</b>\n"
            f"<b>Job:</b> {job.title} @ {job.company}\n"
            f"<b>Fit:</b> {int(ranking.overall_score * 100)}%\n"
            f"Playwright will attempt this application."
        )

    async def _route_human_queue(self, job, ranking, friction_result) -> None:
        """
        Order of operations -- DB portion is ONE ATOMIC TRANSACTION (Invariant #9):

          -- BEGIN TRANSACTION (explicit async with session.begin()) ----------
          1. Create ApplicationORM(PENDING_MANUAL) -- FIRST
          2. Create HumanQueueORM referencing application.id -- application_id is NEVER None
          -- COMMIT (context manager exit) ------------------------------------

          Post-commit (failures here never roll back the DB):
          3. Telegram inline keyboard
          4. set_telegram_pending_id() -- metadata, no state change
          5. Generate signed token for Sheet link
          6. GoogleSheetsSyncService.sync_entry() -- best-effort, non-blocking
          7. mark_sheets_synced(entry.id) -- ONLY after successful sync
        """
        from core.models.application import Application, ApplicationStatus
        from core.models.human_queue import HumanQueueEntry

        user_id = "user_default"

        # -- ATOMIC DB TRANSACTION --------------------------------------------
        application = None
        entry = None

        if self.app_repo and self.queue_repo:
            session = getattr(self.app_repo, "session", None)
            if session is not None and session.in_transaction():
                # Session transaction is already open (e.g. from prior SELECT query)
                application_model = Application(
                    user_id=user_id,
                    job_id=job.id,
                    status=ApplicationStatus.PENDING_MANUAL,
                    fit_rating=ranking.overall_score,
                    source_channel="human_queue",
                )
                application = await self.app_repo.create_within_transaction(application_model)

                entry_model = HumanQueueEntry(
                    user_id=user_id,
                    job_id=job.id,
                    application_id=application.id,   # NEVER None (Invariant #6)
                    fit_score=ranking.overall_score,
                    confidence_score=ranking.confidence,
                    friction_score=friction_result.score,
                    routing_reason=(
                        f"Fit {int(ranking.overall_score * 100)}%, "
                        f"Friction: {friction_result.label}"
                    ),
                    application_url=getattr(job, "apply_url", None) or job.source_url,
                    matching_skills=[],
                    missing_skills=ranking.missing_skills[:5],
                )
                entry = await self.queue_repo.enqueue_within_transaction(entry_model)
                await session.commit()
            elif session is not None:
                async with session.begin():
                    application_model = Application(
                        user_id=user_id,
                        job_id=job.id,
                        status=ApplicationStatus.PENDING_MANUAL,
                        fit_rating=ranking.overall_score,
                        source_channel="human_queue",
                    )
                    application = await self.app_repo.create_within_transaction(application_model)

                    entry_model = HumanQueueEntry(
                        user_id=user_id,
                        job_id=job.id,
                        application_id=application.id,   # NEVER None (Invariant #6)
                        fit_score=ranking.overall_score,
                        confidence_score=ranking.confidence,
                        friction_score=friction_result.score,
                        routing_reason=(
                            f"Fit {int(ranking.overall_score * 100)}%, "
                            f"Friction: {friction_result.label}"
                        ),
                        application_url=getattr(job, "apply_url", None) or job.source_url,
                        matching_skills=[],
                        missing_skills=ranking.missing_skills[:5],
                    )
                    entry = await self.queue_repo.enqueue_within_transaction(entry_model)
            # -- COMMIT happened here -------
        else:
            # Repos not wired (unit test mode) -- use in-memory domain objects
            application_model = Application(
                user_id=user_id, job_id=job.id,
                status=ApplicationStatus.PENDING_MANUAL,
                fit_rating=ranking.overall_score, source_channel="human_queue",
            )
            application = application_model
            from core.models.human_queue import HumanQueueEntry
            entry = HumanQueueEntry(
                user_id=user_id, job_id=job.id,
                application_id=application.id,
                fit_score=ranking.overall_score, confidence_score=ranking.confidence,
                friction_score=friction_result.score,
                routing_reason=f"Fit {int(ranking.overall_score * 100)}%",
                application_url=getattr(job, "apply_url", None) or job.source_url,
                matching_skills=[], missing_skills=ranking.missing_skills[:5],
            )
        # -- END ATOMIC DB SECTION --------------------------------------------

        # Step 3: Telegram -- post-commit. Failure here does NOT roll back the DB.
        pending = await self.notifier.send_approval_request(job, ranking, entry_id=entry.id)

        # Step 4: Metadata update -- no state transition
        if self.queue_repo and pending and pending.id:
            await self.queue_repo.set_telegram_pending_id(entry.id, pending.id)
            if hasattr(self.queue_repo, "session") and self.queue_repo.session:
                await self.queue_repo.session.commit()

        # Step 5: Signed token for Sheet "Mark Applied" link (Phase 2+)
        try:
            from backend.src.services.action_token_service import ActionTokenService
            token_service = ActionTokenService()
            mark_applied_token = token_service.create_mark_applied_token(
                application_id=application.id,
                user_id=user_id,
            )
        except ModuleNotFoundError:
            # ActionTokenService not yet implemented (Phase 0/1). Skip token generation.
            mark_applied_token = ""

        base_url = os.getenv("HELIOS_BASE_URL", "https://helios.vinaykhosya.com")

        # Step 6: Google Sheets sync -- non-blocking best-effort (Invariant #4)
        if self.sheets_sync_service:
            try:
                synced = await asyncio.to_thread(
                    self.sheets_sync_service.sync_entry,
                    entry, job, mark_applied_token, base_url,
                )
                # Step 7: mark synced ONLY if sync succeeded
                if synced and self.queue_repo:
                    await self.queue_repo.mark_sheets_synced(entry.id)
                    if hasattr(self.queue_repo, "session") and self.queue_repo.session:
                        await self.queue_repo.session.commit()
            except Exception as e:
                print(f"[GoogleSheets] sync_entry failed for {entry.id}: {e}")
        else:
            print(
                f"[HumanQueue] {job.title} @ {job.company} "
                f"| app={application.id[:8]} "
                f"| mark_applied_url={base_url}/mark-applied/{mark_applied_token}"
            )

        # Emit event
        await self.bus.publish(HumanApprovalRequested(
            pending_id=pending.id,
            job_id=job.id,
            user_id=user_id,
            pause_reason="ASK_USER_CONFIDENCE",
            confidence_score=ranking.confidence,
        ))

    # -- Unit Test Backward Compat --------------------------------------------

    async def _handle_job_discovered_test_only(self, event: JobDiscovered) -> list[RankingResult]:
        """
        Legacy handler for unit tests that publish JobDiscovered directly.
        Contains ZERO business logic. Only exists to prevent KeyError in tests
        that subscribed to JobDiscovered before this refactor.
        DO NOT ADD LOGIC HERE.
        """
        import warnings
        warnings.warn(
            "_handle_job_discovered_test_only fired. "
            "Update your test to publish EmbeddingGenerated instead.",
            stacklevel=2,
        )
        return []
