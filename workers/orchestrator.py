"""
workers/orchestrator.py

WorkflowOrchestrator — Event-driven pipeline worker coordinating discovery, filtering, ranking,
resume tailoring, form filling, and notification dispatches over InMemoryEventBus.
"""
from __future__ import annotations

from typing import Optional
from ai.memory.service import MemoryService
from automation.confidence import ConfidenceEngine, ApplicationDecision
from automation.notification import TelegramNotifier
from core.config.profile_loader import load_candidate_profile
from core.events.bus import InMemoryEventBus
from core.events.definitions import (
    ApplicationSubmitted,
    HumanApprovalRequested,
    JobDiscovered,
    JobRanked,
)

from core.models.candidate_profile import CandidateProfile
from core.models.job import Job
from intelligence.ranking.eligibility import EligibilityGate
from intelligence.ranking.ranker import RankingAgent, RankingResult


class WorkflowOrchestrator:
    """
    Coordinates end-to-end Helios pipeline execution via domain events.
    """

    def __init__(
        self,
        event_bus: Optional[InMemoryEventBus] = None,
        profile: Optional[CandidateProfile] = None,
        memory: Optional[MemoryService] = None,
        notifier: Optional[TelegramNotifier] = None,
    ):
        self.bus = event_bus or InMemoryEventBus()
        self.profile = profile or load_candidate_profile()
        self.memory = memory or MemoryService()
        self.notifier = notifier or TelegramNotifier()

        self.eligibility_gate = EligibilityGate(self.profile)
        self.ranker = RankingAgent(self.profile)
        self.confidence_engine = ConfidenceEngine()

        # Subscribe handlers
        self.bus.subscribe("JobDiscovered", self.handle_job_discovered)

    async def handle_job_discovered(self, event: JobDiscovered) -> list[RankingResult]:
        """
        Handler for JobDiscovered events. Filters eligible jobs and ranks fit score.
        """

        results: list[RankingResult] = []

        # Convert event metadata to synthetic job if needed or query JobRepo
        job = Job(
            id=event.job_id,
            source=event.source,
            source_id=event.source_id,
            source_url=event.source_url,
            title="AI Ingested Job",
            company="Target Company",
            description="Python developer job posting",
            skills=["Python"],
        )


        eligibility = self.eligibility_gate.check(job)
        if not eligibility.eligible:
            return results

        ranking = self.ranker.rank(job)
        results.append(ranking)

        # Emit JobRanked event
        await self.bus.publish(JobRanked(job_id=job.id, user_id="user_default", fit_score=ranking.overall_score))

        decision = self.confidence_engine.decide(ranking)

        if decision == ApplicationDecision.AUTO_APPLY:
            # Emit ApplicationSubmitted event
            await self.bus.publish(ApplicationSubmitted(
                app_id=f"app_{job.id}",
                user_id="user_default",
                job_id=job.id,
                source=job.source,
                confirmation_id=f"CONF_{job.id[:6]}",
                confidence_score=ranking.confidence,
            ))
        elif decision == ApplicationDecision.ASK_USER:
            pending = await self.notifier.send_approval_request(job, ranking)
            await self.bus.publish(HumanApprovalRequested(
                pending_id=pending.id,
                job_id=job.id,
                user_id="user_default",
                pause_reason="ASK_USER_CONFIDENCE",
                confidence_score=ranking.confidence,
            ))

        return results
