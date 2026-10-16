import { expect, test } from '@playwright/test'

test('development ForkCast harness is not served by the production application', async ({ request }) => {
  const response = await request.get('/contract-tests/preview.html')
  expect(response.status()).toBe(404)
})
