// Display fixes for names RAWG spells oddly. Add more here if you spot any.
const NAME_FIXES = {
  "mecha break": "Mecha Break",
  "Persona5: The Phantom X": "Persona 5: The Phantom X",
};

function displayName(name) {
  return NAME_FIXES[name] || name;
}

function scoreText(g) {
  if (g.metacritic) return `Metacritic ${g.metacritic}`;
  if (g.igdbCritic) return `IGDB critic ${g.igdbCritic}`;
  if (g.igdbUsers) return `IGDB overall ${g.igdbUsers}`;
  if (g.rawgRating) return `RAWG ${g.rawgRating}/5`;
  return "Not rated";
}

function fill(listId, games) {
  const ol = document.getElementById(listId);
  if (!ol) {
    console.error(`No element with id="${listId}" on this page`);
    return;
  }
  ol.innerHTML = "";

  games.forEach((g) => {
    const li = document.createElement("li");
    li.className = "py-2";

    const row = document.createElement("div");
    row.className = "flex justify-between gap-4";

    const name = document.createElement("span");
    name.className = "text-gray-50 font-bold";
    name.textContent = displayName(g.name);

    const meta = document.createElement("span");
    meta.className = "text-gray-300 text-right text-sm";

    const time = document.createElement("time");
    time.dateTime = g.released;
    time.textContent = new Date(g.released + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      year: "numeric",
    });

    meta.append(time, ` · ${scoreText(g)}`);

    if (g.peakPlayers) {
      meta.append(` · Peak ${g.peakPlayers.toLocaleString("en-US")}`);
    }

    row.append(name, meta);
    li.append(row);
    ol.append(li);
  });
}

fetch(new URL("games.json", document.currentScript.src))
  .then((r) => {
    if (!r.ok) throw new Error(`games.json returned ${r.status}. Is it in the same folder as index.html?`);
    return r.json();
  })
  .then((data) => {
    fill("paid-list", data.paid);
    fill("free-list", data.free);

    const hasPeaks = [...data.paid, ...data.free].some((g) => g.peakPlayers);
    const note = document.getElementById("collected");
    if (note) {
      note.textContent =
        "Data collected " + data.collected + " from RAWG and IGDB" + (hasPeaks ? " and SteamDB." : ".");
    }
  })
  .catch((err) => {
    console.error("Game data failed to load:", err);
    ["paid-list", "free-list"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = "<li class='py-2'>Game data failed to load. Check the browser console (F12).</li>";
    });
  });