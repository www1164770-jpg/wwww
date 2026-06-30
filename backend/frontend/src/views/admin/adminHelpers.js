export function readData(response, fallback = []) {
  const payload = response?.data?.data ?? response?.data ?? fallback;
  return payload?.items ?? payload ?? fallback;
}
