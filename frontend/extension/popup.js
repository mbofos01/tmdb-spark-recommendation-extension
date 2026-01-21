const btn = document.getElementById("connect");
const status_block = document.getElementById("status");

btn.onclick = async () => {
  status_block.innerText = "Redirecting to TMDb...";
  status_block.classList.add("show");
  const res = await fetch("http://127.0.0.1:8000/api/request-token");
  const data = await res.json();

  const redirectUrl = encodeURIComponent(`http://127.0.0.1:3000/`);

  const tmdbUrl =
    `https://www.themoviedb.org/authenticate/${data.request_token}` +
    `?redirect_to=${redirectUrl}&request_token=${data.request_token}`;

  chrome.tabs.create({ url: tmdbUrl });
};
