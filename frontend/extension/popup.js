const connectBtn = document.getElementById("connect");
const table = document.getElementById("table");
const body = document.getElementById("body");

connectBtn.onclick = async () => {
  const res = await fetch("http://127.0.0.1:8000/api/request-token");
  const data = await res.json();

  const redirectUrl = encodeURIComponent(
    "http://127.0.0.1:5500/frontend/index.html"
  );

  const tmdbUrl =
    `https://www.themoviedb.org/authenticate/${data.request_token}` +
    `?redirect_to=${redirectUrl}`;

  chrome.tabs.create({ url: tmdbUrl });
};

// OPTIONAL: fetch ratings if session already exists
async function loadRatings() {
  const res = await fetch("http://127.0.0.1:8000/api/get-ratings");
  if (!res.ok) return;

  const data = await res.json();
  body.innerHTML = "";

  data.rated_movies.forEach(m => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${m.tmdbId}</td><td>${m.rating}</td>`;
    body.appendChild(tr);
  });

  table.style.display = "table";
}

loadRatings();
