(function () {
  "use strict";
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const T = (() => { try { return JSON.parse(document.getElementById("i18n-strings").textContent); } catch (e) { return {}; } })();
  const t = (key, fallback) => T[key] || fallback;
  const LANG = document.documentElement.lang || undefined;

  // Mobile navigation
  const toggle = $(".nav-toggle");
  const nav = $(".main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open);
      toggle.innerHTML = open ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-bars"></i>';
    });
  }

  // Dropdowns
  $$("[data-dropdown]").forEach((btn) => {
    const menu = document.getElementById(btn.dataset.dropdown);
    btn.addEventListener("click", (e) => { e.stopPropagation(); menu.classList.toggle("open"); });
  });
  document.addEventListener("click", () => $$(".dropdown.open").forEach((m) => m.classList.remove("open")));

  // Flash messages auto-dismiss
  $$(".messages .alert").forEach((el, i) => {
    const close = () => { el.style.transition = "opacity .3s"; el.style.opacity = 0; setTimeout(() => el.remove(), 300); };
    $(".close", el)?.addEventListener("click", close);
    setTimeout(close, 5000 + i * 600);
  });

  // Password visibility toggle
  $$(".toggle-pass").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.parentElement.querySelector("input");
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.innerHTML = show ? '<i class="fa-regular fa-eye-slash"></i>' : '<i class="fa-regular fa-eye"></i>';
    });
  });

  // Signup: show doctor-only fields
  const doctorFields = $("#doctor-fields");
  if (doctorFields) {
    const sync = () => {
      const role = $('input[name="role"]:checked');
      doctorFields.hidden = !role || role.value !== "doctor";
    };
    $$('input[name="role"]').forEach((r) => r.addEventListener("change", sync));
    sync();
  }

  // Booking: day chips + slot picker
  const booking = $("[data-booking]");
  if (booking) {
    const dateInput = $("#id_date", booking);
    const timeInput = $("#id_time", booking);
    const grid = $("[data-slots]", booking);
    const summary = $("[data-summary]", booking);
    const url = booking.dataset.slotsUrl;
    const initialTime = timeInput.value ? timeInput.value.slice(0, 5) : "";

    const renderSlots = (slots) => {
      grid.innerHTML = "";
      if (!slots.length) {
        grid.innerHTML = `<p class="text-muted text-sm mb-0">${t("noSlots", "No free slots on this day. Please choose another date.")}</p>`;
        return;
      }
      slots.forEach((s) => {
        const b = document.createElement("button");
        b.type = "button"; b.className = "slot"; b.textContent = s.label; b.dataset.value = s.value;
        if (s.value === (timeInput.value || "").slice(0, 5)) b.classList.add("selected");
        b.addEventListener("click", () => {
          $$(".slot", grid).forEach((x) => x.classList.remove("selected"));
          b.classList.add("selected");
          timeInput.value = s.value;
          if (summary) summary.textContent = `${new Date(dateInput.value + "T00:00").toLocaleDateString(LANG, { weekday: "long", month: "short", day: "numeric" })} ${t("at", "at")} ${s.label}`;
        });
        grid.appendChild(b);
      });
    };

    const load = (keepTime) => {
      if (!keepTime) timeInput.value = "";
      if (summary) summary.textContent = t("noTime", "No time selected");
      $$(".day-chip", booking).forEach((c) => c.classList.toggle("selected", c.dataset.date === dateInput.value));
      if (!dateInput.value) { grid.innerHTML = `<p class="text-muted text-sm mb-0">${t("selectDate", "Select a date to see available times.")}</p>`; return; }
      grid.innerHTML = `<p class="text-muted text-sm mb-0"><i class="fa-solid fa-spinner fa-spin"></i> ${t("loading", "Loading slots…")}</p>`;
      fetch(`${url}?date=${encodeURIComponent(dateInput.value)}`, { headers: { Accept: "application/json" } })
        .then((r) => r.json())
        .then((data) => renderSlots(data.slots || []))
        .catch(() => { grid.innerHTML = `<p class="text-danger text-sm">${t("loadError", "Could not load slots. Please retry.")}</p>`; });
    };

    $$(".day-chip:not(.disabled)", booking).forEach((chip) => {
      chip.addEventListener("click", () => { dateInput.value = chip.dataset.date; load(false); });
    });
    dateInput.addEventListener("change", () => load(false));
    if (initialTime) timeInput.value = initialTime;
    load(true);
  }

  // Health metric form: only show diastolic for blood pressure
  const metricType = $("#id_metric_type");
  const secondary = $("#group-value_secondary");
  if (metricType && secondary) {
    const sync = () => { secondary.hidden = metricType.value !== "blood_pressure"; };
    metricType.addEventListener("change", sync); sync();
  }

  // Confirm dangerous actions
  $$("[data-confirm]").forEach((el) => {
    el.addEventListener("submit", (e) => { if (!window.confirm(el.dataset.confirm)) e.preventDefault(); });
  });

  // Availability formset: add row
  const addBtn = $("[data-add-form]");
  if (addBtn) {
    addBtn.addEventListener("click", () => {
      const total = $('input[name$="-TOTAL_FORMS"]');
      const tpl = $("#empty-form").innerHTML.replace(/__prefix__/g, total.value);
      $("#formset-rows").insertAdjacentHTML("beforeend", tpl);
      total.value = parseInt(total.value, 10) + 1;
    });
  }
})();
