document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-confirm-close]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!confirm("This will permanently delete your demo account and transaction history. Continue?")) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('input[inputmode="numeric"]').forEach((input) => {
    input.addEventListener("input", () => {
      if (input.name === "card_number" || input.name === "receiver_card" ||
          input.name === "pin" || input.name === "confirm_pin") {
        input.value = input.value.replace(/\D/g, "");
      }
    });
  });

  const flashes = document.querySelectorAll(".flash");
  flashes.forEach((flash) => {
    window.setTimeout(() => {
      flash.classList.add("flash-hide");
    }, 5000);
  });
});
