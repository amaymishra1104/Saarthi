import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

async def run_walkthrough():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("[1/6] Navigating to SAARTHI at http://127.0.0.1:5173...")
        await page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # -------------------------------------------------------------
        # Scenario A: Failed Payment Auto-Reversal
        # -------------------------------------------------------------
        print("[2/6] Running Scenario A: Failed Payment Auto-Reversal...")
        await page.click("button:has-text('Scenario A: ₹2,000 Failed (Zomato)')")
        await page.wait_for_selector("text=Resolved (Verified via Banking Switch)", timeout=10000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "scenario_a_resolved.png"), full_page=True)
        print("  ✓ Scenario A verified and screenshot saved.")

        # -------------------------------------------------------------
        # Scenario B: Pending Confirmation (Never Infer)
        # -------------------------------------------------------------
        print("[3/6] Running Scenario B: Pending Confirmation...")
        await page.click("button:has-text('Scenario B: ₹2,000 Pending (Swiggy)')")
        await page.wait_for_selector("text=Awaiting Status Change (Unconfirmed)", timeout=10000)
        await page.wait_for_selector("text=I can't call it failed or successful yet", timeout=10000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "scenario_b_pending.png"), full_page=True)
        print("  ✓ Scenario B verified and screenshot saved.")

        # -------------------------------------------------------------
        # Scenario E: Above Auto-Limit Approval -> Human Console Approval
        # -------------------------------------------------------------
        print("[4/6] Running Scenario E: High-Value Approval...")
        await page.click("button:has-text('Scenario E: ₹12,000 Approval (Croma)')")
        await page.wait_for_selector("text=Escalated to Human Operations", timeout=10000)
        await page.wait_for_timeout(1000)

        # Navigate to Human Console
        await page.click("nav button:has-text('Human Console')")
        await page.wait_for_selector("text=Supervisor Authorization Required", timeout=10000)
        await page.wait_for_selector("button:has-text('Approve Reversal')", timeout=10000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "scenario_e_pending_approval.png"), full_page=True)

        # Click Approve Reversal
        await page.click("button:has-text('Approve Reversal')")
        await page.wait_for_selector("text=Approval granted by SUPV-OPS-01", timeout=10000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "scenario_e_approved.png"), full_page=True)
        print("  ✓ Scenario E supervisor approval flow verified and screenshot saved.")

        # -------------------------------------------------------------
        # Scenario F: Verification Mismatch Failure
        # -------------------------------------------------------------
        print("[5/6] Running Scenario F: Verification Mismatch...")
        await page.click("nav button:has-text('Customer Chat')")
        await page.wait_for_timeout(500)
        await page.click("button:has-text('Scenario F: Verification Mismatch (Uber)')")
        await page.wait_for_selector("text=Escalated to Human Operations", timeout=10000)
        await page.wait_for_selector("text=verification check did not confirm settlement", timeout=10000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "scenario_f_mismatch.png"), full_page=True)
        print("  ✓ Scenario F verification mismatch verified and screenshot saved.")

        # -------------------------------------------------------------
        # Agent Trace & Metrics Pages
        # -------------------------------------------------------------
        print("[6/6] Capturing Agent Trace and Honest Metrics...")
        await page.click("nav button:has-text('Agent Trace')")
        await page.wait_for_selector("text=PERMISSION GATE (DETERMINISTIC)", timeout=10000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "agent_trace.png"), full_page=True)

        await page.click("nav button:has-text('Honest Metrics')")
        await page.wait_for_selector("text=Non-Negotiable Rule 7: Strict Honesty Guarantee", timeout=10000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(SCREENSHOTS_DIR / "metrics_dashboard.png"), full_page=True)
        print("  ✓ Agent Trace and Metrics screenshots captured.")

        await browser.close()
        print("All browser walkthroughs completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_walkthrough())
