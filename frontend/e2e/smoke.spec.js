import { expect, test } from '@playwright/test';

// Tomorrow's date in New York, "YYYY-MM-DD" (what the date input expects).
function tomorrowNY() {
  const fmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' });
  return fmt.format(new Date(Date.now() + 24 * 3600 * 1000));
}

test('a student signs in, posts an event, finds it, saves it, and sees the map', async ({ page }) => {
  const title = `Smoke study ${Date.now()}`;

  // Sign in (local dev sign-in; Microsoft is covered by backend tests).
  await page.goto('/map'); // signed out → bounced to the sign-in page
  await expect(page).toHaveURL(/\/$/);
  await page.getByLabel('School email').fill(`smoke${Date.now()}@my.sunywcc.edu`);
  await page.getByRole('button', { name: 'Sign in (dev)' }).click();
  await expect(page.getByRole('heading', { name: "What's on" })).toBeVisible();

  // Post an event for tomorrow 10–11am in TEC room 38.
  await page.getByRole('button', { name: 'New event' }).click();
  await page.getByLabel("What's happening?").fill(title);
  await page.getByRole('combobox', { name: 'Room' }).click();
  await page.getByRole('option', { name: 'TEC · Room 38' }).click();
  await page.getByLabel('Date', { exact: true }).fill(tomorrowNY());
  await page.getByLabel('Starts', { exact: true }).fill('10:00');
  await page.getByLabel('Ends', { exact: true }).fill('11:00');
  await page.getByRole('button', { name: 'Post' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();

  // It's on the calendar (list view)…
  await page.getByRole('navigation').getByRole('button', { name: 'Calendar' }).click();
  await page.getByRole('button', { name: 'List' }).click();
  const card = page.locator('.MuiCard-root', { hasText: title });
  await expect(card).toBeVisible();
  await expect(card).toContainText('10:00 AM – 11:00 AM · TEC · Room 38');

  // …save it, and it shows on Favorites.
  await card.getByRole('button', { name: 'Save' }).click();
  await expect(card.getByRole('button', { name: 'Unsave' })).toBeVisible();
  await page.getByRole('navigation').getByRole('button', { name: 'Favorites' }).click();
  await expect(page.locator('.MuiCard-root', { hasText: title })).toBeVisible();

  // The map loads the campus image and the TEC room pins.
  await page.getByRole('navigation').getByRole('button', { name: 'Map' }).click();
  await expect(page.getByAltText('Campus map')).toBeVisible();
  await expect(page.getByRole('button', { name: /TEC · Room 38/ })).toBeVisible();

  // Nothing overflows the phone width.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
