// Highlight the week at the top of the reading area, below the sticky navigation.
(() => {
  const nav = document.querySelector('.week-nav');
  const weeks = [...document.querySelectorAll('section.week')];
  const links = [...document.querySelectorAll('.week-jumps a')];
  if (!nav || !weeks.length) return;

  let pending = false;
  const update = () => {
    pending = false;
    const height = nav.getBoundingClientRect().height;
    document.documentElement.style.setProperty('--nav-height', `${height}px`);
    const readingLine = height + 24;
    let current = null;
    for (const week of weeks) {
      if (week.getBoundingClientRect().top <= readingLine) current = week.id;
    }
    const lastWeek = weeks[weeks.length - 1];
    const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
    // A short final week cannot always scroll all the way to the reading line.
    if (atBottom && lastWeek.getBoundingClientRect().bottom > readingLine) current = lastWeek.id;
    // Clear the week highlight when the reader reaches the problem-set section.
    if (lastWeek.getBoundingClientRect().bottom <= readingLine || (atBottom && location.hash === '#psets')) current = null;
    for (const link of links) {
      if (link.hash === `#${current}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  };
  const scheduleUpdate = () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(update);
  };
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', scheduleUpdate);
  window.addEventListener('hashchange', scheduleUpdate);
  window.addEventListener('pageshow', scheduleUpdate);
  update();
})();
