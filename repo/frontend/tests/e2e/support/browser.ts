import type { Page } from "@playwright/test";

export async function installNoopWebSocket(page: Page): Promise<void> {
  await page.addInitScript(() => {
    class MockWebSocket {
      url: string;
      readyState = 1;
      onopen: ((event: Event) => void) | null = null;
      onclose: ((event: Event) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;

      constructor(url: string) {
        this.url = url;
        setTimeout(() => {
          this.onopen?.(new Event("open"));
        }, 0);
      }

      close(): void {
        this.readyState = 3;
        this.onclose?.(new Event("close"));
      }

      send(): void {
        // No-op for browser workflow tests.
      }
    }

    window.WebSocket = MockWebSocket as unknown as typeof window.WebSocket;
  });
}
