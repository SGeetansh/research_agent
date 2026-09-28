import chromadb
from fastembed import TextEmbedding
from logger import get_logger   

logger = get_logger(__name__)

CHROMA_STORAGE_PATH = "./chroma_db"
COLLECTION = "uploaded_sources_bge_base"
MODEL_NAME = "BAAI/bge-base-en-v1.5"

logger.info("Loading embedding model: %s", MODEL_NAME)
embedding_model = TextEmbedding(
    model_name=MODEL_NAME,
)
logger.info("Embedding model loaded.")

logger.info("Opening Chroma database at %s", CHROMA_STORAGE_PATH)
client = chromadb.PersistentClient(
    path=CHROMA_STORAGE_PATH,
)
collection = client.get_or_create_collection(
    name=COLLECTION,
)
logger.info(
    "Chroma collection ready: %s",
    COLLECTION,
)

def embed_documents(
    texts: list[str],
) -> list[list[float]]:
    """TODO"""

    return [
        vector.tolist()
        for vector in embedding_model.passage_embed(
            texts
        )
    ]


def embed_query(
    query: str,
) -> list[float]:
    """TODO"""

    vector = next(
        iter(
            embedding_model.query_embed(
                query
            )
        )
    )

    return vector.tolist()


def store_chunks(chunks: list[dict], filename: str) -> None:
    """
    TODO
    """
    logger.info(
        "Embedding %d chunks from %s",
        len(chunks),
        filename,
    )

    collection.delete(
        where={
            "source": filename
        }
    )

    if not chunks:
        logger.warning(
            "No chunks to store for %s",
            filename,
        )
        return

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embed_documents(
        texts
    )

    collection.upsert(
        ids=[
            chunk["metadata"]["chunk_id"]
            for chunk in chunks
        ],

        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {
                "source": chunk["metadata"]["source"],
                "page": chunk["metadata"]["page"],
                "chunk_index": chunk["metadata"]["chunk_index"],
                "token_count": chunk["metadata"]["token_count"],
            }
            for chunk in chunks
        ],
    )
    logger.info(
        "Stored %d chunks from %s",
        len(chunks),
        filename,
    )


def search_chunks(
    query: str,
    k: int = 5,
) -> list[dict]:
    """
    TODO
    """

    count = collection.count()

    if count == 0:
        return []

    query_embedding = embed_query(
        query
    )

    results = collection.query(
        query_embeddings=[
            query_embedding
        ],

        n_results=min(
            k,
            count,
        ),

        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    return [
        {
            "text": document,
            "metadata": metadata,
            "distance": distance,
        }
        for document, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


def clear_store() -> None:
    """"""
    ids = collection.get()["ids"]

    if ids:
        collection.delete(
            ids=ids
        )