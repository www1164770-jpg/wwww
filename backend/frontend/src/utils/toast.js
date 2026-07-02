export function showToast(message, type = "info") {
  window.dispatchEvent(
    new CustomEvent("app-toast", {
      detail: { message, type, id: Date.now() },
    }),
  );
}

export function successToast(message) {
  showToast(message, "success");
}

export function errorToast(message = "操作失败，请稍后重试") {
  showToast(message, "error");
}
