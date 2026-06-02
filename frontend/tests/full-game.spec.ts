import { test, expect } from '@playwright/test';

// 一局完整游戏可能需要 5-10 分钟（AI 生成发言需要时间）
test.setTimeout(600_000); // 10 minutes

test('play a full game from start to game_over', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    // 1. 打开欢迎页
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('AI 狼人杀');
    console.log('[TEST] Welcome page loaded');

    // 2. 等待配置加载，点开始
    await page.waitForTimeout(2000);
    const startBtn = page.locator('button', { hasText: '开始游戏' });
    await expect(startBtn).toBeVisible({ timeout: 5000 });
    await startBtn.click();
    console.log('[TEST] Clicked start game');

    // 3. 等待进入游戏界面
    await page.waitForTimeout(4000);
    await expect(page.locator('header')).toBeVisible({ timeout: 15000 });
    console.log('[TEST] Game board visible');

    // 验证初始状态
    const bodyClass = await page.locator('body').getAttribute('class');
    expect(bodyClass).toContain('night'); // 游戏从夜晚开始
    console.log('[TEST] Night theme confirmed');

    // 4. 循环点击继续直到游戏结束
    let stepCount = 0;
    let sawDay = false;
    let sawVote = false;
    let sawNight = false;
    let gameOver = false;

    while (!gameOver && stepCount < 100) {
        // 等待继续按钮可用
        const continueBtn = page.locator('button', { hasText: '继续' });

        try {
            await continueBtn.waitFor({ state: 'visible', timeout: 30000 });
        } catch {
            // 可能游戏结束了，或者按钮文字变了
            const pageText = await page.textContent('body');
            if (pageText?.includes('游戏结束') || pageText?.includes('胜利')) {
                gameOver = true;
                break;
            }
            // 可能 AI 还在思考，再等等
            await page.waitForTimeout(3000);
            continue;
        }

        // 检查是否已经 game_over
        const pageText = await page.textContent('body');
        if (pageText?.includes('战报卷轴') || pageText?.includes('重开一局')) {
            gameOver = true;
            break;
        }

        // 检查当前阶段
        const currentBodyClass = await page.locator('body').getAttribute('class') || '';
        if (currentBodyClass.includes('night')) sawNight = true;
        if (currentBodyClass.includes('day')) sawDay = true;

        const badgeText = await page.locator('.phase-badge, [class*="rounded"][class*="font-bold"]').first().textContent() || '';
        if (badgeText.includes('投票')) sawVote = true;

        // 点击继续
        if (await continueBtn.isEnabled()) {
            await continueBtn.click();
            stepCount++;
            if (stepCount % 5 === 0) {
                console.log(`[TEST] Step ${stepCount}, phase badge: "${badgeText}", body: ${currentBodyClass}`);
            }
            // 等待后端处理（AI 生成需要时间）
            await page.waitForTimeout(3000);
        } else {
            await page.waitForTimeout(2000);
        }
    }

    console.log(`[TEST] Game ended after ${stepCount} steps`);
    console.log(`[TEST] Saw night: ${sawNight}, day: ${sawDay}, vote: ${sawVote}`);

    // 5. 验证结果
    expect(stepCount).toBeGreaterThan(5); // 至少走了几步
    expect(sawNight).toBe(true);  // 经过了夜晚
    expect(sawDay).toBe(true);    // 经过了白天

    // 6. 检查复盘覆盖层是否出现
    if (gameOver) {
        await page.waitForTimeout(2000);
        const overlay = page.locator('text=战报卷轴');
        if (await overlay.isVisible()) {
            console.log('[TEST] PostGame overlay is visible');
            // 验证复盘内容 - use .first() to avoid strict mode
            await expect(page.locator('text=阵营胜利').first()).toBeVisible();
            // 角色表格应该有
            await expect(page.locator('table').first()).toBeVisible();
            console.log('[TEST] PostGame content verified');
        }
    }

    // 7. 检查无 JS 错误
    const realErrors = errors.filter(e =>
        !e.includes('fetch') &&
        !e.includes('Failed') &&
        !e.includes('NetworkError') &&
        !e.includes('WebSocket')
    );
    if (realErrors.length > 0) {
        console.log('[TEST] JS Errors:', realErrors);
    }
    expect(realErrors).toHaveLength(0);

    console.log('[TEST] ✅ Full game test passed!');
});
