'use strict';

(() => {
  if (window.__tdIntegrationNotificationsReady) return;
  window.__tdIntegrationNotificationsReady = true;

  const HEALTH_KEY = 'tdIntegrationHealthV1';
  const HEALTH_STATES = new Set(['connected', 'warning', 'disconnected']);
  const qs = (selector, root = document) => root?.querySelector?.(selector) || null;

  function readHealth() {
    try {
      const value = JSON.parse(localStorage.getItem(HEALTH_KEY) || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch {
      return {};
    }
  }

  function writeHealth(value) {
    try { localStorage.setItem(HEALTH_KEY, JSON.stringify(value || {})); } catch {}
  }

  function healthLabel(status) {
    if (status === 'connected') return 'Connected';
    if (status === 'disconnected') return 'Disconnected';
    return 'Needs attention';
  }

  function failureStatus(message = '') {
    return /could not connect|failed to fetch|network|timed out|timeout|refused|unreachable|name or service not known|temporary failure|dns/i.test(String(message))
      ? 'disconnected'
      : 'warning';
  }

  function storedHealth(id) {
    const record = readHealth()[String(id || '')];
    if (!record) return null;
    const status = HEALTH_STATES.has(record.status) ? record.status : 'warning';
    return {
      status,
      message: String(record.message || healthLabel(status)),
      checkedAt: Number(record.checkedAt || 0)
    };
  }

  function rememberHealth(id, status, message) {
    id = String(id || '');
    if (!id) return;
    const map = readHealth();
    map[id] = {status, message: String(message || healthLabel(status)), checkedAt: Date.now()};
    writeHealth(map);
  }

  function pruneHealth(cards) {
    if (!cards.length) return;
    const active = new Set(cards.map(card => String(card.dataset.id || '')).filter(Boolean));
    const map = readHealth();
    let changed = false;
    for (const id of Object.keys(map)) {
      if (!active.has(id)) { delete map[id]; changed = true; }
    }
    if (changed) writeHealth(map);
  }

  function setCardHealth(card, status, message, persist = true) {
    if (!card) return;
    status = HEALTH_STATES.has(status) ? status : 'warning';
    const dot = qs('.integration-status-dot', card);
    const label = healthLabel(status);
    card.dataset.healthStatus = status;
    if (dot) {
      const className = `integration-status-dot ${status}`;
      if (dot.className !== className) dot.className = className;
      if (dot.getAttribute('aria-label') !== label) dot.setAttribute('aria-label', label);
      dot.title = message || label;
    }
    if (persist) rememberHealth(card.dataset.id, status, message || label);
  }

  function initialCardHealth(card) {
    const enabled = qs('[data-field="enabled"]', card);
    if (enabled && !enabled.checked) return {status: 'disconnected', message: 'Integration is disabled.'};
    const record = storedHealth(card.dataset.id);
    if (record) {
      const checked = record.checkedAt ? ` · Checked ${new Date(record.checkedAt).toLocaleString()}` : '';
      return {status: record.status, message: `${record.message}${checked}`};
    }
    return {status: 'warning', message: card.dataset.id ? 'Connection has not been tested on this device.' : 'Save and test this integration.'};
  }

  function syncCardResult(card) {
    const result = qs('.integration-result', card);
    if (!result) return;
    const message = result.textContent.trim();
    if (!message) return;
    if (result.classList.contains('ok')) {
      setCardHealth(card, 'connected', message);
    } else if (result.classList.contains('bad')) {
      setCardHealth(card, failureStatus(message), message);
    } else if (/testing/i.test(message)) {
      setCardHealth(card, 'warning', 'Checking connection…', false);
    }
  }

  function decorateIntegrationCard(card) {
    if (!card || card.dataset.healthReady === '1') return;
    const summary = qs('.accordion-summary', card);
    if (!summary) return;
    card.dataset.healthReady = '1';
    summary.classList.add('integration-summary-with-status');

    const dot = document.createElement('span');
    dot.className = 'integration-status-dot warning';
    dot.setAttribute('role', 'img');
    summary.insertBefore(dot, summary.firstChild);

    const initial = initialCardHealth(card);
    setCardHealth(card, initial.status, initial.message, false);

    const enabled = qs('[data-field="enabled"]', card);
    card.querySelectorAll('[data-field]').forEach(input => {
      input.addEventListener('input', () => {
        if (enabled && !enabled.checked) setCardHealth(card, 'disconnected', 'Integration is disabled.');
        else setCardHealth(card, 'warning', 'Changes have not been tested.');
      });
    });
    syncCardResult(card);
  }

  function ensureIntegrationLegend() {
    const panel = qs('[data-settings-section="integrations"] .settings-card');
    const addRow = qs('.integration-add-row', panel);
    if (!panel || !addRow || qs('.integration-health-legend', panel)) return;
    const legend = document.createElement('div');
    legend.className = 'integration-health-legend';
    legend.setAttribute('aria-label', 'Integration status legend');
    legend.innerHTML = [
      ['connected', 'Connected'],
      ['warning', 'Needs attention'],
      ['disconnected', 'Disconnected']
    ].map(([status, label]) => `<span><i class="integration-status-dot ${status}" aria-hidden="true"></i>${label}</span>`).join('');
    panel.insertBefore(legend, addRow);
  }

  function decorateIntegrations() {
    ensureIntegrationLegend();
    const cards = [...document.querySelectorAll('#integrationList .integration-item')];
    cards.forEach(decorateIntegrationCard);
    cards.forEach(syncCardResult);
    pruneHealth(cards);
  }

  function observeIntegrations() {
    const list = qs('#integrationList');
    if (!list || list.dataset.healthObserver === '1') return;
    list.dataset.healthObserver = '1';
    new MutationObserver(records => {
      let needsDecoration = false;
      const cards = new Set();
      for (const record of records) {
        const targetCard = record.target?.closest?.('.integration-item');
        if (targetCard) cards.add(targetCard);
        if (record.addedNodes?.length || record.removedNodes?.length) needsDecoration = true;
      }
      if (needsDecoration) decorateIntegrations();
      cards.forEach(syncCardResult);
    }).observe(list, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class']});
  }

  function isAppleMobile() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent || '') || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  function isStandalone() {
    return !!(window.matchMedia?.('(display-mode: standalone)').matches || navigator.standalone === true);
  }

  function currentDashboardTitle() {
    try {
      if (typeof state !== 'undefined') return state.settings?.dashboard?.title || state.me?.title || 'Torrent Dashboard';
    } catch {}
    return 'Torrent Dashboard';
  }

  function pushStatus(message = '', tone = '') {
    const status = qs('#mobilePushStatus');
    const toggle = qs('#nBrowser');
    if (!status) return;
    let text = message;
    let kind = tone;
    if (!text) {
      if (!('Notification' in window)) {
        text = 'Notifications are not supported by this browser.';
        kind = 'bad';
      } else if (toggle && !toggle.checked) {
        text = 'Browser and mobile notifications are disabled in Torrent Dashboard.';
        kind = 'muted';
      } else if (Notification.permission === 'granted') {
        text = 'Notification permission is granted and notifications are enabled.';
        kind = 'ok';
      } else if (Notification.permission === 'denied') {
        text = 'Notification permission is blocked in the browser or device settings.';
        kind = 'bad';
      } else {
        text = 'Permission has not been requested. Use Enable to request it.';
        kind = 'muted';
      }
    }
    if (isAppleMobile() && !isStandalone()) {
      text += ' On Apple mobile devices, add Torrent Dashboard to the Home Screen before enabling notifications.';
    }
    status.className = `test-result ${kind || 'muted'}`;
    status.textContent = text;
  }

  async function requestPermission() {
    if (!('Notification' in window)) throw new Error('Notifications are not supported by this browser.');
    let permission = Notification.permission;
    if (permission === 'default') permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      throw new Error(permission === 'denied'
        ? 'Notification permission is blocked. Enable it in the browser or device settings.'
        : 'Notification permission was not granted.');
    }
  }

  async function persistBrowserNotifications(enabled) {
    if (typeof post !== 'function') throw new Error('Settings API is not available yet.');
    const data = await post('/api/settings', {notifications: {browser: !!enabled}});
    try {
      if (typeof state !== 'undefined' && data?.settings) state.settings = data.settings;
    } catch {}
    return data;
  }

  async function showTestNotification() {
    const title = currentDashboardTitle();
    const options = {
      body: 'Torrent Dashboard notification test completed successfully.',
      tag: 'torrent-dashboard-mobile-test',
      data: {url: '/'}
    };
    if ('serviceWorker' in navigator) {
      const registration = await navigator.serviceWorker.ready;
      if (registration?.showNotification) {
        await registration.showNotification(title, options);
        return;
      }
    }
    new Notification(title, options);
  }

  async function withButton(button, action) {
    if (button) button.disabled = true;
    try { await action(); } finally { if (button) button.disabled = false; }
  }

  function decorateBrowserNotifications() {
    const toggle = qs('#nBrowser');
    if (!toggle || qs('#mobilePushActions')) return;
    const label = toggle.closest('label');
    const help = label?.nextElementSibling;
    const labelText = label?.querySelector('span');
    if (labelText) labelText.textContent = 'Browser / mobile notifications';
    if (help?.classList.contains('field-help')) {
      help.textContent = 'Uses browser or installed-PWA notification permission on supported desktop, Android, and Apple devices.';
    }

    const platforms = document.createElement('div');
    platforms.className = 'mobile-notification-platforms';
    platforms.innerHTML = '<span>Android</span><span>Apple PWA</span>';

    const actions = document.createElement('div');
    actions.id = 'mobilePushActions';
    actions.className = 'settings-inline-actions notification-actions mobile-push-actions';
    actions.innerHTML = '<button class="primary" id="enableMobilePush" type="button">Enable</button><button class="secondary" id="disableMobilePush" type="button">Disable</button><button class="secondary" id="testMobilePush" type="button">Test notification</button>';

    const status = document.createElement('div');
    status.id = 'mobilePushStatus';
    status.className = 'test-result muted';
    status.textContent = 'Permission has not been checked.';

    const note = document.createElement('div');
    note.className = 'field-help mobile-push-note';
    note.textContent = 'These alerts use the browser/PWA notification path. Disabling them here does not revoke device permission. Background Web Push delivery from a closed dashboard requires a server-side push subscription/sender and is not configured by this control.';

    const anchor = help || label;
    anchor.after(platforms, actions, status, note);

    qs('#enableMobilePush')?.addEventListener('click', event => withButton(event.currentTarget, async () => {
      const previous = toggle.checked;
      try {
        await requestPermission();
        toggle.checked = true;
        await persistBrowserNotifications(true);
        pushStatus('Browser and mobile notifications are enabled for this dashboard.', 'ok');
      } catch (error) {
        toggle.checked = previous;
        pushStatus(error.message || 'Could not enable notifications.', 'bad');
      }
    }));

    qs('#disableMobilePush')?.addEventListener('click', event => withButton(event.currentTarget, async () => {
      const previous = toggle.checked;
      try {
        toggle.checked = false;
        await persistBrowserNotifications(false);
        pushStatus('Browser and mobile notifications are disabled in Torrent Dashboard.', 'muted');
      } catch (error) {
        toggle.checked = previous;
        pushStatus(error.message || 'Could not disable notifications.', 'bad');
      }
    }));

    qs('#testMobilePush')?.addEventListener('click', event => withButton(event.currentTarget, async () => {
      try {
        await requestPermission();
        await showTestNotification();
        pushStatus('Test notification sent successfully.', 'ok');
      } catch (error) {
        pushStatus(error.message || 'Notification test failed.', 'bad');
      }
    }));

    toggle.addEventListener('change', () => pushStatus());
    window.addEventListener('focus', () => pushStatus());
    pushStatus();
  }

  function init() {
    decorateBrowserNotifications();
    decorateIntegrations();
    observeIntegrations();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
  else init();
})();
