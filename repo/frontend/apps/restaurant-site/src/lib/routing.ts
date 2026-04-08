export function buildOrderingHref(
  baseUrl: string,
  mode: "pickup" | "delivery"
): string {
  const url = new URL(baseUrl);
  url.searchParams.set("mode", mode);
  return url.toString();
}
