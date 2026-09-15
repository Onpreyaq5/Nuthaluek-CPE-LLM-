/* Local, consistent 24px outline icons. No network dependency. */
window.TradeIcons = (function () {
  var paths = {
    brand: '<path d="m4 17 5-10 4 10 3-6h4M4 20h16"/>',
    chat: '<rect x="3" y="4" width="18" height="14" rx="4"/><path d="m7 18-3 3v-5M8 9h8M8 13h5"/>',
    pipeline: '<rect x="3" y="3" width="6" height="6" rx="2"/><rect x="15" y="15" width="6" height="6" rx="2"/><path d="M9 6h6a3 3 0 0 1 3 3v6M6 9v6a3 3 0 0 0 3 3h6"/>',
    problems: '<path d="M9 3h6M10 3v6l-6 10a1 1 0 0 0 1 2h14a1 1 0 0 0 1-2L14 9V3M8 14h8"/>',
    evaluate: '<path d="M4 3v17h17M8 15v-4M13 15V7M18 15v-6"/>',
    mindmap: '<rect x="9" y="3" width="6" height="5" rx="1.5"/><rect x="3" y="16" width="6" height="5" rx="1.5"/><rect x="15" y="16" width="6" height="5" rx="1.5"/><path d="M12 8v4M6 16v-4h12v4"/>',
    usecase: '<path d="M12 5c-3-2-6-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Zm0 0v15"/>',
    settings: '<path d="M3 7h4m6 0h8M3 17h10m6 0h2"/><circle cx="10" cy="7" r="3"/><circle cx="16" cy="17" r="3"/>',
    chart: '<path d="M4 4v16h16M7 14l4-4 4 2 5-7M16 5h4v4"/>',
    shield: '<path d="m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7zM8 12l3 3 5-6"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5"/>',
    arrow: '<path d="M12 20V4m-6 6 6-6 6 6"/>',
    diagonal: '<path d="M6 18 18 6M6 6h12v12"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    sparkles: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
    document: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Zm0 0v6h6M8 13h8M8 17h5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2"/>'
  };
  function svg(name) { return '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + (paths[name] || paths.document) + '</svg>'; }
  return { svg: svg };
})();
