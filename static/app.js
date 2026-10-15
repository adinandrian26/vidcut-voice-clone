/* Frontend Voice Clone: fetch API + SSE progres. Tanpa API key. */
const API = "";
const $ = (id) => document.getElementById(id);

$("go").addEventListener("click", async () => {
  $("err").textContent = "";
  const consent = $("consent").checked;
  if (!consent) { $("err").textContent = "Centang persetujuan pemilik suara dulu."; return; }
  const text = $("teks").value.trim();
  if (!text) { $("err").textContent = "Teks tidak boleh kosong."; return; }
  const yt = $("yt").value.trim();
  const file = $("file").files[0];
  if (!yt && !file) { $("err").textContent = "Sertakan link YouTube atau file audio."; return; }

  $("prog-card").hidden = false;
  $("player").hidden = true;
  $("dl-row").hidden = true;
  $("warn").textContent = "";
  setBar(2, "Membuat job...");

  let jobId;
  try {
    if (file) {
      const fd = new FormData();
      fd.append("text", text);
      fd.append("language", $("lang").value);
      fd.append("consent", "true");
      fd.append("upload", file);
      const r = await fetch(`${API}/api/jobs/upload`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(await errText(r));
      jobId = (await r.json()).id;
    } else {
      const r = await fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          youtube_url: yt,
          start_seconds: Number($("start").value) || 0,
          duration_seconds: Number($("dur").value) || 30,
          text, language: $("lang").value, consent: true,
        }),
      });
      if (!r.ok) throw new Error(await errText(r));
      jobId = (await r.json()).id;
    }
  } catch (e) { $("err").textContent = e.message; return; }

  const es = new EventSource(`${API}/api/jobs/${jobId}/events`);
  es.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    setBar(d.progress, d.stage_detail || d.status);
    if (d.warning) $("warn").textContent = "Perhatian: " + d.warning;
    if (d.status === "done") {
      es.close();
      $("player").src = `${API}/api/jobs/${jobId}/audio?format=wav`;
      $("player").hidden = false;
      $("dl-wav").href = `${API}/api/jobs/${jobId}/audio?format=wav`;
      $("dl-mp3").href = `${API}/api/jobs/${jobId}/audio?format=mp3`;
      $("dl-row").hidden = false;
    }
    if (d.status === "failed") {
      es.close();
      $("err").textContent = "Gagal: " + (d.error || "tidak diketahui");
    }
  };
  es.onerror = () => { es.close(); $("err").textContent = "Koneksi SSE terputus."; };

  $("del").onclick = async () => {
    await fetch(`${API}/api/jobs/${jobId}`, { method: "DELETE" });
    $("prog-card").hidden = true;
  };
});

function setBar(p, t) {
  $("bar").style.width = p + "%";
  $("stage").textContent = t;
}

async function errText(r) {
  try { return (await r.json()).detail || `Error ${r.status}`;
  } catch { return `Error ${r.status}`; }
}
