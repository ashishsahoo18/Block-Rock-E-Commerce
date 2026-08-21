document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-primary-nav]');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.textContent = open ? '×' : '☰';
    });
  }

  const countdown = document.querySelector('[data-countdown]');
  if (countdown) {
    const end = Date.now() + (15 * 60 * 60 + 42 * 60 + 37) * 1000;
    const tick = () => {
      const seconds = Math.max(0, Math.floor((end - Date.now()) / 1000));
      const values = [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60];
      countdown.querySelectorAll('b').forEach((node, index) => { node.textContent = String(values[index]).padStart(2, '0'); });
    };
    tick(); setInterval(tick, 1000);
  }
});
