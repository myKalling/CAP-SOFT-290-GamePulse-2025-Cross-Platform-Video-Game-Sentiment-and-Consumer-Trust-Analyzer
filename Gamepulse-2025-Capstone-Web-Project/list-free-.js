const RAWG_KEY = "";
const url =
  `https://api.rawg.io/api/games?key=${'b04d9624d2dc482a8f6abec09aa08957'}` +
  `&dates=2025-01-01,2025-12-31&ordering=-added&exclude_additions=true` +
  `&tags=free-to-play&page_size=40&page=2`;

fetch(url)
  .then((r) => r.json())
  .then((d) => {
    d.results.forEach((g) => console.log(`${g.name} | ${g.released} | added ${g.added}`));
  });