(function(global){
  'use strict';

  var AGENT_FACES = {
    jarvis: {
      calm: {
        browL: '58,76 90,78 88,86 58,84',
        browR: '110,68 142,70 142,78 110,76',
        eyeL: 'M58 95 Q75 90 92 95',
        eyeR: 'M108 94 Q125 84 142 94',
        coreL: {cx: 75, cy: 91, r: 3},
        coreR: {cx: 125, cy: 88, r: 3.5},
        mouth: 'M82 133 Q100 141 118 133'
      },
      curious: {
        browL: '58,66 90,68 88,78 58,76',
        browR: '110,66 142,68 142,78 110,76',
        eyeL: 'M58 94 Q75 82 92 94',
        eyeR: 'M108 94 Q125 82 142 94',
        coreL: {cx: 75, cy: 88, r: 3.5},
        coreR: {cx: 125, cy: 88, r: 3.5},
        mouth: 'M82 132 Q100 143 118 132'
      },
      stern: {
        browL: '56,70 92,78 88,88 56,84',
        browR: '144,70 108,78 112,88 144,84',
        eyeL: 'M58 95 Q75 92 92 95',
        eyeR: 'M108 95 Q125 92 142 95',
        coreL: {cx: 75, cy: 93, r: 2.6},
        coreR: {cx: 125, cy: 93, r: 2.6},
        mouth: 'M82 136 Q100 134 118 136'
      },
      menacing: {
        browL: '58,64 94,80 88,90 58,78',
        browR: '142,64 106,80 112,90 142,78',
        eyeL: 'M60 95 Q75 93.5 90 95',
        eyeR: 'M110 95 Q125 93.5 140 95',
        coreL: {cx: 75, cy: 94, r: 2.2},
        coreR: {cx: 125, cy: 94, r: 2.2},
        mouth: 'M82 140 Q100 132 118 140'
      },
      concerned: {
        browL: '60,70 88,74 86,84 60,82',
        browR: '140,70 112,74 114,84 140,82',
        eyeL: 'M58 95 Q75 91 92 95',
        eyeR: 'M108 95 Q125 91 142 95',
        coreL: {cx: 75, cy: 93, r: 2.8},
        coreR: {cx: 125, cy: 93, r: 2.8},
        mouth: 'M84 137 Q100 133 116 137'
      }
    },
    edith: {
      calm: {
        browL: '58,80 90,81 89,86 58,85',
        browR: '110,73 142,74 141,79 110,78',
        eyeL: 'M58 95 Q75 93 92 95',
        eyeR: 'M108 95 Q125 93 142 95',
        coreL: {cx: 75, cy: 94, r: 2.2},
        coreR: {cx: 125, cy: 94, r: 2.2},
        mouth: 'M82 134 Q100 135 118 134'
      },
      curious: {
        browL: '58,72 90,73 89,80 58,79',
        browR: '110,68 142,69 141,76 110,75',
        eyeL: 'M58 94 Q75 90 92 94',
        eyeR: 'M108 94 Q125 90 142 94',
        coreL: {cx: 75, cy: 92, r: 2.4},
        coreR: {cx: 125, cy: 92, r: 2.4},
        mouth: 'M82 133 Q100 136 118 133'
      },
      stern: {
        browL: '56,74 92,82 89,90 56,86',
        browR: '144,74 108,82 111,90 144,86',
        eyeL: 'M58 96 Q75 94.5 92 96',
        eyeR: 'M108 96 Q125 94.5 142 96',
        coreL: {cx: 75, cy: 95, r: 2},
        coreR: {cx: 125, cy: 95, r: 2},
        mouth: 'M82 137 Q100 136 118 137'
      },
      menacing: {
        browL: '58,70 94,84 89,92 58,82',
        browR: '142,70 106,84 111,92 142,82',
        eyeL: 'M60 96 Q75 95 90 96',
        eyeR: 'M110 96 Q125 95 140 96',
        coreL: {cx: 75, cy: 95.5, r: 1.8},
        coreR: {cx: 125, cy: 95.5, r: 1.8},
        mouth: 'M82 141 Q100 135 118 141'
      },
      concerned: {
        browL: '60,74 88,77 87,85 60,83',
        browR: '140,74 112,77 113,85 140,83',
        eyeL: 'M58 96 Q75 93.5 92 96',
        eyeR: 'M108 96 Q125 93.5 142 96',
        coreL: {cx: 75, cy: 95, r: 2.4},
        coreR: {cx: 125, cy: 95, r: 2.4},
        mouth: 'M84 138 Q100 136 116 138'
      }
    },
    friday: {
      calm: {
        browL: '58,70 90,73 88,82 58,79',
        browR: '110,60 142,63 142,72 110,68',
        eyeL: 'M56 96 Q75 86 94 96',
        eyeR: 'M106 95 Q125 80 144 95',
        coreL: {cx: 75, cy: 90, r: 4.2},
        coreR: {cx: 125, cy: 86, r: 4.6},
        mouth: 'M80 132 Q100 146 120 132'
      },
      curious: {
        browL: '58,60 90,63 88,74 58,71',
        browR: '110,58 142,61 142,72 110,68',
        eyeL: 'M56 95 Q75 78 94 95',
        eyeR: 'M106 95 Q125 78 144 95',
        coreL: {cx: 75, cy: 86, r: 4.5},
        coreR: {cx: 125, cy: 86, r: 4.5},
        mouth: 'M80 131 Q100 148 120 131'
      },
      stern: {
        browL: '54,66 92,74 88,86 54,82',
        browR: '146,66 108,74 112,86 146,82',
        eyeL: 'M56 96 Q75 90 94 96',
        eyeR: 'M106 96 Q125 90 144 96',
        coreL: {cx: 75, cy: 93, r: 3.2},
        coreR: {cx: 125, cy: 93, r: 3.2},
        mouth: 'M80 135 Q100 133 120 135'
      },
      menacing: {
        browL: '58,58 96,78 88,90 58,74',
        browR: '142,58 104,78 112,90 142,74',
        eyeL: 'M58 96 Q75 92 92 96',
        eyeR: 'M108 96 Q125 92 142 96',
        coreL: {cx: 75, cy: 94, r: 2.8},
        coreR: {cx: 125, cy: 94, r: 2.8},
        mouth: 'M80 140 Q100 130 120 140'
      },
      concerned: {
        browL: '58,68 88,72 86,84 58,80',
        browR: '142,68 112,72 114,84 142,80',
        eyeL: 'M56 96 Q75 89 94 96',
        eyeR: 'M106 96 Q125 89 144 96',
        coreL: {cx: 75, cy: 92, r: 3.4},
        coreR: {cx: 125, cy: 92, r: 3.4},
        mouth: 'M82 138 Q100 132 118 138'
      }
    }
  };

  var AGENT_COLORS = {
    jarvis: {
      browFill: 'rgba(255,190,60,0.16)', browStrokeL: 'rgba(255,205,90,0.3)', browStrokeR: 'rgba(255,220,130,0.4)',
      eyeStrokeL: 'rgba(255,210,110,0.8)', eyeStrokeR: 'rgba(255,225,140,0.9)',
      haloFill: 'rgba(255,205,90,0.22)', mouthStroke: 'rgba(255,205,90,0.55)', ambient: 'rgba(255,170,20,0.05)'
    },
    edith: {
      browFill: 'rgba(255,90,28,0.16)', browStrokeL: 'rgba(255,120,50,0.3)', browStrokeR: 'rgba(255,150,90,0.4)',
      eyeStrokeL: 'rgba(255,140,90,0.8)', eyeStrokeR: 'rgba(255,160,110,0.9)',
      haloFill: 'rgba(255,120,50,0.22)', mouthStroke: 'rgba(255,120,50,0.55)', ambient: 'rgba(255,60,0,0.05)'
    },
    friday: {
      browFill: 'rgba(240,80,200,0.16)', browStrokeL: 'rgba(245,100,210,0.3)', browStrokeR: 'rgba(248,130,222,0.4)',
      eyeStrokeL: 'rgba(245,110,215,0.8)', eyeStrokeR: 'rgba(248,140,225,0.9)',
      haloFill: 'rgba(245,100,210,0.22)', mouthStroke: 'rgba(245,100,210,0.55)', ambient: 'rgba(230,40,180,0.05)'
    }
  };

  var DEFAULT_EMOTION = 'calm';
  var MORPH_MS = 350;
  var idCounter = 0;

  var CSS = (
    '.jarvis-face-mount{display:flex;}' +
    '.jarvis-face{width:100%;height:100%;overflow:visible;}' +
    '.jf-ambient{animation:jf-glow 5s ease-in-out infinite;transform-origin:center;transform-box:fill-box;}' +
    '.jf-coreL,.jf-coreL-halo,.jf-coreR,.jf-coreR-halo{' +
      'transform-origin:center;transform-box:fill-box;}' +
    '.jf-coreL,.jf-coreL-halo{animation:jf-breathe 2.2s ease-in-out infinite;}' +
    '.jf-coreR,.jf-coreR-halo{animation:jf-breathe 2.2s ease-in-out infinite .1s;}' +
    '.jf-eyeL,.jf-eyeR{animation:jf-blink 6s ease-in-out infinite;transform-origin:center;transform-box:fill-box;}' +
    '.jf-eyeR{animation-delay:.08s;}' +
    '@keyframes jf-glow{0%,100%{opacity:.05;transform:scale(1);}50%{opacity:.16;transform:scale(1.04);}}' +
    '@keyframes jf-breathe{0%,100%{opacity:.85;}50%{opacity:1;}}' +
    '@keyframes jf-blink{0%,90%,100%{transform:scaleY(1);}94%{transform:scaleY(.15);}}' +
    '.jarvis-face[data-state="listening"] .jf-coreL,' +
    '.jarvis-face[data-state="listening"] .jf-coreR{animation-duration:1s;}' +
    '.jarvis-face[data-state="thinking"] .jf-ambient{animation:jf-thinking-pulse 1s ease-in-out infinite;}' +
    '@keyframes jf-thinking-pulse{0%,100%{opacity:.4;}50%{opacity:.9;}}' +
    '.jarvis-face[data-agent="friday"] .jf-eyeL,.jarvis-face[data-agent="friday"] .jf-eyeR{animation-duration:4.5s;}' +
    '.jarvis-face[data-agent="friday"] .jf-coreL,.jarvis-face[data-agent="friday"] .jf-coreL-halo,' +
    '.jarvis-face[data-agent="friday"] .jf-coreR,.jarvis-face[data-agent="friday"] .jf-coreR-halo{animation-duration:1.8s;}'
  );

  function injectCssOnce(){
    if (document.getElementById('jarvis-face-css')) return;
    var style = document.createElement('style');
    style.id = 'jarvis-face-css';
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function lerp(a, b, t){ return a + (b - a) * t; }

  /* Every tween (emotion morph, agent switch, chrome accent color) is driven
     by one of these loops. Calling the SAME returned `run` again cancels
     whatever it was previously animating — needed once switches take 600ms,
     long enough for a user to double-click through one mid-flight. */
  function easeInOutCubic(t){
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function makeCanceledRAFLoop(){
    var gen = 0;
    return function run(duration, onStep, onDone){
      gen++;
      var myGen = gen;
      var start = null;
      function frame(ts){
        if (myGen !== gen) return;
        if (start === null) start = ts;
        var raw = duration <= 0 ? 1 : Math.min(1, (ts - start) / duration);
        onStep(easeInOutCubic(raw));
        if (raw < 1) requestAnimationFrame(frame);
        else if (onDone) onDone();
      }
      requestAnimationFrame(frame);
    };
  }

  function frameGroup(id, agent, ambientColor, markup){
    return '<g class="jf-frame jf-frame-' + id + '" opacity="' + (id === agent ? 1 : 0) + '">' +
      '<ellipse class="jf-ambient" cx="100" cy="94" rx="100" ry="105" fill="' + ambientColor + '"/>' +
      '<ellipse cx="100" cy="94" rx="65" ry="68" fill="' + ambientColor + '"/>' +
      markup +
      '</g>';
  }

  function buildFrames(agent){
    var edith = frameGroup('edith', agent, AGENT_COLORS.edith.ambient,
      '<rect x="28" y="24" width="144" height="152" fill="rgba(16,6,2,.94)" stroke="rgba(255,90,28,.85)" stroke-width="3"/>' +
      '<path d="M28,40 L28,24 L44,24" fill="none" stroke="rgba(255,150,90,.6)" stroke-width="2"/>' +
      '<path d="M172,40 L172,24 L156,24" fill="none" stroke="rgba(255,150,90,.6)" stroke-width="2"/>' +
      '<path d="M28,160 L28,176 L44,176" fill="none" stroke="rgba(255,150,90,.6)" stroke-width="2"/>' +
      '<path d="M172,160 L172,176 L156,176" fill="none" stroke="rgba(255,150,90,.6)" stroke-width="2"/>' +
      '<line x1="30" y1="98" x2="170" y2="98" stroke="rgba(255,90,28,.18)" stroke-width="1"/>');
    var jarvis = frameGroup('jarvis', agent, AGENT_COLORS.jarvis.ambient,
      '<rect x="30" y="26" width="140" height="148" fill="rgba(16,6,2,.94)" stroke="rgba(255,205,90,.7)" stroke-width="2"/>' +
      '<line x1="32" y1="28" x2="32" y2="172" stroke="rgba(255,225,190,.4)" stroke-width="1.5"/>' +
      '<line x1="32" y1="28" x2="168" y2="28" stroke="rgba(255,225,190,.28)" stroke-width="1"/>' +
      '<line x1="30" y1="66" x2="170" y2="66" stroke="rgba(255,205,90,.22)" stroke-width="1"/>' +
      '<line x1="30" y1="150" x2="170" y2="150" stroke="rgba(255,205,90,.22)" stroke-width="1"/>' +
      '<circle cx="38" cy="34" r="2" fill="rgba(255,205,90,.7)"/>' +
      '<circle cx="162" cy="34" r="2" fill="rgba(255,205,90,.7)"/>' +
      '<circle cx="38" cy="166" r="2" fill="rgba(255,205,90,.7)"/>' +
      '<circle cx="162" cy="166" r="2" fill="rgba(255,205,90,.7)"/>');
    var friday = frameGroup('friday', agent, AGENT_COLORS.friday.ambient,
      '<rect x="30" y="26" width="140" height="148" rx="10" fill="rgba(16,6,2,.94)" stroke="rgba(245,100,210,.65)" stroke-width="2"/>' +
      '<circle cx="38" cy="34" r="3" fill="rgba(245,130,222,.8)"/>' +
      '<circle cx="162" cy="166" r="3" fill="rgba(245,130,222,.8)"/>' +
      '<line x1="150" y1="30" x2="168" y2="48" stroke="rgba(248,140,225,.5)" stroke-width="1.5"/>' +
      '<line x1="30" y1="66" x2="170" y2="66" stroke="rgba(245,100,210,.2)" stroke-width="1"/>');
    return edith + jarvis + friday;
  }

  function buildSvg(agent){
    var d = AGENT_FACES[agent][DEFAULT_EMOTION];
    var c = AGENT_COLORS[agent];
    return (
      '<svg class="jarvis-face" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" data-state="idle" data-agent="' + agent + '">' +
      buildFrames(agent) +
      '<polygon class="jf-browL" points="' + d.browL + '" fill="' + c.browFill + '" stroke="' + c.browStrokeL + '" stroke-width="1"/>' +
      '<polygon class="jf-browR" points="' + d.browR + '" fill="' + c.browFill + '" stroke="' + c.browStrokeR + '" stroke-width="1"/>' +
      '<g class="jf-eyeL">' +
        '<path class="jf-eyeL-path" d="' + d.eyeL + '" fill="none" stroke="' + c.eyeStrokeL + '" stroke-width="6" stroke-linecap="round"/>' +
        '<circle class="jf-coreL-halo" cx="' + d.coreL.cx + '" cy="' + d.coreL.cy + '" r="' + (d.coreL.r * 2.4) + '" fill="' + c.haloFill + '"/>' +
        '<circle class="jf-coreL" cx="' + d.coreL.cx + '" cy="' + d.coreL.cy + '" r="' + d.coreL.r + '" fill="rgba(255,224,205,.95)"/>' +
      '</g>' +
      '<g class="jf-eyeR">' +
        '<path class="jf-eyeR-path" d="' + d.eyeR + '" fill="none" stroke="' + c.eyeStrokeR + '" stroke-width="7" stroke-linecap="round"/>' +
        '<circle class="jf-coreR-halo" cx="' + d.coreR.cx + '" cy="' + d.coreR.cy + '" r="' + (d.coreR.r * 2.4) + '" fill="' + c.haloFill + '"/>' +
        '<circle class="jf-coreR" cx="' + d.coreR.cx + '" cy="' + d.coreR.cy + '" r="' + d.coreR.r + '" fill="rgba(255,224,205,.95)"/>' +
      '</g>' +
      '<path class="jf-mouth" d="' + d.mouth + '" fill="none" stroke="' + c.mouthStroke + '" stroke-width="2.5" stroke-linecap="round"/>' +
      '</svg>'
    );
  }

  function JarvisFaceInstance(containerEl, agent){
    idCounter++;
    this.agent = AGENT_FACES[agent] ? agent : 'jarvis';
    containerEl.innerHTML = buildSvg(this.agent);
    containerEl.classList.add('jarvis-face-mount');
    this.root = containerEl.querySelector('svg');
    this.browL = containerEl.querySelector('.jf-browL');
    this.browR = containerEl.querySelector('.jf-browR');
    this.eyeLPath = containerEl.querySelector('.jf-eyeL-path');
    this.eyeRPath = containerEl.querySelector('.jf-eyeR-path');
    this.coreL = containerEl.querySelector('.jf-coreL');
    this.coreR = containerEl.querySelector('.jf-coreR');
    this.coreLHalo = containerEl.querySelector('.jf-coreL-halo');
    this.coreRHalo = containerEl.querySelector('.jf-coreR-halo');
    this.mouth = containerEl.querySelector('.jf-mouth');
    this.frames = {
      edith: containerEl.querySelector('.jf-frame-edith'),
      jarvis: containerEl.querySelector('.jf-frame-jarvis'),
      friday: containerEl.querySelector('.jf-frame-friday')
    };
    this.emotion = DEFAULT_EMOTION;
    this._runRAF = makeCanceledRAFLoop();
  }

  /* Parsing each shape/color string's numbers via regex is done ONCE here,
     not per rAF frame — with ~26 tasks across a ~1400ms switch, re-parsing
     on every frame was measurable per-frame cost on the Pi's software
     renderer and made the morph look stepped rather than fluid. */
  JarvisFaceInstance.prototype._applyTasks = function(tasks, duration){
    for (var i = 0; i < tasks.length; i++){
      var task = tasks[i];
      if (task.shape){
        task._fromNums = task.from.match(/-?\d+\.?\d*/g).map(Number);
        task._toNums = task.to.match(/-?\d+\.?\d*/g).map(Number);
        task._parts = task.to.split(/-?\d+\.?\d*/);
      }
    }
    this._runRAF(duration, function(t){
      for (var i = 0; i < tasks.length; i++){
        var task = tasks[i];
        var val;
        if (task.shape){
          val = task._parts[0];
          for (var j = 0; j < task._toNums.length; j++){
            val += lerp(task._fromNums[j], task._toNums[j], t).toFixed(2) + task._parts[j + 1];
          }
        } else {
          val = lerp(task.from, task.to, t).toFixed(2);
        }
        task.el.setAttribute(task.attr, val);
      }
    });
  };

  JarvisFaceInstance.prototype.setEmotion = function(name){
    var preset = AGENT_FACES[this.agent][name] ? name : DEFAULT_EMOTION;
    var to = AGENT_FACES[this.agent][preset];
    var from = AGENT_FACES[this.agent][this.emotion] || AGENT_FACES[this.agent][DEFAULT_EMOTION];
    this._applyTasks([
      {el: this.browL, attr: 'points', from: from.browL, to: to.browL, shape: true},
      {el: this.browR, attr: 'points', from: from.browR, to: to.browR, shape: true},
      {el: this.eyeLPath, attr: 'd', from: from.eyeL, to: to.eyeL, shape: true},
      {el: this.eyeRPath, attr: 'd', from: from.eyeR, to: to.eyeR, shape: true},
      {el: this.mouth, attr: 'd', from: from.mouth, to: to.mouth, shape: true},
      {el: this.coreL, attr: 'cx', from: from.coreL.cx, to: to.coreL.cx},
      {el: this.coreL, attr: 'cy', from: from.coreL.cy, to: to.coreL.cy},
      {el: this.coreL, attr: 'r', from: from.coreL.r, to: to.coreL.r},
      {el: this.coreLHalo, attr: 'cx', from: from.coreL.cx, to: to.coreL.cx},
      {el: this.coreLHalo, attr: 'cy', from: from.coreL.cy, to: to.coreL.cy},
      {el: this.coreLHalo, attr: 'r', from: from.coreL.r * 2.4, to: to.coreL.r * 2.4},
      {el: this.coreR, attr: 'cx', from: from.coreR.cx, to: to.coreR.cx},
      {el: this.coreR, attr: 'cy', from: from.coreR.cy, to: to.coreR.cy},
      {el: this.coreR, attr: 'r', from: from.coreR.r, to: to.coreR.r},
      {el: this.coreRHalo, attr: 'cx', from: from.coreR.cx, to: to.coreR.cx},
      {el: this.coreRHalo, attr: 'cy', from: from.coreR.cy, to: to.coreR.cy},
      {el: this.coreRHalo, attr: 'r', from: from.coreR.r * 2.4, to: to.coreR.r * 2.4}
    ], MORPH_MS);
    this.emotion = preset;
  };

  var SWITCH_MS = 1400;

  JarvisFaceInstance.prototype.setAgent = function(id, opts){
    opts = opts || {};
    var target = AGENT_FACES[id] ? id : 'jarvis';
    var fromShape = AGENT_FACES[this.agent][this.emotion] || AGENT_FACES[this.agent][DEFAULT_EMOTION];
    var toShape = AGENT_FACES[target][DEFAULT_EMOTION];
    var fromColor = AGENT_COLORS[this.agent];
    var toColor = AGENT_COLORS[target];
    var tasks = [
      {el: this.browL, attr: 'points', from: fromShape.browL, to: toShape.browL, shape: true},
      {el: this.browR, attr: 'points', from: fromShape.browR, to: toShape.browR, shape: true},
      {el: this.eyeLPath, attr: 'd', from: fromShape.eyeL, to: toShape.eyeL, shape: true},
      {el: this.eyeRPath, attr: 'd', from: fromShape.eyeR, to: toShape.eyeR, shape: true},
      {el: this.mouth, attr: 'd', from: fromShape.mouth, to: toShape.mouth, shape: true},
      {el: this.coreL, attr: 'cx', from: fromShape.coreL.cx, to: toShape.coreL.cx},
      {el: this.coreL, attr: 'cy', from: fromShape.coreL.cy, to: toShape.coreL.cy},
      {el: this.coreL, attr: 'r', from: fromShape.coreL.r, to: toShape.coreL.r},
      {el: this.coreLHalo, attr: 'cx', from: fromShape.coreL.cx, to: toShape.coreL.cx},
      {el: this.coreLHalo, attr: 'cy', from: fromShape.coreL.cy, to: toShape.coreL.cy},
      {el: this.coreLHalo, attr: 'r', from: fromShape.coreL.r * 2.4, to: toShape.coreL.r * 2.4},
      {el: this.coreR, attr: 'cx', from: fromShape.coreR.cx, to: toShape.coreR.cx},
      {el: this.coreR, attr: 'cy', from: fromShape.coreR.cy, to: toShape.coreR.cy},
      {el: this.coreR, attr: 'r', from: fromShape.coreR.r, to: toShape.coreR.r},
      {el: this.coreRHalo, attr: 'cx', from: fromShape.coreR.cx, to: toShape.coreR.cx},
      {el: this.coreRHalo, attr: 'cy', from: fromShape.coreR.cy, to: toShape.coreR.cy},
      {el: this.coreRHalo, attr: 'r', from: fromShape.coreR.r * 2.4, to: toShape.coreR.r * 2.4},
      {el: this.browL, attr: 'fill', from: fromColor.browFill, to: toColor.browFill, shape: true},
      {el: this.browR, attr: 'fill', from: fromColor.browFill, to: toColor.browFill, shape: true},
      {el: this.browL, attr: 'stroke', from: fromColor.browStrokeL, to: toColor.browStrokeL, shape: true},
      {el: this.browR, attr: 'stroke', from: fromColor.browStrokeR, to: toColor.browStrokeR, shape: true},
      {el: this.eyeLPath, attr: 'stroke', from: fromColor.eyeStrokeL, to: toColor.eyeStrokeL, shape: true},
      {el: this.eyeRPath, attr: 'stroke', from: fromColor.eyeStrokeR, to: toColor.eyeStrokeR, shape: true},
      {el: this.coreLHalo, attr: 'fill', from: fromColor.haloFill, to: toColor.haloFill, shape: true},
      {el: this.coreRHalo, attr: 'fill', from: fromColor.haloFill, to: toColor.haloFill, shape: true},
      {el: this.mouth, attr: 'stroke', from: fromColor.mouthStroke, to: toColor.mouthStroke, shape: true}
    ];
    var frames = this.frames;
    Object.keys(frames).forEach(function(fid){
      var el = frames[fid];
      var from = parseFloat(el.getAttribute('opacity'));
      if (isNaN(from)) from = 0;
      tasks.push({el: el, attr: 'opacity', from: from, to: fid === target ? 1 : 0});
    });
    this.root.setAttribute('data-agent', target);
    if (opts.instant){
      tasks.forEach(function(task){
        task.el.setAttribute(task.attr, task.shape ? task.to : (+task.to).toFixed(2));
      });
    } else {
      this._applyTasks(tasks, SWITCH_MS);
    }
    this.agent = target;
    this.emotion = DEFAULT_EMOTION;
  };

  JarvisFaceInstance.prototype.setState = function(name){
    this.root.setAttribute('data-state', name);
  };

  /* nx, ny: normalized offset toward the cursor, each clamped to [-1, 1].
     Lets the eyes track the pointer so the face reads as watching you
     rather than looping a canned idle animation. */
  JarvisFaceInstance.prototype.lookAt = function(nx, ny){
    var pupil = 10, socket = 3.5;
    var tp = 'translate(' + (nx * pupil).toFixed(2) + 'px,' + (ny * pupil).toFixed(2) + 'px)';
    var ts = 'translate(' + (nx * socket).toFixed(2) + 'px,' + (ny * socket).toFixed(2) + 'px)';
    this.coreL.style.transform = tp;
    this.coreLHalo.style.transform = tp;
    this.coreR.style.transform = tp;
    this.coreRHalo.style.transform = tp;
    this.eyeLPath.style.transform = ts;
    this.eyeRPath.style.transform = ts;
  };

  global.JarvisFace = {
    mount: function(containerEl, opts){
      injectCssOnce();
      return new JarvisFaceInstance(containerEl, (opts && opts.agent) || 'jarvis');
    },
    tween: makeCanceledRAFLoop(),
    SWITCH_MS: SWITCH_MS,
    EMOTIONS: Object.keys(AGENT_FACES.jarvis)
  };
})(window);
