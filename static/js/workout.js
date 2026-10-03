(function () {
  const data = JSON.parse(document.getElementById('plan-data').textContent);
  const ex = data.exercises;
  const $ = id => document.getElementById(id);
  let i = 0, set = 1, phase = 'ready', left = 0, paused = false, elapsed = 0, ended = false;
  const fmt = s => String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  const say = t => ($('live').textContent = t);
  const post = (path, body) => fetch(`/workout/${data.planId}/${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': data.csrf }, body: JSON.stringify(body)
  }).then(r => r.json()).catch(() => ({ ok: false }));

  function fill(list, items) { list.innerHTML = ''; items.forEach(t => { const li = document.createElement('li'); li.textContent = t; list.append(li); }); }

  function renderExercise() {
    const e = ex[i];
    $('ex-name').textContent = e.name;
    $('ex-count').textContent = `Exercise ${i + 1} of ${ex.length}`;
    document.querySelectorAll('[data-pos]').forEach(d => (d.hidden = d.dataset.pos !== e.position));
    fill($('ex-inst'), e.instructions); fill($('ex-mods'), e.mods); fill($('ex-safety'), e.safety);
    $('ex-breath').textContent = e.breathing;
    const b = $('wbar'); b.setAttribute('aria-valuenow', i); b.firstElementChild.style.width = (i / ex.length * 100) + '%';
    setPhase('ready');
    say(`Exercise ${i + 1} of ${ex.length}: ${e.name}`);
  }

  function setPhase(p) {
    phase = p; const e = ex[i];
    $('ex-set').textContent = `Set ${set} of ${e.sets}`;
    const main = $('btn-main'), label = $('timer-label'), t = $('timer');
    if (p === 'ready') {
      label.textContent = 'Ready';
      t.textContent = e.reps ? `${e.reps} reps` : fmt(e.duration);
      main.textContent = `Start set ${set}`;
    } else if (p === 'work') {
      label.textContent = e.reps ? 'Go at your own pace' : 'Keep going';
      left = e.duration; t.textContent = e.reps ? `${e.reps} reps` : fmt(left);
      main.textContent = 'Set done';
    } else if (p === 'rest') {
      label.textContent = 'Rest'; left = e.rest; t.textContent = fmt(left); main.textContent = 'Skip rest';
      say('Rest. Breathe and relax.');
    } else if (p === 'feedback') {
      $('player').hidden = true; $('fb-panel').hidden = false; $('fb-h').setAttribute('tabindex', '-1'); $('fb-h').focus(); say('How did this feel?');
    }
  }

  function finishSet() { ex[i].sets > set ? setPhase('rest') : setPhase('feedback'); }
  function advance() {
    if (paused || ended) return;
    if (phase === 'ready') setPhase('work');
    else if (phase === 'work') finishSet();
    else if (phase === 'rest') { set++; setPhase('ready'); }
  }

  function nextExercise() {
    if (i >= ex.length - 1) return finish(true);
    i++; set = 1; $('player').hidden = false; $('fb-panel').hidden = true; renderExercise();
  }

  function finish(completed) {
    ended = true; $('player').hidden = true; $('fb-panel').hidden = true;
    post('complete', { duration_seconds: elapsed, completed }).then(r => {
      $('done-time').textContent = fmt(elapsed);
      (r.achievements || []).forEach(a => { const li = document.createElement('li'); li.textContent = 'Achievement unlocked: ' + a; $('done-ach').append(li); });
      $('done-panel').hidden = false; $('done-panel').querySelector('h2').setAttribute('tabindex', '-1'); $('done-panel').querySelector('h2').focus();
    });
  }

  function painStop() {
    ended = true; $('player').hidden = true; $('fb-panel').hidden = true; $('pain-panel').hidden = false;
    post('complete', { duration_seconds: elapsed, completed: false });
  }

  document.querySelectorAll('#fb-panel [data-rating]').forEach(btn => btn.addEventListener('click', () => {
    const rating = btn.dataset.rating;
    document.querySelectorAll('#fb-panel button').forEach(b => (b.disabled = true));
    const sent = post('feedback', { exercise: ex[i].slug, rating });
    if (rating === 'pain') return painStop();       // never auto-progress after pain
    sent.then(() => { document.querySelectorAll('#fb-panel button').forEach(b => (b.disabled = false)); nextExercise(); });
  }));

  $('btn-main').addEventListener('click', advance);
  $('btn-next').addEventListener('click', () => {
    if (paused || ended) return;
    if (i >= ex.length - 1) return finish(true);
    i++; set = 1; renderExercise();
  });
  $('btn-pause').addEventListener('click', () => {
    paused = !paused; $('btn-pause').textContent = paused ? 'Resume' : 'Pause';
    $('btn-pause').setAttribute('aria-pressed', paused); $('btn-main').disabled = paused;
    $('timer-label').textContent = paused ? 'Paused' : (phase === 'rest' ? 'Rest' : phase === 'work' ? 'Keep going' : 'Ready');
    say(paused ? 'Paused' : 'Resumed');
  });
  $('btn-stop').addEventListener('click', () => {
    if (!confirm('End this session now? Your progress so far will be saved.')) return;
    ended = true; post('complete', { duration_seconds: elapsed, completed: false }).then(() => (location.href = '/dashboard'));
  });

  setInterval(() => {
    if (paused || ended) return;
    elapsed++;
    if (phase === 'work' && !ex[i].reps) { left--; $('timer').textContent = fmt(Math.max(left, 0)); if (left <= 0) finishSet(); }
    else if (phase === 'rest') { left--; $('timer').textContent = fmt(Math.max(left, 0)); if (left <= 0) advance(); }
  }, 1000);

  renderExercise();
})();
