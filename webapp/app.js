// === НАСТРОЙКИ ===
// URL калькулятора (куда редиректим после отправки)
const FREE_CALC_URL = "https://human-design.space/dizajn-cheloveka-raschet-karty/#/";
// URL веб-приложения Google Apps Script (…/exec) — ВСТАВЬ СВОЙ
const LEAD_FORM_URL = "PUT_YOUR_APPS_SCRIPT_EXEC_URL_HERE";

// === УТИЛИТЫ ===
const $ = (id) => document.getElementById(id);
const EMAIL_RE = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;

function safeFetch(url, payload) {
  if (!url) return Promise.resolve();
  return fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload),
  }).catch(() => {}); // молча игнорим сетевые ошибки
}

function redirectToCalc() {
  try {
    // Внутри Telegram WebApp редирект в том же webview — норм
    window.location.href = FREE_CALC_URL;
  } catch (e) {
    // На всякий случай
    window.open(FREE_CALC_URL, "_blank");
  }
}

// === ОСНОВА ===
window.addEventListener("DOMContentLoaded", () => {
  const form = $("hd-form");
  const btn  = $("submit");

  // Немного UI
  btn.disabled = false;
  btn.textContent = "Отправить и перейти к расчёту";

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    btn.disabled = true;
    btn.textContent = "Отправляем…";

    // Собираем данные
    const payload = {
      name:   $("name").value.trim(),
      gender: $("gender").value,
      date:   $("date").value,  // yyyy-mm-dd
      time:   $("time").value,  // hh:mm
      city:   $("city").value.trim(),
      email:  $("email").value.trim(),
      source: "web",
    };

    // Простая валидация (email необязателен, но если ввели — проверим)
    if (payload.email && !EMAIL_RE.test(payload.email)) {
      alert("Пожалуйста, проверь e-mail.");
      btn.disabled = false;
      btn.textContent = "Отправить и перейти к расчёту";
      return;
    }

    // 1) Логируем лида в Google Sheets (через Apps Script)
    await safeFetch(LEAD_FORM_URL, {
      ...payload,
      tag: "lead_from_webapp"
    });

    // 2) Отправляем те же данные в Telegram-бота (если форма открыта как WebApp)
    if (window.Telegram && window.Telegram.WebApp && Telegram.WebApp.sendData) {
      try {
        Telegram.WebApp.sendData(JSON.stringify(payload));
      } catch (_) {}
    }

    // 3) Переходим на сайт расчёта
    redirectToCalc();
  });
});
