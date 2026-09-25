/*
 * Живой фон главного экрана: графики функций, бесконечно бегущие по координатной сетке.
 * Рисуется на <canvas>, без библиотек. Анимация ставится на паузу, когда главный экран
 * не виден или вкладка неактивна; при «уменьшении движения» в системе — статичный кадр.
 */
(function () {
  "use strict";

  var canvas = document.querySelector("[data-hero-graphs]");
  if (!canvas || !canvas.getContext) return;

  var ctx = canvas.getContext("2d");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var GOLD = "201, 162, 39";
  var WHITE = "255, 255, 255";
  var BLUE = "140, 175, 255";

  var width = 0;
  var height = 0;
  var dpr = 1;
  var running = false;
  var visible = true;
  var startTime = performance.now();
  var rafId = null;

  /*
   * Описание кривых. f(x, t) возвращает значение в «математических» единицах,
   * y0 — положение оси (доля высоты), amp — масштаб по вертикали (доля высоты),
   * scaleX — сколько пикселей в единице x, speed — скорость бегущей волны.
   */
  var curves = [
    {
      label: "y = sin(x − t)",
      color: GOLD, alpha: 0.85, width: 2.2, y0: 0.62, amp: 0.11, scaleX: 70, speed: 0.9,
      f: function (x, t) { return Math.sin(x - t); }
    },
    {
      label: "y = sin x + ⅓ sin 3x + ⅕ sin 5x + …",
      color: WHITE, alpha: 0.32, width: 1.3, y0: 0.72, amp: 0.09, scaleX: 55, speed: 0.55,
      f: function (x, t) {
        // Частичная сумма ряда Фурье прямоугольного сигнала
        var s = 0;
        for (var k = 1; k <= 9; k += 2) s += Math.sin(k * (x - t)) / k;
        return s;
      }
    },
    {
      label: "y = e^(−x²/8) cos 3x",
      color: BLUE, alpha: 0.45, width: 1.4, y0: 0.4, amp: 0.1, scaleX: 45, speed: 0.7,
      f: function (x, t) {
        // Волновой пакет, повторяющийся с периодом 20 по x (хвосты гауссианы ≈ 0, стыков не видно)
        var u = (((x - t) % 20) + 20) % 20 - 10;
        return Math.exp(-u * u / 8) * Math.cos(3 * u);
      }
    },
    {
      label: "y = sin(x)/x",
      color: WHITE, alpha: 0.22, width: 1.2, y0: 0.84, amp: 0.1, scaleX: 40, speed: 0.4,
      f: function (x, t) {
        var u = (((x - t) % 40) + 40) % 40 - 20;
        return u === 0 ? 1 : Math.sin(u * 1.6) / (u * 1.6) * 1.6;
      }
    },
    {
      label: "y = sin x · cos(x/7)",
      color: GOLD, alpha: 0.35, width: 1.2, y0: 0.26, amp: 0.07, scaleX: 60, speed: -0.5,
      f: function (x, t) { return Math.sin(x - t) * Math.cos((x + t) / 7); }
    }
  ];

  var box = canvas.parentElement;

  function resize() {
    // Размер берём у родителя (он растянут на весь главный экран) и задаём canvas явно
    // в пикселях — так одинаково ведут себя Safari, Chrome и Firefox
    var w = Math.round(box.clientWidth);
    var h = Math.round(box.clientHeight);
    if (w < 2 || h < 2) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (w === width && h === height && canvas.width === Math.round(w * dpr)) return;
    width = w;
    height = h;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!running) safeDraw(elapsed());
  }

  function safeDraw(t) {
    try {
      draw(t);
    } catch (e) {
      /* ошибка рисования не должна ломать страницу */
    }
  }

  function elapsed() {
    return (performance.now() - startTime) / 1000;
  }

  function drawCurve(curve, t) {
    var baseY = curve.y0 * height;
    var amp = curve.amp * height;
    var phase = t * curve.speed;
    var stepPx = 3;

    ctx.lineWidth = curve.width;
    ctx.lineJoin = "round";
    ctx.strokeStyle = "rgba(" + curve.color + ", " + curve.alpha + ")";
    ctx.beginPath();
    for (var px = -stepPx; px <= width + stepPx; px += stepPx) {
      var y = baseY - curve.f(px / curve.scaleX, phase) * amp;
      if (px === -stepPx) ctx.moveTo(px, y);
      else ctx.lineTo(px, y);
    }
    ctx.stroke();

    // Подпись с формулой справа, над кривой
    if (width > 640) {
      var labelX = width - 24;
      var labelY = baseY - curve.f(labelX / curve.scaleX, phase) * amp - 12;
      ctx.font = "italic 15px 'Oranienbaum', Georgia, serif";
      ctx.textAlign = "right";
      ctx.fillStyle = "rgba(" + curve.color + ", " + Math.min(curve.alpha + 0.1, 0.75) + ")";
      ctx.fillText(curve.label, labelX, Math.max(18, labelY));
    }
  }

  function drawLissajous(t) {
    // Фигура Лиссажу с медленно меняющимся сдвигом фаз — справа вверху
    var cx = width * 0.8;
    var cy = height * 0.3;
    var r = Math.min(width, height) * 0.17;
    if (width < 640) {
      cx = width * 0.78;
      r = width * 0.2;
    }
    var delta = t * 0.25;

    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(" + WHITE + ", 0.12)";
    ctx.beginPath();
    ctx.arc(cx, cy, r * 1.25, 0, Math.PI * 2);
    ctx.moveTo(cx - r * 1.45, cy);
    ctx.lineTo(cx + r * 1.45, cy);
    ctx.moveTo(cx, cy - r * 1.45);
    ctx.lineTo(cx, cy + r * 1.45);
    ctx.stroke();

    ctx.lineWidth = 1.4;
    ctx.strokeStyle = "rgba(" + GOLD + ", 0.55)";
    ctx.beginPath();
    for (var i = 0; i <= 400; i++) {
      var s = (i / 400) * Math.PI * 2;
      var x = cx + r * Math.sin(3 * s + delta);
      var y = cy + r * Math.sin(2 * s);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Бегущая точка по фигуре
    var p = t * 0.6;
    ctx.fillStyle = "rgba(" + GOLD + ", 0.95)";
    ctx.beginPath();
    ctx.arc(cx + r * Math.sin(3 * p + delta), cy + r * Math.sin(2 * p), 3.5, 0, Math.PI * 2);
    ctx.fill();
  }

  function draw(t) {
    ctx.clearRect(0, 0, width, height);
    drawLissajous(t);
    for (var i = 0; i < curves.length; i++) drawCurve(curves[i], t);
  }

  function frame() {
    if (!running) return;
    safeDraw(elapsed());
    rafId = window.requestAnimationFrame(frame);
  }

  function start() {
    if (running || reduceMotion || !visible || document.hidden) return;
    running = true;
    rafId = window.requestAnimationFrame(frame);
  }

  function stop() {
    running = false;
    if (rafId) window.cancelAnimationFrame(rafId);
    rafId = null;
  }

  resize();
  canvas.classList.add("is-ready");
  // Страховка: если при первом замере блок ещё не имел размера
  window.addEventListener("load", resize);
  window.addEventListener("resize", resize);
  // Высота главного экрана меняется и без resize окна (подгрузка шрифтов, перенос строк
  // заголовка), поэтому следим за размером самого canvas
  if ("ResizeObserver" in window) {
    new ResizeObserver(function () {
      resize();
    }).observe(box);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stop();
    else start();
  });

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      if (visible) start();
      else stop();
    }).observe(canvas);
  }

  // Когда шрифты загрузятся, перерисуем подписи правильным начертанием
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      if (!running) safeDraw(elapsed());
    });
  }

  start();
})();
