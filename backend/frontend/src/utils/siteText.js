function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Removes a duplicated card-title prefix from a website description.
 *
 * Only an exact site name at the beginning followed by a supported separator
 * is removed, so regular sentences that merely mention the website remain
 * untouched.
 */
export function cleanSiteDescription(name, description) {
  const text = String(description ?? "").trim();
  const siteName = String(name ?? "").trim();

  if (!text || !siteName) return text;

  const prefix = new RegExp(
    `^${escapeRegExp(siteName)}\\s*(?:[:：]|-|–|—)\\s*`,
    "i",
  );
  return text.replace(prefix, "").trim();
}
