import { defineStore } from "pinia";
import { ref } from "vue";

export const useAiAssistantStore = defineStore("aiAssistant", () => {
  const isOpen = ref(false);

  function openAssistant() {
    isOpen.value = true;
  }

  function closeAssistant() {
    isOpen.value = false;
  }

  function toggleAssistant() {
    isOpen.value = !isOpen.value;
  }

  return {
    isOpen,
    openAssistant,
    closeAssistant,
    toggleAssistant,
  };
});
