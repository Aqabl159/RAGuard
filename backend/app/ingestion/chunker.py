"""Text chunking using RecursiveCharacterTextSplitter strategy."""

from app.config import settings


def chunk_text(text: str, chunk_size: int | None = None, chunk_overlap: int | None = None) -> list[str]:
    """Split text into overlapping chunks.

    Uses a character-based recursive splitter with separators optimized
    for Chinese and English content.

    Args:
        text: Input text to split.
        chunk_size: Maximum chunk size in characters (default from settings).
        chunk_overlap: Overlap between chunks in characters (default from settings).

    Returns:
        List of text chunks.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    # Separators ordered by priority: paragraphs, sentences, phrases
    separators = [
        "\n\n",
        "\n",
        "。",
        "；",
        "，",
        ".",
        ";",
        ",",
        " ",
        "",
    ]

    chunks = _recursive_split(text, separators, chunk_size, chunk_overlap)
    return [c.strip() for c in chunks if c.strip()]


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Recursively split text using a hierarchy of separators."""
    # Find the best separator to use
    best_sep = ""
    for sep in separators:
        if sep == "":
            best_sep = ""
            break
        if sep in text:
            best_sep = sep
            break

    # If no separator found or text fits in one chunk
    if len(text) <= chunk_size or best_sep == "":
        return [text] if text.strip() else []

    # Split by the best separator
    splits = text.split(best_sep)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0

    for split in splits:
        split_len = len(split)
        if split_len == 0:
            continue

        if current_size + split_len + len(best_sep) > chunk_size and current_chunk:
            # Finish current chunk
            chunks.append(best_sep.join(current_chunk))
            # Start new chunk with overlap: keep last portion of previous chunk
            overlap_text = best_sep.join(current_chunk)
            overlap_chars = overlap_text[-chunk_overlap:] if chunk_overlap > 0 else ""
            if overlap_chars:
                current_chunk = [overlap_chars]
                current_size = len(overlap_chars)
            else:
                current_chunk = []
                current_size = 0

        if split_len > chunk_size and not current_chunk:
            # If a single split is larger than chunk_size, recurse with remaining separators
            if len(separators) > 1:
                sub_chunks = _recursive_split(
                    split, separators[separators.index(best_sep) + 1:], chunk_size, chunk_overlap
                )
                chunks.extend(sub_chunks)
            else:
                # Force split by character
                for i in range(0, split_len, chunk_size - chunk_overlap):
                    chunks.append(split[i:i + chunk_size])
            continue

        current_chunk.append(split)
        current_size += split_len + (len(best_sep) if current_chunk else 0)

    if current_chunk:
        chunks.append(best_sep.join(current_chunk))

    return chunks


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string.

    Uses tiktoken with cl100k_base encoding as an approximation.
    For Chinese text, the ratio is roughly 1.5-2 characters per token.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        # Fallback: rough estimate for mixed CN/EN text
        return len(text) // 2
