import { ref } from "vue";
import {
  careerDirections,
  getOccupation,
} from "../../utils/occupation.js";

export function useCareerSelector(initialOccupation = "") {
  const initialDirection = getOccupation(initialOccupation)?.direction || "";
  const activeDirection = ref(initialDirection);

  function selectDirection(directionName) {
    if (
      careerDirections.some((direction) => direction.name === directionName)
    ) {
      activeDirection.value = directionName;
    }
  }

  function backToDirections() {
    activeDirection.value = "";
  }

  function syncWithOccupation(occupation) {
    const direction = getOccupation(occupation)?.direction;
    if (direction) activeDirection.value = direction;
  }

  return {
    activeDirection,
    backToDirections,
    selectDirection,
    syncWithOccupation,
  };
}

