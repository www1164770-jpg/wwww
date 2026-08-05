export function normalizeSite(site = {}) {
  const rawSiteId = site?.siteId ?? site?.site_id ?? site?.id ?? null;
  const siteId =
    rawSiteId === null || rawSiteId === undefined
      ? null
      : String(rawSiteId).trim() || null;
  const category = site?.category;

  return {
    ...site,
    siteId,
    id: siteId,
    name: site?.name ?? site?.title ?? site?.site_name ?? "未命名网站",
    url: site?.url ?? site?.website_url ?? site?.link ?? "",
    logoUrl: site?.logoUrl ?? site?.logo_url ?? site?.logo ?? site?.icon ?? "",
    summary:
      site?.summary ?? site?.description ?? site?.slogan ?? site?.intro ?? "",
    categoryName:
      site?.categoryName ??
      site?.category_name ??
      (typeof category === "object" ? category?.name : category) ??
      "",
  };
}
