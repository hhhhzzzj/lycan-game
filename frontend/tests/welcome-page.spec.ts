import { test, expect } from '@playwright/test';

test.describe('WelcomePage', () => {
    test('renders without crashing', async ({ page }) => {
        await page.goto('/');
        // Should not show a blank page - verify root has content
        const root = page.locator('#root');
        await expect(root).not.toBeEmpty();
    });

    test('shows title "AI 狼人杀"', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('h1')).toContainText('AI 狼人杀');
    });

    test('shows narrative text', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=黑暗降临')).toBeVisible();
    });

    test('shows start button', async ({ page }) => {
        await page.goto('/');
        const btn = page.locator('button', { hasText: '开始游戏' });
        await expect(btn).toBeVisible();
    });

    test('has dark background (night theme by default)', async ({ page }) => {
        await page.goto('/');
        const body = page.locator('body');
        await expect(body).toHaveClass(/night/);
    });

    test('no console errors on load', async ({ page }) => {
        const errors: string[] = [];
        page.on('pageerror', err => errors.push(err.message));
        await page.goto('/');
        await page.waitForTimeout(1000);
        // Filter out expected fetch error (backend not running)
        const realErrors = errors.filter(e => !e.includes('fetch') && !e.includes('Failed'));
        expect(realErrors).toHaveLength(0);
    });

    test('font loads correctly (Cinzel)', async ({ page }) => {
        await page.goto('/');
        const title = page.locator('h1');
        const fontFamily = await title.evaluate(el => getComputedStyle(el).fontFamily);
        expect(fontFamily.toLowerCase()).toContain('cinzel');
    });
});
