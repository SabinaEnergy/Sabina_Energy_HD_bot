// Простой сбор формы + отправка на наш /api/compute
async function submitForm(e){
  e.preventDefault();
  const btn = document.getElementById('submitBtn');
  btn.disabled = true; btn.innerText = 'Отправляем...';

  // читаем поля
  const name   = document.getElementById('name').value.trim();
  const gender = document.getElementById('gender').value;
  const date   = document.getElementById('date').value;   // ДД.ММ.ГГГГ
  const time   = document.getElementById('time').value;   // HH:MM
  const city   = document.getElementById('city').value;

  // если у тебя подключён автокомплит города, сюда можно добавить lat/lon/tz_offset
  const payload = { name, gender, date, time, city };

  try{
    const r = await fetch('/api/compute', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const j = await r.json();

    // если открыты внутри Telegram WebApp — просто открываем отчёт/сайт
    const dest = j.report_url || j.fallback_url;
    if(dest){
      // открываем в той же вкладке
      window.location.href = dest;
    }else{
      alert('Не удалось получить ссылку отчёта.');
      btn.disabled = false; btn.innerText = 'Рассчитать';
    }
  }catch(err){
    console.error(err);
    alert('Ошибка сети. Попробуйте ещё раз.');
    btn.disabled = false; btn.innerText = 'Рассчитать';
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('hd-form');
  form.addEventListener('submit', submitForm);
});
