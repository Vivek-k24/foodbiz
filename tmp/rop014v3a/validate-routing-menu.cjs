const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = {};

  await page.goto('http://localhost:5176', { waitUntil: 'networkidle' });
  results.siteUrl = page.url();
  results.siteHasPickup = await page.getByRole('link', { name: 'Order Pickup' }).isVisible();
  results.siteHasDelivery = await page.getByRole('link', { name: 'Order Delivery' }).isVisible();

  await page.getByRole('link', { name: 'Order Pickup' }).click();
  await page.waitForURL('http://localhost:5173/**');
  await page.waitForLoadState('networkidle');
  results.pickupUrl = page.url();
  results.pickupContext = await page.locator('.contextCard .subheading').first().textContent();
  results.pickupCategoryCount = await page.locator('.categorySection').count();
  results.pickupItemCount = await page.locator('.menuCard').count();
  results.pickupFirstItems = await page.locator('.menuCard .subheading').evaluateAll(nodes => nodes.slice(0, 5).map((node) => node.textContent));
  await page.getByRole('button', { name: 'Add to Cart' }).first().click();
  results.pickupCartLines = await page.locator('.cartLine').count();
  results.pickupPlaceButton = await page.getByRole('button', { name: 'Place Pickup Order' }).isVisible();

  await page.goto('http://localhost:5176', { waitUntil: 'networkidle' });
  await page.getByRole('link', { name: 'Order Delivery' }).click();
  await page.waitForURL('http://localhost:5173/**');
  await page.waitForLoadState('networkidle');
  results.deliveryUrl = page.url();
  results.deliveryContext = await page.locator('.contextCard .subheading').first().textContent();
  results.deliveryCategoryCount = await page.locator('.categorySection').count();
  results.deliveryItemCount = await page.locator('.menuCard').count();
  await page.getByRole('button', { name: 'Add to Cart' }).first().click();
  results.deliveryCartLines = await page.locator('.cartLine').count();
  results.deliveryPlaceButton = await page.getByRole('button', { name: 'Place Delivery Order' }).isVisible();

  console.log(JSON.stringify(results, null, 2));
  await browser.close();
})();
