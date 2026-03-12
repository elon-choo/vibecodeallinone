#!/usr/bin/env python3
"""Headless browser smoke for assistant-web against assistant-api mock mode."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Error, expect, sync_playwright

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from smoke_support import (  # noqa: E402
    find_free_port,
    initialize_runtime_repo,
    start_assistant_api,
    start_assistant_web,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="artifacts/browser_smoke/assistant_web_browser_smoke.json",
        help="Where to write the browser smoke report JSON.",
    )
    parser.add_argument(
        "--screenshot",
        default="artifacts/browser_smoke/assistant_web_browser_smoke.png",
        help="Where to write the final browser screenshot.",
    )
    parser.add_argument(
        "--e2e-score",
        default="artifacts/e2e_score.json",
        help="Where to write the release-evidence E2E score artifact.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_port = find_free_port()
    web_port = find_free_port()
    screenshot_path = Path(args.screenshot)
    output_path = Path(args.output)
    e2e_score_path = Path(args.e2e_score)

    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    e2e_score_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="assistant-browser-smoke-") as temp_dir:
        runtime_seed = initialize_runtime_repo(Path(temp_dir) / "runtime-repo", stale_trust=True)
        with (
            start_assistant_api(runtime_seed.repo_root, api_port=api_port, web_port=web_port, provider_mode="mock") as api_base,
            start_assistant_web(web_port=web_port) as web_base,
        ):
            checks: list[dict[str, object]] = []
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    context = browser.new_context(accept_downloads=True, timezone_id="Asia/Seoul")
                    context.add_init_script(
                        script=f'window.localStorage.setItem("assistant_api_base_url", {json.dumps(api_base)});'
                    )
                    page = context.new_page()
                    page.goto(web_base, wait_until="networkidle")

                    expect(page.locator("#runtimeMeta")).to_contain_text(api_base)
                    expect(page.locator("#trustCard")).to_contain_text("Evidence stale")
                    expect(page.locator("#trustCard")).to_contain_text("Re-run release validation")
                    checks.append(
                        {
                            "check": "stale_trust_fallback",
                            "detail": "stale trust summary rendered the fallback copy instead of raw artifact details",
                        }
                    )

                    page.get_by_role("button", name="Connect OpenAI").click()
                    expect(page.locator("#sessionCard")).to_contain_text("active")
                    expect(page.locator("#notice")).to_contain_text("Runtime synced.")
                    checks.append(
                        {
                            "check": "auth_round_trip",
                            "detail": "browser completed the mock auth start, redirect, callback, and active session refresh flow",
                        }
                    )

                    page.get_by_role("button", name="Start Telegram Link").click()
                    expect(page.locator("#telegramCard")).to_contain_text("pending")
                    page.evaluate(
                        """async (apiBase) => {
                            const pendingResponse = await fetch(`${apiBase}/v1/surfaces/telegram/link`, {
                              credentials: "include"
                            });
                            const pending = await pendingResponse.json();
                            const completeResponse = await fetch(`${apiBase}/v1/internal/test/telegram/link/complete`, {
                              method: "POST",
                              credentials: "include",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({
                                link_code: pending.link_code,
                                telegram_user_id: "tg_user_smoke",
                                telegram_chat_id: "chat_smoke",
                                telegram_username: "powerpack",
                                telegram_display_name: "Power Pack",
                                last_resume_token_ref: "resume_tg_smoke"
                              })
                            });
                            if (!completeResponse.ok) {
                              throw new Error(`telegram mock link completion failed with ${completeResponse.status}`);
                            }
                            return completeResponse.json();
                        }""",
                        api_base,
                    )
                    page.get_by_role("button", name="Refresh Runtime").click()
                    expect(page.locator("#telegramCard")).to_contain_text("linked")
                    expect(page.locator("#telegramCard")).to_contain_text("@powerpack")
                    expect(page.locator("#telegramCard")).to_contain_text("Web-only control")
                    checks.append(
                        {
                            "check": "telegram_link_state",
                            "detail": "browser issued a Telegram link, completed the smoke-only mock bind, and rendered the linked companion state while keeping workspace broker control web-only",
                        }
                    )

                    page.locator("#brokerWorkspaceIdInput").fill("workspace_browser_smoke")
                    page.locator("#brokerProjectIdsInput").fill("project_release, project_ops")
                    page.locator("#brokerEnabledInput").check()
                    page.get_by_role("button", name="Save Broker Scope").click()
                    expect(page.locator("#brokerCard")).to_contain_text("workspace_browser_smoke")
                    expect(page.locator("#brokerCard")).to_contain_text("enabled")
                    expect(page.locator("#brokerCard")).to_contain_text("project_release, project_ops")
                    expect(page.locator("#brokerCard")).to_contain_text("provider disabled")
                    expect(page.locator("#notice")).to_contain_text("Provider is still unavailable")

                    page.locator("#brokerQueryInput").fill("release evidence")
                    page.locator("#brokerQueryProjectIdInput").fill("project_release")
                    page.get_by_role("button", name="Probe Broker").click()
                    expect(page.locator("#brokerCard")).to_contain_text("Last broker probe")
                    expect(page.locator("#brokerCard")).to_contain_text("unavailable")
                    expect(page.locator("#brokerCard")).to_contain_text("No scoped results")
                    expect(page.locator("#brokerCard")).to_contain_text("project_release")
                    checks.append(
                        {
                            "check": "memory_broker_opt_in_and_probe",
                            "detail": "browser stored workspace-scoped broker opt-in state from the web shell, then walked the web-only broker probe path and rendered the disabled-provider audit result without expanding Telegram beyond the summary-safe boundary",
                        }
                    )

                    page.locator("#memoryContentInput").fill("Prefers concise answers from the browser smoke flow.")
                    page.locator("#memorySourceNoteInput").fill("Captured from browser smoke")
                    page.get_by_role("button", name="Save Memory").click()
                    expect(page.locator("#memoryList")).to_contain_text("Prefers concise answers from the browser smoke flow.")
                    expect(page.locator("#memoryList")).to_contain_text("Captured from browser smoke")
                    checks.append(
                        {
                            "check": "memory_save_with_provenance",
                            "detail": "browser saved a memory item and rendered its provenance note",
                        }
                    )

                    page.evaluate(
                        """async (apiBase) => {
                            const sessionResponse = await fetch(`${apiBase}/v1/auth/session`, {
                              credentials: "include"
                            });
                            const session = await sessionResponse.json();
                            const checkpointPayload = {
                              user_id: session.user_id,
                              device_session_id: session.device_session_id,
                              conversation_id: "conv_browser_smoke",
                              last_message_id: "msg_browser_smoke",
                              draft_text: "Resume from Telegram handoff",
                              selected_memory_ids: [],
                              route: "/chat/conv_browser_smoke",
                              surface: "telegram",
                              handoff_kind: "resume_link",
                              resume_token_ref: "resume_tg_smoke",
                              last_surface_at: "2026-03-10T00:00:00Z",
                              updated_at: "2026-03-10T00:00:00Z",
                              version: 1,
                              base_version: null,
                              force: false
                            };
                            const checkpointResponse = await fetch(`${apiBase}/v1/checkpoints/current`, {
                              method: "PUT",
                              credentials: "include",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify(checkpointPayload)
                            });
                            if (!checkpointResponse.ok) {
                              throw new Error(`checkpoint setup failed with ${checkpointResponse.status}`);
                            }
                            return checkpointResponse.json();
                        }""",
                        api_base,
                    )
                    page.get_by_role("button", name="Refresh Runtime").click()
                    expect(page.locator("#checkpointContinuity")).to_contain_text("telegram")
                    expect(page.locator("#checkpointContinuity")).to_contain_text("resume link")
                    expect(page.locator("#checkpointContinuity")).to_contain_text("resume_tg_smoke")
                    checks.append(
                        {
                            "check": "checkpoint_continuity_metadata",
                            "detail": "browser refreshed a Telegram handoff checkpoint and rendered its surface, handoff kind, and resume token metadata",
                        }
                    )

                    page.locator("#reminderAtInput").fill("2030-03-11T09:00")
                    page.locator("#reminderMessageInput").fill("Observe browser smoke follow-up")
                    page.locator("#reminderFollowUpActionInput").select_option("retry")
                    page.locator("#reminderMaxAttemptsInput").fill("3")
                    page.locator("#reminderRetryDelayInput").fill("120")
                    page.get_by_role("button", name="Schedule Reminder").click()
                    expect(page.locator("#remindersCard")).to_contain_text("Observe browser smoke follow-up")
                    expect(page.locator("#remindersCard")).to_contain_text("scheduled")
                    expect(page.locator("#remindersCard")).to_contain_text("Retry ready")
                    expect(page.locator("#remindersCard")).to_contain_text("Retry on Telegram failure")
                    expect(page.locator("#remindersCard")).to_contain_text("0 / 3")
                    expect(page.locator("#telegramCard")).to_contain_text("1 scheduled")
                    expect(page.locator("#telegramCard")).to_contain_text("1 retry ready")
                    expect(page.locator("#jobsCard")).to_contain_text("follow up policy on failure")
                    expect(page.locator("#jobsCard")).to_contain_text("follow up policy max attempts")
                    checks.append(
                        {
                            "check": "reminder_follow_up_policy_surface",
                            "detail": "browser scheduled a retry-configured Telegram reminder and rendered its retry-ready follow-up policy/state across the reminder card, Telegram summary-safe card, and runtime ledger",
                        }
                    )

                    page.locator("#reminderAtInput").fill("2030-03-11T09:30")
                    page.locator("#reminderMessageInput").fill("Cancel browser smoke reminder")
                    page.get_by_role("button", name="Schedule Reminder").click()
                    page.locator("#remindersCard .reminder-item").filter(has_text="Cancel browser smoke reminder").get_by_role(
                        "button",
                        name="Cancel Reminder",
                    ).click()
                    expect(page.locator("#remindersCard")).to_contain_text("Cancel browser smoke reminder")
                    expect(page.locator("#remindersCard")).to_contain_text("canceled")
                    expect(page.locator("#telegramCard")).to_contain_text("1 canceled")
                    expect(page.locator("#telegramCard")).to_contain_text("1 retry ready")
                    expect(page.locator("#jobsCard")).to_contain_text("reminder delivery")
                    expect(page.locator("#jobsCard")).to_contain_text("Observe browser smoke follow-up")
                    expect(page.locator("#jobsCard")).to_contain_text("Cancel browser smoke reminder")
                    checks.append(
                        {
                            "check": "reminder_schedule_and_cancel",
                            "detail": "browser preserved the existing schedule/cancel path while keeping the retry-configured reminder visible across the reminder card, Telegram summary, and runtime ledger",
                        }
                    )

                    with page.expect_download() as download_info:
                        page.get_by_role("button", name="Export Memory").click()
                    download = download_info.value
                    suggested_filename = download.suggested_filename
                    assert suggested_filename.endswith(".json")
                    expect(page.locator("#jobsCard")).to_contain_text("memory export")
                    expect(page.locator("#jobsCard")).to_contain_text("succeeded")
                    checks.append(
                        {
                            "check": "memory_export_download",
                            "detail": f"browser received a JSON download named {suggested_filename} and surfaced the export job in the runtime ledger",
                        }
                    )

                    page.get_by_role("button", name="Delete").click()
                    expect(page.locator("#notice")).to_contain_text("Purge queued")
                    expect(page.locator("#memoryList")).to_contain_text("deleted")
                    expect(page.locator("#jobsCard")).to_contain_text("memory delete")
                    expect(page.locator("#jobsCard")).to_contain_text("queued")
                    checks.append(
                        {
                            "check": "memory_delete_receipt_and_job",
                            "detail": "browser surfaced the pending purge receipt after delete and rendered the queued delete job audit trail",
                        }
                    )

                    page.screenshot(path=str(screenshot_path), full_page=True)
                    browser.close()
            except Error as exc:
                raise RuntimeError(
                    "Playwright Chromium could not launch. Install it with `python3 -m playwright install chromium`."
                ) from exc

    report = {
        "timestamp": utc_now_iso(),
        "status": "pass",
        "bundle_id": runtime_seed.bundle_id,
        "app_version": runtime_seed.app_version,
        "screenshot": str(screenshot_path),
        "checks": checks,
    }
    write_json(output_path, report)
    write_json(
        e2e_score_path,
        {
            "total_score": 20,
            "max_score": 20,
            "checks": {
                "assistant_web_auth_round_trip": {
                    "check": "assistant_web_auth_round_trip",
                    "score": 10,
                    "max": 10,
                    "detail": "Mock auth redirect, callback, Telegram link initiation, and active session refresh completed in Chromium headless.",
                },
                "assistant_web_memory_controls": {
                    "check": "assistant_web_memory_controls",
                    "score": 10,
                    "max": 10,
                    "detail": "Continuity metadata render plus reminder schedule/cancel, memory save, export, delete receipt, and auditable jobs completed in Chromium headless.",
                },
            },
            "timestamp": utc_now_iso(),
        },
    )

    print(f"wrote browser smoke report to {output_path}")
    print(f"wrote browser smoke screenshot to {screenshot_path}")
    print(f"wrote e2e score artifact to {e2e_score_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
