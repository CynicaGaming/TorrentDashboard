'use strict';

(() => {
  if (window.__tdDefaultNotificationSoundPatched) return;
  window.__tdDefaultNotificationSoundPatched = true;

  const replacement = '/static/notification-default.mp3';
  const replaceDefaultSound = source => String(source || '').replace('/static/default-completion.wav', replacement);

  const NativeAudio = window.Audio;
  if (typeof NativeAudio === 'function') {
    function TorrentDashboardAudio(source) {
      return new NativeAudio(replaceDefaultSound(source));
    }
    TorrentDashboardAudio.prototype = NativeAudio.prototype;
    Object.setPrototypeOf(TorrentDashboardAudio, NativeAudio);
    window.Audio = TorrentDashboardAudio;
  }

  if (typeof window.playSoundUrl === 'function') {
    const originalPlaySoundUrl = window.playSoundUrl;
    window.playSoundUrl = function(source) {
      return originalPlaySoundUrl.call(this, replaceDefaultSound(source));
    };
  }

  if (typeof window.configuredCompletionSoundUrl === 'function') {
    const originalConfiguredSoundUrl = window.configuredCompletionSoundUrl;
    window.configuredCompletionSoundUrl = function() {
      return replaceDefaultSound(originalConfiguredSoundUrl.call(this));
    };
  }
})();
