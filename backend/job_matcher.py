from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models import JobPosting, Candidate, Match
from vector_store import VectorStore
from openai import AsyncOpenAI
import json


class JobMatcher:
    def __init__(self, vector_store: VectorStore, openai_client: AsyncOpenAI):
        self.vector_store = vector_store
        self.openai_client = openai_client

    async def _analyze_match(self, job: JobPosting, candidate: Candidate) -> Dict:
        """Use LLM to analyze the match between a job and candidate"""
        try:
            prompt = f"""Analyze the match between this job posting and candidate:

Job Posting:
Title: {job.title}
Company: {job.company}
Description: {job.description}
Requirements: {job.requirements}
Location: {job.location}

Candidate:
Skills: {candidate.skills}
Experience: {candidate.experience}
Preferred Location: {candidate.preferred_location}
Resume: {candidate.resume_text}

Provide your analysis in the following JSON format:
{{
    "match_score": 0.0 to 1.0,
    "analysis": "Detailed explanation of the match...",
    "key_matches": ["List of key matching points"],
    "gaps": ["List of potential gaps or mismatches"]
}}"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert job matcher. Analyze the match between jobs and candidates.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"Error in match analysis: {str(e)}")
            return {
                "match_score": 0.0,
                "analysis": f"Error in analysis: {str(e)}",
                "key_matches": [],
                "gaps": [],
            }

    async def find_matching_candidates(
        self, job: JobPosting, db: Session, limit: int = 5
    ) -> List[Dict]:
        """Find and analyze matching candidates for a job posting"""
        # Get job embedding
        job_embedding = await self.vector_store._get_embedding(
            f"{job.title} {job.description} {job.requirements}"
        )

        # Search for candidates
        results = self.vector_store.collection.query(
            query_embeddings=[job_embedding],
            n_results=limit,
            where={"type": "candidate"},  # Filter for candidate embeddings
            include=["documents", "metadatas", "distances"],
        )

        matches = []
        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            candidate = (
                db.query(Candidate)
                .filter(Candidate.embedding_id == metadata["embedding_id"])
                .first()
            )
            if not candidate:
                continue

            # Calculate initial similarity score
            similarity_score = 1 - distance

            # Get detailed AI analysis
            analysis = await self._analyze_match(job, candidate)

            # Create or update match record
            match = (
                db.query(Match)
                .filter(
                    Match.job_id == job.id,
                    Match.candidate_id == candidate.id,
                )
                .first()
            )

            if not match:
                match = Match(
                    job_id=job.id,
                    candidate_id=candidate.id,
                    match_score=analysis["match_score"],
                    ai_analysis=json.dumps(analysis),
                )
                db.add(match)
            else:
                match.match_score = analysis["match_score"]
                match.ai_analysis = json.dumps(analysis)

            matches.append(
                {
                    "candidate": candidate,
                    "match_score": analysis["match_score"],
                    "ai_analysis": analysis["analysis"],
                    "key_matches": analysis["key_matches"],
                    "gaps": analysis["gaps"],
                }
            )

        db.commit()
        return sorted(matches, key=lambda x: x["match_score"], reverse=True)

    async def find_matching_jobs(
        self, candidate: Candidate, db: Session, limit: int = 5
    ) -> List[Dict]:
        """Find and analyze matching jobs for a candidate"""
        # Get candidate embedding
        candidate_embedding = await self.vector_store._get_embedding(
            f"{candidate.skills} {candidate.experience} {candidate.resume_text}"
        )

        # Search for jobs
        results = self.vector_store.collection.query(
            query_embeddings=[candidate_embedding],
            n_results=limit,
            where={"type": "job"},  # Filter for job embeddings
            include=["documents", "metadatas", "distances"],
        )

        matches = []
        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            job = (
                db.query(JobPosting)
                .filter(JobPosting.embedding_id == metadata["embedding_id"])
                .first()
            )
            if not job:
                continue

            # Calculate initial similarity score
            similarity_score = 1 - distance

            # Get detailed AI analysis
            analysis = await self._analyze_match(job, candidate)

            # Create or update match record
            match = (
                db.query(Match)
                .filter(
                    Match.job_id == job.id,
                    Match.candidate_id == candidate.id,
                )
                .first()
            )

            if not match:
                match = Match(
                    job_id=job.id,
                    candidate_id=candidate.id,
                    match_score=analysis["match_score"],
                    ai_analysis=json.dumps(analysis),
                )
                db.add(match)
            else:
                match.match_score = analysis["match_score"]
                match.ai_analysis = json.dumps(analysis)

            matches.append(
                {
                    "job": job,
                    "match_score": analysis["match_score"],
                    "ai_analysis": analysis["analysis"],
                    "key_matches": analysis["key_matches"],
                    "gaps": analysis["gaps"],
                }
            )

        db.commit()
        return sorted(matches, key=lambda x: x["match_score"], reverse=True)
