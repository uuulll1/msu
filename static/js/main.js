/*
 * Минимум JavaScript: меню-бургер, переключатель темы, закрытие уведомлений,
 * рендер формул KaTeX. Сайт полностью работает и без JS (кроме формул,
 * которые тогда показываются в исходном виде LaTeX).
 */
(function () {
  "use strict";

  var root = document.documentElement;

  /* --- Тема --- */
  function currentTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit) return explicit;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try {
        localStorage.setItem("theme", next);
      } catch (e) {
        /* игнорируем */
      }
    });
  });

  /* --- Полноэкранное меню --- */
  var burger = document.querySelector("[data-burger]");
  var panel = document.querySelector("[data-nav]");
  var headerEl = document.querySelector("[data-header]");
  if (burger && panel) {
    var setMenu = function (open) {
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      burger.setAttribute("aria-label", open ? "Закрыть меню" : "Открыть меню");
      panel.classList.toggle("is-open", open);
      document.body.classList.toggle("menu-open", open);
      if (headerEl) headerEl.classList.toggle("menu-is-open", open);
      if (open) {
        var field = panel.querySelector("input");
        if (field && window.innerWidth > 960) field.focus({ preventScroll: true });
      }
    };
    burger.addEventListener("click", function () {
      setMenu(burger.getAttribute("aria-expanded") !== "true");
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setMenu(false);
    });
    panel.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setMenu(false);
      });
    });
  }

  /* --- Закрытие меню пользователя по клику вне его --- */
  document.addEventListener("click", function (event) {
    document.querySelectorAll("details.user-menu[open]").forEach(function (menu) {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });

  /* --- Уведомления --- */
  document.querySelectorAll("[data-dismiss]").forEach(function (button) {
    button.addEventListener("click", function () {
      var alert = button.closest(".alert");
      if (alert) alert.remove();
    });
  });

  /* --- Шапка при прокрутке: становится непрозрачной, строка разделов сворачивается --- */
  var header = document.querySelector("[data-header]");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 40);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* --- Формулы KaTeX --- */
  function renderMath() {
    if (typeof window.renderMathInElement !== "function") return;
    document.querySelectorAll(".prose, .math-scope").forEach(function (element) {
      window.renderMathInElement(element, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\[", right: "\\]", display: true },
          { left: "\\(", right: "\\)", display: false },
          { left: "$", right: "$", display: false }
        ],
        throwOnError: false,
        strict: "ignore",
        trust: false /* запрещаем \href, \url и т.п. — безопасность */
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderMath);
  } else {
    renderMath();
  }
})();
