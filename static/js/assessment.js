(function () {
  const form = document.getElementById('assess');
  const steps = Array.from(form.querySelectorAll(':scope > fieldset.step'));
  const bar = document.getElementById('pbar'), title = document.getElementById('step-title');
  const back = document.getElementById('back'), next = document.getElementById('next'), submit = document.getElementById('submit');
  let cur = 0;
  document.documentElement.classList.add('js');

  function show(n) {
    cur = n;
    steps.forEach((s, i) => (s.hidden = i !== n));
    back.hidden = n === 0; next.hidden = n === steps.length - 1; submit.hidden = n !== steps.length - 1;
    title.textContent = `Step ${n + 1} of ${steps.length}: ${steps[n].dataset.title}`;
    bar.setAttribute('aria-valuenow', n + 1);
    bar.firstElementChild.style.width = ((n + 1) / steps.length * 100) + '%';
    if (n === steps.length - 1) buildSummary();
    steps[n].querySelector('h2').setAttribute('tabindex', '-1');
    steps[n].querySelector('h2').focus({ preventScroll: false });
  }

  function valid() {
    const step = steps[cur];
    for (const inp of step.querySelectorAll('input[required]')) {
      if (inp.type === 'radio') {
        if (!step.querySelector(`input[name="${inp.name}"]:checked`)) { inp.focus(); inp.reportValidity(); return false; }
      } else if (!inp.checked && inp.type === 'checkbox') { inp.focus(); inp.reportValidity(); return false; }
    }
    const lim = document.getElementById('limit-error');
    if (step.querySelector('#limits')) {
      const any = step.querySelectorAll('#limits input:checked').length > 0;
      lim.hidden = any; if (!any) { lim.scrollIntoView({ block: 'center' }); return false; }
    }
    return true;
  }

  function buildSummary() {
    const box = document.getElementById('summary'); box.innerHTML = '';
    steps.slice(0, -1).forEach((s, i) => {
      const picked = Array.from(s.querySelectorAll('input:checked')).map(x => x.closest('label').querySelector('.t').textContent);
      const row = document.createElement('div'); row.className = 'summary-row';
      const txt = document.createElement('div');
      const h = document.createElement('strong'); h.textContent = s.dataset.title;
      const p = document.createElement('div'); p.className = 'muted small'; p.textContent = picked.join(' · ') || 'Nothing selected';
      txt.append(h, p);
      const b = document.createElement('button'); b.type = 'button'; b.className = 'btn'; b.textContent = 'Edit';
      b.setAttribute('aria-label', 'Edit ' + s.dataset.title); b.onclick = () => show(i);
      row.append(txt, b); box.append(row);
    });
  }

  // "None of these" is exclusive
  const limits = form.querySelector('#limits');
  if (limits) limits.addEventListener('change', e => {
    const none = limits.querySelector('input[value="none"]');
    if (e.target === none && none.checked) limits.querySelectorAll('input:not([value="none"])').forEach(i => (i.checked = false));
    else if (e.target !== none) none.checked = false;
    document.getElementById('limit-error').hidden = true;
  });

  // live red-flag notice
  function flagCheck() {
    const sym = form.querySelectorAll('#symptoms input:checked').length > 0;
    const pro = form.querySelector('input[name="professional_restriction"][value="yes"]').checked;
    const inj = form.querySelector('input[name="injury_status"][value="recent_serious"]').checked;
    document.getElementById('flag-warn').hidden = !(sym || pro || inj);
  }
  form.addEventListener('change', flagCheck); flagCheck();

  next.onclick = () => { if (valid()) show(cur + 1); };
  back.onclick = () => show(cur - 1);
  form.addEventListener('submit', e => {
    if (!form.querySelector('input[name="confirm"]').checked) { e.preventDefault(); form.querySelector('input[name="confirm"]').reportValidity(); }
  });
  show(0);
})();
