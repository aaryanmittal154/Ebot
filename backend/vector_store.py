import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional, Tuple
import uuid
from config import Settings
from models import Email
from sqlalchemy.orm import Session
import numpy as np
from openai import AsyncOpenAI
import json


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        # Initialize ChromaDB with new client format
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)

        # Initialize OpenAI with new client
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Get or create collection with correct dimensionality
        try:
            self.collection = self.client.get_collection("email_embeddings")
        except:
            # Create new collection if it doesn't exist
            self.collection = self.client.create_collection(
                name="email_embeddings",
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better embedding quality"""
        # Remove excessive whitespace
        text = " ".join(text.split())
        return text

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API"""
        text = self._preprocess_text(text)
        response = await self.openai_client.embeddings.create(
            model="text-embedding-3-small", input=text, encoding_format="float"
        )
        return response.data[0].embedding

    async def add_text(self, text: str, metadata: Dict) -> str:
        """Add text to vector store and return embedding ID"""
        embedding_id = str(uuid.uuid4())

        # Get embedding from OpenAI
        embedding = await self._get_embedding(text)

        # Add to ChromaDB
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[embedding_id],
        )

        return embedding_id

    async def _validate_with_llm(
        self, original_email: Dict, similar_emails: List[Dict]
    ) -> Tuple[List[Dict], bool]:
        """Use LLM to validate and rank similar emails"""
        try:
            print("\n" + "=" * 80)
            print("LLM Analysis Request")
            print("=" * 80)
            print("\nOriginal Email:")
            print(f"Subject: {original_email.get('subject', 'No Subject')}")
            print(f"Content: {original_email.get('content', 'No Content')[:200]}...")

            print("\nSimilar Emails:")
            for idx, email in enumerate(similar_emails[:3]):
                print(f"\n{idx + 1}. Subject: {email['subject']}")
                print(f"   Score: {email['similarity_score']:.2f}")
                print(f"   Content: {email['content'][:200]}...")

            prompt = f"""You are an expert email similarity analyzer. Analyze the following emails and determine their relevance and similarity.

Original Email:
Subject: {original_email.get('subject', 'No Subject')}
Content: {original_email.get('content', 'No Content')}

Similar Emails (up to 3):
{json.dumps([{
    'subject': email['subject'],
    'content': email['content'],
    'similarity_score': email['similarity_score']
} for email in similar_emails[:3]], indent=2)}

Task:
1. Analyze if any of the similar emails are truly relevant to the original email
2. Provide a detailed analysis of why they are or aren't relevant
3. Determine if the most similar email is relevant enough to be shown as a match

Provide your analysis in the following JSON format:
{{
    "show_best_match": true,
    "overall_analysis": "Detailed explanation of the similarity analysis..."
}}

Important: Your response must be valid JSON."""

            print("\nSending request to LLM...")
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert email similarity analyzer. Always respond with valid JSON containing show_best_match and overall_analysis.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            print("\nLLM Response:")
            print("-" * 80)
            print(json.dumps(json.loads(content), indent=2))
            print("-" * 80)

            try:
                analysis = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"\nError parsing LLM response: {str(e)}")
                print(f"Raw content: {content}")
                raise

            if "show_best_match" not in analysis or "overall_analysis" not in analysis:
                print("\nWarning: Missing required fields in LLM response")
                if "show_best_match" not in analysis:
                    analysis["show_best_match"] = True
                if "overall_analysis" not in analysis:
                    analysis["overall_analysis"] = "Analysis not available"

            similar_emails.sort(key=lambda x: x["similarity_score"], reverse=True)

            # Add LLM analysis to all similar emails
            for email in similar_emails:
                email["llm_explanation"] = analysis["overall_analysis"]

            print("\nAnalysis complete!")
            print("=" * 80 + "\n")
            return similar_emails, analysis["show_best_match"]

        except Exception as e:
            print(f"\nError in LLM analysis: {str(e)}")
            for email in similar_emails:
                email["llm_explanation"] = f"Error in LLM analysis: {str(e)}"
            return similar_emails, True

    async def find_similar_emails(
        self,
        query_text: str,
        db: Session,
        n_results: int = 5,
        current_thread_id: Optional[str] = None,
        original_email: Optional[Dict] = None,
    ) -> Dict:
        """Find similar emails using advanced vector similarity search with LLM validation"""
        # Initialize variables
        similar_emails = []
        best_match = None
        max_similarity = 0.0
        show_best_match = False  # Initialize show_best_match

        # Preprocess query
        processed_query = self._preprocess_text(query_text)
        query_embedding = await self._get_embedding(processed_query)

        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results + 1,
            include=["documents", "metadatas", "distances"],
        )

        if results["documents"]:
            for i, (doc, metadata, distance) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                if current_thread_id and metadata["thread_id"] == current_thread_id:
                    continue

                similarity_score = 1 - distance

                email = (
                    db.query(Email)
                    .filter(Email.thread_id == metadata["thread_id"])
                    .first()
                )

                if not email:
                    continue

                length_penalty = min(len(doc.split()) / 100, 1.0)
                subject_similarity = np.dot(
                    query_embedding, await self._get_embedding(email.subject)
                )

                final_score = (
                    0.6 * similarity_score
                    + 0.3 * subject_similarity
                    + 0.1 * length_penalty
                )

                email_result = {
                    "id": email.id,
                    "content": doc,
                    "subject": email.subject,
                    "thread_id": email.thread_id,
                    "similarity_score": final_score,
                }

                similar_emails.append(email_result)

        # Sort by similarity score
        similar_emails.sort(key=lambda x: x["similarity_score"], reverse=True)
        similar_emails = similar_emails[:n_results]

        if original_email and similar_emails:
            # Validate with LLM
            validated_emails, show_best_match = await self._validate_with_llm(
                original_email, similar_emails
            )

            similar_emails = validated_emails
            if show_best_match and validated_emails:
                best_match = validated_emails[0]
                # Use similarity_score as fallback if llm_relevance_score is not available
                max_similarity = best_match.get(
                    "llm_relevance_score", best_match["similarity_score"]
                )

        return {
            "best_match": best_match if show_best_match else None,
            "similar_emails": similar_emails,
            "similarity_score": max_similarity,
        }

    def delete_embedding(self, embedding_id: str):
        """Delete an embedding from the vector store"""
        self.collection.delete(ids=[embedding_id])

    async def update_embedding(self, embedding_id: str, text: str, metadata: Dict):
        """Update an existing embedding"""
        embedding = await self._get_embedding(text)

        self.collection.update(
            ids=[embedding_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )

    def clear_collection(self):
        """Clear and recreate the collection"""
        try:
            self.client.delete_collection("email_embeddings")
        except:
            pass  # Collection might not exist

        # Create new collection
        self.collection = self.client.create_collection(
            name="email_embeddings",
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )

    async def search_emails(self, query: str, db: Session, n_results: int = 10) -> Dict:
        """Search emails using vector similarity and return results"""
        try:
            # Get embedding for search query
            query_embedding = await self._get_embedding(query)

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )

            if not results["documents"]:
                return {"results": []}

            search_results = []
            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                # Get email from database
                email = (
                    db.query(Email)
                    .filter(Email.thread_id == metadata["thread_id"])
                    .first()
                )
                if not email:
                    continue

                similarity_score = 1 - distance

                # Get subject similarity
                subject_similarity = np.dot(
                    query_embedding, await self._get_embedding(email.subject)
                )

                # Calculate final score with weights
                final_score = 0.6 * similarity_score + 0.4 * subject_similarity

                search_results.append(
                    {
                        "id": email.id,
                        "thread_id": email.thread_id,
                        "subject": email.subject,
                        "content": email.content,
                        "sender": email.sender,
                        "received_date": email.received_date,
                        "similarity_score": final_score,
                    }
                )

            # Sort by similarity score
            search_results.sort(key=lambda x: x["similarity_score"], reverse=True)

            return {"results": search_results}

        except Exception as e:
            print(f"Error in search_emails: {str(e)}")
            return {"results": []}
