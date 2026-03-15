"""
run.py — Programmatic runner for the Hedge Fund Analyst
Use this to run the agent from the command line without the ADK web UI.

Usage:
    uv run python run.py NVDA
    uv run python run.py AAPL
    uv run python run.py "Analyse Tesla"
"""

import asyncio
import sys
import os

from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import the root agent
from hedge_fund_analyst.agent import root_agent


async def run_analysis(query: str):
    """Run the hedge fund analyst multi-agent pipeline."""

    print("\n" + "=" * 70)
    print("  AI HEDGE FUND ANALYST — Multi-Agent System")
    print("  Powered by Google ADK + Gemini")
    print("=" * 70)
    print(f"\n  Query: {query}")
    print("\n  Initialising research pipeline...")
    print("  [Parallel agents will run simultaneously — this takes ~30-60 seconds]\n")

    # Set up ADK session and runner
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="hedge_fund_analyst",
        user_id="user_001",
    )

    runner = Runner(
        agent=root_agent,
        app_name="hedge_fund_analyst",
        session_service=session_service,
    )

    # Build the user message
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    # Stream events from the agent pipeline
    print("  Agent activity log:")
    print("  " + "-" * 50)

    final_response = ""
    async for event in runner.run_async(
        user_id="user_001",
        session_id=session.id,
        new_message=user_message,
    ):
        # Print agent activity
        if hasattr(event, "author") and event.author:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        # Only log non-final, shorter messages as activity
                        text = part.text.strip()
                        if len(text) < 200 and text:
                            print(f"  [{event.author}] {text[:120]}...")
                        # Capture the final investment memo
                        if "INVESTMENT MEMO" in text or "## EXECUTIVE SUMMARY" in text:
                            final_response = text

        # Capture final response from the root agent
        if hasattr(event, "is_final_response") and event.is_final_response():
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_response = part.text

    print("\n" + "=" * 70)
    print("  RESEARCH COMPLETE")
    print("=" * 70 + "\n")

    if final_response:
        print(final_response)
    else:
        # Try to get the memo from session state
        updated_session = await session_service.get_session(
            app_name="hedge_fund_analyst",
            user_id="user_001",
            session_id=session.id,
        )
        if updated_session and updated_session.state:
            state = updated_session.state
            if "investment_memo" in state:
                print(state["investment_memo"])
            else:
                print("Analysis complete. Check the ADK web UI for full results.")
                print("\nSession state keys:", list(state.keys()))

    print("\n" + "=" * 70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python run.py <TICKER or query>")
        print("Example: uv run python run.py NVDA")
        print("Example: uv run python run.py 'Analyse Apple stock'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    # Validate API key
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your_google_api_key_here":
        print("\nERROR: GOOGLE_API_KEY not set in .env file.")
        print("Get your key at: https://aistudio.google.com/app/apikey")
        print("Then add it to your .env file: GOOGLE_API_KEY=your_key_here\n")
        sys.exit(1)

    asyncio.run(run_analysis(query))


if __name__ == "__main__":
    main()
