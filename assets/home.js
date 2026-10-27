// Home page interactions (states are specified in design/mmlabs-interaction-states.html).
// The page works without this script: links, anchors and the mailto forms still do their job.
(function () {
  var header = document.querySelector('.header');
  var toastEl = document.getElementById('toast');
  var toastTimer;

  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 2600);
  }

  // Header gets a shadow once the page scrolls under it
  function onScroll() { header.classList.toggle('is-scrolled', window.scrollY > 8); }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Apps dropdown: click to open, closes on outside click, Esc or picking an item.
  // Below 1200px the nav scrolls sideways, the menu is hidden by CSS and "Apps" stays a link to #apps.
  var dropdown = document.querySelector('.dropdown');
  var toggle = dropdown.querySelector('.dd-toggle');
  var wide = window.matchMedia('(min-width: 1201px)');
  function setOpen(open) {
    dropdown.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  }
  toggle.addEventListener('click', function (e) {
    if (!wide.matches) return;
    e.preventDefault();
    setOpen(!dropdown.classList.contains('open'));
  });
  dropdown.querySelector('.menu').addEventListener('click', function (e) {
    if (e.target.closest('a')) setOpen(false);
  });
  document.addEventListener('click', function (e) {
    if (!dropdown.contains(e.target)) setOpen(false);
  });
  dropdown.addEventListener('focusout', function (e) {
    if (e.relatedTarget && !dropdown.contains(e.relatedTarget)) setOpen(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && dropdown.classList.contains('open')) { setOpen(false); toggle.focus(); }
  });
  wide.addEventListener('change', function () { setOpen(false); });

  // Highlight the nav item for the section being read (home page only; blog posts mark Updates in the HTML)
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.nav > a, .nav .dd-toggle'));
  var targets = navLinks.map(function (a) {
    var id = a.getAttribute('href');
    return id.charAt(0) === '#' ? document.querySelector(id) : null;
  });
  function spy() {
    var line = header.offsetHeight + 40, current = 0;
    targets.forEach(function (el, i) {
      if (el && el.getBoundingClientRect().top <= line) current = i;
    });
    // At the very bottom the last section may never reach the line
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) current = targets.length - 1;
    navLinks.forEach(function (a, i) { a.classList.toggle('on', i === current); });
  }
  if (targets.some(Boolean)) {
    window.addEventListener('scroll', spy, { passive: true });
    window.addEventListener('resize', spy);
    spy();
  }

  // Whole card is clickable; links inside it keep their own target
  document.addEventListener('click', function (e) {
    var card = e.target.closest('[data-href]');
    if (!card || e.target.closest('a, button, input, select, textarea')) return;
    var href = card.getAttribute('data-href');
    if (e.ctrlKey || e.metaKey) window.open(href, '_blank', 'noopener');
    else window.location.href = href;
  });

  // Workday carousel: drag with the mouse (touch and trackpads scroll natively), dots jump to a position,
  // arrow keys work when the track has focus. Cards half outside the focus area are dimmed; clicking one slides it in.
  var track = document.getElementById('workday-track');
  var wdNav = document.querySelector('.workday-nav');
  if (track && wdNav) {
    var cards = Array.prototype.slice.call(track.children);
    var dotsEl = wdNav.querySelector('.workday-dots');
    var calm = window.matchMedia('(prefers-reduced-motion: reduce)');
    var stops = [];

    function measure() {
      // One stop per card that can sit at the start of the focus area; the last stop is the scroll end.
      var max = track.scrollWidth - track.clientWidth;
      var base = cards[0].offsetLeft;
      stops = [];
      for (var i = 0; i < cards.length; i++) {
        var x = Math.min(cards[i].offsetLeft - base, max);
        stops.push(x);
        if (x >= max - 1) break;
      }
      dotsEl.innerHTML = '';
      stops.forEach(function (x, i) {
        var b = document.createElement('button');
        b.type = 'button';
        b.setAttribute('aria-label', 'Go to position ' + (i + 1));
        b.addEventListener('click', function () { go(i); });
        dotsEl.appendChild(b);
      });
      wdNav.hidden = stops.length < 2;
      update();
    }
    function nearest(x) {
      var best = 0;
      stops.forEach(function (s, i) { if (Math.abs(s - x) < Math.abs(stops[best] - x)) best = i; });
      return best;
    }
    function go(i) {
      i = Math.max(0, Math.min(stops.length - 1, i));
      track.scrollTo({ left: stops[i], behavior: calm.matches ? 'auto' : 'smooth' });
      update();
    }
    function update() {
      var i = nearest(track.scrollLeft);
      Array.prototype.forEach.call(dotsEl.children, function (d, j) {
        d.classList.toggle('on', j === i);
        if (j === i) d.setAttribute('aria-current', 'true'); else d.removeAttribute('aria-current');
      });
      // Focus area = the track minus its side padding (where the half cards peek out)
      var pad = parseFloat(getComputedStyle(track).paddingLeft) || 0;
      var box = track.getBoundingClientRect();
      var from = box.left + pad - 2, to = box.right - pad + 2;
      cards.forEach(function (c) {
        var r = c.getBoundingClientRect();
        var peek = r.left < from || r.right > to;
        c.classList.toggle('is-peek', peek);
      });
    }

    // Mouse drag. Snap is paused while dragging, then the track settles on the next stop in the drag direction.
    var drag = null, moved = false;
    track.addEventListener('pointerdown', function (e) {
      if (e.pointerType !== 'mouse' || e.button !== 0 || e.target.closest('a, button')) return;
      drag = { x: e.clientX, left: track.scrollLeft, from: nearest(track.scrollLeft) };
      moved = false;
    });
    window.addEventListener('pointermove', function (e) {
      if (!drag) return;
      var dx = e.clientX - drag.x;
      if (!moved && Math.abs(dx) > 5) {
        moved = true;
        track.classList.add('is-dragging');
      }
      if (moved) track.scrollLeft = drag.left - dx;
    });
    window.addEventListener('pointerup', function (e) {
      if (!drag) return;
      var d = drag;
      drag = null;
      if (!moved) return;
      track.classList.remove('is-dragging');
      setTimeout(function () { moved = false; }, 0);  // the click that follows this pointerup is swallowed first
      var dx = e.clientX - d.x;
      var target = Math.abs(dx) > 60 ? d.from + (dx < 0 ? 1 : -1) : nearest(track.scrollLeft);
      go(target);
    });
    // A drag must not count as a click; a click on a dimmed card slides it into the focus area.
    track.addEventListener('click', function (e) {
      if (moved) { e.preventDefault(); e.stopPropagation(); return; }
      var card = e.target.closest('.class-card');
      if (card && card.classList.contains('is-peek')) {
        e.preventDefault();
        e.stopPropagation();
        var r = card.getBoundingClientRect(), box = track.getBoundingClientRect();
        go(nearest(track.scrollLeft) + (r.left + r.width / 2 > box.left + box.width / 2 ? 1 : -1));
      }
    }, true);

    track.addEventListener('keydown', function (e) {
      if (e.target !== track) return;
      if (e.key === 'ArrowRight') { e.preventDefault(); go(nearest(track.scrollLeft) + 1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); go(nearest(track.scrollLeft) - 1); }
    });
    track.addEventListener('scroll', update, { passive: true });
    track.addEventListener('scrollend', update);
    window.addEventListener('resize', measure);
    measure();
  }

  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  function mailto(form, subject, body) {
    var to = form.getAttribute('action').split('?')[0];
    window.location.href = to + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
  }

  // Contact form: check the required fields, then hand the message to the visitor's email app
  var contact = document.getElementById('contact-form');
  var contactError = document.getElementById('contact-error');
  if (contact) contact.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = contact.elements;
    var bad = [];
    if (!f.name.value.trim()) bad.push(f.name);
    if (!EMAIL.test(f.email.value.trim())) bad.push(f.email);
    if (!f.message.value.trim()) bad.push(f.message);
    [f.name, f.email, f.message].forEach(function (el) {
      el.classList.toggle('is-error', bad.indexOf(el) !== -1);
      el.setAttribute('aria-invalid', String(bad.indexOf(el) !== -1));
    });
    contactError.hidden = !bad.length;
    if (bad.length) { bad[0].focus(); return; }

    var body = f.message.value.trim() + '\n\n' + f.name.value.trim() + ' <' + f.email.value.trim() + '>'
      + (f.company.value.trim() ? '\n' + f.company.value.trim() : '')
      + (f.app.value ? '\nInterested in: ' + f.app.value : '');
    mailto(contact, 'Hello from ' + f.name.value.trim(), body);
    toast('Thanks! Your email app is opening to send it.');
  });
  // Plan buttons jump to the form with a starter message, unless the visitor already wrote one
  document.addEventListener('click', function (e) {
    var link = e.target.closest('[data-prefill]');
    if (!link || !contact || contact.elements.message.value.trim()) return;
    contact.elements.message.value = link.getAttribute('data-prefill');
  });
  if (contact) contact.addEventListener('input', function (e) {
    if (!e.target.classList.contains('is-error')) return;
    e.target.classList.remove('is-error');
    e.target.removeAttribute('aria-invalid');
    if (!contact.querySelector('.is-error')) contactError.hidden = true;
  });

  // Newsletter: valid email -> email app opens, button shows success for 3s
  var sub = document.getElementById('subscribe-form');
  var subInput = sub.querySelector('input');
  var subBtn = sub.querySelector('.btn');
  sub.addEventListener('submit', function (e) {
    e.preventDefault();
    var email = subInput.value.trim();
    if (!EMAIL.test(email)) {
      sub.classList.add('is-error');
      subInput.setAttribute('aria-invalid', 'true');
      subInput.focus();
      toast('Add a valid email so we can reach you.');
      return;
    }
    mailto(sub, 'Subscribe', 'Please add ' + email + ' to the mmlabs updates list.');
    subBtn.classList.add('is-done');
    subBtn.textContent = 'Subscribed ✓';
    toast('Thanks! Send the email that just opened to confirm.');
    setTimeout(function () { subBtn.classList.remove('is-done'); subBtn.textContent = 'Subscribe'; }, 3000);
  });
  subInput.addEventListener('input', function () {
    sub.classList.remove('is-error');
    subInput.removeAttribute('aria-invalid');
  });
})();
