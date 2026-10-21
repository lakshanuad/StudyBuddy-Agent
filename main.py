import asyncio
from ingestion import get_vectorstore_and_retriever
from agent import create_study_agent
from cli import start_cli_session


async def main():
    """Main application bootstrap: initializes vector storage, builds agent, and starts CLI."""
    _, retriever = get_vectorstore_and_retriever()
    agent = create_study_agent(retriever)
    await start_cli_session(agent, retriever=retriever)


if __name__ == "__main__":
    asyncio.run(main())
