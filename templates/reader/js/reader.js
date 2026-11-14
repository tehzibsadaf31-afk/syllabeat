/* SyllaBeat reader - works from a plain folder (no server needed) and never talks to the internet except
   for the optional Google Fonts. All timings come from data/syllabeat-data.js, made by the build scripts. */
(() => {
  "use strict";
  const D = window.SYLLABEAT;
  const $ = (id) => document.getElementById(id);
  const bnDigits = "০১২৩৪৫৬৭৮৯";
  const bn = (n) => String(n).replace(/\d/g, (d) => bnDigits[d]);
  const wordKey = (t) => t.toLowerCase().replace(/[^a-z]/g, "");

  document.title = D.title + " – SyllaBeat";
  $("title").textContent = D.title;
  if (D.subtitle) { $("subtitle").textContent = D.subtitle; $("subtitle").hidden = false; }

  /* ---------- the text: every word is a button ---------- */
  const story = $("story");
  const paras = D.paragraphs.map((para, pi) => {
    const p = document.createElement("p");
    const toks = [];
    let last = 0;
    for (const m of para.text.matchAll(/\S+/g)) {
      if (m.index > last) p.append(para.text.slice(last, m.index));
      const key = wordKey(m[0]);
      const b = document.createElement("button");
      b.type = "button"; b.className = "w"; b.textContent = m[0];
      if (D.words[key]) b.addEventListener("click", () => openCard(key, m[0].replace(/^[^A-Za-z]+|[^A-Za-z]+$/g, "")));
      p.appendChild(b); toks.push(b); last = m.index + m[0].length;
    }
    if (last < para.text.length) p.append(para.text.slice(last));
    story.appendChild(p);
    return { toks, data: para };
  });

  /* ---------- narration: the highlight follows the audio's own clock ---------- */
  const audio = new Audio();
  audio.preload = "auto";
  let rate = 1, state = "idle", cur = 0, raf = 0, activeP = -1, activeI = -1;
  const mascot = $("mascot");
  const ui = () => { $("play").disabled = state === "playing"; $("pause").disabled = state !== "playing"; };

  function setActive(pi, i) {
    if (pi === activeP && i === activeI) return;
    if (activeP >= 0 && paras[activeP].toks[activeI]) paras[activeP].toks[activeI].classList.remove("active");
    activeP = pi; activeI = i;
    if (pi < 0 || i < 0) return;
    const el = paras[pi].toks[i];
    el.classList.add("active");
    mascot.classList.remove("thump"); void mascot.offsetWidth; mascot.classList.add("thump");
    const r = el.getBoundingClientRect();
    if (r.top < 90 || r.bottom > innerHeight - 170) el.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  // We read the audio's own clock about 30 times a second (a timer, not requestAnimationFrame, so it also keeps
  // working when the page is in a background tab). The highlight can never drift away from the voice.
  const POLL_MS = 30;
  function loop() {
    clearInterval(raf);
    raf = setInterval(() => {
      if (state !== "playing") return;
      const t = audio.currentTime, tk = paras[cur].data.tokens;
      let idx = 0;
      for (let i = 0; i < tk.length; i++) { if (tk[i][0] <= t + 0.03) idx = i; else break; }
      setActive(cur, idx);
    }, POLL_MS);
  }
  function playPara(i) {
    cur = i; audio.src = paras[i].data.audio;
    audio.playbackRate = rate; audio.defaultPlaybackRate = rate;
    audio.play().then(() => { state = "playing"; ui(); loop(); }).catch(() => { state = "paused"; ui(); });
  }
  $("play").onclick = () => {
    if (state === "paused" && audio.src && !audio.ended) { audio.playbackRate = rate; audio.play().then(() => { state = "playing"; ui(); loop(); }); }
    else playPara(0);
  };
  $("pause").onclick = () => { audio.pause(); clearInterval(raf); state = "paused"; ui(); };
  $("slower").onclick = (e) => { rate = rate < 1 ? 1 : D.slowPlaybackRate; audio.playbackRate = rate; e.currentTarget.setAttribute("aria-pressed", rate < 1); };
  audio.onended = () => {
    clearInterval(raf);
    if (cur + 1 < paras.length) setTimeout(() => { if (state === "playing") playPara(cur + 1); }, 300);
    else { state = "idle"; setActive(-1, -1); ui(); }
  };

  /* ---------- the word card ---------- */
  const dlg = $("card");
  let wordAudio = null, wraf = 0;
  const PAL = [["#e0f2fe", "#0369a1", "#b3dcf5"], ["#dcfce7", "#15803d", "#b4ebc6"], ["#fce7f3", "#be185d", "#f6c3dc"], ["#ede9fe", "#6d28d9", "#d2c6f6"]];

  function stopWord() {
    clearInterval(wraf);
    if (wordAudio) { wordAudio.pause(); wordAudio = null; }
    $("c-beats").querySelectorAll(".beat.lit").forEach((b) => b.classList.remove("lit"));
  }
  function openCard(key, shown) {
    if (state === "playing") $("pause").click();
    const w = D.words[key];
    const many = w.syl.length > 1;
    $("c-word").textContent = shown;
    const pic = $("c-pic"); pic.textContent = "";
    if (w.image) { const im = document.createElement("img"); im.src = w.image; im.alt = ""; pic.appendChild(im); }
    else pic.textContent = w.emoji || "💬";
    $("c-say").textContent = bn(w.syl.length) + "টি Syllable";
    $("c-legend").hidden = !many;
    $("c-mean").textContent = w.meaning;
    const box = $("c-beats"); box.textContent = "";
    w.syl.forEach((s, i) => {
      const pal = PAL[i % PAL.length], b = document.createElement("div");
      b.className = "beat" + (many && i === w.stress ? " stress" : "");
      b.style.setProperty("--bg", pal[0]); b.style.setProperty("--fg", pal[1]); b.style.setProperty("--sh", pal[2]);
      const en = document.createElement("span"); en.className = "en"; en.textContent = s;
      const bb = document.createElement("span"); bb.className = "bn"; bb.textContent = w.bn[i] || "";
      b.append(en, bb); box.appendChild(b);
    });
    dlg.dataset.key = key;
    if (!dlg.open) dlg.showModal();
    listen(key);
  }

  // Listen: the word at the same pace as the narration.
  function listen(key) {
    stopWord();
    wordAudio = new Audio(D.words[key].normal);
    wordAudio.play().catch(() => {});
  }

  // Slow: slower playback; each English syllable lights up exactly while it is being said.
  // The windows come from the real letter timings of THIS audio file, and we read the audio's own
  // clock (currentTime), so the light can never drift - even if the student pauses or taps again.
  function slow(key) {
    stopWord();
    // only the syllable blocks inside the card (the mascot is a different element)
    const w = D.words[key], blocks = [...$("c-beats").querySelectorAll(".beat")], wins = w.slow.syllables;
    const a = new Audio(w.slow.file);
    a.playbackRate = D.slowPlaybackRate; wordAudio = a;
    const tick = () => {
      if (wordAudio !== a) { clearInterval(wraf); return; }
      const t = a.currentTime;
      let lit = -1;
      for (let i = 0; i < wins.length; i++) { if (t >= wins[i][0] && t < wins[i][1]) { lit = i; break; } }
      blocks.forEach((b, i) => b.classList.toggle("lit", i === lit));
      if (a.ended) { clearInterval(wraf); blocks.forEach((b) => b.classList.remove("lit")); }
    };
    a.play().then(() => { clearInterval(wraf); wraf = setInterval(tick, POLL_MS); tick(); }).catch(() => {});
  }

  $("c-listen").onclick = () => listen(dlg.dataset.key);
  $("c-slow").onclick = () => slow(dlg.dataset.key);
  $("c-x").onclick = () => dlg.close();
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  dlg.addEventListener("close", stopWord);
  ui();
})();
