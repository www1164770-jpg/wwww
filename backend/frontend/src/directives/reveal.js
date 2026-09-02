const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
const DEFAULT_REVEAL_RATIO = 0.28;
const TALL_SECTION_REVEAL_RATIO = 0.22;
const RESET_RATIO = 0.08;
const STATE_GUARD_MS = 180;
const REVEAL_OPTIONS = {
  threshold: [0, 0.05, RESET_RATIO, 0.15, 0.2, 0.22, 0.28, 0.35, 0.5, 0.75, 1],
  rootMargin: "0px 0px -12% 0px",
};

let sectionObserver;
const observedSections = new Set();
const childObservers = new WeakMap();
const sectionStates = new WeakMap();

function getSectionState(section) {
  let state = sectionStates.get(section);
  if (state) return state;

  state = {
    current: "hidden",
    enterRatio: DEFAULT_REVEAL_RATIO,
    latestRatio: 0,
    lastChangeAt: 0,
    pendingTimer: 0,
    prepareFrame: 0,
    resetFrame: 0,
  };
  sectionStates.set(section, state);
  return state;
}

function stageLateChild(child) {
  if (
    child.classList.contains("reveal-complete") ||
    child.classList.contains("card-refresh-item")
  ) {
    return;
  }

  child.classList.add("reveal-late-child");
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      if (child.isConnected) child.classList.add("is-late-revealed");
    });
  });
}

function observeLateChildren(section) {
  if (typeof MutationObserver === "undefined") return;

  const childObserver = new MutationObserver((mutations) => {
    if (!section.classList.contains("is-revealed")) return;

    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof Element)) return;
        if (node.classList.contains("reveal-child")) stageLateChild(node);
        node.querySelectorAll?.(".reveal-child").forEach(stageLateChild);
      });
    });
  });

  childObserver.observe(section, { childList: true, subtree: true });
  childObservers.set(section, childObserver);
}

function markChildComplete(event) {
  const child = event.target;
  if (
    event.propertyName !== "transform" ||
    !(child instanceof Element) ||
    !child.classList.contains("reveal-child")
  ) {
    return;
  }

  child.classList.add("reveal-complete");
  child.classList.remove("reveal-late-child", "is-late-revealed");
}

function markRefreshComplete(event) {
  const child = event.target;
  if (
    event.animationName !== "card-refresh-in" ||
    !(child instanceof Element) ||
    !child.classList.contains("reveal-child")
  ) {
    return;
  }

  child.classList.add("reveal-complete");
}

function playSection(section, state) {
  window.cancelAnimationFrame(state.resetFrame);
  window.cancelAnimationFrame(state.prepareFrame);
  section.classList.remove("is-resetting");
  section.classList.add("is-preparing-reveal");
  section.dataset.revealState = "visible";

  state.prepareFrame = window.requestAnimationFrame(() => {
    state.prepareFrame = 0;
    if (state.current !== "visible") return;
    section.classList.add("is-revealed");
    section.classList.remove("is-preparing-reveal");
  });
}

function resetSection(section, state) {
  window.cancelAnimationFrame(state.prepareFrame);
  window.cancelAnimationFrame(state.resetFrame);
  section.classList.add("is-resetting");
  section.classList.remove("is-revealed", "is-preparing-reveal");
  section.dataset.revealState = "hidden";
  section.querySelectorAll(".reveal-child").forEach((child) => {
    child.classList.remove(
      "reveal-complete",
      "reveal-late-child",
      "is-late-revealed",
    );
  });

  state.resetFrame = window.requestAnimationFrame(() => {
    state.resetFrame = 0;
    if (state.current === "hidden") section.classList.remove("is-resetting");
  });
}

function commitSectionState(section, nextState) {
  const state = getSectionState(section);
  if (state.current === nextState) return;
  if (nextState === "visible" && state.latestRatio < state.enterRatio) return;
  if (nextState === "hidden" && state.latestRatio > RESET_RATIO) return;

  state.current = nextState;
  state.lastChangeAt = performance.now();
  if (nextState === "visible") playSection(section, state);
  else resetSection(section, state);
}

function requestSectionState(section, nextState) {
  const state = getSectionState(section);
  if (state.current === nextState) return;

  window.clearTimeout(state.pendingTimer);
  const remainingGuard =
    STATE_GUARD_MS - (performance.now() - state.lastChangeAt);
  if (remainingGuard <= 0) {
    commitSectionState(section, nextState);
    return;
  }

  state.pendingTimer = window.setTimeout(() => {
    state.pendingTimer = 0;
    commitSectionState(section, nextState);
  }, remainingGuard);
}

function handleSectionIntersections(entries) {
  entries.forEach((entry) => {
    const section = entry.target;
    const state = getSectionState(section);
    const rootHeight = entry.rootBounds?.height || window.innerHeight;
    const isTallSection = entry.boundingClientRect.height > rootHeight * 1.8;
    state.enterRatio = isTallSection
      ? TALL_SECTION_REVEAL_RATIO
      : DEFAULT_REVEAL_RATIO;
    state.latestRatio = entry.intersectionRatio;

    if (entry.intersectionRatio >= state.enterRatio) {
      requestSectionState(section, "visible");
    } else if (entry.intersectionRatio <= RESET_RATIO) {
      requestSectionState(section, "hidden");
    }
  });
}

function getSectionObserver() {
  if (
    sectionObserver ||
    typeof window === "undefined" ||
    !("IntersectionObserver" in window)
  ) {
    return sectionObserver;
  }

  sectionObserver = new IntersectionObserver(
    handleSectionIntersections,
    REVEAL_OPTIONS,
  );
  return sectionObserver;
}

export default {
  mounted(section) {
    section.classList.add("reveal-section");
    section.dataset.revealState = "hidden";
    getSectionState(section);
    section.addEventListener("transitionend", markChildComplete);
    section.addEventListener("animationend", markRefreshComplete);
    observeLateChildren(section);

    const reducedMotion = window.matchMedia?.(REDUCED_MOTION_QUERY).matches;
    const observer = getSectionObserver();

    if (reducedMotion || !observer) {
      const state = getSectionState(section);
      state.latestRatio = 1;
      state.enterRatio = 0;
      commitSectionState(section, "visible");
      return;
    }

    observedSections.add(section);
    observer.observe(section);
  },

  unmounted(section) {
    const state = getSectionState(section);
    window.clearTimeout(state.pendingTimer);
    window.cancelAnimationFrame(state.prepareFrame);
    window.cancelAnimationFrame(state.resetFrame);
    observedSections.delete(section);
    if (sectionObserver) {
      sectionObserver.disconnect();
      observedSections.forEach((observedSection) => {
        sectionObserver.observe(observedSection);
      });
    }
    childObservers.get(section)?.disconnect();
    childObservers.delete(section);
    sectionStates.delete(section);
    section.removeEventListener("transitionend", markChildComplete);
    section.removeEventListener("animationend", markRefreshComplete);
  },
};
