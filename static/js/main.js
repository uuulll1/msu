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

  /* --- Меню-бургер --- */
  var burger = document.querySelector("[data-burger]");
  var nav = document.querySelector("[data-nav]");
  if (burger && nav) {
    var closeMenu = function () {
      burger.setAttribute("aria-expanded", "false");
      burger.setAttribute("aria-label", "Открыть меню");
      nav.classList.remove("is-open");
      document.body.classList.remove("menu-open");
    };
    burger.addEventListener("click", function () {
      var isOpen = burger.getAttribute("aria-expanded") === "true";
      if (isOpen) {
        closeMenu();
      } else {
        // Панель меню начинается сразу под шапкой (над ней может быть полоса-дисклеймер)
        var headerEl = document.querySelector("[data-header]");
        if (headerEl) {
          nav.style.setProperty("--nav-top", headerEl.getBoundingClientRect().bottom + "px");
        }
        burger.setAttribute("aria-expanded", "true");
        burger.setAttribute("aria-label", "Закрыть меню");
        nav.classList.add("is-open");
        document.body.classList.add("menu-open");
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeMenu();
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 960) closeMenu();
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

  /* --- Тень у шапки при прокрутке --- */
  var header = document.querySelector("[data-header]");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
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
