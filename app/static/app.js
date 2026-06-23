const tg = window.Telegram?.WebApp
const state = { data: null, admin: null }
const $ = (s, p = document) => p.querySelector(s)
const $$ = (s, p = document) => [...p.querySelectorAll(s)]

function initData() {
  if (tg?.initData) return tg.initData
  const dev = new URLSearchParams(location.search).get('dev_id')
  return dev ? `dev:${dev}` : ''
}

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {'Content-Type': 'application/json', 'X-Telegram-Init-Data': initData(), ...(options.headers || {})}
  })
  let data = null
  try { data = await response.json() } catch (_) {}
  if (!response.ok) throw new Error(data?.detail || 'Ошибка соединения')
  return data
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))
}

function toast(text) {
  const node = $('#toast')
  node.textContent = text
  node.classList.add('show')
  clearTimeout(node.timer)
  node.timer = setTimeout(() => node.classList.remove('show'), 2800)
  tg?.HapticFeedback?.notificationOccurred(text.toLowerCase().includes('ошиб') ? 'error' : 'success')
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('ru-RU', {day:'2-digit', month:'short', year:'numeric'}).format(new Date(value))
}

function trafficText(sub) {
  if (!sub) return '—'
  return sub.traffic_gb ? `${sub.traffic_gb} ГБ` : '∞'
}

function showPage(name) {
  $$('.page').forEach(p => p.classList.toggle('active', p.id === `page-${name}`))
  $$('.bottom-nav [data-page]').forEach(b => b.classList.toggle('active', b.dataset.page === name))
  window.scrollTo({top: 0, behavior: 'smooth'})
  if (name === 'admin') loadAdmin()
  tg?.HapticFeedback?.selectionChanged()
}

function renderProtocols() {
  const list = state.data.protocols?.length ? state.data.protocols : [
    {name:'VLESS Reality 443', kind:'Reality'},
    {name:'Trojan Reality', kind:'Reality'},
    {name:'VLESS XHTTP', kind:'TLS'},
    {name:'VLESS TLS', kind:'TLS'}
  ]
  $('#protocolList').innerHTML = list.map(item => `<article><div><b>${escapeHtml(item.name)}</b><span>${escapeHtml(item.kind)}</span></div><i>✓</i></article>`).join('')
}

function renderUser() {
  const user = state.data.user
  const name = user.first_name || user.username || 'JOOT'
  $('#avatar').textContent = name[0].toUpperCase()
  $('#profileUsername').textContent = user.username ? `@${user.username}` : name
  $('#profileId').textContent = `ID ${user.telegram_id}`
  $('#adminNav').classList.toggle('hidden', !state.data.is_admin)
}

function renderSubscription() {
  const sub = state.data.subscription
  const active = sub?.status === 'active'
  $('#heroState').textContent = active ? 'Активен' : 'Не активен'
  $('#heroState').classList.toggle('active', active)
  $('#statusText').textContent = active ? 'Активна' : 'Нет'
  $('#devicesText').textContent = active ? `0 / ${sub.devices}` : `0 / ${state.data.default_devices || 3}`
  $('#trafficText').textContent = trafficText(sub)
  $('#daysText').textContent = active ? `${sub.days_left} дн.` : `${state.data.default_days || 30} дн.`
  $('#connectButton').classList.toggle('active', active)
  $('#copyButton').classList.toggle('hidden', !active)
  $('#refreshButton').classList.toggle('hidden', !active)
  $('#connectButton').title = active ? 'Подписка активна' : 'Подключить VPN'
  $('#profileSubscription').innerHTML = active
    ? `<div class="panel-head"><div><span>SUBSCRIPTION</span><h2>Активна</h2></div><small>${formatDate(sub.expires_at)}</small></div><div class="mini-table"><p><span>Устройства</span><b>до ${sub.devices}</b></p><p><span>Трафик</span><b>${trafficText(sub)}</b></p><p><span>Ссылка</span><b>готова</b></p></div><pre>${escapeHtml(sub.access_url)}</pre>`
    : `<div class="panel-head"><div><span>SUBSCRIPTION</span><h2>Нет доступа</h2></div><small>—</small></div><p class="panel-copy">Нажмите кнопку подключения, чтобы получить подписку.</p>`
}

function renderAll() {
  renderUser()
  renderSubscription()
  renderProtocols()
}

async function connectVpn() {
  try {
    $('#connectButton').classList.add('loading')
    const sub = await api('/connect', {method:'POST'})
    state.data.subscription = sub
    renderSubscription()
    toast('VPN-подписка готова')
  } catch (error) {
    toast(error.message)
  } finally {
    $('#connectButton').classList.remove('loading')
  }
}

async function refreshVpn() {
  try {
    const sub = await api('/subscription/reprovision', {method:'POST'})
    state.data.subscription = sub
    renderSubscription()
    toast('Конфиг обновлён')
  } catch (error) {
    toast(error.message)
  }
}

async function copyAccess() {
  const url = state.data.subscription?.access_url
  if (!url) return toast('Ссылка ещё не создана')
  try {
    await navigator.clipboard.writeText(url)
    toast('Ссылка скопирована')
  } catch (_) {
    toast('Не удалось скопировать')
  }
}

async function loadAdmin() {
  if (!state.data?.is_admin) return
  try {
    state.admin = await api('/admin/dashboard')
    const s = state.admin.stats
    $('#adminStats').innerHTML = `<article><span>Пользователи</span><b>${s.users}</b></article><article><span>Активные</span><b>${s.active_subscriptions}</b></article><article><span>Оплаты</span><b>${s.paid_orders}</b></article>`
    $('#adminContent').innerHTML = state.admin.users.map(u => `<article><div><b>${escapeHtml(u.name || u.username || u.telegram_id)}</b><span>ID ${u.telegram_id}</span></div><small>${u.blocked ? 'blocked' : 'active'}</small></article>`).join('') || '<p>Пользователей пока нет.</p>'
  } catch (error) {
    toast(error.message)
  }
}

async function boot() {
  try {
    tg?.ready()
    tg?.expand()
    tg?.setHeaderColor?.('#070a0f')
    tg?.setBackgroundColor?.('#070a0f')
    tg?.enableClosingConfirmation?.()
    state.data = await api('/bootstrap')
    renderAll()
    $('#loader').classList.add('hidden')
    $('#app').classList.remove('hidden')
  } catch (error) {
    $('#loader').innerHTML = `<b>JOOT</b><p>${escapeHtml(error.message)}<br><br>Откройте приложение через Telegram-бота.</p>`
  }
}

$$('[data-page]').forEach(b => b.addEventListener('click', () => showPage(b.dataset.page)))
$('#connectButton').onclick = connectVpn
$('#copyButton').onclick = copyAccess
$('#refreshButton').onclick = refreshVpn
$('#supportButton').onclick = () => {
  const u = state.data?.support_username
  if (!u) return showPage('guide')
  tg?.openTelegramLink?.(`https://t.me/${u.replace('@','')}`) || window.open(`https://t.me/${u.replace('@','')}`)
}

boot()
