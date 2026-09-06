'use strict';

(() => {
  const HEALTH_KEY = 'tdIntegrationHealthV1';
  const qs = (selector, root = document) => root.querySelector(selector);

  function readHealth() {
    try {
      const value = JSON.parse(localStorage.getItem(HEALTH_KEY) || '{}');
      return value && typeof value === 'object' ? value : {};
    } catch {
      return {};
    }
  }

  function writeHealth(value) {
    try { localStorage.setItem(HEALTH_KEY, JSON.stringify(value || {})); } catch {}
  }

  function healthLabel(status) {
    return status === 'connected' ? 'Connected' : status === 'disconnected' ? 'Disconnected' : 'Needs attention';
  }

  function healthClassFromError(message = '') {
    return /could not connect|failed to fetch|network|timed out|timeout|refused|unreachable|name or service not known|temporary failure|dns/i.test(String(message))
      ? 'disconnected'
      : 'warning';
  }

  function storedHealth(id) {
    const record = readHealth()[id || ''];
    if (!record) return null;
    const status = ['connected', 'warning', 'disconnected'].includes(record.status) ? record.status : 'warning';
    return {
      status,
      message: record.message || healthLabel(status),
      checkedAt: Number(record.checkedAt || 0)
    };
  }

  function rememberHealth(id, status, message) {
    if (!id) return;
    const map = readHealth();
    map[id] = {status, message, checkedAt: Date.now()};
    writeHealth(map);
  }

  function setCardHealth(card, status, message, persist = true) {
    if (!card) return;
    status = ['connected', 'warning', 'disconnected'].includes(status) ? status : 'warning';
    const dot = qs('.integration-status-dot', card);
    const label = healthLabel(status);
    card.dataset.healthStatus = status;
    if (dot) {
      dot.className = `integration-status-dot ${status}`;
      dot.setAttribute('aria-label', label);
      dot.title = message || label;
    }
    const id = card.dataset.id || '';
    if (persist && id) rememberHealth(id, status, message || label);
  }

  function initialCardHealth(card) {
    const enabled = qs('[data-field="enabled"]', card);
    if (enabled && !enabled.checked) return {status: 'disconnected', message: 'Integration is disabled.'};
    const record = storedHealth(card.dataset.id);
    if (record) {
      const checked = record.checkedAt ? ` · Checked ${new Date(record.checkedAt).toLocaleString()}` : '';
      return {status: record.status, message: `${record.message}${checked}`};
    }
    return {status: 'warning', message: card.dataset.id ? 'Connection has not been tested on this device.' : 'Not saved yet.'};
  }

  function decorateIntegrationCard(card) {
    if (!card || card.dataset.healthReady === '1') return;
    card.dataset.healthReady = '1';
    const summary = qs('.accordion-summary', card);
    if (!summary) return;

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

    const result = qs('.integration-result', card);
    if (!result) return;
    const syncResult = () => {
      const message = result.textContent.trim();
      if (!message) return;
      if (result.classList.contains('ok')) {
        setCardHealth(card, 'connected', message);
      } else if (result.classList.contains('bad')) {
        setCardHealth(card, healthClassFromError(message), message);
      } else if (/testing/i.test(message)) {
        setCardHealth(card, 'warning', 'Checking connection…', false);
      }
    };
    new MutationObserver(syncResult).observe(result, {childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ['class']});
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
    document.querySelectorAll('#integrationList .integration-item').forEach(decorateIntegrationCard);
  }

  function isAppleMobile() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent || '') || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  function isStandalone() {
    return !!(window.matchMedia?.('(display-mode: standalone)').matches || navigator.standalone === true);
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
        text = 'Mobile notifications are disabled in Torrent Dashboard.';
        kind = 'muted';
      } else if (Notification.permission === 'granted') {
        text = 'Notification permission is granted and mobile notifications are enabled.';
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
      text += ' Add Torrent Dashboard to the Home Screen before enabling notifications on Apple mobile devices.';
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

  async function persistNotificationSetting() {
    if (window.TDSettings?.saveCore) await window.TDSettings.saveCore();
  }

  async function showTestNotification() {
    const title = window.state?.settings?.dashboard?.title || 'Torrent Dashboard';
    const options = {
      body: 'Mobile notification test completed successfully.',
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

  function decorateMobileNotifications() {
    const toggle = qs('#nBrowser');
    if (!toggle || qs('#mobilePushActions')) return;
    const label = toggle.closest('label');
    const help = label?.nextElementSibling;
    const labelText = label?.querySelector('span');
    if (labelText) labelText.textContent = 'Mobile push notifications';

    if (help?.classList.contains('field-help')) {
      help.textContent = 'Uses browser or installed-app notification permission on supported Android and Apple devices.';
    }

    const platforms = document.createElement('div');
    platforms.className = 'mobile-notification-platforms';
    platforms.innerHTML = '<span>Android</span><span>Apple</span>';

    const actions = document.createElement('div');
    actions.id = 'mobilePushActions';
    actions.className = 'settings-inline-actions notification-actions mobile-push-actions';
    actions.innerHTML = '<button class="primary" id="enableMobilePush" type="button">Enable</button><button class="secondary" id="disableMobilePush" type="button">Disable</button><button class="secondary" id="testMobilePush" type="button">Test push</button>';

    const status = document.createElement('div');
    status.id = 'mobilePushStatus';
    status.className = 'test-result muted';
    status.textContent = 'Permission has not been checked.';

    const note = document.createElement('div');
    note.className = 'field-help mobile-push-note';
    note.textContent = 'Disabling notifications here stops Torrent Dashboard from sending them; device-level permission remains controlled by the browser or operating system.';

    const anchor = help || label;
    anchor.after(platforms, actions, status, note);

    qs('#enableMobilePush')?.addEventListener('click', event => withButton(event.currentTarget, async () => {
      try {
        await requestPermission();
        toggle.checked = true;
        await persistNotificationSetting();
        pushStatus('Mobile notifications are enabled for this dashboard.', 'ok');
      } catch (error) {
        pushStatus(error.message || 'Could not enable mobile notifications.', 'bad');
      }
    }));

    qs('#disableMobilePush')?.addEventListener('click', event => withButton(event.currentTarget, async () => {
      toggle.checked = false;
      await persistNotificationSetting();
      pushStatus('Mobile notifications are disabled in Torrent Dashboard.', 'muted');
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
    decorateMobileNotifications();
    decorateIntegrations();
    new MutationObserver(() => {
      decorateMobileNotifications();
      decorateIntegrations();
    }).observe(document.body, {childList: true, subtree: true});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
  else init();
})();
