(function () {
  // ---- Mermaid ----
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'base',
      securityLevel: 'loose',
      flowchart: { htmlLabels: true, curve: 'basis', padding: 14 },
      themeVariables: {
        fontFamily: "'InstrumentSans','PingFang SC','Microsoft YaHei',sans-serif",
        fontSize: '13px',
        primaryColor: '#FFFFFF',
        primaryTextColor: '#1B1F24',
        primaryBorderColor: '#A6192E',
        secondaryColor: '#F3EDE9',
        secondaryBorderColor: '#D9D1C9',
        tertiaryColor: '#F7F5F2',
        tertiaryBorderColor: '#E4DFD9',
        lineColor: '#8C857E',
        textColor: '#1B1F24',
        edgeLabelBackground: '#F7F5F2'
      }
    });
  }

  // ---- TOC scroll spy ----
  var links = Array.prototype.slice.call(document.querySelectorAll('aside.toc nav a'));
  var sections = links
    .map(function (a) {
      var id = a.getAttribute('href').slice(1);
      return { link: a, el: document.getElementById(id) };
    })
    .filter(function (s) { return s.el; });

  function sync() {
    var y = window.scrollY + 140;
    var current = null;
    for (var i = 0; i < sections.length; i++) {
      if (sections[i].el.offsetTop <= y) current = sections[i];
    }
    links.forEach(function (a) { a.classList.remove('active'); });
    if (current) current.link.classList.add('active');
  }

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (!ticking) {
      window.requestAnimationFrame(function () { sync(); ticking = false; });
      ticking = true;
    }
  }, { passive: true });
  sync();
})();
