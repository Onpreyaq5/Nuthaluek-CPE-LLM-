/* Pointer lighting uses one scheduled frame, and follows device/motion preferences. */
(function initializeInteractions() {
  'use strict';
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeInteractions, { once: true });
    return;
  }
  var media = window.matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
  var active = null, frame = 0, x = 0, y = 0;
  function clear() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    if (active) active.classList.remove('pointer-active');
    active = null;
  }
  document.addEventListener('pointermove', function (event) {
    if (!media.matches || event.pointerType === 'touch') return;
    var surface = event.target.closest('.side-card, .chat-box, .set-group, .stage-card, .problem-card, .uc-card, .suggest');
    if (surface !== active) {
      clear(); active = surface;
      if (active) active.classList.add('pointer-surface', 'pointer-active');
    }
    if (!active) return;
    x = event.clientX; y = event.clientY;
    if (!frame) frame = requestAnimationFrame(function () {
      frame = 0;
      if (!active) return;
      var bounds = active.getBoundingClientRect();
      active.style.setProperty('--pointer-x', (x - bounds.left) + 'px');
      active.style.setProperty('--pointer-y', (y - bounds.top) + 'px');
    });
  }, { passive: true });
  document.documentElement.addEventListener('pointerleave', clear);
  window.addEventListener('blur', clear);
  window.addEventListener('scroll', clear, { passive: true });
  media.addEventListener('change', clear);

  document.querySelectorAll('[data-icon]').forEach(function (node) {
    node.innerHTML = window.TradeIcons.svg(node.dataset.icon);
  });
  document.querySelector('.brand-mark').innerHTML = window.TradeIcons.svg('brand');
  document.querySelector('.welcome .msg-avatar').innerHTML = window.TradeIcons.svg('brand');
  document.querySelector('.source-col h3 svg').outerHTML = window.TradeIcons.svg('document');

  // Make existing expandable cards operable with a keyboard too.
  document.querySelectorAll('.problem-head, .uc-head').forEach(function (head, index) {
    var body = head.nextElementSibling;
    body.id = 'accordion-content-' + index;
    head.setAttribute('role', 'button');
    head.tabIndex = 0;
    head.setAttribute('aria-controls', body.id);
    function sync() {
      var open = head.parentElement.classList.contains('open');
      head.setAttribute('aria-expanded', String(open));
      body.inert = !open;
    }
    head.addEventListener('click', sync);
    head.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault(); head.click();
      }
    });
    sync();
  });
  function labelSettings() {
    document.querySelectorAll('#settingsHost [data-key]').forEach(function (input) {
      input.id = 'setting-' + input.dataset.key;
      var label = input.closest('.set-row').querySelector('label');
      label.htmlFor = input.id;
    });
  }
  labelSettings();
  new MutationObserver(labelSettings).observe(document.getElementById('settingsHost'), {childList:true});
  var tabs = document.querySelectorAll('.tab');
  document.getElementById('tabs').setAttribute('aria-label', 'เมนูหลัก');
  function syncTabs() {
    tabs.forEach(function (tab) {
      tab.setAttribute('aria-current', tab.classList.contains('active') ? 'page' : 'false');
      tab.setAttribute('aria-controls', 'panel-' + tab.dataset.tab);
    });
  }
  tabs.forEach(function (tab) { tab.addEventListener('click', syncTabs); });
  syncTabs();
  document.querySelectorAll('svg').forEach(function (icon) {
    if (!icon.closest('.mindmap-host, #usecaseDiagram')) icon.setAttribute('aria-hidden', 'true');
  });
})();
