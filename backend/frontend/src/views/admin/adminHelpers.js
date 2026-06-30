export function readData(response, fallback = []) {
  const payload = response?.data?.data ?? response?.data ?? fallback;
  return (
    payload?.items ?? payload?.users ?? payload?.comments ?? payload ?? fallback
  );
}

export function toDate(value) {
  if (!value) return "-";
  return String(value).slice(0, 10);
}

export function boolText(value) {
  return value ? "是" : "否";
}
