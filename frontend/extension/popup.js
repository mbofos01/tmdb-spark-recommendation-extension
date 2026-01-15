const btn = document.getElementById("connect");
const status = document.getElementById("status");

btn.onclick = async () => {
  status.innerText = "Redirecting to TMDb...";

  const res = await fetch("http://127.0.0.1:8000/api/request-token");
  const data = await res.json();

  const redirectUrl = encodeURIComponent(
    `http://127.0.0.1:8000/`
  );

  const tmdbUrl =
    `https://www.themoviedb.org/authenticate/${data.request_token}` +
    `?redirect_to=${redirectUrl}&request_token=${data.request_token}`;

  chrome.tabs.create({ url: tmdbUrl });
};
