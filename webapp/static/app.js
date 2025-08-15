// webapp/static/app.js
// — автоподсказки городов из Nominatim (OpenStreetMap) и отправка данных в Telegram

(function () {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.expand(); // раскрыть WebApp на весь экран
    tg.MainButton.hide();
  }

  const form = document.getElementById('hdForm');
  const cityInput = document.getElementById('city');
  const datalist = document.getElementById('citylist');
  const submitBtn = document.getElementById('submitBtn');

  // --- автоподсказки для города ---
  let cityTimer = null;
  cityInput.addEventListener('input', () => {
    const q = cityInput.value.trim();
    if (q.length < 3) { datalist.innerHTML = ''; return; }

    clearTimeout(cityTimer);
    cityTimer = setTimeout(async () => {
      try {
        const resp = await fetch(
          'https://nominatim.openstreetmap.org/search?format=json&accept-language=ru&q=' + encodeURIComponent(q),
          { headers: { 'User-Agent': 'SabinaEnergyHD/1.0' } }
        );
        const data = await resp.json();
        datalist.innerHTML = data.slice(0, 7).map(item => {
          const city = item.display_name.split(',')[0];
          return `<option value="${city}">`;
        }).join('');
      } catch (e) {
        console.log('city suggest error', e);
      }
    }, 350);
  });

  // --- отправка формы в Telegram (web_app_data) ---
  form.addEventListener('submit', (e) => {
    e.preventDefault();

    const fd = new FormData(form);
    const payload = {
      name:   (fd.get('name')   || '').trim(),
      gender: fd.get('gender')  || '',
      date:   fd.get('date')    || '',
      time:   fd.get('time')    || '',
      city:   (fd.get('city')   || '').trim()
    };

    // валидация по минимуму
    if (!payload.name || !payload.gender || !payload.date || !payload.time || !payload.city) {
      alert('Заполни, пожалуйста, все поля.');
      return;
    }

    submitBtn.disabled = true; submitBtn.textContent = 'Отправляем…';

    try {
      if (tg && tg.sendData) {
        tg.sendData(JSON.stringify(payload));
        // опционально: закрыть форму автоматически
        setTimeout(() => tg.close && tg.close(), 600);
      } else {
        alert('Открой, пожалуйста, форму из Telegram-бота.');
      }
    } catch (e) {
      console.error(e);
      alert('Не удалось отправить. Попробуй ещё раз.');
      submitBtn.disabled = false; submitBtn.textContent = 'Рассчитать';
    }
  });
})();
