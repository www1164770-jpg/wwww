export async function runListRequest(loader) {
  try {
    const value = await loader();
    const items = Array.isArray(value) ? value : [];
    return {
      status: items.length ? "success" : "empty",
      items,
      error: null,
    };
  } catch (error) {
    return {
      status: "error",
      items: [],
      error,
    };
  }
}

