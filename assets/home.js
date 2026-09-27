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
