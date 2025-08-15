const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) tg.expand();

const $ = id => document.getElementById(id);
let gender = "Муж";

// Маски
IMask($('date'), { mask: '00.00.0000' });
IMask($('time'), { mask: '00:00' });

// Пол
$('male').addEventListener('click', ()=>{ gender="Муж";  $('male').classList.add('active'); $('female').classList.remove('active'); });
$('female').addEventListener('click', ()=>{ gender="Жен"; $('female').classList.add('active'); $('male').classList.remove('active'); });

// --- Автодополнение города (OpenStreetMap Nominatim) ---
const cityInput = $('city');
const list = $('cityList');
let cityTimer = null;

cityInput.addEventListener('input', ()=>{
  const q = cityInput.value.trim();
  if (q.length < 2){ list.hidden = true; list.innerHTML=''; return; }
  clearTimeout(cityTimer);
  cityTimer = setTimeout(()=> searchCity(q), 350);
});

document.addEventListener('click', (e)=>{
  if (!list.contains(e.target) && e.target !== cityInput) list.hidden = true;
});

function pickCity(item){
  const display = [item.name, item.state, item.country].filter(Boolean).join(', ');
  cityInput.value = display;
  cityInput.dataset.lat = item.lat;
  cityInput.dataset.lon = item.lon;
  cityInput.dataset.country = item.country;
  cityInput.dataset.cc = (item.country_code || '').toUpperCase();
  list.hidden = true;
}

async function searchCity(q){
  try{
    const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=5&accept-language=ru&q=${encodeURIComponent(q)}`;
    const r = await fetch(url, {headers:{'Accept':'application/json'}});
    const arr = await r.json();
    list.innerHTML = '';
    if (!arr.length){ list.hidden = true; return; }
    arr.forEach(e=>{
      const addr = e.address || {};
      const item = {
        name: addr.city || addr.town || addr.village || e.display_name.split(',')[0],
        state: addr.state || addr.region,
        country: addr.country,
        lat: e.lat, lon: e.lon, country_code: addr.country_code
      };
      const div = document.createElement('div');
      div.className = 'opt';
      div.innerHTML = `<div>${item.name}</div><div class="small">${[item.state, item.country].filter(Boolean).join(', ')}</div>`;
      div.addEventListener('click', ()=> pickCity(item));
      list.appendChild(div);
    });
    list.hidden = false;
  }catch(err){
    console.error(err); list.hidden = true;
  }
}

// Отправка формы
$('hdForm').addEventListener('submit', (e)=>{
  e.preventDefault();
  const payload = {
    date: $('date').value.trim(),
    time: $('time').value.trim(),
    city: $('city').value.trim(),
    name: $('name').value.trim(),
    gender,
    lat: $('city').dataset.lat || '',
    lon: $('city').dataset.lon || '',
    country: $('city').dataset.country || '',
    cc: $('city').dataset.cc || '',
    tz: Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  };
  const dateRe = /^\d{2}\.\d{2}\.\d{4}$/;
  const timeRe = /^\d{2}:\d{2}$/;
  if (!dateRe.test(payload.date)) return alert("Дата в формате дд.мм.гггг");
  if (!timeRe.test(payload.time)) return alert("Время в формате чч:мм");
  if (!$('agree').checked) return alert("Нужно согласие на обработку данных");

  if (tg){ tg.sendData(JSON.stringify(payload)); tg.close(); }
  else { alert("Откройте форму из Telegram-бота."); }
});
