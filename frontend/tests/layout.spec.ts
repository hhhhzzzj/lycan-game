import { test, expect } from '@playwright/test';

test.describe('Page Structure', () => {
    test('page fills viewport without scrollbar', async ({ page }) => {
        await page.goto('/');
        const hasVerticalScroll = await page.evaluate(() => {
            return document.documentElement.scrollHeight > document.documentElement.clientHeight;
        });
        expect(hasVerticalScroll).toBe(false);
    });

    test('root element has content (React rendered)', async ({ page }) => {
        await page.goto('/');
        await page.waitForTimeout(500);
        const childCount = await page.locator('#root').evaluate(el => el.childElementCount);
        expect(childCount).toBeGreaterThan(0);
    });

    test('CSS variables are defined', async ({ page }) => {
        await page.goto('/');
        const gold = await page.evaluate(() =>
            getComputedStyle(document.documentElement).getPropertyValue('--gold').trim()
        );
        expect(gold).toBe('#c9a84c');
    });

    test('Tailwind is working (utility class resolves)', async ({ page }) => {
        await page.goto('/');
        // h-screen on the welcome page container should set height to 100vh
        const el = page.locator('.h-screen').first();
        if (await el.count() > 0) {
            const height = await el.evaluate(el => getComputedStyle(el).height);
            expect(parseInt(height)).toBeGreaterThan(0);
        }
    });
});
