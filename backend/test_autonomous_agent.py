"""
End-to-end test harness for AutonomousAgentController.

This script validates the full autonomous browser automation loop:
1. Launch Playwright browser
2. Navigate to test URL (Coursera)
3. Run AutonomousAgentController with HybridPlanner or LLMPlanner
4. Print execution results

Supports two modes:
- "deterministic": HybridPlanner (no LLM client required)
- "llm": LLMPlanner (requires LM Studio running at http://localhost:1234)

Usage:
    python test_autonomous_agent.py
    
    # Or change MODE constant for LLM mode:
    # MODE = "llm"

Author: Agent System
Date: 2026-02-26
Version: 1.1.0
"""

import asyncio
import sys
from typing import Optional
from datetime import datetime

from playwright.async_api import async_playwright, Page

from .autonomous_controller import AutonomousAgentController
from .page_analyzer import PageAnalyzer
from .action_executor import ActionExecutor


# ============================================================================
# Configuration
# ============================================================================

TEST_URL = "https://www.coursera.org"
TEST_GOAL = "Find a free Python course and open it"
TEST_MAX_STEPS = 10
MODE = "deterministic"  # "deterministic" or "llm"

BROWSER_HEADLESS = True  # Set to False to see browser UI
BROWSER_SLOWDOWN = 100  # ms delay between actions (0 = no delay)


# ============================================================================
# Console Formatting
# ============================================================================

class Colors:
    """ANSI color codes for console output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


def print_header(text: str):
    """Print formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")


def print_section(text: str):
    """Print formatted subsection header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[{text}]{Colors.RESET}")


def print_success(text: str):
    """Print success message (green)."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message (red)."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message (yellow)."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message (cyan)."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.RESET}")


def print_step(step_num: int, action: str, selector: Optional[str], status: str):
    """Print formatted step result."""
    status_color = Colors.GREEN if status == "success" else Colors.RED
    status_symbol = "✓" if status == "success" else "✗"
    
    selector_str = f" → {selector}" if selector else ""
    print(f"  {Colors.DIM}Step {step_num}:{Colors.RESET} {action}{selector_str} "
          f"{status_color}{status_symbol}{Colors.RESET}")


# ============================================================================
# Test Functions
# ============================================================================

async def run_test():
    """
    Run end-to-end autonomous agent test.
    
    Returns:
        Boolean indicating test success
    """
    browser_context = None
    page = None
    success = False
    
    try:
        print_header("AUTONOMOUS AGENT END-TO-END TEST")
        
        # ====================================================================
        # SETUP: Browser Launch
        # ====================================================================
        print_section("Browser Setup")
        
        async with async_playwright() as playwright:
            print_info(f"Launching Chromium (headless={BROWSER_HEADLESS})...")
            browser = await playwright.chromium.launch(
                headless=BROWSER_HEADLESS,
                args=["--disable-gpu"]  # Better performance on CI/CD
            )
            print_success("Browser launched")
            
            # Create new page
            print_info(f"Creating new page...")
            page = await browser.new_page()
            
            # Set slowdown for visibility (optional)
            if BROWSER_SLOWDOWN > 0:
                page.slow_mo = BROWSER_SLOWDOWN
                print_info(f"Slowdown set to {BROWSER_SLOWDOWN}ms")
            
            print_success("Page created")
            
            # ================================================================
            # NAVIGATION: Go to test URL
            # ================================================================
            print_section("Navigation")
            
            print_info(f"Navigating to {TEST_URL}...")
            try:
                await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
                print_success(f"Page loaded: {page.url}")
            except Exception as e:
                print_error(f"Failed to load page: {e}")
                print_warning("Test will attempt to continue with current page")
            
            # ================================================================
            # SETUP: Instantiate Agent Components
            # ================================================================
            print_section("Agent Initialization")
            
            print_info("Initializing PageAnalyzer...")
            analyzer = PageAnalyzer(page)
            print_success("PageAnalyzer created")
            
            print_info("Initializing ActionExecutor...")
            executor = ActionExecutor()
            print_success("ActionExecutor created")
            
            print_info("Initializing AutonomousAgentController...")
            controller = AutonomousAgentController(
                page=page,
                analyzer=analyzer,
                executor=executor,
                llm_client=None,
                mode=MODE
            )
            print_success(f"AutonomousAgentController created (mode={MODE})")
            print_info(f"Controller page URL: {controller.page.url}")
            print_info(f"PageAnalyzer page URL: {controller.analyzer.page.url}")
            
            # ================================================================
            # EXECUTION: Run Autonomous Goal
            # ================================================================
            print_section("Autonomous Execution")
            
            print_info(f"Goal: {TEST_GOAL}")
            print_info(f"Max steps: {TEST_MAX_STEPS}")
            start_time = datetime.now()
            
            result = await controller.run_goal(
                user_goal=TEST_GOAL,
                max_steps=TEST_MAX_STEPS
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # ================================================================
            # RESULTS: Print Execution Report
            # ================================================================
            print_section("Execution Results")
            
            final_status = result.get("final_status", "unknown")
            steps_taken = result.get("steps_taken", 0)
            
            # Status color coding
            if final_status == "completed":
                status_color = Colors.GREEN
                status_icon = "✓"
            elif final_status == "error":
                status_color = Colors.RED
                status_icon = "✗"
            else:
                status_color = Colors.YELLOW
                status_icon = "⚠"
            
            print(f"Status: {status_color}{status_icon} {final_status.upper()}{Colors.RESET}")
            print(f"Steps Taken: {steps_taken}")
            print(f"Execution Time: {execution_time:.2f}s")
            
            if "error" in result:
                print_error(f"Error: {result['error']}")
            
            # Print summary
            summary = result.get("summary", "")
            if summary:
                print_info(f"Summary: {summary}")
            
            # ================================================================
            # EXECUTION HISTORY: Detailed Step Breakdown
            # ================================================================
            print_section("Execution History")
            
            execution_history = result.get("execution_history", [])
            
            if not execution_history:
                print_warning("No execution history available")
            else:
                print(f"{Colors.DIM}Total steps: {len(execution_history)}{Colors.RESET}\n")
                
                for idx, step_record in enumerate(execution_history, 1):
                    # Extract step information
                    decision = step_record.get("decision", {})
                    execution = step_record.get("execution", {})
                    
                    action = decision.get("action", "unknown")
                    selector = decision.get("target_selector")
                    confidence = decision.get("confidence", 0)
                    exec_status = execution.get("status", "unknown")
                    
                    # Format and print
                    print_step(idx, action, selector, exec_status)
                    
                    # Print additional details
                    explanation = decision.get("explanation", "")
                    if explanation:
                        print(f"    {Colors.DIM}Explanation: {explanation[:60]}{Colors.RESET}")
                    
                    details = execution.get("details", "")
                    if details and exec_status == "failed":
                        print(f"    {Colors.DIM}Details: {details[:60]}{Colors.RESET}")
                    
                    print()
            
            # ================================================================
            # FINAL ASSESSMENT
            # ================================================================
            print_section("Final Assessment")
            
            # Determine test success
            if final_status == "completed":
                print_success("Test PASSED - Autonomous goal completed!")
                success = True
            elif final_status == "max_steps_reached":
                print_warning("Test INCONCLUSIVE - Reached maximum steps")
                print_info(f"Attempted {steps_taken} steps before limit")
                success = None  # Partial success
            elif final_status == "loop_detected":
                print_warning("Test INCONCLUSIVE - Loop detected (safety stop)")
                print_info("Agent correctly detected and prevented infinite loop")
                success = None  # Partial success
            else:  # error
                print_error(f"Test FAILED - {final_status}")
                if "error" in result:
                    print_error(f"Error: {result['error']}")
                success = False
            
            # Print statistics
            print("\nStatistics:")
            print(f"  • Total steps: {steps_taken}")
            print(f"  • Execution time: {execution_time:.2f}s")
            
            if execution_history:
                success_count = sum(
                    1 for step in execution_history
                    if step.get("execution", {}).get("status") == "success"
                )
                print(f"  • Successful actions: {success_count}/{len(execution_history)}")
            
            # ================================================================
            # CLEANUP
            # ================================================================
            print_section("Cleanup")
            
            await browser.close()
            print_success("Browser closed")
            
            return success
    
    except Exception as e:
        print_error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Ensure browser is closed even on exception
        if page:
            try:
                await page.close()
            except:
                pass


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main test entry point."""
    try:
        success = await run_test()
        
        # Print final result
        print_header("TEST COMPLETE")
        
        if success is True:
            print(f"{Colors.GREEN}✓ ALL TESTS PASSED{Colors.RESET}\n")
            return 0
        elif success is False:
            print(f"{Colors.RED}✗ TEST FAILED{Colors.RESET}\n")
            return 1
        else:
            print(f"{Colors.YELLOW}⚠ TEST INCONCLUSIVE{Colors.RESET}\n")
            return 2
    
    except KeyboardInterrupt:
        print_warning("\nTest interrupted by user")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
