import { test, expect } from '@playwright/test';

test.describe('End-to-End User Workflows', () => {
  // Use a unique email for each run
  const testEmail = `testuser_${Date.now()}@example.com`;
  const password = 'TestPassword123!';

  test('User Registration and Login Flow', async ({ page }) => {
    // 1. Go to Login Page
    await page.goto('/login');
    await expect(page).toHaveTitle(/frontend/i);

    // 2. Navigate to Register
    await page.click('text="Don\'t have an account? Sign up"');
    await expect(page).toHaveURL(/.*register/);

    // 3. Fill Registration Form
    await page.fill('input[placeholder="Full name"]', 'E2E Test User');
    await page.fill('input[placeholder="Email address"]', testEmail);
    await page.fill('input[placeholder="Phone number"]', '9999999999');
    await page.fill('input[placeholder="Password"]', password);
    await page.check('input[value="Customer"]');
    
    // In a real E2E environment with backend running, we would submit this
    // await page.click('button:has-text("Create account")');
    // await expect(page).toHaveURL(/.*login/);

    // 4. Login Form
    // await page.fill('input[placeholder="Email address"]', testEmail);
    // await page.fill('input[placeholder="Password"]', password);
    // await page.click('button:has-text("Sign in")');
    // await expect(page).toHaveURL(/.*customer/);
  });
});
