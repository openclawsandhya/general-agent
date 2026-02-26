"""
Example usage script for the Trial Automation Agent.

This demonstrates:
1. Chat-only requests
2. Automation requests with human-in-the-loop approval
3. Using the core agent programmatically
4. Using the REST API client
"""

import asyncio
import requests
import json
from typing import Optional

# For programmatic usage
from .llm_client import LLMClient
from .planner import Planner
from .browser_controller import BrowserController
from .executor import Executor
from .agent_core import AutomationAgent
from .agent_controller import AutonomousAgentController


class AgentClient:
    """Simple client for testing the agent."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def send_message(self, message: str, session_id: Optional[str] = None) -> dict:
        """
        Send a message to the agent.
        
        Args:
            message: User message
            session_id: Optional session ID
            
        Returns:
            Response dictionary
        """
        payload = {
            "message": message,
            "session_id": session_id
        }
        
        response = requests.post(
            f"{self.base_url}/agent/message",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    
    def stream_message(self, message: str, session_id: Optional[str] = None):
        """
        Stream a message to the agent.
        
        Args:
            message: User message
            session_id: Optional session ID
            
        Yields:
            Status updates as they come
        """
        payload = {
            "message": message,
            "session_id": session_id
        }
        
        response = requests.post(
            f"{self.base_url}/agent/message/stream",
            json=payload,
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                if line.startswith(b"data: "):
                    data = json.loads(line[6:])
                    yield data


async def demo_programmatic():
    """
    Demonstrate using the agent directly (without HTTP).
    Shows the full flow: chat, automation request, and approval.
    """
    print("=" * 60)
    print("DEMO: Using Agent Directly (Programmatic)")
    print("=" * 60)
    
    # Initialize components
    llm = LLMClient()
    planner = Planner(llm)
    browser = BrowserController(headless=True)
    executor = Executor(browser)
    
    # Create agent
    agent = AutomationAgent(
        planner=planner,
        executor=executor,
        llm_client=llm
    )
    
    # Test 1: Chat interaction
    print("\n[1] Chat Interaction:")
    chat_response = await agent.handle_message("What is Python programming?")
    print(f"User: 'What is Python programming?'")
    print(f"Agent: {chat_response[:100]}...")
    
    # Test 2: Automation request (pending approval)
    print("\n[2] Automation Request (Pending Approval):")
    automation_request = "Search for best free Python course on Google"
    auto_response = await agent.handle_message(automation_request)
    print(f"User: '{automation_request}'")
    print(f"Agent:\n{auto_response}")
    
    print(f"\n✓ Agent has pending approval: {agent.has_pending_approval()}")
    
    # Test 3: User denies automation
    print("\n[3] User Denies Automation:")
    denial_response = await agent.handle_message("no")
    print(f"User: 'no'")
    print(f"Agent: {denial_response}")
    
    # Test 4: Another automation request, then approve
    print("\n[4] Automation Request + Approval:")
    agent_2 = AutomationAgent(
        planner=planner,
        executor=executor,
        llm_client=llm
    )
    
    automation_request_2 = "Search for Docker tutorials"
    auto_response_2 = await agent_2.handle_message(automation_request_2)
    print(f"User: '{automation_request_2}'")
    print(f"Agent:\n{auto_response_2}")
    
    # Approve automation
    print(f"\nUser: 'yes'")
    approval_response = await agent_2.handle_message("yes")
    print(f"Agent: {approval_response[:150]}...")
    
    # Test 5: View history
    print("\n[5] Conversation History:")
    history = agent_2.get_history()
    print(f"Total messages: {len(history)}")
    for i, msg in enumerate(history, 1):
        print(f"  {i}. [{msg['role'].upper()}] {msg['content'][:60]}...")


def demo_rest_api():
    """
    Demonstrate using the agent via REST API with approval flow.
    """
    print("\n" + "=" * 60)
    print("DEMO: Using REST API with Approval Flow")
    print("=" * 60)
    
    client = AgentClient()
    
    # Example 1: Chat request
    print("\n[1] Chat Request:")
    try:
        response = client.send_message("What is machine learning?")
        print(f"  Request: Chat query")
        print(f"  Response: {response['response'][:80]}...")
    except Exception as e:
        print(f"  Error: {e}")
        print("  → Make sure the server is running: python api_server.py")
    
    # Example 2: Automation request (gets pending approval)
    print("\n[2] Automation Request (Pending Approval):")
    try:
        session_id = None
        
        # Send automation request
        response_1 = client.send_message("Search for Python tutorials on Google")
        print(f"  Request: Automation")
        print(f"  Response:\n{response_1['response']}")
        session_id = response_1.get('session_id')
        
        # Approve automation
        if session_id:
            print(f"\n  Approving automation...")
            response_2 = client.send_message("yes", session_id=session_id)
            print(f"  Response:\n{response_2['response'][:150]}...")
    except Exception as e:
        print(f"  Error: {e}")
        print("  → Make sure the server and browser are ready")
    
    # Example 3: Check session
    if session_id:
        print(f"\n[3] Session Info:")
        try:
            session_info = requests.get(
                f"http://localhost:8000/sessions/{session_id}",
                timeout=10
            ).json()
            print(f"  Session ID: {session_info['session_id']}")
            print(f"  History length: {session_info['history_length']}")
            print(f"  Pending approval: {session_info['has_pending_approval']}")
        except Exception as e:
            print(f"  Error: {e}")


def demo_streaming():
    """
    Demonstrate streaming responses with real-time updates.
    """
    print("\n" + "=" * 60)
    print("DEMO: Streaming Responses")
    print("=" * 60)
    
    client = AgentClient()
    
    print("\n[1] Streaming Chat Request:")
    try:
        print("  Sending: 'What are microservices?'")
        for update in client.stream_message("What are microservices?"):
            print(f"  [{update['type'].upper()}] {update['content'][:60]}...")
            if update.get('is_final'):
                break
    except Exception as e:
        print(f"  Error: {e}")
        print("  → Make sure the server is running")
    
    print("\n[2] Streaming Automation Request:")
    try:
        print("  Sending: 'Search for React tutorials'")
        session_id = None
        for update in client.stream_message("Search for React tutorials"):
            print(f"  [{update['type'].upper()}] {update['content'][:60]}...")
            if update.get('is_final'):
                break
    except Exception as e:
        print(f"  Error: {e}")


async def demo_autonomous():
    """
    Demonstrate autonomous goal-driven agent.
    
    Shows the agent running a continuous feedback loop to achieve a goal.
    """
    print("\n" + "=" * 60)
    print("DEMO: Autonomous Goal-Driven Agent")
    print("=" * 60)
    
    # Initialize components
    llm = LLMClient()
    browser = BrowserController(headless=True)
    executor = Executor(browser)
    
    # Create autonomous agent
    agent = AutonomousAgentController(
        browser_controller=browser,
        executor=executor,
        llm_client=llm,
        max_iterations=10
    )
    
    # Set up status tracking
    print("\n[1] Autonomous Goal-Driven Loop:")
    print("\nGoal: Search for Python tutorials and find introduction for beginners")
    print("-" * 60)
    
    def on_status(msg: str):
        print(f"  {msg}")
    
    agent.set_status_callback(on_status)
    
    try:
        # Run autonomous loop
        goal = "Search for Python tutorials and find introduction for beginners"
        result = await agent.run_goal(goal)
        
        print("\nFinal Report:")
        print(result)
    
    except Exception as e:
        print(f"  Error: {e}")
        print("  → Make sure LM Studio is running and browser is available")


def demo_autonomous_rest():
    """
    Demonstrate autonomous goal via REST API.
    """
    print("\n" + "=" * 60)
    print("DEMO: Autonomous Goal via REST API")
    print("=" * 60)
    
    client = AgentClient()
    
    print("\n[1] Autonomous Goal Request:")
    try:
        goal = "Find information about Docker on the official website"
        print(f"  Goal: {goal}")
        print("-" * 60)
        
        response = client.send_message(goal)
        print(f"\nResponse:")
        print(response['response'])
        print(f"\nSession ID: {response.get('session_id')}")
        
    except Exception as e:
        print(f"  Error: {e}")
        print("  → Make sure the server is running: python api_server.py")
    
    print("\n[2] Autonomous Goal Streaming:")
    try:
        goal = "Find Python documentation"
        print(f"  Goal: {goal}")
        print("-" * 60)
        
        for update in client.stream_message(goal):
            if update.get('is_final'):
                print(f"\n[FINAL] {update['content']}")
                break
            else:
                print(f"  {update['content']}")
        
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    import sys
    
    print("Trial Automation Agent - Usage Examples\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--programmatic":
            # Run programmatic demo
            asyncio.run(demo_programmatic())
        elif sys.argv[1] == "--stream":
            # Run streaming demo
            demo_streaming()
        elif sys.argv[1] == "--api":
            # Run REST API demo
            demo_rest_api()
        elif sys.argv[1] == "--autonomous":
            # Run autonomous agent demo
            asyncio.run(demo_autonomous())
        elif sys.argv[1] == "--autonomous-rest":
            # Run autonomous agent REST API demo
            demo_autonomous_rest()
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("\nAvailable demos:")
            print("  python examples.py --programmatic       # Direct agent usage (most comprehensive)")
            print("  python examples.py --api                # REST API with approval flow")
            print("  python examples.py --stream             # Streaming responses")
            print("  python examples.py --autonomous         # Autonomous agent loop")
            print("  python examples.py --autonomous-rest    # Autonomous agent REST API")
    else:
        # Default: show list of available demos
        print("Running examples...\n")
        
        print("=" * 60)
        print("AVAILABLE DEMOS:")
        print("=" * 60)
        print("  python examples.py --programmatic       # Direct agent usage with approval flow")
        print("  python examples.py --api                # REST API with approval flow")
        print("  python examples.py --stream             # Streaming responses")
        print("  python examples.py --autonomous         # Autonomous goal-driven loop (programmatic)")
        print("  python examples.py --autonomous-rest    # Autonomous goal-driven loop (REST API)")
        print("=" * 60)
        print("\nRun a demo: python examples.py --autonomous")

