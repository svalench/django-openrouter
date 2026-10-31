"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("or-dashboard-filters");
    if (!(form instanceof HTMLFormElement)) {
        return;
    }
    form.querySelectorAll("[data-auto-submit]").forEach((control) => {
        control.addEventListener("change", () => {
            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
                return;
            }
            form.submit();
        });
    });
});
