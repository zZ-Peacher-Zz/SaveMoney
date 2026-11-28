(() => {
  const button = document.getElementById("musicToggle");
  const label = document.getElementById("musicLabel");
  const volume = document.getElementById("musicVolume");
  const status = document.getElementById("musicStatus");
  const trackSelect = document.getElementById("musicTrack");
  // Original pentatonic spring instrumentals, synthesized locally.
  const tracks = {
    spring: {name: "Sắc xuân sum vầy", beat: .30, score: [
      ["C",1],["D",.5],["E",.5],["G",1],["E",1],["D",1],["C",1],["A4",2],
      ["C",1],["E",1],["G",.5],["A",.5],["G",1],["E",1],["D",1],["C",2],
      ["G",1],["A",1],["C6",1],["A",.5],["G",.5],["E",1],["G",1],["D",2],
      ["E",1],["D",.5],["C",.5],["A4",1],["D",1],["C",3],[null,1]
    ]},
    apricot: {name: "Mai vàng trước ngõ", beat: .43, score: [
      ["E",2],["D",1],["C",1],["G4",2],["A4",1],["C",1],
      ["D",1.5],["E",.5],["G",2],["E",1],["D",1],["C",2],
      ["A4",1],["C",1],["D",2],["E",1],["G",1],["A",2],
      ["G",1.5],["E",.5],["D",1],["C",1],["A4",2],["C",3],[null,1]
    ]},
    fortune: {name: "Lì xì may mắn", beat: .25, score: [
      ["C",.5],["E",.5],["G",1],["G",.5],["A",.5],["G",1],
      ["E",.5],["D",.5],["C",1],["D",.5],["E",.5],["G",1],
      ["A",1],["G",.5],["E",.5],["D",1],["C",1],
      ["E",.5],["G",.5],["A",1],["C6",1],["A",1],
      ["G",.5],["E",.5],["D",1],["E",1],["C",2],[null,2]
    ]}
  };
  const frequencies = {C4:261.63,D4:293.66,E4:329.63,F4:349.23,G4:392,A4:440,B4:493.88,C:523.25,D:587.33,E:659.25,F:698.46,G:783.99,A:880,B:987.77,C6:1046.5};
  for (const [id, track] of Object.entries(tracks)) {
    trackSelect.add(new Option(track.name, id));
  }
  function selectedTrack() { return tracks[trackSelect.value]; }
  let context, master, timer, nextTime, position=0, playing=false, busy=false;
  const voices = new Set();
  function updateVolume() {
    if (master) master.gain.setTargetAtTime(Number(volume.value)/100*.22,context.currentTime,.04);
  }
  volume.addEventListener("input",updateVolume);
  function bell(frequency,when,duration) {
    for (const [ratio,strength] of [[1,.8],[2,.18],[3,.04]]) {
      const oscillator=context.createOscillator(), envelope=context.createGain();
      oscillator.type="triangle"; oscillator.frequency.value=frequency*ratio;
      envelope.gain.setValueAtTime(0,when);
      envelope.gain.linearRampToValueAtTime(strength,when+.008);
      envelope.gain.exponentialRampToValueAtTime(.0001,when+duration);
      oscillator.connect(envelope).connect(master);
      oscillator.start(when); oscillator.stop(when+duration+.02);
      voices.add(oscillator);
      oscillator.onended=()=>{voices.delete(oscillator);oscillator.disconnect();envelope.disconnect();};
    }
  }
  function schedule() {
    if (!playing) return;
    while (nextTime<context.currentTime+.25) {
      const {score, beat}=selectedTrack();
      const [note,beats]=score[position];
      if (note) bell(frequencies[note],nextTime,Math.min(beats*beat*1.4,1.6));
      nextTime+=beats*beat;position=(position+1)%score.length;
    }
    timer=setTimeout(schedule,80);
  }
  function clearSound() {
    clearTimeout(timer);
    for (const voice of voices) {try {voice.stop();} catch (_) {}}
    voices.clear();
  }
  function stop() {
    playing=false;clearSound();
    if (context) context.suspend().catch(()=>{});
    button.setAttribute("aria-pressed","false");
    label.textContent="B\u1eadt nh\u1ea1c T\u1ebft";
    status.textContent="\u0110\u00e3 t\u1eaft nh\u1ea1c.";
  }
  button.addEventListener("click",async()=>{
    if (busy) return;
    if (playing) {stop();return;}
    busy=true;button.disabled=true;trackSelect.disabled=true;
    try {
      const AudioContext=window.AudioContext||window.webkitAudioContext;
      if (!AudioContext) throw new Error("Unsupported audio");
      if (!context) {context=new AudioContext();master=context.createGain();master.connect(context.destination);updateVolume();}
      await context.resume();
      if (document.hidden) {stop();return;}
      playing=true;position=0;nextTime=context.currentTime+.08;schedule();
      button.setAttribute("aria-pressed","true");label.textContent="T\u1eaft nh\u1ea1c T\u1ebft";
      status.textContent=`\u0110ang ph\u00e1t ${selectedTrack().name}.`;
    } catch (_) {stop();status.textContent="Kh\u00f4ng th\u1ec3 ph\u00e1t nh\u1ea1c tr\u00ean tr\u00ecnh duy\u1ec7t n\u00e0y.";}
    finally {busy=false;button.disabled=false;trackSelect.disabled=false;}
  });
  trackSelect.addEventListener("change", () => {
    if (!playing) return;
    clearSound();position=0;nextTime=context.currentTime+.08;schedule();
    status.textContent=`\u0110ang ph\u00e1t ${selectedTrack().name}.`;
  });
  document.addEventListener("visibilitychange",()=>{if(document.hidden)stop();});
  window.addEventListener("pagehide",stop);
})();
