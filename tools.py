from pathlib import Path
from agents import function_tool


def create_search_tool(retriever):
    """Creates a function tool for the OpenAI Agents SDK wired to the vector retriever."""

    @function_tool
    def search_lectures(query: str) -> str:
        """Search lecture notes and materials for relevant information given a query.

        Args:
            query: The search query to look up in lecture materials.

        Returns:
            Joined text content of relevant lecture notes chunks with clean source names and pages.
        """
        docs = retriever.invoke(query)
        if not docs:
            return "No relevant lecture content found."

        formatted_chunks = []
        for doc in docs:
            raw_source = doc.metadata.get("source", "Unknown")
            clean_source = Path(raw_source).name if raw_source != "Unknown" else "Unknown Document"
            page_num = doc.metadata.get("page", 0) + 1
            formatted_chunks.append(
                f"[Source Document: {clean_source} | Page: {page_num}]\n{doc.page_content}"
            )

        return "\n\n---\n\n".join(formatted_chunks)

    return search_lectures
