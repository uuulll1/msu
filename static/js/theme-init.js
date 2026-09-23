/* Применяем сохранённую тему до отрисовки страницы (без «мигания»). */
(function () {
  try {
    var saved = localStorage.getItem("theme");
    if (saved === "dark" || saved === "light") {
      document.documentElement.setAttribute("data-theme", saved);
    }
  } catch (e) {
    /* localStorage может быть недоступен — тогда работает системная тема */
  }
})();
