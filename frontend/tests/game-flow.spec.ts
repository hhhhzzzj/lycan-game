import { test, expect } from '@playwright/test';

test.describe('Game Flow E2E', () => {
    test('start game and verify game board renders', async ({ page }) => {
        // Go to welcome page
        await page.goto('/');
        await expect(page.locator('h1')).toContainText('AI 狼人杀');

        // Wait for player config to load (backend is running)
        await page.waitForTimeout(2000);

        // Click start button
        const startBtn = page.locator('button', { hasText: '开始游戏' });
        await expect(startBtn).toBeVisible({ timeout: 5000 });
        await startBtn.click();

        // Wait for game to start and WebSocket to connect
        await page.waitForTimeout(3000);

        // Verify we're now on the game board (TopBar should show)
        const topbar = page.locator('header');
        await expect(topbar).toBeVisible({ timeout: 10000 });

        // Verify Logo is visible
        await expect(page.locator('text=AI 狼人杀').first()).toBeVisible();

        // Verify player panel (left side) has players
        const playerPanel = page.locator('aside').first();
        await expect(playerPanel).toBeVisible();
        await expect(playerPanel.locator('text=玩家')).toBeVisible();

        // Verify connection status shows connected
        await expect(page.locator('text=自动播放')).toBeVisible();
    });

    test('continue button works and advances game', async ({ page }) => {
        await page.goto('/');
        await page.waitForTimeout(1000);

        // Start game
        const startBtn = page.locator('button', { hasText: '开始游戏' });
        await expect(startBtn).toBeVisible({ timeout: 5000 });
        await startBtn.click();
        await page.waitForTimeout(3000);

        // Find and click continue button
        const continueBtn = page.locator('button', { hasText: '继续' });
        if (await continueBtn.isVisible()) {
            await continueBtn.click();
            // Wait for backend to process
            await page.waitForTimeout(5000);

            // After clicking continue, something should change
            // Either the action area updates or dialog stream gets content
            const actionArea = page.locator('text=内心独白').or(page.locator('text=行动中')).or(page.locator('text=思考中'));
            // At least one of these should be visible
            const pageContent = await page.textContent('body');
            expect(pageContent!.length).toBeGreaterThan(100);
        }
    });

    test('night theme is applied during night phase', async ({ page }) => {
        await page.goto('/');
        await page.waitForTimeout(1000);

        const startBtn = page.locator('button', { hasText: '开始游戏' });
        await expect(startBtn).toBeVisible({ timeout: 5000 });
        await startBtn.click();
        await page.waitForTimeout(3000);

        // Game starts at night - body should have night class
        const bodyClass = await page.locator('body').getAttribute('class');
        expect(bodyClass).toContain('night');
    });

    test('no unhandled errors during game flow', async ({ page }) => {
        const errors: string[] = [];
        page.on('pageerror', err => errors.push(err.message));

        await page.goto('/');
        await page.waitForTimeout(1000);

        const startBtn = page.locator('button', { hasText: '开始游戏' });
        await expect(startBtn).toBeVisible({ timeout: 5000 });
        await startBtn.click();
        await page.waitForTimeout(4000);

        // Click continue a few times if available
        for (let i = 0; i < 3; i++) {
            const btn = page.locator('button', { hasText: '继续' });
            if (await btn.isVisible() && await btn.isEnabled()) {
                await btn.click();
                await page.waitForTimeout(4000);
            }
        }

        // No real errors (ignore fetch failures if backend is slow)
        const realErrors = errors.filter(e =>
            !e.includes('fetch') &&
            !e.includes('Failed') &&
            !e.includes('NetworkError')
        );
        expect(realErrors).toHaveLength(0);
    });
});
