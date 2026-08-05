function getFavoriteErrorPayload(error) {
  const responsePayload = error?.response?.data;
  if (!responsePayload || typeof responsePayload !== "object") return {};
  return responsePayload;
}

export function getFavoriteErrorDetails(error) {
  const payload = getFavoriteErrorPayload(error);
  const nested =
    payload.data && typeof payload.data === "object" ? payload.data : {};
  const status = error?.response?.status;
  const rawCode =
    payload.code ??
    payload.error_code ??
    nested.code ??
    nested.error_code ??
    "";
  return {
    payload,
    nested,
    status,
    code: String(rawCode || "")
      .trim()
      .toUpperCase(),
  };
}

export function normalizeFavoriteError(error) {
  const { payload, nested, status, code } = getFavoriteErrorDetails(error);

  if (status === 401 || ["AUTH_REQUIRED", "AUTH_INVALID"].includes(code)) {
    return {
      code: "AUTH_REQUIRED",
      status: 401,
      message: "请先登录后操作收藏",
    };
  }

  if (status === 403 || code === "FORBIDDEN") {
    return {
      code: "FORBIDDEN",
      status: 403,
      message: "当前账号无权访问收藏数据",
    };
  }

  if (status === 409 || code === "FAVORITE_ALREADY_EXISTS") {
    return {
      code: code || "FAVORITE_ALREADY_EXISTS",
      status: 409,
      message: "该网站已经收藏",
    };
  }

  if (code === "SITE_NOT_FOUND") {
    return {
      code,
      status: status || 404,
      message: "该网站暂时无法收藏",
    };
  }

  if (code === "INVALID_SITE" || status === 422) {
    return {
      code: code || "INVALID_SITE",
      status: 422,
      message: "网站信息不完整，暂时无法收藏",
    };
  }

  if (status === 404) {
    return {
      code: code || "SITE_NOT_FOUND",
      status: 404,
      message: "该网站暂时无法收藏",
    };
  }

  if (
    status === 503 ||
    [
      "FAVORITE_DATABASE_ERROR",
      "DATABASE_UNAVAILABLE",
      "DATABASE_ERROR",
    ].includes(code)
  ) {
    return {
      code: code || "FAVORITE_DATABASE_ERROR",
      status: status || 503,
      message: "收藏服务暂时不可用，请稍后重试",
    };
  }

  if (status === 500) {
    return {
      code: code || "FAVORITE_SERVER_ERROR",
      status: 500,
      message: "收藏服务出现异常，请稍后重试",
    };
  }

  if (error?.code === "ECONNABORTED" || error?.code === "ETIMEDOUT") {
    return {
      code: "TIMEOUT",
      status,
      message: "收藏请求超时，状态已恢复",
    };
  }

  if (error?.code === "ERR_NETWORK" || !error?.response) {
    return {
      code: "NETWORK_ERROR",
      status,
      message: "无法连接收藏服务，请检查后端状态",
    };
  }

  return {
    code:
      code || (status === 500 ? "FAVORITE_SERVER_ERROR" : "FAVORITES_ERROR"),
    status,
    message:
      payload.msg ||
      payload.message ||
      nested.msg ||
      nested.message ||
      "收藏服务出现异常，请稍后重试",
  };
}
