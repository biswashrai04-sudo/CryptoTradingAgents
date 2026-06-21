import contextlib
import os
from typing import Any, cast


def _get_chromadb():
    import chromadb

    return chromadb


def _get_default_embedding_function():
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    return DefaultEmbeddingFunction()


# Resolve a stable, project-relative directory so the ChromaDB store survives
# across multiple TradingAgentsGraph instantiations (e.g. Streamlit reruns or
# repeated CLI invocations) without colliding on collection names.
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_CHROMA_PERSIST_DIR = os.path.join(_PROJECT_ROOT, "data_cache", "chroma")
os.makedirs(_CHROMA_PERSIST_DIR, exist_ok=True)


class FinancialSituationMemory:
    def __init__(self, name, config):
        self.config = config
        self.embedding_fn = _get_default_embedding_function()

        # Default to an ephemeral in-memory client to avoid issues with the
        # platform-specific Rust-backed persistent client during tests or on
        # platforms where the chromadb rust bindings can panic. To enable the
        # persistent client, set the environment variable
        # `TRADINGAGENTS_USE_PERSISTENT_CHROMA=1`.
        use_persistent = os.getenv(
            "TRADINGAGENTS_USE_PERSISTENT_CHROMA", "0"
        ).lower() in (
            "1",
            "true",
            "yes",
        )

        chromadb = _get_chromadb()
        if use_persistent:
            try:
                self.chroma_client = chromadb.PersistentClient(path=_CHROMA_PERSIST_DIR)
            except BaseException:
                self.chroma_client = chromadb.EphemeralClient()
        else:
            self.chroma_client = chromadb.EphemeralClient()

        # Be defensive: a previous run may have created the collection with
        # different settings (e.g. a different embedding function), which makes
        # ``get_or_create_collection`` raise "Collection already exists". Recover
        # by retrieving the existing collection, or by recreating a clean one.
        self.situation_collection = None
        try:
            self.situation_collection = self.chroma_client.get_or_create_collection(
                name=name,
                embedding_function=cast(Any, self.embedding_fn),
            )
        except Exception:
            try:
                self.situation_collection = self.chroma_client.get_collection(
                    name=name,
                    embedding_function=cast(Any, self.embedding_fn),
                )
            except Exception:
                # Last resort: drop and recreate so the rest of the workflow
                # can proceed even if the persisted metadata is incompatible.
                with contextlib.suppress(Exception):
                    self.chroma_client.delete_collection(name=name)
                self.situation_collection = self.chroma_client.get_or_create_collection(
                    name=name,
                    embedding_function=cast(Any, self.embedding_fn),
                )

        # At this point we've attempted to create or retrieve the collection —
        # ensure it's available for the rest of the instance methods.
        assert self.situation_collection is not None

    def add_situations(self, situations_and_advice):
        situations = []
        advice = []
        ids = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        results = self.situation_collection.query(
            query_texts=[current_situation],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": results["metadatas"][0][i]["recommendation"],
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results


if __name__ == "__main__":
    matcher = FinancialSituationMemory("test", config={})

    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    matcher.add_situations(example_data)

    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {e!s}")
