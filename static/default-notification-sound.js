'use strict';

(() => {
  if (window.__tdDefaultNotificationSoundPatched) return;
  window.__tdDefaultNotificationSoundPatched = true;

  const legacyPath = '/static/default-completion.wav';
  const defaultPath = '/static/notification-default.mp3';

  function replaceDefaultSound(source) {
    if (typeof source !== 'string' || !source) return source;
    try {
      const url = new URL(source, window.location.href);
      if (url.origin !== window.location.origin || url.pathname !== legacyPath) return source;
      url.pathname = defaultPath;
      return /^https?:\/\//i.test(source)
        ? url.href
        : `${url.pathname}${url.search}${url.hash}`;
    } catch {
      return source;
    }
  }

  const NativeAudio = window.Audio;
  if (typeof NativeAudio !== 'function') return;

  function TorrentDashboardAudio(source) {
    return new NativeAudio(replaceDefaultSound(source));
  }

  TorrentDashboardAudio.prototype = NativeAudio.prototype;
  Object.setPrototypeOf(TorrentDashboardAudio, NativeAudio);
  window.Audio = TorrentDashboardAudio;
})();
