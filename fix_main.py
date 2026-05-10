with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

clean_funcs = """async def _run_notion_queue_sequential(
    settings: AppSettings,
    pending: list[NotionPendingSong],
) -> tuple[list[dict], bool]:
    results: list[dict] = []
    all_ok = True
    for i, row in enumerate(pending, start=1):
        logger.info(
            "[%s/%s] Notion → Mureka：%r (page=%s, instrumental=%s)",
            i,
            len(pending),
            row.song.song_title,
            row.notion_page_id,
            row.song.instrumental,
        )
        result = await run_song_generation(
            settings,
            row.song,
            attach_open_page=True,
            existing_notion_page_id=row.notion_page_id,
        )
        results.append(result.model_dump(mode="json"))
        if not result.success:
            all_ok = False

        if i % 8 == 0 and i < len(pending):
            logger.info("已連續送出 8 首，為避免排隊塞車，暫停 3 分鐘讓伺服器消化...")
            import asyncio
            await asyncio.sleep(180)

    return results, all_ok


async def _run_notion_queue(
    settings: AppSettings,
    pending: list[NotionPendingSong],
) -> tuple[list[dict], bool]:
    from app.utils.cdp_targets import list_page_target_ids_matching_url_async

    want = max(1, min(settings.notion_parallel_max, 10))
    if want <= 1 or len(pending) <= 1:
        return await _run_notion_queue_sequential(settings, pending)

    try:
        target_ids = await list_page_target_ids_matching_url_async(
            settings.browser_cdp_url,
            url_substrings=("mureka",),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("列舉 Chrome 分頁失敗（改為串行）：%s", exc)
        return await _run_notion_queue_sequential(settings, pending)

    eff = min(want, len(target_ids), len(pending))
    if eff < want:
        logger.warning(
            "NOTION_PARALLEL_MAX=%s 但偵測到 %s 個 URL 含 mureka 的分頁，本輪並行度調整為 %s",
            settings.notion_parallel_max,
            len(target_ids),
            eff,
        )
    if eff < 2:
        if want >= 2 and not target_ids:
            logger.warning(
                "未偵測到 Mureka 分頁：請預先開啟多個 Create Music 分頁，或將 NOTION_PARALLEL_MAX 設為 1"
            )
        return await _run_notion_queue_sequential(settings, pending)

    results: list[dict] = []
    all_ok = True
    for batch_start in range(0, len(pending), eff):
        batch = pending[batch_start : batch_start + eff]
        tids = target_ids[: len(batch)]
        logger.info(
            "Notion 佇列並行：第 %s–%s 筆，使用 %s 個分頁",
            batch_start + 1,
            batch_start + len(batch),
            len(tids),
        )
        coros = [
            run_song_generation(
                settings,
                row.song,
                attach_open_page=True,
                existing_notion_page_id=row.notion_page_id,
                cdp_focus_target_id=tid,
            )
            for row, tid in zip(batch, tids, strict=True)
        ]
        batch_results = await asyncio.gather(*coros)
        for r in batch_results:
            results.append(r.model_dump(mode="json"))
            if not r.success:
                all_ok = False
    return results, all_ok"""

start_idx = content.find('    return True\n') + len('    return True\n')
end_idx = content.find('async def _async_main() -> int:\n')

new_content = content[:start_idx] + '\n\n' + clean_funcs + '\n\n' + content[end_idx:]

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Fixed main.py!')
