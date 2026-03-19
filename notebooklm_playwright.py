"""
notebooklm_playwright.py
Standalone Playwright script for NotebookLM Video Overview automation.

Normal mode (called by upload_to_notebooklm):
  python notebooklm_playwright.py \
    --notebook-url "https://notebooklm.google.com/notebook/..." \
    --session-dir  "/path/to/notebooklm_session" \
    --document-text "..." \
    --notebooklm-prompt "..."

Setup mode (called by setup_notebooklm, opens headed browser for Google login):
  python notebooklm_playwright.py \
    --setup \
    --notebook-url "https://notebooklm.google.com/notebook/..." \
    --session-dir  "/path/to/notebooklm_session"

CONFIRMED SELECTORS (verified March 2026, NotebookLM PRO):
  Add sources btn   : button[aria-label="Add source"]
  Copied text       : button:has-text("Copied text")
  Paste textarea    : textarea[placeholder="Paste text here"]
  Insert button     : button:has-text("Insert")
  Source item       : div.single-source-container
  Source menu btn   : div.single-source-container button[aria-label="Source options"]
  Remove source     : button:has-text("Remove source")
  Video card menu   : button[aria-label="Video overview options"]
  Delete video      : button:has-text("Delete")
  Chat textarea     : textarea[placeholder="Start typing..."]
  Chat submit       : button[aria-label="Submit"]:not([disabled])
  Generation start  : text "Generating Video Overview" in Studio panel

WORKFLOW:
  1. Clear existing sources (Remove source) and videos (Delete) from previous run
  2. Add source via "Add sources" -> "Copied text" -> paste -> Insert
  3. Type the notebooklm_prompt into the Chat textarea and submit
  4. NotebookLM automatically starts Video Overview generation
  5. Script exits; generation continues in NotebookLM's cloud

NOTE: Uses channel="chrome" (real system Chrome) to avoid Google's
headless detection which would sign out the Playwright session.
"""

import argparse
import json
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--setup", action="store_true",
                   help="Open headed browser for Google login, save session, then exit.")
    p.add_argument("--clear-only", action="store_true",
                   help="Open headed browser, clear all sources and videos, then exit.")
    p.add_argument("--notebook-url", required=True)
    p.add_argument("--session-dir", required=True)
    p.add_argument("--document-text", default="")
    p.add_argument("--notebooklm-prompt", default="")
    return p.parse_args()


# ── Setup mode ───────────────────────────────────────────────────────────────

def run_setup(args):
    """
    Opens a headed Chrome window so the user can log in to Google.
    Blocks until the user presses Enter, then saves the session.
    """
    print("Opening Chrome for Google login...", file=sys.stderr)
    print(f"URL: {args.notebook_url}", file=sys.stderr)
    print("Log in, open the notebook, then press Enter here.", file=sys.stderr)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            args.session_dir,
            headless=False,
            channel="chrome",
        )
        page = ctx.new_page()
        page.goto(args.notebook_url)

        try:
            input("\n[notebooklm] Press Enter once you are logged in and the notebook is open: ")
        except EOFError:
            print("Non-interactive: waiting for networkidle...", file=sys.stderr)
            page.wait_for_load_state("networkidle", timeout=120_000)

        ctx.close()

    print("Session saved.", file=sys.stderr)
    print(json.dumps({"status": "session_saved"}))


# ── Clear mode ────────────────────────────────────────────────────────────────

def clear_notebook(page):
    """
    Removes all existing sources and deletes all existing video overviews
    from the notebook before a new upload.

    Sources: hover source row to reveal three-dot menu -> Remove source
    Videos:  click the three-dot menu on each video card -> Delete
    """

    # ── Remove all sources ────────────────────────────────────────────────────
    while True:
        sources = page.locator('div.single-source-container')
        if sources.count() == 0:
            break
        try:
            source = sources.first
            source.hover()
            page.wait_for_timeout(500)
            # The menu button appears on hover — find any icon button within the row
            menu_btn = source.locator('button').last
            menu_btn.click()
            page.wait_for_selector('button:has-text("Remove source")', timeout=5000)
            page.click('button:has-text("Remove source")')
            # Confirm the "Delete Pasted Text?" dialog
            page.wait_for_selector('[role="dialog"] button:has-text("Delete")', timeout=5000)
            page.click('[role="dialog"] button:has-text("Delete")')
            page.wait_for_timeout(2000)
        except PlaywrightTimeoutError:
            break

    # ── Delete all video overviews ────────────────────────────────────────────
    # Anchor off the play button -- each video card in Studio has a play button
    # and a three-dot (More options) button as siblings inside the same card.
    while True:
        # Find any play button visible in the Studio panel
        play_btn = page.locator(
            'button[aria-label="Play"], '
            'button[aria-label="Play video overview"], '
            'button[aria-label*="play" i]'
        ).first
        if play_btn.count() == 0:
            break
        try:
            # Walk up to the card container and find the three-dot (last button)
            card = play_btn.locator('xpath=../..')
            card.hover()
            page.wait_for_timeout(500)
            menu_btn = card.locator('button').last
            menu_btn.click()
            page.wait_for_selector('button:has-text("Delete")', timeout=5000)
            page.locator('button:has-text("Delete")').last.click()
            # Confirm the deletion dialog
            page.wait_for_selector('[role="dialog"] button:has-text("Delete")', timeout=5000)
            page.click('[role="dialog"] button:has-text("Delete")')
            page.wait_for_timeout(2000)
        except PlaywrightTimeoutError:
            break


# ── Upload mode ───────────────────────────────────────────────────────────────

def run_upload(args):
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            args.session_dir,
            headless=True,
            channel="chrome",  # real Chrome bypasses Google headless detection
        )
        page = ctx.new_page()
        page.goto(args.notebook_url)
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        page.wait_for_timeout(6000)  # let Angular fully render

        # Dismiss any leftover overlay from a previous session
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # ── 0. Clear previous sources and videos ──────────────────────────
        clear_notebook(page)

        # ── 1. Add source ─────────────────────────────────────────────────
        page.wait_for_selector('button[aria-label="Add source"]', timeout=15_000)
        page.click('button[aria-label="Add source"]')

        page.wait_for_selector('button:has-text("Copied text")', timeout=10_000)
        page.click('button:has-text("Copied text")')

        page.wait_for_selector('textarea[placeholder="Paste text here"]', timeout=10_000)
        page.fill('textarea[placeholder="Paste text here"]', args.document_text)

        page.click('button:has-text("Insert")')

        # ── 2. Wait for source to appear ──────────────────────────────────
        try:
            page.wait_for_selector('div.single-source-container', timeout=20_000)
        except PlaywrightTimeoutError:
            raise RuntimeError("Source did not appear after insert")

        # ── 3. Type chat prompt -> triggers Video Overview generation ──────
        # Typing a prompt that mentions "Video Overview" in the Chat area
        # causes NotebookLM to automatically start generating a Video Overview.
        chat = 'textarea[placeholder="Start typing..."]'
        page.wait_for_selector(chat, timeout=10_000)
        page.click(chat)
        # Must use type() (not fill()) so Angular's reactive form enables Submit
        page.type(chat, args.notebooklm_prompt, delay=20)

        # ── 4. Submit ─────────────────────────────────────────────────────
        submit = 'button[aria-label="Submit"]:not([disabled])'
        page.wait_for_selector(submit, timeout=10_000)
        page.click(submit)

        # ── 5. Wait for generation to START ──────────────────────────────
        try:
            page.wait_for_selector(
                ':has-text("Generating Video Overview")',
                timeout=20_000,
            )
        except PlaywrightTimeoutError:
            pass  # generation may have started without the exact text; proceed

        ctx.close()

    print(json.dumps({"status": "generating", "notebook_url": args.notebook_url}))


# ── Entry point ───────────────────────────────────────────────────────────────

def run_clear_only(args):
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            args.session_dir,
            headless=False,
            channel="chrome",
        )
        page = ctx.new_page()
        page.goto(args.notebook_url)
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        page.wait_for_timeout(6000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        print("Clearing notebook...", file=sys.stderr)
        clear_notebook(page)
        print("Done. Browser stays open for inspection. Close it to exit.", file=sys.stderr)

        input("\n[notebooklm] Press Enter to close the browser: ")
        ctx.close()

    print(json.dumps({"status": "cleared"}))


def main():
    args = parse_args()
    try:
        if args.setup:
            run_setup(args)
        elif args.clear_only:
            run_clear_only(args)
        else:
            if not args.document_text:
                print(json.dumps({"status": "error", "message": "--document-text is required"}))
                sys.exit(1)
            run_upload(args)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
